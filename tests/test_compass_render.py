# -*- coding: utf-8 -*-
"""Render tests: short card + long card + assemble."""

from __future__ import annotations

from datetime import date


from src.services.compass import render
from src.services.compass.engine import EngineOutput


def _engine_out() -> EngineOutput:
    return EngineOutput(
        l0="weekly_bull",
        l1="annual_bull",
        l2="alive",
        l3="healthy",
        phase="trend_expanding",
        observe_horizon="1m",
        position_filter="full",
        weekly_ema50=1600.0,
        weekly_ema200=1400.0,
        weekly_sample_size=120,
        daily_sample_size=600,
        ema20=1700.0,
        ema50=1680.0,
        ema100=1660.0,
        ema200=1500.0,
        rsi14=55.0,
        slope_ema20_10d=0.5,
        slope_ema50_20d=0.4,
        slope_ema200_40d=0.3,
        last_close=1720.0,
        cross_ema20_ema50="above",
    )


def test_assemble_returns_frozen_compass():
    engine = _engine_out()
    c = render.assemble(
        code="600519", name="Kweichow Moutai", subject_type="stock",
        as_of_trade_date=date(2026, 8, 14), engine=engine,
    )
    assert c.code == "600519"
    assert c.phase == "trend_expanding"
    assert c.weekly == "weekly_bull"


def test_short_card_zh_includes_phase_and_action():
    engine = _engine_out()
    c = render.assemble(
        code="600519", name=None, subject_type="stock",
        as_of_trade_date=date(2026, 8, 14), engine=engine,
    )
    line = render.short_card(c, lang="zh")
    assert "趋势扩张" in line
    assert "买入" not in line  # P1: action_bias = watch
    assert "观望" in line
    assert "已收" in line
    assert "周多" in line


def test_long_card_has_8_sections():
    engine = _engine_out()
    c = render.assemble(
        code="600519", name="Moutai", subject_type="stock",
        as_of_trade_date=date(2026, 8, 14), engine=engine,
    )
    md = render.long_card(c, lang="zh")
    for idx in range(1, 9):
        assert f"## {idx}." in md, f"missing section {idx} in long card"


def test_short_card_en_labels():
    engine = _engine_out()
    c = render.assemble(
        code="600519", name="Moutai", subject_type="stock",
        as_of_trade_date=date(2026, 8, 14), engine=engine,
    )
    line = render.short_card(c, lang="en")
    assert "Expanding" in line
    assert "Watch" in line
    assert "W-Bull" in line
