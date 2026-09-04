# -*- coding: utf-8 -*-
"""i18n label parity tests."""

from __future__ import annotations

from typing import cast

from src.schemas.compass import (
    BarStatus,
    CompassAction,
    L2Status,
    Phase as CompassPhase,
)
from src.services.compass.i18n import (
    action_text,
    bar_text,
    l2_text,
    phase_text,
)


def test_phase_labels_bilingual():
    phases = cast(
        list[CompassPhase],
        ["trend_expanding", "trend_holding", "trend_tiring", "coiling", "transitioning"],
    )
    for phase in phases:
        zh = phase_text(phase, "zh")
        en = phase_text(phase, "en")
        assert zh != en
        assert len(zh) >= 2
        assert len(en) >= 4


def test_action_labels_bilingual():
    actions = cast(list[CompassAction], ["buy", "watch", "sell"])
    for action in actions:
        assert action_text(action, "zh") in {"买入", "观望", "卖出"}
        assert action_text(action, "en") in {"Buy", "Watch", "Sell"}


def test_bar_status_labels_bilingual():
    bars = cast(list[BarStatus], ["closed", "intraday_unconfirmed", "stale", "suspended"])
    for bar in bars:
        assert bar_text(bar, "zh") != bar_text(bar, "en")


def test_l2_label_count_matches_enum_size():
    expected = cast(list[L2Status], ["alive", "resting", "flattening", "broken"])
    for status in expected:
        assert l2_text(status, "zh") != l2_text(status, "en")
