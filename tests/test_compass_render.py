# -*- coding: utf-8 -*-
"""Render tests: short card + long card + assemble."""

from __future__ import annotations

import re
from datetime import date

from src.schemas.compass import MidtrendCompass
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


def _assemble(engine: EngineOutput) -> MidtrendCompass:
    return render.assemble(
        code="600519", name="Moutai", subject_type="stock",
        as_of_trade_date=date(2026, 8, 14), engine=engine,
    )


def test_assemble_returns_frozen_compass():
    c = _assemble(_engine_out())
    assert c.code == "600519"
    assert c.phase == "trend_expanding"
    assert c.weekly == "weekly_bull"


def test_short_card_zh_includes_phase_and_action():
    c = _assemble(_engine_out())
    line = render.short_card(c, lang="zh")
    assert "趋势扩张" in line
    assert "买入" not in line  # default action_bias = watch
    assert "观望" in line
    assert "已收" in line
    assert "周多" in line


def test_long_card_has_9_sections():
    md = render.long_card(_assemble(_engine_out()), lang="zh")
    for idx in range(1, 10):
        assert f"## {idx}." in md, f"missing section {idx} in long card"
    assert "当前无择时信号" in md


def test_long_card_with_timing_signal_renders_section9():
    from datetime import date as _date

    from src.schemas.compass import TimingSignal
    c = _assemble(_engine_out())
    c = c.model_copy(update={"timing": [
        TimingSignal(
            type="pullback_entry", status="triggered",
            trigger_price=1720.0, invalidation_price=1685.0,
            position_hint="full", horizon_days=5,
            as_of_bar_date=_date(2026, 8, 14),
        ),
        TimingSignal(
            type="top_escape", status="triggered",
            reason_codes=["top_escape_divergence"],
            trigger_price=1700.0, invalidation_price=1730.0,
            position_hint="light", horizon_days=5,
            as_of_bar_date=_date(2026, 8, 14),
        ),
    ]})
    md = render.long_card(c, lang="zh")
    assert "## 9." in md
    assert "触发价" in md and "失效价" in md
    assert "1685.0" in md
    # 逃顶变体 reason code 展开为中文解释
    assert "顶背离" in md
    md_en = render.long_card(c, lang="en")
    assert "Bearish divergence" in md_en


def test_short_card_en_labels():
    line = render.short_card(_assemble(_engine_out()), lang="en")
    assert "Expanding" in line
    assert "Watch" in line
    assert "W-Bull" in line


def test_long_card_zh_explains_weekly_filter():
    md = render.long_card(_assemble(_engine_out()), lang="zh")
    assert "周线多头结构，允许在仓位上限内执行买入" in md
    assert "原理" in md
    assert "50周线 1600.00" in md
    # last_close 1720 vs weekly_ema200 1400 → +22.9%
    assert "现价（日线收盘）高于 200 周线约 22.9%" in md
    assert "仓位上限=允许重仓波段" in md
    assert "主趋势窗：未来 1 个月" in md
    assert "未指定初稿动作" in md
    assert "rewrite" not in md


def test_long_card_en_has_no_cjk():
    md = render.long_card(_assemble(_engine_out()), lang="en")
    assert re.search(r"[\u4e00-\u9fff]", md) is None
    assert "Weekly Filter (L0)" in md
    assert "Position cap = Full position allowed" in md
    assert "above the 200-week EMA" in md
    assert "Segment window: 1 month" in md
    assert "No draft action supplied" in md
    assert "Disclaimer" in md


def test_long_card_weekly_disabled_skips_pct_line():
    engine = EngineOutput(
        l0="weekly_disabled",
        l1="annual_bull",
        l2="alive",
        l3="healthy",
        phase="trend_expanding",
        observe_horizon="1m",
        position_filter="none",
        weekly_ema50=None,
        weekly_ema200=None,
        weekly_sample_size=30,
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
    md = render.long_card(_assemble(engine), lang="zh")
    assert "周线样本不足，本层不参与决策" in md
    assert "仓位上限=禁止买入" in md
    assert "200 周线约" not in md


def test_long_card_with_rewrite_renders_chain():
    from src.services.compass.rewriter import CompassState, rewrite

    result = rewrite(
        "buy",
        CompassState(
            weekly="weekly_bull",
            annual="annual_bear",
            segment="broken",
            rhythm="noisy",
            phase="transitioning",
            bar_status="closed",
        ),
    )
    c = _assemble(_engine_out())
    md = render.long_card(c, lang="zh", rewrite=("buy", result))
    assert "结论: 卖出" in md
    assert "触发约束:" in md
    assert "1. 收敛/切换阶段，买入降级为观望（动作：买入 → 观望）" in md
    assert "2. 空头结构破坏，允许离场（动作：观望 → 卖出）" in md
    assert "未指定初稿动作" not in md
    md_en = render.long_card(c, lang="en", rewrite=("buy", result))
    assert "1. Coiling/transitioning phase; buy downgraded to watch (action: Buy -> Watch)" in md_en


def test_long_card_with_clean_rewrite_shows_pass_through():
    from src.services.compass.rewriter import CompassState, rewrite

    result = rewrite("buy", CompassState(
        weekly="weekly_bull", annual="annual_bull", segment="alive",
        rhythm="healthy", phase="trend_expanding", bar_status="closed",
    ))
    md = render.long_card(_assemble(_engine_out()), lang="zh", rewrite=("buy", result))
    assert "结论: 买入" in md
    assert "未命中任何硬约束，初稿原样通过。" in md
