#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrate fundamental_snapshot table to add as_of_date column.

Why:
    The staleness detector in ``data_provider.base._detect_payload_staleness``
    scans text inside ``payload`` for a 4-digit year. The fundamental data
    providers (AkShare, iFinD MCP, Tushare) all report the actual period the
    figures are anchored to (e.g. ``2025-09-30`` for a Q3 report). Storing
    that date in a first-class column lets the staleness check read it
    directly instead of guessing from a possibly-truncated text snippet, and
    gives users a clear "as-of" stamp on every snapshot.

What this script does:
    1. Adds ``as_of_date VARCHAR(10)`` to ``fundamental_snapshot`` (idempotent
       via ``PRAGMA table_info``).
    2. Creates an index on the new column to keep range queries fast.
    3. Backfills ``as_of_date`` for existing rows by scanning the
       ``payload`` JSON for the most recent 4-digit year appearing in any
       block's ``data`` field. Falls back to ``NULL`` when no year is found.

Usage:
    python scripts/migrate_fundamental_snapshot_as_of_20260708.py
    DATABASE_PATH=/path/to/stock_analysis.db python scripts/migrate_fundamental_snapshot_as_of_20260708.py
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional


def get_db_path() -> Path:
    """Resolve the SQLite database path used by the application."""
    db_path = Path(__file__).parent.parent / "data" / "stock_analysis.db"
    env_db = os.environ.get("DATABASE_PATH")
    if env_db:
        db_path = Path(env_db)
    return db_path


_YEAR_PATTERN = re.compile(r"(?<![0-9])(20[12]\d)(?![0-9])")


def _scan_latest_year(payload: Any) -> Optional[int]:
    """Return the largest 4-digit year (2010-2029) appearing in any string
    nested inside ``payload``. Returns None when no year is found.
    """
    latest: Optional[int] = None
    if isinstance(payload, str):
        for match in _YEAR_PATTERN.finditer(payload):
            year = int(match.group(1))
            if latest is None or year > latest:
                latest = year
        return latest
    if isinstance(payload, dict):
        for value in payload.values():
            candidate = _scan_latest_year(value)
            if candidate is not None and (latest is None or candidate > latest):
                latest = candidate
        return latest
    if isinstance(payload, (list, tuple, set)):
        for value in payload:
            candidate = _scan_latest_year(value)
            if candidate is not None and (latest is None or candidate > latest):
                latest = candidate
        return latest
    return latest


def _infer_block_year(block: Any) -> Optional[int]:
    """The block's reported year is the most recent year in the block's
    ``data`` field. Empty data falls back to scanning the whole block.
    """
    if not isinstance(block, dict):
        return None
    data = block.get("data")
    if isinstance(data, dict) and data:
        year = _scan_latest_year(data)
        if year is not None:
            return year
    return _scan_latest_year(block)


def derive_as_of_date(payload_text: str) -> Optional[str]:
    """Return ``YYYY-MM-DD`` for the payload's most recent year.

    Annual reports are anchored to ``YYYY-12-31``; interim quarters to
    ``YYYY-03-31`` / ``YYYY-06-30`` / ``YYYY-09-30``. Heuristic: prefer the
    latest year present in the growth / earnings / valuation / institution
    blocks; when no year is found at all, return ``None``.
    """
    try:
        payload = json.loads(payload_text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    # Prefer the earnings / growth blocks as they carry the reporting
    # period most explicitly. Fall back to valuation / institution.
    for block_name in ("earnings", "growth", "institution", "valuation"):
        year = _infer_block_year(payload.get(block_name))
        if year is not None:
            return f"{year}-12-31"
    return None


def migrate_add_column(conn: sqlite3.Connection) -> int:
    """Add ``as_of_date`` to ``fundamental_snapshot`` if missing.

    Returns the number of columns added (0 or 1).
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(fundamental_snapshot)")
    existing = {row[1] for row in cursor.fetchall()}
    if "as_of_date" in existing:
        print("[SKIP] fundamental_snapshot.as_of_date already exists")
        return 0
    cursor.execute("ALTER TABLE fundamental_snapshot ADD COLUMN as_of_date VARCHAR(10)")
    conn.commit()
    print("[ADD]  fundamental_snapshot.as_of_date VARCHAR(10)")
    return 1


def migrate_add_index(conn: sqlite3.Connection) -> None:
    """Create the as_of_date index if it does not exist."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='index' AND name='ix_fundamental_snapshot_as_of'"
    )
    if cursor.fetchone():
        print("[SKIP] ix_fundamental_snapshot_as_of already exists")
        return
    cursor.execute(
        "CREATE INDEX ix_fundamental_snapshot_as_of "
        "ON fundamental_snapshot (as_of_date)"
    )
    conn.commit()
    print("[ADD]  ix_fundamental_snapshot_as_of")


def migrate_backfill(conn: sqlite3.Connection) -> int:
    """Backfill ``as_of_date`` for rows that have NULL.

    Returns the number of rows updated.

    Strategy:
        1. Try to derive from the payload's text (forecast_summary,
           quick_report_summary, period tokens in source_chain, ...).
        2. If that fails, fall back to ``created_at`` as a coarse but
           truthful upper bound: the snapshot cannot possibly be anchored
           to data that was not yet disclosed at write time. Annual
           reports filed in March/April anchor the prior full year; we
           therefore tag the row with the prior ``YYYY-12-31`` when
           ``created_at`` is between January and April of year Y.

           We deliberately avoid using ``created_at.year-12-31``
           verbatim: a snapshot written in 2026-07 about a stock whose
           2025 annual report was already filed in 2026-03 should be
           anchored to 2025-12-31, not 2026-12-31.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, payload, created_at FROM fundamental_snapshot "
        "WHERE as_of_date IS NULL OR as_of_date = ''"
    )
    rows = cursor.fetchall()
    if not rows:
        print("[SKIP] no NULL as_of_date rows to backfill")
        return 0

    updates: list[tuple[str, int]] = []
    for row_id, payload_text, created_at in rows:
        as_of = derive_as_of_date(payload_text or "")
        if as_of is None:
            as_of = _derive_from_created_at(created_at)
        if as_of is None:
            continue
        updates.append((as_of, row_id))

    if not updates:
        print("[SKIP] no derivable as_of_date from existing payloads")
        return 0

    cursor.executemany(
        "UPDATE fundamental_snapshot SET as_of_date = ? WHERE id = ?",
        updates,
    )
    conn.commit()
    print(f"[BACKFILL] updated {len(updates)} rows")
    return len(updates)


def _derive_from_created_at(created_at: Any) -> Optional[str]:
    """Coarse fallback: anchor the snapshot to the most recent annual
    report that could reasonably have been filed by ``created_at``.

    Rules (A-share disclosure calendar; conservative):
        - January-April: prior full year (annual report window).
        - May onward:    prior full year (we cannot distinguish between
                         the just-filed annual and the upcoming Q1/Q2/Q3
                         without further signals; we use the prior year
                         because AkShare's forecast/quick report data
                         we backfill from is also tied to the prior
                         year).
    """
    if not created_at:
        return None
    text = str(created_at)
    # Accept both 'YYYY-MM-DD ...' and 'YYYY-MM-DDTHH:MM:SS...'
    if len(text) < 4 or not text[:4].isdigit():
        return None
    try:
        year = int(text[:4])
    except ValueError:
        return None
    return f"{year - 1}-12-31"


def main() -> int:
    db_path = get_db_path()
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        return 1

    print(f"[INFO] Migrating database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    try:
        migrate_add_column(conn)
        migrate_add_index(conn)
        migrate_backfill(conn)
    finally:
        conn.close()

    print("[DONE] Migration completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
