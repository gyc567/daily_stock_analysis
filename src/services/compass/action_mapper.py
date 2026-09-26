# -*- coding: utf-8 -*-
"""CompassAction -> decision-field mapping for the midterm trend compass.

Issue scope: docs/midterm-trend-compass-plan.md §4.5.5 (映射单一函数维护).

The mapping CompassAction -> (decision_type / DecisionAction /
InvestmentConclusion.action / operation_advice) lives in this one module;
pipeline code must not scatter ad-hoc translations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import icontract

from src.schemas.compass import CompassAction
from src.schemas.decision_action import DecisionAction

DecisionType = Literal["buy", "hold", "sell"]


@dataclass(frozen=True)
class MappedAction:
    """All decision-field write-backs for one compass action."""

    decision_type: DecisionType
    action: DecisionAction
    investment_action: Literal["建仓", "观察", "止损"]
    operation_advice: Literal["买入", "观望", "卖出"]


_MAP: dict[CompassAction, MappedAction] = {
    "buy": MappedAction(
        decision_type="buy",
        action="buy",
        investment_action="建仓",
        operation_advice="买入",
    ),
    "watch": MappedAction(
        decision_type="hold",
        action="watch",
        investment_action="观察",
        operation_advice="观望",
    ),
    "sell": MappedAction(
        decision_type="sell",
        action="sell",
        investment_action="止损",
        operation_advice="卖出",
    ),
}


@icontract.require(
    lambda action: action in ("buy", "watch", "sell"),
    "action must be a valid CompassAction",
)
@icontract.ensure(
    lambda action, result: result.action
    == {"buy": "buy", "watch": "watch", "sell": "sell"}[action],
    "DecisionAction must mirror the compass action exactly (buy/watch/sell)",
)
@icontract.ensure(
    lambda action, result: result.decision_type
    == {"buy": "buy", "watch": "hold", "sell": "sell"}[action],
    "decision_type follows the buy/hold/sell statistics contract",
)
def map_compass_action(action: CompassAction) -> MappedAction:
    """Map a three-state compass action to all decision write-back fields.

    ``watch`` maps to ``decision_type="hold"`` because that field is the
    legacy buy/hold/sell statistics contract with no neutral state; the
    eight-state ``action`` field carries the precise ``watch`` semantics.
    """
    return _MAP[action]
