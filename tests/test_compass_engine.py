# -*- coding: utf-8 -*-
"""Engine tests: L0/L1/L2/L3 classification + phase priority table.

Issue scope: docs/midterm-trend-compass-plan.md §4.3 (phase priority table).
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.services.compass.engine import (
    compose_phase,
    compute,
    derive_l0,
    derive_l1,
    derive_l2,
    derive_l3,
)


def _trend(seed: float, step: float, n: int = 600) -> pd.Series:
    """Linear trend series (up if step > 0, down if step < 0)."""
    return pd.Series([seed + step * i for i in range(n)], dtype=float)


def _sine_wave(n: int = 600, amp: float = 5.0) -> pd.Series:
    import math
    return pd.Series([100.0 + amp * math.sin(i / 10.0) for i in range(n)], dtype=float)


# ---------- L0 weekly filter ----------


def test_l0_short_sample_disables():
    # ~70 weekly bars (< 200) => weekly_disabled
    idx = pd.date_range("2024-01-01", periods=300, freq="D")
    weekly = pd.Series(
        [100.0 + 0.5 * i for i in range(300)], index=idx
    ).resample("W-FRI").last().dropna()
    assert len(weekly) < 200, f"test fixture broken: {len(weekly)} weekly bars"
    status, meta = derive_l0(weekly)
    assert status == "weekly_disabled"
    assert meta["weekly_sample_size"] == len(weekly)


def test_l0_classifies_when_sample_meets_ema200():
    idx = pd.date_range("2020-01-01", periods=1500, freq="D")
    weekly = pd.Series(
        [100.0 + 0.1 * i for i in range(1500)], index=idx
    ).resample("W-FRI").last().dropna()
    assert len(weekly) >= 200, f"test fixture broken: {len(weekly)} weekly bars"
    status, meta = derive_l0(weekly)
    assert status in {"weekly_bull", "weekly_bear", "weekly_transition"}
    assert meta["weekly_ema50"] is not None
    assert meta["weekly_ema200"] is not None


def test_l0_disabled_for_trivial_input():
    closes = pd.Series([100.0, 101.0, 102.0])  # too short
    status, meta = derive_l0(closes)
    assert status == "weekly_disabled"


# ---------- L1 annual filter ----------


def test_l1_disabled_when_too_short():
    closes = _trend(100, 1, n=200)
    assert derive_l1(closes) == "annual_disabled"


def test_l1_bull_on_steady_uptrend():
    closes = _trend(100, 0.5, n=300)
    assert derive_l1(closes) == "annual_bull"


def test_l1_bear_on_steady_downtrend():
    closes = _trend(200, -0.5, n=300)
    assert derive_l1(closes) == "annual_bear"


# ---------- L2 segment ----------


def test_l2_broken_when_price_below_ema50_down():
    closes = _trend(300, -0.5, n=200)
    assert derive_l2(closes) == "broken"


def test_l2_alive_on_clean_uptrend():
    closes = _trend(100, 0.5, n=200)
    assert derive_l2(closes) == "alive"


# ---------- L3 rhythm ----------


def test_l3_healthy_on_steady_uptrend():
    closes = _trend(100, 0.4, n=200)
    assert derive_l3(closes) == "healthy"


def test_l3_noisy_on_random_walk():
    import random
    random.seed(42)
    closes = pd.Series([100.0 + random.gauss(0, 5.0) for _ in range(200)])
    # Random walk should not classify as healthy/cooling/exhausted.
    assert derive_l3(closes) in {"noisy", "cooling"}


# ---------- Phase priority table (§4.3) ----------


def test_phase_rule1_l1_disabled_caps_at_holding():
    assert compose_phase("weekly_bull", "annual_disabled", "alive", "healthy") == "trend_holding"


def test_phase_rule2_l1_transition_and_l2_flattening():
    assert compose_phase("weekly_bull", "annual_transition", "flattening", "healthy") == "transitioning"
    assert compose_phase("weekly_bull", "annual_transition", "broken", "healthy") == "transitioning"


def test_phase_rule3_l2_flattening_or_l2_non_alive_l3_exhausted_noisy():
    assert compose_phase("weekly_bull", "annual_bull", "flattening", "healthy") == "coiling"
    assert compose_phase("weekly_bull", "annual_bull", "broken", "exhausted") == "coiling"
    assert compose_phase("weekly_bull", "annual_bull", "broken", "noisy") == "coiling"


def test_phase_rule4_l2_alive_and_l3_exhausted_is_tiring():
    # Plan §4.3 priority table: rule 4 fires for (alive, exhausted) → trend_tiring.
    # (resting, exhausted) falls into rule 3 (resting != alive AND exhausted ∈ {exhausted, noisy}).
    assert compose_phase("weekly_bull", "annual_bull", "alive", "exhausted") == "trend_tiring"


def test_phase_rule3_catches_resting_with_exhausted():
    # Per plan §4.3 rule 3, (resting, exhausted) → coiling, NOT trend_tiring.
    assert compose_phase("weekly_bull", "annual_bull", "resting", "exhausted") == "coiling"


def test_phase_rule5_l2_resting_or_l3_cooling_is_holding():
    assert compose_phase("weekly_bull", "annual_bull", "resting", "healthy") == "trend_holding"
    assert compose_phase("weekly_bull", "annual_bull", "alive", "cooling") == "trend_holding"


def test_phase_rule6_all_healthy_is_expanding():
    assert compose_phase("weekly_bull", "annual_bull", "alive", "healthy") == "trend_expanding"
    assert compose_phase("weekly_transition", "annual_bull", "alive", "healthy") == "trend_expanding"
    assert compose_phase("weekly_disabled", "annual_bull", "alive", "healthy") == "trend_expanding"


def test_phase_rule6_blocks_when_weekly_bear():
    assert compose_phase("weekly_bear", "annual_bull", "alive", "healthy") != "trend_expanding"


def test_phase_rule7_fallback_is_transitioning():
    # L2 alive but L3 noisy (not exhausted) => rule 7
    assert compose_phase("weekly_bull", "annual_bull", "alive", "noisy") == "transitioning"
    # L3 exhausted but L2 broken => rule 3 fires first
    assert compose_phase("weekly_bull", "annual_bull", "broken", "exhausted") == "coiling"


# ---------- End-to-end compute ----------


def test_compute_returns_engine_output_with_phase():
    idx = pd.date_range("2024-01-01", periods=300, freq="D")
    daily = pd.Series([100.0 + 0.4 * i for i in range(300)], index=idx)
    weekly = daily.resample("W-FRI").last().dropna()
    out = compute(daily, weekly)
    assert out.phase in {
        "trend_expanding", "trend_holding", "trend_tiring", "coiling", "transitioning"
    }
    assert out.l1 in {
        "annual_bull", "annual_bear", "annual_transition", "annual_disabled"
    }
    assert out.l0 in {
        "weekly_bull", "weekly_bear", "weekly_transition", "weekly_disabled"
    }


def test_compute_rejects_short_daily():
    daily = pd.Series([1.0, 2.0, 3.0])
    weekly = pd.Series([1.0, 2.0, 3.0])
    with pytest.raises(Exception):
        compute(daily, weekly)
