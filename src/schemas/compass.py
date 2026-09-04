# -*- coding: utf-8 -*-
"""Pydantic v2 contracts for the midterm trend compass.

Issue scope: docs/midterm-trend-compass-plan.md §8 (字段契约 v2)
Three-Layer Defense Layer 3: data shape + Literal enums + field constraints.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ----- Public enumerations (kept outside model so they can be reused) -----

SubjectType = Literal["stock", "etf", "index"]

BarStatus = Literal["closed", "intraday_unconfirmed", "stale", "suspended"]

# L0 weekly filter
L0Status = Literal["weekly_bull", "weekly_bear", "weekly_transition", "weekly_disabled"]

# L1 annual filter
L1Status = Literal["annual_bull", "annual_bear", "annual_transition", "annual_disabled"]

# L2 1-3 months segment
L2Status = Literal["alive", "resting", "flattening", "broken"]

# L3 2-6 weeks rhythm
L3Status = Literal["healthy", "cooling", "exhausted", "noisy"]

# Phase
Phase = Literal[
    "trend_expanding",
    "trend_holding",
    "trend_tiring",
    "coiling",
    "transitioning",
]

# Compass action
CompassAction = Literal["buy", "watch", "sell"]

# Structured reason codes (must align with §4.5.2 table)
ActionReasonCode = Literal[
    "data_missing",
    "intraday_unconfirmed_buy_blocked",
    "weekly_bear_buy_blocked",
    "weekly_transition_buy_blocked",
    "l1_disabled_buy_blocked",
    "coiling_transitioning_buy_downgraded",
    "tiring_buy_downgraded",
    "resting_sell_blocked",
    "l2_broken_bear_allow_sell",
    "l2_broken_bull_sell_blocked",
    "l1_l2_bear_sell_default",
    "l3_exhausted_sell_downgraded",
    "l1_l2_l3_healthy_buy_allowed",
    "market_guardrail_softened",
    "phase_guardrail_suppressed",
]

# Horizons (derived from phase, never user-overridable)
ObserveHorizon = Literal["1w", "2w", "1m"]

# Position ceiling (derived from L0 weekly filter)
PositionFilter = Literal["full", "half", "none"]


# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----


class _StrictBase(BaseModel):
    """Base for all compass models: strict, frozen, validate-on-assign."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        validate_assignment=True,
        extra="forbid",
    )


class IndicatorsBlock(_StrictBase):
    """Raw daily indicator values + slope snapshots."""

    price: Optional[float] = None
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema100: Optional[float] = None
    ema200: Optional[float] = None
    rsi14: Annotated[Optional[float], Field(default=None, ge=0.0, le=100.0)] = None
    slope_ema20_10d: Optional[float] = None
    slope_ema50_20d: Optional[float] = None
    slope_ema200_40d: Optional[float] = None
    cross_ema20_ema50: Optional[Literal["above", "below", "touched"]] = None


class WeeklyIndicators(_StrictBase):
    """Weekly EMA snapshot used by L0."""

    weekly_ema50: Optional[float] = None
    weekly_ema200: Optional[float] = None
    sample_size: Annotated[int, Field(ge=0, le=520)] = 0


class QualityBlock(_StrictBase):
    """Per-layer availability & sample size."""

    sample_size: Annotated[int, Field(ge=0)] = 0
    weekly_sample_size: Annotated[int, Field(ge=0, le=520)] = 0
    l0_available: bool = False
    l1_available: bool = False
    status: Literal["ok", "degraded"] = "ok"
    limitations: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list,
        max_length=20,
    )


class VsPrevious(_StrictBase):
    """Comparison against most recent `closed` snapshot (none if absent)."""

    previous_trade_date: date
    previous_phase: Phase
    previous_action: CompassAction
    phase_change: Literal["up", "down", "flat"]
    l2_change: Literal["up", "down", "flat"]
    l0_change: Literal["up", "down", "flat"]


class MidtrendCompass(_StrictBase):
    """The frozen v1 contract. Versioned; breaking change => bump to 1.1+."""

    compass_version: Literal["1.0"] = "1.0"

    code: Annotated[str, Field(min_length=1, max_length=16)]
    name: Optional[Annotated[str, Field(max_length=64)]] = None
    market: Literal["cn"] = "cn"
    subject_type: SubjectType
    as_of_trade_date: date
    calculated_at: datetime
    bar_status: BarStatus
    stale_since: Optional[date] = None
    adjust: Literal["qfq"] = "qfq"

    quality: QualityBlock
    indicators: IndicatorsBlock
    weekly_indicators: WeeklyIndicators

    weekly: L0Status
    annual: L1Status
    segment: L2Status
    rhythm: L3Status
    phase: Phase
    observe_horizon: ObserveHorizon
    position_filter: PositionFilter

    # P1 only: rewriter is P2. The struct keeps the field but stays neutral.
    action_bias: CompassAction = "watch"
    action_reason: list[ActionReasonCode] = Field(default_factory=list, max_length=10)

    vs_previous: Optional[VsPrevious] = None
    risks: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list,
        max_length=20,
    )
    disclaimer: Annotated[str, Field(max_length=500)] = (
        "本模块不预测短期价格；分批与执行窗不在本模块范围。"
    )

    @field_validator("calculated_at")
    @classmethod
    def _calculated_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("calculated_at must be timezone-aware (UTC)")
        return value.astimezone(timezone.utc)

    def model_post_init(self, __context: Any) -> None:
        # Cross-field invariant: stale_since ↔ bar_status linkage.
        if self.stale_since is None and self.bar_status in {"stale", "suspended"}:
            raise ValueError("stale_since must be set when bar_status is stale/suspended")
        if self.stale_since is not None and self.bar_status not in {"stale", "suspended"}:
            raise ValueError("stale_since is only valid when bar_status is stale/suspended")
