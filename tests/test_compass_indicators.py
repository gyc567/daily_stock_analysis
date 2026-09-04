# -*- coding: utf-8 -*-
"""Indicator math tests: Wilder EMA + Wilder RSI + slope.

Issue scope: docs/midterm-trend-compass-plan.md §14 (icontract contracts).
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.services.compass.engine import (
    _slope,
    _wilder_ema,
    compute_ema,
    compute_rsi_wilder,
)


def test_wilder_ema_seed_value_matches_sma():
    closes = pd.Series([1, 2, 3, 4, 5, 6, 7, 8], dtype=float)
    out = _wilder_ema(closes, period=3)
    # Wilder seed = SMA over first ``period`` bars, placed at index (period-1).
    assert math.isclose(out.iloc[2], (1 + 2 + 3) / 3, rel_tol=1e-9)
    # First (period-1) bars are NaN.
    assert out.iloc[0] != out.iloc[0]  # NaN check
    assert out.iloc[1] != out.iloc[1]
    # Wilder EMA lags behind price; later values are < current close.
    assert out.iloc[-1] < closes.iloc[-1]


def test_wilder_ema_constant_input_stays_at_constant():
    closes = pd.Series([7.0] * 30)
    out = _wilder_ema(closes, period=3)
    valid = out.dropna()
    assert (valid == 7.0).all()


def test_wilder_ema_handles_constant_input():
    closes = pd.Series([5.0] * 30)
    out = _wilder_ema(closes, period=14)
    valid = out.dropna()
    assert (valid == 5.0).all()


def test_compute_ema_constant_input_stays_constant():
    closes = pd.Series([42.0] * 30)
    out = compute_ema(closes, period=10)
    valid = out.dropna()
    assert (valid == 42.0).all()


def test_rsi_wilder_all_up_is_100():
    closes = pd.Series([float(i) for i in range(1, 30)])
    rsi = compute_rsi_wilder(closes, period=14)
    valid = rsi.dropna()
    assert (valid == 100.0).all()


def test_rsi_wilder_all_down_is_0():
    closes = pd.Series([float(30 - i) for i in range(30)])
    rsi = compute_rsi_wilder(closes, period=14)
    valid = rsi.dropna()
    assert (valid == 0.0).all()


def test_rsi_wilder_zigzag_converges_to_50():
    # 100+ alternating points needed for Wilder EMA to settle on equal gain/loss.
    closes = pd.Series([1.0 if i % 2 == 0 else 2.0 for i in range(200)])
    rsi = compute_rsi_wilder(closes, period=14)
    last = float(rsi.dropna().iloc[-1])
    assert 40.0 <= last <= 60.0, f"expected RSI≈50, got {last}"


def test_slope_positive_for_monotonic_up():
    s = pd.Series([float(i) for i in range(1, 30)])
    slope = _slope(s, window=10).dropna()
    assert (slope > 0).all()


def test_wilder_ema_rejects_short_input():
    closes = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(Exception):
        _wilder_ema(closes, period=10)


def test_rsi_rejects_short_input():
    closes = pd.Series([1.0] * 5)
    with pytest.raises(Exception):
        compute_rsi_wilder(closes, period=14)
