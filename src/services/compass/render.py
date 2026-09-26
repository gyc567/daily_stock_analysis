# -*- coding: utf-8 -*-
"""Rendering helpers for the midterm trend compass.

Issue scope: docs/midterm-trend-compass-plan.md §3 (用户能看到什么).

Renders the short card (one line per subject) and the long card (full
report, sections 1..8 in 结论 → 原理 → 关键数字 → 怎么做 form, bilingual).
Notification wiring is out of scope — compass snapshots are cron-only (§13.7).
"""

from __future__ import annotations

from datetime import date as _date, datetime, timezone
from typing import Iterable, Optional

import icontract

from src.schemas.compass import (
    BarStatus,
    CompassAction,
    IndicatorsBlock,
    MidtrendCompass,
    QualityBlock,
    SubjectType,
    TimingSignal,
    VsPrevious,
    WeeklyIndicators,
)
from src.services.compass import i18n
from src.services.compass.engine import EngineOutput
from src.services.compass.rewriter import RewriteResult


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
    timing: Iterable[TimingSignal] = (),
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
        action_bias="watch",  # default neutral; endpoints may override via model_copy
        action_reason=[],
        vs_previous=vs_previous,
        risks=[],
        disclaimer=i18n.disclaimer_text("zh"),
        timing=list(timing),
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


def long_card(
    c: MidtrendCompass,
    lang: i18n.Language = "zh",
    rewrite: Optional[tuple[CompassAction, RewriteResult]] = None,
) -> str:
    """Full report per plan §3.2 (sections 1..8).

    Each section renders 结论 → 原理 → 关键数字 → 怎么做, fully bilingual;
    reason codes are expanded to one-line explanations (§4.5.2 table).

    ``rewrite`` optionally carries the (draft, RewriteResult) pair of a
    user-supplied draft action; when present, section 5 renders the real
    constraint chain instead of the compass default verdict.
    """
    i = c.indicators
    w = c.weekly_indicators
    name = c.name or c.code

    def lb(key: str) -> str:
        return i18n.card_label(key, lang)

    zh = lang == "zh"
    verdict = "结论" if zh else "Verdict"
    principle = "原理" if zh else "Principle"
    numbers = "关键数字" if zh else "Key numbers"
    how = "怎么做" if zh else "What to do"

    head = (
        f"# 中期趋势罗盘 · {name} ({c.code})\n\n"
        if zh
        else f"# Midterm Trend Compass · {name} ({c.code})\n\n"
    )
    head += f"{lb('as_of')}: {c.as_of_trade_date}\n"

    # --- 1. 周线过滤 ---
    numbers1 = (
        f"- {numbers}: {lb('w50')} {_fmt(w.weekly_ema50)} | {lb('w200')} {_fmt(w.weekly_ema200)}"
        f" | {lb('weekly_samples')} {_bars(w.sample_size, lang)}"
    )
    pct = _pct_distance(i.price, w.weekly_ema200)
    if pct is not None:
        if zh:
            numbers1 += f"；现价（日线收盘）{'高于' if pct >= 0 else '低于'} 200 周线约 {abs(pct):.1f}%"
        else:
            numbers1 += (
                f"; last close (daily) ~{abs(pct):.1f}% "
                f"{'above' if pct >= 0 else 'below'} the 200-week EMA"
            )
    cap = i18n.position_cap(c.position_filter, lang)
    sep = "；" if zh else "; "
    dash = "——" if zh else "—"
    eq = "=" if zh else " = "
    sec1 = (
        f"## 1. {i18n.section_title(1, lang)}\n"
        f"- {verdict}: {i18n.l0_text(c.weekly, lang)} {dash} {i18n.l0_verdict(c.weekly, lang)}"
        f"{sep}{lb('cap')}{eq}{cap}\n"
        f"- {principle}: {i18n.section_principle(1, lang)}\n"
        f"{numbers1}\n"
        f"- {how}: {i18n.position_guide(c.position_filter, lang)}\n"
    )

    # --- 2. 日线阶段 + 观察量级 ---
    sec2 = (
        f"## 2. {i18n.section_title(2, lang)}\n"
        f"- {verdict}: {lb('phase')}={i18n.phase_text(c.phase, lang)}"
        f" | {lb('horizon')}={i18n.horizon_text(c.observe_horizon, lang)}\n"
        f"- {principle}: {i18n.section_principle(2, lang)}\n"
        f"- {how}: {i18n.horizon_guide(c.observe_horizon, lang)}\n"
    )

    # --- 3. L1 / L2 / L3 ---
    arrow20 = _trend_arrow(i.slope_ema20_10d)
    arrow50 = _trend_arrow(i.slope_ema50_20d)
    arrow200 = _trend_arrow(i.slope_ema200_40d)
    sec3 = (
        f"## 3. {i18n.section_title(3, lang)}\n"
        f"- {verdict}: {lb('l1')} {i18n.l1_text(c.annual, lang)}"
        f" | {lb('l2')} {i18n.l2_text(c.segment, lang)}"
        f" | {lb('l3')} {i18n.l3_text(c.rhythm, lang)}\n"
        f"- {principle}: {i18n.section_principle(3, lang)}\n"
        f"- {numbers}: {lb('close')} {_fmt(i.price)} | EMA20 {_fmt(i.ema20)}{arrow20}"
        f" | EMA50 {_fmt(i.ema50)}{arrow50} | EMA100 {_fmt(i.ema100)}"
        f" | EMA200 {_fmt(i.ema200)}{arrow200} | RSI14 {_fmt(i.rsi14)}\n"
        f"- {lb('slopes')} (10d/20d/40d): {_fmt(i.slope_ema20_10d)}{arrow20}"
        f" / {_fmt(i.slope_ema50_20d)}{arrow50} / {_fmt(i.slope_ema200_40d)}{arrow200}"
        f" | EMA20×EMA50: {i18n.cross_text(i.cross_ema20_ema50, lang)}\n"
    )

    # --- 4. 失效条件 ---
    invalidation = (
        "- 周线状态转为 周空（weekly_bear）\n"
        "- L2 主趋势段由 持主段/休整 转为 破坏（broken）\n"
        "- L3 持续 动能乏力（exhausted）且 L2 仍为 持主段（alive）\n"
        if zh
        else
        "- Weekly status turns W-Bear (weekly_bear)\n"
        "- L2 segment turns Broken from Alive/Resting\n"
        "- L3 stays Exhausted while L2 remains Alive\n"
    )
    sec4 = (
        f"## 4. {i18n.section_title(4, lang)}\n"
        f"- {principle}: {i18n.section_principle(4, lang)}\n"
        f"{invalidation}"
    )

    # --- 5. 系统动作 ---
    if rewrite is not None:
        draft, result = rewrite
        prev_action: CompassAction = draft
        step_lines = []
        for n, step in enumerate(result.steps, start=1):
            prev_label = i18n.action_text(prev_action, lang)
            after_label = i18n.action_text(step.action_after, lang)
            if zh:
                step_lines.append(
                    f"  {n}. {i18n.reason_text(step.reason_code, lang)}"
                    f"（动作：{prev_label} → {after_label}）"
                )
            else:
                step_lines.append(
                    f"  {n}. {i18n.reason_text(step.reason_code, lang)}"
                    f" (action: {prev_label} -> {after_label})"
                )
            prev_action = step.action_after
        if step_lines:
            constraints = f"- {lb('triggered')}:\n" + "\n".join(step_lines) + "\n"
        else:
            constraints = f"- {lb('triggered')}: {lb('no_constraints')}\n"
        verdict_action = i18n.action_text(result.final_action, lang)
    else:
        constraints = f"- {lb('no_draft')}\n"
        verdict_action = i18n.action_text(c.action_bias, lang)
    sec5 = (
        f"## 5. {i18n.section_title(5, lang)}\n"
        f"- {verdict}: {verdict_action}\n"
        f"- {principle}: {i18n.section_principle(5, lang)}\n"
        f"{constraints}"
    )

    # --- 6. 较昨日 ---
    if c.vs_previous is None:
        sec6_body = f"- {lb('no_snapshot')}\n"
    else:
        vp = c.vs_previous
        arrow = {"up": "↑", "down": "↓", "flat": "→"}
        sec6_body = (
            f"- {lb('prev_date')}: {vp.previous_trade_date}\n"
            f"- {lb('phase_chg')}: {i18n.phase_text(vp.previous_phase, lang)}"
            f" {arrow[vp.phase_change]} {i18n.phase_text(c.phase, lang)}"
            f"（{i18n.change_text(vp.phase_change, lang)}）\n"
            f"- {lb('l0_chg')}: {arrow[vp.l0_change]} {i18n.change_text(vp.l0_change, lang)}\n"
            f"- {lb('l2_chg')}: {arrow[vp.l2_change]} {i18n.change_text(vp.l2_change, lang)}\n"
        )
    sec6 = (
        f"## 6. {i18n.section_title(6, lang)}\n"
        f"- {principle}: {i18n.section_principle(6, lang)}\n"
        f"{sec6_body}"
    )

    # --- 7. 风险与数据限制 ---
    sec7 = (
        f"## 7. {i18n.section_title(7, lang)}\n"
        f"- {principle}: {i18n.section_principle(7, lang)}\n"
        f"- {lb('bar_status')}: {i18n.bar_text(c.bar_status, lang)}\n"
        f"- {lb('daily_samples')}: {_bars(c.quality.sample_size, lang)}"
        f" | {lb('weekly_samples')}: {_bars(c.quality.weekly_sample_size, lang)}\n"
        f"- {lb('quality')}: {i18n.quality_status_text(c.quality.status, lang)}\n"
    )

    # --- 9. 择时信号（L4，永远渲染；无信号也写明） ---
    if c.timing:
        blocks = []
        for s in c.timing:
            lines = [
                f"- {verdict}: {i18n.timing_type_text(s.type, lang)}"
                f" — {i18n.timing_status_text(s.status, lang)}"
            ]
            if s.countertrend:
                lines.append(f"- {lb('timing_countertrend')}")
            for code in s.reason_codes:
                lines.append(f"- {i18n.reason_text(code, lang)}")
            if s.status == "triggered" and s.trigger_price is not None:
                numbers_line = (
                    f"- {numbers}: {lb('timing_trigger')} {_fmt(s.trigger_price)}"
                    f" | {lb('timing_invalidate')} {_fmt(s.invalidation_price)}"
                    f" | {lb('timing_horizon')} {s.horizon_days} {lb('timing_days_unit')}"
                )
            else:
                numbers_line = (
                    f"- {numbers}: {lb('timing_trigger')} —"
                    f" | {lb('timing_invalidate')} —"
                    f"（{i18n.timing_status_text('armed', lang)}）"
                )
            lines.append(numbers_line)
            lines.append(f"- {how}: {i18n.position_hint_text(s.position_hint, lang)}")
            blocks.append("\n".join(lines))
        sec9 = (
            f"## 9. {i18n.section_title(9, lang)}\n"
            f"- {principle}: {lb('timing_principle')}\n"
            + "\n\n".join(blocks)
            + "\n"
        )
    else:
        sec9 = f"## 9. {i18n.section_title(9, lang)}\n- {lb('no_timing')}\n"

    # --- 8. 其它模块 ---
    other_line = (
        "- 缠论 / 波浪 / 其它模块独立运行，与本罗盘互不归因、互不读取。\n"
        if zh
        else
        "- Chan / Elliott / other modules run independently; no shared reads or attribution.\n"
    )
    sec8 = (
        f"## 8. {i18n.section_title(8, lang)}\n"
        f"- {principle}: {i18n.section_principle(8, lang)}\n"
        f"{other_line}"
        f"\n_{lb('disclaimer')}: {i18n.disclaimer_text(lang)}_\n"
    )

    return head + "\n" + sec1 + sec2 + sec3 + sec4 + sec5 + sec6 + sec7 + sec8 + sec9


def _bars(n: int, lang: i18n.Language) -> str:
    return f"{n} 根" if lang == "zh" else f"{n} bars"


def _pct_distance(price: Optional[float], ema200: Optional[float]) -> Optional[float]:
    """Percent distance of the daily close to the 200-week EMA.

    Cross-period comparison on purpose: the daily close is the tradable price,
    the 200-week EMA is the filter line. None when either side is missing.
    """
    if price is None or ema200 is None or ema200 == 0:
        return None
    return (price - ema200) / ema200 * 100.0


def _trend_arrow(slope: Optional[float]) -> str:
    if slope is None or slope == 0:
        return "→"
    return "▲" if slope > 0 else "▼"


def _fmt(value: Optional[float | int | str]) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
