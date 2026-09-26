# -*- coding: utf-8 -*-
"""Tests for src/services/compass/rewriter.py (P2 PR-B2, plan §4.5.2 table)."""

from __future__ import annotations

from src.services.compass.rewriter import CompassState, rewrite, to_compass_draft
from src.schemas.compass import ActionReasonCode


def _state(**overrides: object) -> CompassState:
    base: dict[str, object] = {
        "weekly": "weekly_bull",
        "annual": "annual_bull",
        "segment": "alive",
        "rhythm": "healthy",
        "phase": "trend_expanding",
        "bar_status": "closed",
        "data_usable": True,
    }
    base.update(overrides)
    return CompassState(**base)  # type: ignore[arg-type]


class TestDataMissing:
    def test_data_unusable_defaults_watch(self) -> None:
        result = rewrite("sell", _state(data_usable=False))
        assert result.final_action == "watch"
        assert result.reason_codes == ("data_missing",)


class TestIntradayUnconfirmed:
    def test_intraday_blocks_buy(self) -> None:
        result = rewrite("buy", _state(bar_status="intraday_unconfirmed"))
        assert result.final_action == "watch"
        assert "intraday_unconfirmed_buy_blocked" in result.reason_codes

    def test_intraday_does_not_block_sell(self) -> None:
        result = rewrite("sell", _state(bar_status="intraday_unconfirmed"))
        assert result.final_action == "sell"
        assert "intraday_unconfirmed_buy_blocked" not in result.reason_codes


class TestWeeklyFilter:
    def test_weekly_bear_blocks_buy(self) -> None:
        result = rewrite("buy", _state(weekly="weekly_bear"))
        assert result.final_action == "watch"
        assert "weekly_bear_buy_blocked" in result.reason_codes

    def test_weekly_bear_does_not_block_sell(self) -> None:
        result = rewrite("sell", _state(weekly="weekly_bear"))
        assert result.final_action == "sell"

    def test_weekly_bear_passes_buy_with_bottom_fishing_signal(self) -> None:
        # §13.8 (B7): 周线空头下的超卖抄底信号放行买入，
        # 但仅允许逆势博弈仓（仓位提示 light，与趋势仓分离）。
        result = rewrite(
            "buy", _state(weekly="weekly_bear", timing_signal="bottom_fishing")
        )
        assert result.final_action == "buy"
        assert "weekly_bear_bottom_fishing_pass" in result.reason_codes
        assert "weekly_bear_buy_blocked" not in result.reason_codes
        assert [(s.reason_code, s.action_after) for s in result.steps] == [
            ("weekly_bear_bottom_fishing_pass", "buy"),
        ]

    def test_weekly_bear_blocks_buy_with_other_timing_signals(self) -> None:
        result = rewrite(
            "buy", _state(weekly="weekly_bear", timing_signal="pullback_entry")
        )
        assert result.final_action == "watch"
        assert "weekly_bear_buy_blocked" in result.reason_codes

    def test_weekly_bear_blocks_buy_with_no_timing_signal(self) -> None:
        result = rewrite("buy", _state(weekly="weekly_bear"))
        assert result.final_action == "watch"

    def test_weekly_transition_passes_buy_per_section13_1(self) -> None:
        # §13.1 frozen decision (分级): weekly_transition only downgrades
        # confidence; the rewriter must NOT rewrite the action.
        result = rewrite("buy", _state(weekly="weekly_transition"))
        assert result.final_action == "buy"
        assert "weekly_transition_buy_blocked" not in result.reason_codes

    def test_weekly_disabled_passes(self) -> None:
        result = rewrite("buy", _state(weekly="weekly_disabled"))
        assert result.final_action == "buy"


class TestPhaseDowngrades:
    def test_coiling_downgrades_buy(self) -> None:
        result = rewrite("buy", _state(phase="coiling"))
        assert result.final_action == "watch"
        assert "coiling_transitioning_buy_downgraded" in result.reason_codes

    def test_transitioning_downgrades_buy(self) -> None:
        result = rewrite("buy", _state(phase="transitioning"))
        assert result.final_action == "watch"

    def test_tiring_downgrades_buy(self) -> None:
        result = rewrite("buy", _state(phase="trend_tiring", rhythm="exhausted"))
        assert result.final_action == "watch"
        assert "tiring_buy_downgraded" in result.reason_codes

    def test_holding_does_not_upgrade_or_block(self) -> None:
        result = rewrite("buy", _state(phase="trend_holding"))
        assert result.final_action == "buy"


class TestL1Disabled:
    def test_l1_disabled_blocks_buy(self) -> None:
        result = rewrite("buy", _state(annual="annual_disabled", phase="trend_holding"))
        assert result.final_action == "watch"
        assert "l1_disabled_buy_blocked" in result.reason_codes


class TestSellSideRules:
    def test_resting_blocks_sell(self) -> None:
        result = rewrite("sell", _state(segment="resting", phase="trend_holding"))
        assert result.final_action == "watch"
        assert result.reason_codes == ("resting_sell_blocked",)

    def test_broken_bear_allows_sell_from_watch(self) -> None:
        result = rewrite(
            "watch",
            _state(annual="annual_bear", segment="broken", phase="coiling"),
        )
        assert result.final_action == "sell"
        assert "l2_broken_bear_allow_sell" in result.reason_codes

    def test_broken_bear_allows_sell_from_buy(self) -> None:
        result = rewrite(
            "buy",
            _state(annual="annual_bear", segment="broken", phase="coiling"),
        )
        assert result.final_action == "sell"

    def test_broken_bull_blocks_sell(self) -> None:
        result = rewrite(
            "sell",
            _state(annual="annual_bull", segment="broken", phase="transitioning"),
        )
        assert result.final_action == "watch"
        assert "l2_broken_bull_sell_blocked" in result.reason_codes


class TestL1L2BearDefault:
    def test_l1_l2_bear_defaults_sell(self) -> None:
        result = rewrite(
            "watch",
            _state(annual="annual_bear", segment="alive", rhythm="cooling",
                   phase="trend_holding"),
        )
        assert result.final_action == "sell"
        assert "l1_l2_bear_sell_default" in result.reason_codes

    def test_l3_exhausted_downgrades_sell_to_watch(self) -> None:
        result = rewrite(
            "watch",
            _state(annual="annual_bear", segment="alive", rhythm="exhausted",
                   phase="trend_tiring"),
        )
        assert result.final_action == "watch"
        assert result.reason_codes == ("l3_exhausted_sell_downgraded",)

    def test_l1_l2_bear_default_requires_closed_bar(self) -> None:
        result = rewrite(
            "watch",
            _state(annual="annual_bear", segment="alive", rhythm="cooling",
                   phase="trend_holding", bar_status="intraday_unconfirmed"),
        )
        assert result.final_action == "watch"


class TestHealthyStackBlocksSell:
    def test_healthy_bull_stack_blocks_sell(self) -> None:
        result = rewrite(
            "sell",
            _state(annual="annual_bull", segment="alive", rhythm="healthy",
                   phase="trend_expanding"),
        )
        assert result.final_action == "watch"
        assert result.reason_codes == ("l1_l2_l3_healthy_buy_allowed",)

    def test_healthy_stack_allows_sell_when_weekly_bear(self) -> None:
        # L0=weekly_bear removes the healthy-stack sell shield (§4.5.2 row 12).
        result = rewrite(
            "sell",
            _state(weekly="weekly_bear", annual="annual_bull", segment="alive",
                   rhythm="healthy", phase="trend_holding"),
        )
        assert result.final_action == "sell"


class TestPassthroughReasons:
    def test_market_guardrail_softened_passthrough(self) -> None:
        result = rewrite("watch", _state(), prior_softened=True)
        assert result.final_action == "watch"
        assert result.reason_codes == ("market_guardrail_softened",)

    def test_phase_guardrail_suppressed_passthrough(self) -> None:
        result = rewrite("watch", _state(), prior_suppressed=True)
        assert result.reason_codes == ("phase_guardrail_suppressed",)

    def test_compass_rule_takes_priority_over_passthrough(self) -> None:
        result = rewrite(
            "buy", _state(weekly="weekly_bear"), prior_softened=True
        )
        assert "weekly_bear_buy_blocked" in result.reason_codes
        assert "market_guardrail_softened" not in result.reason_codes

    def test_no_reasons_when_clean(self) -> None:
        result = rewrite("buy", _state())
        assert result.final_action == "buy"
        assert result.reason_codes == ()


class TestReasonCodeSchemaAlignment:
    def test_all_emitted_codes_are_valid_enum_members(self) -> None:
        valid: tuple[str, ...] = ActionReasonCode.__args__  # type: ignore[attr-defined]
        result = rewrite(
            "buy",
            _state(weekly="weekly_bear", phase="coiling"),
        )
        assert result.reason_codes
        for code in result.reason_codes:
            assert code in valid


class TestToCompassDraft:
    def test_eight_state_narrowing(self) -> None:
        assert to_compass_draft("buy") == "buy"
        assert to_compass_draft("add") == "buy"
        assert to_compass_draft("sell") == "sell"
        assert to_compass_draft("reduce") == "sell"
        assert to_compass_draft("hold") == "watch"
        assert to_compass_draft("watch") == "watch"
        assert to_compass_draft("avoid") == "watch"
        assert to_compass_draft("alert") == "watch"
        assert to_compass_draft(None) == "watch"
        assert to_compass_draft("") == "watch"


class TestInferBarStatus:
    from datetime import date as _date, datetime as _datetime

    def test_previous_day_bar_is_closed(self) -> None:
        from src.services.compass.rewriter import infer_bar_status

        d = self._date(2026, 9, 10)
        assert infer_bar_status(d, now=self._datetime(2026, 9, 11, 10, 0)) == "closed"

    def test_today_bar_before_close_is_unconfirmed(self) -> None:
        from src.services.compass.rewriter import infer_bar_status

        d = self._date(2026, 9, 11)
        assert infer_bar_status(d, now=self._datetime(2026, 9, 11, 10, 0)) == "intraday_unconfirmed"
        assert infer_bar_status(d, now=self._datetime(2026, 9, 11, 15, 29)) == "intraday_unconfirmed"

    def test_today_bar_after_close_buffer_is_closed(self) -> None:
        from src.services.compass.rewriter import infer_bar_status

        d = self._date(2026, 9, 11)
        assert infer_bar_status(d, now=self._datetime(2026, 9, 11, 15, 30)) == "closed"
        assert infer_bar_status(d, now=self._datetime(2026, 9, 11, 21, 0)) == "closed"


class TestSteps:
    """RewriteStep 因果链：每步记录触发码与动作值，顺序与 reason_codes 一致。"""

    def test_user_case_buy_downgraded_then_bear_breakout_sell(self) -> None:
        # 用户实测 case：初稿买入 → 阶段切换降级观望 → 空头结构破坏允许离场 → 卖出。
        result = rewrite(
            "buy",
            _state(phase="transitioning", annual="annual_bear", segment="broken"),
        )
        assert result.final_action == "sell"
        assert [(s.reason_code, s.action_after) for s in result.steps] == [
            ("coiling_transitioning_buy_downgraded", "watch"),
            ("l2_broken_bear_allow_sell", "sell"),
        ]

    def test_steps_align_with_reason_codes(self) -> None:
        result = rewrite("buy", _state(weekly="weekly_bear", phase="coiling"))
        assert [s.reason_code for s in result.steps] == list(result.reason_codes)
        assert result.steps[0].action_after == "watch"

    def test_data_missing_records_step(self) -> None:
        result = rewrite("sell", _state(data_usable=False))
        assert [(s.reason_code, s.action_after) for s in result.steps] == [
            ("data_missing", "watch"),
        ]

    def test_no_constraint_yields_empty_steps(self) -> None:
        result = rewrite("buy", _state())
        assert result.steps == ()

    def test_audit_only_step_keeps_action_unchanged(self) -> None:
        result = rewrite("buy", _state(), prior_softened=True)
        assert [(s.reason_code, s.action_after) for s in result.steps] == [
            ("market_guardrail_softened", "buy"),
        ]

    def test_l3_exhausted_records_noop_downgrade(self) -> None:
        # 双空头默认卖出，但 L3 失配把卖出降回观望：step 记录「维持观望」。
        result = rewrite(
            "watch",
            _state(annual="annual_bear", segment="alive", rhythm="exhausted"),
        )
        assert result.final_action == "watch"
        assert [(s.reason_code, s.action_after) for s in result.steps] == [
            ("l3_exhausted_sell_downgraded", "watch"),
        ]
