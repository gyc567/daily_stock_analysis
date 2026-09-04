# -*- coding: utf-8 -*-
"""Rendering helpers for the midterm trend compass.

Issue scope: docs/midterm-trend-compass-plan.md §3 (用户能看到什么).

P1 renders both short card (one line per subject) and long card (full report).
No notification wiring in P1 — that's P3 (require-review path).
"""

from __future__ import annotations

from datetime import date as _date, datetime, timezone
from typing import Optional

import icontract

from src.schemas.compass import (
    BarStatus,
    IndicatorsBlock,
    MidtrendCompass,
    QualityBlock,
    SubjectType,
    VsPrevious,
    WeeklyIndicators,
)
from src.services.compass import i18n
from src.services.compass.engine import EngineOutput


@icontract.ensure(
    lambda result: isinstance(result, MidtrendCompass),
    "result must be a MidtrendCompass instance",
)
def assemble(
    code: str,
    name: Optional[str],
    subject_type: SubjectType,
    as_of_trade_date: _date,
    engine: EngineOutput,
    bar_status: BarStatus = "closed",
    stale_since: Optional[_date] = None,
    vs_previous: Optional[VsPrevious] = None,
    calculated_at: Optional[datetime] = None,
) -> MidtrendCompass:
    """Wrap EngineOutput in the frozen Pydantic v2 contract.

    ``calculated_at`` defaults to ``datetime.now(timezone.utc)``; callers that
    need deterministic snapshots (tests, replay) may inject a fixed timestamp.
    """
    l1_available = engine.l1 != "annual_disabled"
    l0_available = engine.l0 != "weekly_disabled"

    quality = QualityBlock(
        sample_size=engine.daily_sample_size,
        weekly_sample_size=engine.weekly_sample_size,
        l0_available=l0_available,
        l1_available=l1_available,
        status="ok" if (l0_available or l1_available) else "degraded",
    )

    indicators = IndicatorsBlock(
        price=engine.last_close,
        ema20=engine.ema20,
        ema50=engine.ema50,
        ema100=engine.ema100,
        ema200=engine.ema200,
        rsi14=engine.rsi14,
        slope_ema20_10d=engine.slope_ema20_10d,
        slope_ema50_20d=engine.slope_ema50_20d,
        slope_ema200_40d=engine.slope_ema200_40d,
        cross_ema20_ema50=engine.cross_ema20_ema50,
    )

    weekly_indicators = WeeklyIndicators(
        weekly_ema50=engine.weekly_ema50,
        weekly_ema200=engine.weekly_ema200,
        sample_size=engine.weekly_sample_size,
    )

    return MidtrendCompass(
        code=code,
        name=name,
        market="cn",
        subject_type=subject_type,
        as_of_trade_date=as_of_trade_date,
        calculated_at=calculated_at or datetime.now(timezone.utc),
        bar_status=bar_status,
        stale_since=stale_since,
        adjust="qfq",
        quality=quality,
        indicators=indicators,
        weekly_indicators=weekly_indicators,
        weekly=engine.l0,
        annual=engine.l1,
        segment=engine.l2,
        rhythm=engine.l3,
        phase=engine.phase,
        observe_horizon=engine.observe_horizon,
        position_filter=engine.position_filter,
        action_bias="watch",  # P1: rewriter is P2; default neutral
        action_reason=[],
        vs_previous=vs_previous,
        risks=[],
        disclaimer=(
            "本模块不预测短期价格；分批与执行窗不在本模块范围。"
            " P1 不包含 action rewriter，action_bias 固定 watch。"
        ),
    )


def short_card(c: MidtrendCompass, lang: i18n.Language = "zh") -> str:
    """One-line summary per plan §3.1."""
    name = (c.name or c.code)[:8]
    vs_arrow = "—"
    if c.vs_previous is not None:
        vs_arrow = {
            "up": "↑",
            "down": "↓",
            "flat": "→",
        }[c.vs_previous.phase_change]

    return (
        f"{name} | "
        f"{i18n.phase_text(c.phase, lang)} | "
        f"{i18n.l2_text(c.segment, lang)} | "
        f"{i18n.action_text(c.action_bias, lang)} | "
        f"{vs_arrow} | "
        f"{i18n.bar_text(c.bar_status, lang)} | "
        f"{i18n.l0_text(c.weekly, lang)}"
    )


def long_card(c: MidtrendCompass, lang: i18n.Language = "zh") -> str:
    """Full report per plan §3.2 (1..8 sections)."""
    i = c.indicators
    w = c.weekly_indicators
    name = c.name or c.code

    head = f"# 中期趋势罗盘 · {name} ({c.code})\n" if lang == "zh" else f"# Midterm Trend Compass · {name} ({c.code})\n"

    sec1 = (
        f"## 1. 周线过滤\n- 状态: {i18n.l0_text(c.weekly, lang)}\n"
        f"- weekly_ema50: {_fmt(w.weekly_ema50)} | weekly_ema200: {_fmt(w.weekly_ema200)}\n"
        f"- weekly sample: {w.sample_size}\n"
        f"- 仓位上限语义: {c.position_filter}\n"
    )
    sec2 = (
        f"## 2. 日线阶段 + 观察量级\n"
        f"- phase: {i18n.phase_text(c.phase, lang)}\n"
        f"- observe_horizon: {c.observe_horizon}\n"
    )
    sec3 = (
        f"## 3. L1 / L2 / L3\n"
        f"- L1: {i18n.l1_text(c.annual, lang)}\n"
        f"- L2: {i18n.l2_text(c.segment, lang)}\n"
        f"- L3: {i18n.l3_text(c.rhythm, lang)}\n"
        f"- indicators: ema20={_fmt(i.ema20)} ema50={_fmt(i.ema50)} "
        f"ema100={_fmt(i.ema100)} ema200={_fmt(i.ema200)} rsi14={_fmt(i.rsi14)}\n"
    )
    sec4 = (
        "## 4. 失效条件\n"
        "- 周线转 weekly_bear\n- L2 由 alive/resting 转 broken\n"
        "- L3 持续 exhausted 且 L2 alive\n"
    )
    sec5 = (
        f"## 5. 系统动作\n"
        f"- action_bias: {i18n.action_text(c.action_bias, lang)} "
        f"(P1 placeholder，rewriter 见 P2)\n"
        f"- reason codes: {c.action_reason or '[]'}\n"
    )
    sec6 = (
        "## 6. 较昨日\n"
        + (
            "- (无最近 closed 快照)\n"
            if c.vs_previous is None
            else (
                f"- previous_trade_date: {c.vs_previous.previous_trade_date}\n"
                f"- previous_phase: {c.vs_previous.previous_phase}\n"
                f"- phase_change: {c.vs_previous.phase_change}\n"
            )
        )
    )
    sec7 = (
        f"## 7. 风险与数据限制\n"
        f"- bar_status: {i18n.bar_text(c.bar_status, lang)}\n"
        f"- daily sample: {c.quality.sample_size}\n"
        f"- weekly sample: {c.quality.weekly_sample_size}\n"
        f"- status: {c.quality.status}\n"
    )
    sec8 = (
        "## 8. 其它模块（独立并列）\n"
        "- 缠论 / 波浪 / 其它 skill 不读罗盘，罗盘也不读它们。\n"
        f"\n_免责声明: {c.disclaimer}_\n"
    )

    return head + "\n" + sec1 + sec2 + sec3 + sec4 + sec5 + sec6 + sec7 + sec8


def _fmt(value: Optional[float | int | str]) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
