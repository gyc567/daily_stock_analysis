# -*- coding: utf-8 -*-
"""Pure-compute engine for midterm trend compass.

Issue scope: docs/midterm-trend-compass-plan.md §4 (核心逻辑).

Three-Layer Defense Layer 2: every formula carries icontract pre/post-conditions.
Layer 3 inputs are pandas Series; outputs are typed enum strings consumed by
``src.schemas.compass.MidtrendCompass``.

P1 scope: indicator computation + L0/L1/L2/L3 classification + phase synthesis.
P2 (out of scope): action rewriter + guardrail merge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Tuple, TypedDict

import pandas as pd

import icontract

from typing import cast

from src.schemas.compass import (
    L0Status,
    L1Status,
    L2Status,
    L3Status,
    ObserveHorizon,
    Phase,
    PositionFilter,
)

# Local mirror of IndicatorsBlock.cross_ema20_ema50 Literal to keep the dataclass
# field type narrow (the schema re-imports from here).
CrossAboveBelow = Literal["above", "below", "touched"]


# ---------------------------------------------------------------------------
# Indicators (Wilder-style EMA + Wilder RSI)
# ---------------------------------------------------------------------------


@icontract.require(
    lambda closes: isinstance(closes, pd.Series),
    "closes must be a pandas Series",
)
@icontract.require(
    lambda closes, period: len(closes) >= period,
    "closes length must be >= period",
)
@icontract.require(
    lambda period: period >= 1,
    "period must be >= 1",
)
@icontract.ensure(
    lambda result: result.isna().sum() == 0 or result.notna().sum() >= 1,
    "result must have at least one non-NaN value",
)
def _wilder_ema(closes: pd.Series, period: int) -> pd.Series:
    """Wilder smoothing: alpha = 1 / period, applied as EMA with adjust=False.

    The seeding is a simple SMA over the first ``period`` rows; this matches
    the standard TA-Lib / TradingView Wilder output to within floating-point
    rounding.
    """
    alpha = 1.0 / float(period)
    seed_mean = closes.iloc[:period].mean()
    # Wilder seed: SMA over the first ``period`` bars; that SMA sits at index (period - 1).
    # Subsequent bars apply alpha = 1 / period smoothing without adjust (Wilder EMA).
    seed_mean = float(closes.iloc[:period].mean())
    seeded = pd.Series([float("nan")] * (period - 1) + [seed_mean], index=closes.index[:period])
    body = closes.iloc[period:]
    if body.empty:
        return seeded
    smoothed = body.ewm(alpha=alpha, adjust=False).mean()
    # pd.concat can technically return DataFrame if columns misalign; cast
    # back to Series to satisfy pyright (mypy sees the cast as redundant).
    out_series: pd.Series = pd.concat([seeded, smoothed])
    out_series.index = closes.index
    out_series.name = closes.name
    return out_series


@icontract.require(
    lambda closes, period: isinstance(period, int) and period >= 1,
    "period must be int >= 1",
)
@icontract.require(
    lambda closes, period: len(closes) >= period + 1,
    "closes length must be >= period+1 for Wilder RSI",
)
@icontract.ensure(
    lambda result: result.dropna().between(0.0, 100.0).all(),
    "RSI values must lie in [0, 100]",
)
def compute_rsi_wilder(closes: pd.Series, period: int = 14) -> pd.Series:
    """RSI with Wilder smoothing; first ``period`` rows are NaN."""
    delta = closes.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = cast(pd.Series, _wilder_ema(gain, period))  # type: ignore[redundant-cast]
    avg_loss = cast(pd.Series, _wilder_ema(loss, period))  # type: ignore[redundant-cast]
    # Use float("nan") (not pd.NA) so .replace() returns Series, not DataFrame.
    rs = avg_gain / avg_loss.replace(0.0, float("nan"))
    one_plus_rs = cast(pd.Series, 1.0 + rs)  # type: ignore[redundant-cast]
    rsi = cast(pd.Series, 100.0 - 100.0 / one_plus_rs)  # type: ignore[redundant-cast]
    # When avg_loss == 0, force RSI = 100 (pure up-move).
    rsi = rsi.where(avg_loss != 0, 100.0)
    return rsi


@icontract.require(
    lambda closes, period: len(closes) >= period,
    "closes length must be >= period",
)
@icontract.require(
    lambda period: period >= 1,
    "period must be >= 1",
)
def compute_ema(closes: pd.Series, period: int) -> pd.Series:
    """Standard EMA (alpha = 2/(period+1)), seeded via the first non-Na value."""
    # pyright sees ewm().mean() as DataFrame | Series (pandas-stubs is loose);
    # cast narrows to the declared Series return. mypy flags the cast as
    # redundant, so the ignore is required to keep mypy --strict quiet.
    return cast(pd.Series, closes.ewm(span=period, adjust=False).mean())  # type: ignore[redundant-cast]


@icontract.require(
    lambda series, window: window >= 1,
    "slope window must be >= 1",
)
@icontract.ensure(
    lambda result: result.index.equals(result.index),
    "slope index must align with input",
)
def _slope(series: pd.Series, window: int) -> pd.Series:
    """Linear regression slope over a rolling window (last - first) / window.

    Intentionally simple: it preserves sign and avoids sklearn dependency.
    """
    def _delta(arr: pd.Series) -> float:
        arr = arr.dropna()
        if len(arr) < 2:
            return float("nan")
        return float((arr.iloc[-1] - arr.iloc[0]) / (len(arr) - 1))

    return cast(pd.Series, series.rolling(window=window, min_periods=window).apply(_delta, raw=False))  # type: ignore[redundant-cast]


# ---------------------------------------------------------------------------
# L0 — Weekly filter
# ---------------------------------------------------------------------------


class WeeklySnapshot(TypedDict):
    """Snapshot returned by :func:`derive_l0`."""

    weekly_ema50: Optional[float]
    weekly_ema200: Optional[float]
    weekly_sample_size: int


@icontract.require(
    lambda weekly_closes: isinstance(weekly_closes, pd.Series),
    "weekly_closes must be a pandas Series",
)
@icontract.require(
    lambda weekly_closes: len(weekly_closes) >= 0,
    "weekly_closes length must be >= 0",
)
def derive_l0(weekly_closes: pd.Series) -> Tuple[L0Status, WeeklySnapshot]:
    """Compute weekly EMA50 / EMA200 and classify the trend filter.

    Sample rules (per plan §7): < 60 weekly bars => weekly_disabled;
    60 <= sample < 200 cannot seed EMA200 => weekly_disabled; >= 200 full.
    """
    sample = len(weekly_closes.dropna())
    if sample < 200:
        return "weekly_disabled", {
            "weekly_ema50": None,
            "weekly_ema200": None,
            "weekly_sample_size": sample,
        }

    ema50 = float(compute_ema(weekly_closes, 50).iloc[-1])
    ema200 = float(compute_ema(weekly_closes, 200).iloc[-1])
    last_close = float(weekly_closes.iloc[-1])

    if last_close > ema200 and ema50 > ema200:
        status: L0Status = "weekly_bull"
    elif last_close < ema200 and ema50 < ema200:
        status = "weekly_bear"
    else:
        status = "weekly_transition"

    return status, {
        "weekly_ema50": ema50,
        "weekly_ema200": ema200,
        "weekly_sample_size": sample,
    }


# ---------------------------------------------------------------------------
# L1 — Annual filter (EMA200 slope over 40d)
# ---------------------------------------------------------------------------


@icontract.require(
    lambda daily_closes: isinstance(daily_closes, pd.Series),
    "daily_closes must be a pandas Series",
)
def derive_l1(daily_closes: pd.Series) -> L1Status:
    """Annual trend filter; sample < 220 bars => annual_disabled."""
    sample = len(daily_closes.dropna())
    if sample < 220:
        return "annual_disabled"

    ema200 = compute_ema(daily_closes, 200)
    slope40 = _slope(ema200, 40).iloc[-1]
    last_close = float(daily_closes.iloc[-1])

    if pd.isna(slope40):
        return "annual_disabled"

    if last_close > float(ema200.iloc[-1]) and slope40 > 0:
        return "annual_bull"
    if last_close < float(ema200.iloc[-1]) and slope40 < 0:
        return "annual_bear"
    return "annual_transition"


# ---------------------------------------------------------------------------
# L2 — 1-3 month segment (alive / resting / flattening / broken)
# ---------------------------------------------------------------------------


@icontract.require(
    lambda daily_closes: isinstance(daily_closes, pd.Series),
    "daily_closes must be a pandas Series",
)
@icontract.require(
    lambda daily_closes: len(daily_closes) >= 30,
    "daily_closes length must be >= 30 for L2",
)
def derive_l2(daily_closes: pd.Series) -> L2Status:
    """Segment health from EMA50 structure.

    Rules (priority order — first match wins):
      - EMA50 slope flat (abs < 0.05/day)            => flattening
      - Price below EMA50 and EMA50 sloping down     => broken
      - Price touched/reclaimed EMA20 from below     => resting
      - otherwise                                    => alive
    """
    ema20 = compute_ema(daily_closes, 20)
    ema50 = compute_ema(daily_closes, 50)
    slope_ema50 = _slope(ema50, 20).iloc[-1]
    last_close = float(daily_closes.iloc[-1])
    last_ema50 = float(ema50.iloc[-1])

    if pd.isna(slope_ema50):
        return "broken"  # not enough data => treat as broken for safety

    if abs(slope_ema50) < 0.05:
        return "flattening"

    if last_close < last_ema50 and slope_ema50 < 0:
        return "broken"

    # resting = touched EMA20 from below within the last 5 bars
    ema20_recent = ema20.iloc[-5:]
    close_recent = daily_closes.iloc[-5:]
    touched = (close_recent <= ema20_recent * 1.005).any() and last_close > float(
        ema20.iloc[-1]
    )
    if touched:
        return "resting"

    return "alive"


# ---------------------------------------------------------------------------
# L3 — 2-6 week rhythm (healthy / cooling / exhausted / noisy)
# ---------------------------------------------------------------------------


@icontract.require(
    lambda daily_closes: isinstance(daily_closes, pd.Series),
    "daily_closes must be a pandas Series",
)
@icontract.require(
    lambda daily_closes: len(daily_closes) >= 30,
    "daily_closes length must be >= 30 for L3",
)
def derive_l3(daily_closes: pd.Series) -> L3Status:
    """Short-term rhythm from EMA20 + RSI(14).

    - healthy: EMA20 sloping up, RSI 45-75
    - cooling: EMA20 slope flattening, RSI 35-55
    - exhausted: RSI > 75 (overbought) with negative slope
    - noisy:    unable to classify (insufficient data or contradictory signals)
    """
    ema20 = compute_ema(daily_closes, 20)
    slope_ema20 = _slope(ema20, 10).iloc[-1]
    rsi = compute_rsi_wilder(daily_closes, 14).iloc[-1]
    last_close = float(daily_closes.iloc[-1])

    if pd.isna(slope_ema20) or pd.isna(rsi):
        return "noisy"

    # Priority: a clear rising slope above EMA20 is healthy regardless of how
    # overbought RSI gets (a strong uptrend legitimately prints RSI > 75).
    if slope_ema20 > 0 and last_close > float(ema20.iloc[-1]):
        return "healthy"
    if abs(slope_ema20) < 0.05 and 35.0 <= rsi <= 55.0:
        return "cooling"
    if rsi > 75.0 and slope_ema20 < 0:
        return "exhausted"
    return "noisy"


# ---------------------------------------------------------------------------
# Phase synthesis — locked priority table (plan §4.3)
# ---------------------------------------------------------------------------


@icontract.require(
    lambda l0, l1, l2, l3: all(
        v in {"weekly_bull", "weekly_bear", "weekly_transition", "weekly_disabled"}
        for v in [l0]
    ),
    "l0 must be a valid L0Status",
)
def compose_phase(l0: L0Status, l1: L1Status, l2: L2Status, l3: L3Status) -> Phase:
    """Apply the §4.3 priority table (short-circuit evaluation)."""
    if l1 == "annual_disabled":
        return "trend_holding"
    if l1 == "annual_transition" and l2 in {"flattening", "broken"}:
        return "transitioning"
    if l2 == "flattening" or (l2 != "alive" and l3 in {"exhausted", "noisy"}):
        return "coiling"
    if l2 in {"alive", "resting"} and l3 == "exhausted":
        return "trend_tiring"
    if l2 == "resting" or l3 == "cooling":
        return "trend_holding"
    if (
        l0 != "weekly_bear"
        and l1 == "annual_bull"
        and l2 == "alive"
        and l3 == "healthy"
    ):
        return "trend_expanding"
    return "transitioning"


# ---------------------------------------------------------------------------
# Derived enums (observe_horizon, position_filter)
# ---------------------------------------------------------------------------


_PHASE_TO_HORIZON: dict[Phase, ObserveHorizon] = {
    "trend_expanding": "1m",
    "trend_holding": "1m",
    "trend_tiring": "2w",
    "coiling": "2w",
    "transitioning": "1w",
}


@icontract.ensure(
    lambda result, phase: _PHASE_TO_HORIZON[phase] == result,
    "horizon must follow the locked phase-to-horizon table",
)
def observe_horizon_for(phase: Phase) -> ObserveHorizon:
    return _PHASE_TO_HORIZON[phase]


_L0_TO_POSITION: dict[L0Status, PositionFilter] = {
    "weekly_bull": "full",
    "weekly_transition": "half",
    "weekly_bear": "none",
    "weekly_disabled": "half",
}


@icontract.ensure(
    lambda result, l0: _L0_TO_POSITION[l0] == result,
    "position_filter must follow the locked L0 table",
)
def position_filter_for(l0: L0Status) -> PositionFilter:
    return _L0_TO_POSITION[l0]


# ---------------------------------------------------------------------------
# Bundle: aggregate engine output for schema assembly
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineOutput:
    l0: L0Status
    l1: L1Status
    l2: L2Status
    l3: L3Status
    phase: Phase
    observe_horizon: ObserveHorizon
    position_filter: PositionFilter
    weekly_ema50: Optional[float]
    weekly_ema200: Optional[float]
    weekly_sample_size: int
    daily_sample_size: int
    ema20: Optional[float]
    ema50: Optional[float]
    ema100: Optional[float]
    ema200: Optional[float]
    rsi14: Optional[float]
    slope_ema20_10d: Optional[float]
    slope_ema50_20d: Optional[float]
    slope_ema200_40d: Optional[float]
    last_close: Optional[float]
    cross_ema20_ema50: Optional[CrossAboveBelow]


@icontract.require(
    lambda daily_closes: isinstance(daily_closes, pd.Series),
    "daily_closes must be a pandas Series",
)
@icontract.require(
    lambda weekly_closes: isinstance(weekly_closes, pd.Series),
    "weekly_closes must be a pandas Series",
)
@icontract.require(
    lambda daily_closes: len(daily_closes) >= 30,
    "need >= 30 daily bars to attempt classification",
)
def compute(
    daily_closes: pd.Series,
    weekly_closes: pd.Series,
) -> EngineOutput:
    """Run the full L0..L3 + phase pipeline. Pure: no I/O, no globals."""
    l0, l0_meta = derive_l0(weekly_closes)
    l1 = derive_l1(daily_closes)
    l2 = derive_l2(daily_closes)
    l3 = derive_l3(daily_closes)
    phase = compose_phase(l0, l1, l2, l3)

    ema20 = compute_ema(daily_closes, 20)
    ema50 = compute_ema(daily_closes, 50)
    ema100 = compute_ema(daily_closes, 100)
    ema200 = compute_ema(daily_closes, 200)

    slope20 = _slope(ema20, 10).iloc[-1]
    slope50 = _slope(ema50, 20).iloc[-1]
    slope200 = _slope(ema200, 40).iloc[-1]

    last_close = float(daily_closes.iloc[-1])
    ema20_last = float(ema20.iloc[-1])
    ema50_last = float(ema50.iloc[-1])

    if pd.isna(ema20_last) or pd.isna(ema50_last):
        cross: Optional[CrossAboveBelow] = None
    elif last_close > ema20_last > ema50_last:
        cross = "above"
    elif last_close < ema20_last < ema50_last:
        cross = "below"
    else:
        cross = "touched"

    rsi_val = compute_rsi_wilder(daily_closes, 14).iloc[-1]

    return EngineOutput(
        l0=l0,
        l1=l1,
        l2=l2,
        l3=l3,
        phase=phase,
        observe_horizon=observe_horizon_for(phase),
        position_filter=position_filter_for(l0),
        weekly_ema50=l0_meta["weekly_ema50"],
        weekly_ema200=l0_meta["weekly_ema200"],
        weekly_sample_size=l0_meta["weekly_sample_size"],
        daily_sample_size=len(daily_closes.dropna()),
        ema20=ema20_last,
        ema50=ema50_last,
        ema100=float(ema100.iloc[-1]),
        ema200=float(ema200.iloc[-1]),
        rsi14=float(rsi_val) if not pd.isna(rsi_val) else None,
        slope_ema20_10d=float(slope20) if not pd.isna(slope20) else None,
        slope_ema50_20d=float(slope50) if not pd.isna(slope50) else None,
        slope_ema200_40d=float(slope200) if not pd.isna(slope200) else None,
        last_close=last_close,
        cross_ema20_ema50=cross,
    )
