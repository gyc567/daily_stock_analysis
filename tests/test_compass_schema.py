# -*- coding: utf-8 -*-
"""Layer 3 Pydantic schema tests for the midterm trend compass.

Issue scope: docs/midterm-trend-compass-plan.md §8 / §14.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from src.schemas.compass import (
    MidtrendCompass,
    QualityBlock,
    WeeklyIndicators,
)


def _base_kwargs() -> dict[str, Any]:
    return {
        "code": "600519",
        "name": "Kweichow Moutai",
        "subject_type": "stock",
        "as_of_trade_date": date(2026, 8, 14),
        "calculated_at": datetime(2026, 8, 14, 7, 0, tzinfo=timezone.utc),
        "bar_status": "closed",
        "quality": QualityBlock(sample_size=600, weekly_sample_size=120, l0_available=True, l1_available=True),
        "indicators": {"price": 1700.0, "ema20": 1680.0, "ema50": 1650.0, "ema100": 1620.0,
                        "ema200": 1500.0, "rsi14": 55.0},
        "weekly_indicators": WeeklyIndicators(weekly_ema50=1600.0, weekly_ema200=1400.0, sample_size=120),
        "weekly": "weekly_bull",
        "annual": "annual_bull",
        "segment": "alive",
        "rhythm": "healthy",
        "phase": "trend_expanding",
        "observe_horizon": "1m",
        "position_filter": "full",
    }


def test_compass_accepts_minimal_valid_payload():
    c = MidtrendCompass(**_base_kwargs())
    assert c.compass_version == "1.0"
    assert c.adjust == "qfq"
    assert c.market == "cn"
    assert c.action_bias == "watch"


def test_compass_rejects_naive_datetime():
    payload = _base_kwargs()
    payload["calculated_at"] = datetime(2026, 8, 14, 7, 0)
    with pytest.raises(ValidationError):
        MidtrendCompass(**payload)


def test_compass_rejects_bad_bar_status():
    payload = _base_kwargs()
    payload["bar_status"] = "intraday_pending"
    with pytest.raises(ValidationError):
        MidtrendCompass(**payload)


def test_compass_rejects_invalid_phase():
    payload = _base_kwargs()
    payload["phase"] = "expanding"
    with pytest.raises(ValidationError):
        MidtrendCompass(**payload)


def test_compass_rsi_out_of_range_rejected():
    payload = _base_kwargs()
    payload["indicators"] = {"rsi14": 150.0}
    with pytest.raises(ValidationError):
        MidtrendCompass(**payload)


def test_compass_stale_requires_stale_since():
    payload = _base_kwargs()
    payload["bar_status"] = "suspended"
    with pytest.raises(ValidationError):
        MidtrendCompass(**payload)


def test_compass_rejects_extra_fields():
    payload = _base_kwargs()
    payload["unknown_field"] = 1
    with pytest.raises(ValidationError):
        MidtrendCompass(**payload)


def test_compass_is_frozen():
    c = MidtrendCompass(**_base_kwargs())
    with pytest.raises(ValidationError):
        c.code = "000001"  # type: ignore[misc]
