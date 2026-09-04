# -*- coding: utf-8 -*-
"""Fetcher tests: weekly-from-daily resample + contract checks.

P1 has no live network tests (those would belong to integration tests).
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.services.compass.fetcher import derive_weekly_closes


def test_derive_weekly_closes_from_daily_index():
    idx = pd.date_range("2024-01-01", periods=300, freq="D")
    daily = pd.Series([100.0 + i * 0.1 for i in range(300)], index=idx, name="close")
    weekly = derive_weekly_closes(daily)
    assert isinstance(weekly.index, pd.DatetimeIndex)
    assert len(weekly) < len(daily)
    assert weekly.name == "weekly_close"
    assert weekly.iloc[-1] == pytest.approx(float(daily.iloc[-1]))


def test_derive_weekly_closes_empty_input():
    daily = pd.Series([], dtype=float)
    weekly = derive_weekly_closes(daily)
    assert len(weekly) == 0


def test_derive_weekly_closes_uses_friday_close():
    # 2024-01-01 is Monday; the following Friday is 2024-01-05.
    idx = pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    daily = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0], index=idx)
    weekly = derive_weekly_closes(daily)
    assert weekly.iloc[-1] == 14.0  # Friday close
