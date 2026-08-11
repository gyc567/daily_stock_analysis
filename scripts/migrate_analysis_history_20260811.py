#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrate analysis_history table for 2026-08-11 schema (long-term research columns).

Background
----------
The AnalysisHistory SQLAlchemy model (`src/storage.py:285`) was extended with
five new Text columns to persist the long-term research framework output:

  - research_framework
  - bayesian_framework
  - supply_chain
  - value_scenarios
  - investment_conclusion

Existing SQLite databases created before this change break the home page
sidebar with HTTP 500:

  GET /api/v1/history/stocks
  sqlite3.OperationalError: no such column: analysis_history.research_framework

The earlier migration `migrate_analysis_history_20250625.py` predates these
columns, so they were never added. This script adds the missing columns
idempotently using the same approach (PRAGMA table_info + ALTER TABLE).

Usage
-----
    python scripts/migrate_analysis_history_20260811.py

The script is safe to run multiple times; it skips columns that already
exist. After running, restart the backend so SQLAlchemy re-reads the schema.
"""

import os
import sqlite3
import sys
from pathlib import Path

MISSING_COLUMNS: dict[str, str] = {
    "research_framework": "TEXT",
    "bayesian_framework": "TEXT",
    "supply_chain": "TEXT",
    "value_scenarios": "TEXT",
    "investment_conclusion": "TEXT",
}


def get_db_path() -> Path:
    """Resolve the SQLite database path used by the application."""
    db_path = Path(__file__).parent.parent / "data" / "stock_analysis.db"
    env_db = os.environ.get("DATABASE_PATH")
    if env_db:
        db_path = Path(env_db)
    return db_path


def migrate(conn: sqlite3.Connection) -> int:
    """Add missing long-term-research columns. Returns count of columns added."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(analysis_history)")
    existing = {row[1] for row in cursor.fetchall()}

    added = 0
    for column, dtype in MISSING_COLUMNS.items():
        if column in existing:
            print(f"[SKIP] analysis_history.{column} already exists")
            continue
        cursor.execute(
            f"ALTER TABLE analysis_history ADD COLUMN {column} {dtype}"
        )
        print(f"[ADD]  analysis_history.{column} {dtype}")
        added += 1
    conn.commit()
    return added


def main() -> int:
    db_path = get_db_path()
    if not db_path.exists():
        print(f"[ERROR] database not found: {db_path}")
        return 1

    print(f"[INFO] using database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    try:
        added = migrate(conn)
    finally:
        conn.close()

    if added == 0:
        print("[OK] schema already up to date, nothing to do")
    else:
        print(f"[OK] added {added} column(s); restart the backend to pick up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
