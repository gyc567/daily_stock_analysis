# -*- coding: utf-8 -*-
"""Action rewriter for the midterm trend compass (P2).

Issue scope: docs/midterm-trend-compass-plan.md §4.5.2 (硬约束改写表),
with the §13 maintainer decisions frozen on 2026-09-11:

- §13.1 (分级): only ``weekly_bear`` blocks ``buy``; ``weekly_transition``
  downgrades confidence only (outside the rewriter's action scope), so the
  ``weekly_transition_buy_blocked`` code stays reserved and is never emitted.
- §13.2 (采纳): L1 bear + L2 alive defaults to ``sell``; L3 exhausted
  downgrades that to ``watch``.

Pure function: no I/O, no globals. Pipeline supplies the compass state;
any fetch failure upstream must set ``data_usable=False`` (rule 1 handles
the pass-through-to-watch fallback).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Optional, Tuple

import icontract

from src.schemas.compass import (
    ActionReasonCode,
    BarStatus,
    CompassAction,
    L0Status,
    L1Status,
    L2Status,
    L3Status,
    Phase,
)

_BEARISH_L1: Tuple[L1Status, ...] = ("annual_bear",)
_BULLISH_L1: Tuple[L1Status, ...] = ("annual_bull",)

# 当日 K 线收盘确认时间（本地时间，含 30 分钟数据商落地缓冲）。
_CN_CLOSE_CONFIRM: Tuple[int, int] = (15, 30)


def infer_bar_status(last_bar_date: date, *, now: Optional[datetime] = None) -> BarStatus:
    """Classify the last daily bar.

    Bars before today are always closed. Today's bar counts as confirmed only
    after the A-share close buffer (15:30 local server time); earlier it is
    ``intraday_unconfirmed`` (T+1: no intraday correction right). Server local
    time is assumed to be the market timezone (cn deployment default).
    """
    moment = now or datetime.now()
    if last_bar_date < moment.date():
        return "closed"
    if (moment.hour, moment.minute) >= _CN_CLOSE_CONFIRM:
        return "closed"
    return "intraday_unconfirmed"


@dataclass(frozen=True)
class CompassState:
    """Engine output + data quality, everything the rewrite table needs."""

    weekly: L0Status
    annual: L1Status
    segment: L2Status
    rhythm: L3Status
    phase: Phase
    bar_status: BarStatus
    data_usable: bool = True
    # L4 timing context (§13.8): a bottom_fishing draft under weekly_bear is
    # an explicit counter-trend sleeve with its own light-position discipline,
    # so row 3 passes it through instead of vetoing (row 3 amendment).
    timing_signal: Optional[Literal["pullback_entry", "bottom_fishing", "top_escape"]] = None


@dataclass(frozen=True)
class RewriteStep:
    """One fired constraint in evaluation order.

    ``action_after`` is the action value after this constraint applied
    (possibly unchanged, e.g. an audit-only downgrade), so callers can
    render the full causal chain without replaying the rule table.
    """

    reason_code: ActionReasonCode
    action_after: CompassAction


@dataclass(frozen=True)
class RewriteResult:
    final_action: CompassAction
    reason_codes: Tuple[ActionReasonCode, ...]
    steps: Tuple[RewriteStep, ...] = ()


@icontract.require(
    lambda initial_draft: initial_draft in ("buy", "watch", "sell"),
    "initial_draft must be a valid CompassAction",
)
@icontract.ensure(
    lambda result: result.final_action in ("buy", "watch", "sell"),
    "final_action must be a valid CompassAction",
)
@icontract.ensure(
    lambda result: len(result.reason_codes) <= 10,
    "reason_codes must fit the MidtrendCompass.action_reason schema limit",
)
def rewrite(
    initial_draft: CompassAction,
    state: CompassState,
    *,
    prior_softened: bool = False,
    prior_suppressed: bool = False,
) -> RewriteResult:
    """Rewrite a draft action per the §4.5.2 hard-constraint table.

    Rules evaluate top-down; each rule sees the action produced by the rules
    before it. Reason codes accumulate in firing order (deduplicated) so the
    audit trail shows every constraint that applied, not just the last one.
    ``steps`` additionally records the action value after each fired
    constraint, letting API consumers render the causal chain without
    replaying the rule table.

    ``prior_softened`` / ``prior_suppressed`` record pass-through downgrades
    from ``daily_market_context_guardrail`` / ``phase_decision_guardrail``
    when no compass hard rule fires (table rows 13-14).
    """
    if not state.data_usable:
        return RewriteResult(
            final_action="watch",
            reason_codes=("data_missing",),
            steps=(RewriteStep("data_missing", "watch"),),
        )

    action: CompassAction = initial_draft
    reasons: list[ActionReasonCode] = []
    steps: list[RewriteStep] = []

    def _apply(condition: bool, new_action: CompassAction, code: ActionReasonCode) -> None:
        nonlocal action
        if condition and code not in reasons:
            reasons.append(code)
            action = new_action
            steps.append(RewriteStep(code, action))

    closed = state.bar_status == "closed"

    # Row 2: unconfirmed / stale / suspended bars block fresh buys (T+1 discipline).
    _apply(
        state.bar_status in ("intraday_unconfirmed", "stale", "suspended")
        and action == "buy",
        "watch",
        "intraday_unconfirmed_buy_blocked",
    )
    # Row 3 (§13.1 + §13.8 amendment): weekly_bear hard-blocks buy — except an
    # explicit bottom_fishing timing draft, which passes through as its own
    # counter-trend sleeve (light position, hard stop; see derive_l4).
    _apply(
        state.weekly == "weekly_bear"
        and action == "buy"
        and state.timing_signal != "bottom_fishing",
        "watch",
        "weekly_bear_buy_blocked",
    )
    # Row 3 pass-through: the two conditions are mutually exclusive by
    # construction (timing_signal != bottom_fishing vs == bottom_fishing),
    # so no weekly_bear_buy_blocked guard is needed here.
    if (
        state.weekly == "weekly_bear"
        and action == "buy"
        and state.timing_signal == "bottom_fishing"
    ):
        reasons.append("weekly_bear_bottom_fishing_pass")
        steps.append(RewriteStep("weekly_bear_bottom_fishing_pass", action))
    # Row 4: weekly_transition — §13.1 分级决策：仅降级 confidence（rewriter 不改写动作），
    # weekly_transition_buy_blocked 保留为预留 code，P2 不发出。
    # Row 5: L1 disabled blocks buy (sample too small to trust trend expansion).
    _apply(
        state.annual == "annual_disabled" and action == "buy",
        "watch",
        "l1_disabled_buy_blocked",
    )
    # Row 6: coiling / transitioning phases downgrade buy.
    _apply(
        state.phase in ("coiling", "transitioning") and action == "buy",
        "watch",
        "coiling_transitioning_buy_downgraded",
    )
    # Row 7: tiring phase downgrades buy.
    _apply(
        state.phase == "trend_tiring" and action == "buy",
        "watch",
        "tiring_buy_downgraded",
    )
    # Row 8: resting segment blocks sell (a pullback is not a reversal).
    _apply(
        state.segment == "resting" and action == "sell",
        "watch",
        "resting_sell_blocked",
    )
    # Row 9: broken segment in a bearish L1 allows exiting (watch/buy -> sell).
    _apply(
        state.segment == "broken"
        and state.annual in _BEARISH_L1
        and closed
        and action in ("watch", "buy"),
        "sell",
        "l2_broken_bear_allow_sell",
    )
    # Row 10: broken segment inside a bullish L1 blocks panic sell.
    _apply(
        state.segment == "broken"
        and state.annual in _BULLISH_L1
        and action == "sell",
        "watch",
        "l2_broken_bull_sell_blocked",
    )
    # Row 11 (§13.2): double-bear alive defaults watch -> sell, unless L3 is
    # exhausted, which downgrades the sell back to watch.
    if (
        state.annual in _BEARISH_L1
        and state.segment == "alive"
        and closed
        and action == "watch"
    ):
        if state.rhythm == "exhausted":
            _apply(True, "watch", "l3_exhausted_sell_downgraded")
        else:
            _apply(True, "sell", "l1_l2_bear_sell_default")
    # Row 12: fully healthy bull stack blocks sells that fight the trend.
    _apply(
        state.annual in _BULLISH_L1
        and state.segment == "alive"
        and state.rhythm == "healthy"
        and state.weekly != "weekly_bear"
        and closed
        and action == "sell",
        "watch",
        "l1_l2_l3_healthy_buy_allowed",
    )

    # Rows 13-14: pass-through audit codes when no compass rule fired.
    if not reasons:
        if prior_suppressed:
            reasons.append("phase_guardrail_suppressed")
            steps.append(RewriteStep("phase_guardrail_suppressed", action))
        elif prior_softened:
            reasons.append("market_guardrail_softened")
            steps.append(RewriteStep("market_guardrail_softened", action))

    return RewriteResult(
        final_action=action,
        reason_codes=tuple(reasons),
        steps=tuple(steps),
    )


@icontract.ensure(
    lambda result: result in ("buy", "watch", "sell"),
    "draft must be a valid CompassAction",
)
def to_compass_draft(value: Optional[str]) -> CompassAction:
    """Narrow an eight-state DecisionAction (or raw text) to a compass draft.

    buy/add -> buy; sell/reduce -> sell; everything else (hold/watch/avoid/
    alert/unknown) -> watch. Conservative by construction: ambiguous states
    never produce a buy draft.
    """
    normalized = str(value).strip().lower()
    if normalized in ("buy", "add"):
        return "buy"
    if normalized in ("sell", "reduce"):
        return "sell"
    return "watch"
