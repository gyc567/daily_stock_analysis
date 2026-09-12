# -*- coding: utf-8 -*-
"""Tests for src/services/compass/action_mapper.py (P2 PR-B1)."""

from __future__ import annotations

import pytest

from src.schemas.decision_action import DecisionAction
from src.services.compass.action_mapper import MappedAction, map_compass_action


class TestCompassToDecisionAction:
    def test_buy_maps_to_buy(self) -> None:
        mapped = map_compass_action("buy")
        assert mapped.action == "buy"
        assert isinstance(mapped, MappedAction)

    def test_watch_maps_to_watch(self) -> None:
        assert map_compass_action("watch").action == "watch"

    def test_sell_maps_to_sell(self) -> None:
        assert map_compass_action("sell").action == "sell"

    def test_all_actions_are_valid_decision_actions(self) -> None:
        for compass_action in ("buy", "watch", "sell"):
            mapped = map_compass_action(compass_action)  # type: ignore[arg-type]
            assert mapped.action in DecisionAction.__args__  # type: ignore[attr-defined]


class TestCompassToInvestmentConclusion:
    @pytest.mark.parametrize(
        ("compass_action", "investment_action"),
        [("buy", "建仓"), ("watch", "观察"), ("sell", "止损")],
    )
    def test_investment_action_mapping(
        self, compass_action: str, investment_action: str
    ) -> None:
        mapped = map_compass_action(compass_action)  # type: ignore[arg-type]
        assert mapped.investment_action == investment_action

    def test_no_forbidden_investment_actions(self) -> None:
        # Plan §4.5.5: buy 严禁 add/hold/reduce; watch 不允许降为 hold; sell 严禁 reduce.
        assert map_compass_action("buy").investment_action == "建仓"
        assert map_compass_action("watch").investment_action == "观察"
        assert map_compass_action("sell").investment_action == "止损"


class TestDecisionTypeContract:
    def test_decision_type_follows_statistics_contract(self) -> None:
        # decision_type is the legacy buy/hold/sell contract; watch -> hold is
        # the documented narrowing (see map_compass_action docstring).
        assert map_compass_action("buy").decision_type == "buy"
        assert map_compass_action("watch").decision_type == "hold"
        assert map_compass_action("sell").decision_type == "sell"

    def test_operation_advice_labels(self) -> None:
        assert map_compass_action("buy").operation_advice == "买入"
        assert map_compass_action("watch").operation_advice == "观望"
        assert map_compass_action("sell").operation_advice == "卖出"

    def test_result_is_frozen(self) -> None:
        mapped = map_compass_action("buy")
        with pytest.raises(AttributeError):
            mapped.action = "sell"  # type: ignore[misc]
