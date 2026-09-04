#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI runner for the midterm trend compass (P1).

Usage:
    python scripts/compass_print.py 600519
    python scripts/compass_print.py 600519 --lang en
    python scripts/compass_print.py sh000300 --subject-type index
    python scripts/compass_print.py 600519 --offline path/to/daily.csv

P1 scope: single stock/ETF/index, no notification, no Web, no DB writes.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

# Ensure repo root is on syspath when run as `python scripts/compass_print.py`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.services.compass import engine as compass_engine  # noqa: E402
from src.services.compass import render as compass_render  # noqa: E402
from src.services.compass.fetcher import (  # noqa: E402
    derive_weekly_closes,
    fetch_for_compass,
)


logger = logging.getLogger("compass_print")


def _read_csv(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    if "close" not in df.columns or "date" not in df.columns:
        raise SystemExit(f"CSV must contain columns: date, close ({path})")
    df["date"] = pd.to_datetime(df["date"])
    closes = df.set_index("date")["close"].astype(float).sort_index()
    closes.index.name = "date"
    closes.name = "close"
    return closes


def main() -> int:
    parser = argparse.ArgumentParser(description="Midterm trend compass CLI (P1)")
    parser.add_argument("code", help="A-share / ETF / index code, e.g. 600519 / sh000300")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh")
    parser.add_argument(
        "--subject-type", choices=["stock", "etf", "index"], default="stock",
    )
    parser.add_argument("--name", default=None, help="Display name (optional)")
    parser.add_argument(
        "--days", type=int, default=600,
        help="Days of history to load (default 600 ≈ 2.5y)",
    )
    parser.add_argument(
        "--offline", type=str, default=None,
        help="CSV file with date,close columns; bypass data_provider (testing)",
    )
    parser.add_argument(
        "--as-of", type=str, default=None,
        help="Trade date override (YYYY-MM-DD); defaults to latest close",
    )
    args = parser.parse_args()

    if args.offline:
        daily = _read_csv(Path(args.offline))
        source = "offline-csv"
    else:
        from data_provider import DataFetcherManager
        manager = DataFetcherManager()
        try:
            daily, weekly, source = fetch_for_compass(
                manager, args.code, days=args.days,
            )
        except Exception as exc:
            logger.error("daily fetch failed for %s: %s", args.code, exc)
            return 2

    if args.offline:
        weekly = derive_weekly_closes(daily)

    if len(daily.dropna()) < 30:
        logger.error("need >= 30 daily bars, got %d", len(daily.dropna()))
        return 3

    output = compass_engine.compute(daily, weekly)
    as_of = args.as_of or daily.index[-1].date()
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)

    compass = compass_render.assemble(
        code=args.code,
        name=args.name,
        subject_type=args.subject_type,
        as_of_trade_date=as_of,
        engine=output,
        bar_status="closed",
    )

    print(f"[source: {source}]")
    print(compass_render.short_card(compass, lang=args.lang))
    print()
    print(compass_render.long_card(compass, lang=args.lang))
    return 0


if __name__ == "__main__":
    sys.exit(main())
