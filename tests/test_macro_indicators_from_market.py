# -*- coding: utf-8 -*-
"""P5-fix: macro_indicators_from_market 单元测试。

覆盖 3 个枚举 × 2 个数据源 = 6 个组合 + 边界 + 防御性输入。
"""

from __future__ import annotations

import pytest

from src.services.macro_indicators_from_market import (
    LIQUIDITY_ABUNDANT_THRESHOLD_YI,
    LIQUIDITY_MODERATE_THRESHOLD_YI,
    MONETARY_ACCOMMODATIVE_PCT,
    MONETARY_TIGHT_PCT,
    _infer_liquidity_from_market_stats,
    _infer_monetary_policy_from_indices,
    infer_objective_macro_indicators,
)


class TestInferLiquidityFromMarketStats:
    """liquidity_indicator 推断"""

    def test_abundant_high_volume(self) -> None:
        result = _infer_liquidity_from_market_stats(
            {"total_amount": LIQUIDITY_ABUNDANT_THRESHOLD_YI + 100}
        )
        assert result == "abundant"

    def test_abundant_threshold_exact(self) -> None:
        """边界值 = 阈值 → abundant（>= 闭区间）"""
        result = _infer_liquidity_from_market_stats(
            {"total_amount": LIQUIDITY_ABUNDANT_THRESHOLD_YI}
        )
        assert result == "abundant"

    def test_moderate_mid_volume(self) -> None:
        result = _infer_liquidity_from_market_stats(
            {
                "total_amount": (
                    LIQUIDITY_ABUNDANT_THRESHOLD_YI + LIQUIDITY_MODERATE_THRESHOLD_YI
                )
                / 2
            }
        )
        assert result == "moderate"

    def test_moderate_threshold_exact(self) -> None:
        result = _infer_liquidity_from_market_stats(
            {"total_amount": LIQUIDITY_MODERATE_THRESHOLD_YI}
        )
        assert result == "moderate"

    def test_scarce_low_volume(self) -> None:
        result = _infer_liquidity_from_market_stats({"total_amount": 100.0})
        assert result == "scarce"

    def test_scarce_threshold_just_below(self) -> None:
        result = _infer_liquidity_from_market_stats(
            {"total_amount": LIQUIDITY_MODERATE_THRESHOLD_YI - 1}
        )
        assert result == "scarce"

    def test_zero_amount_returns_none(self) -> None:
        assert _infer_liquidity_from_market_stats({"total_amount": 0}) is None

    def test_negative_amount_returns_none(self) -> None:
        assert _infer_liquidity_from_market_stats({"total_amount": -100}) is None

    def test_missing_total_amount_returns_none(self) -> None:
        assert _infer_liquidity_from_market_stats({}) is None

    def test_non_numeric_returns_none(self) -> None:
        assert _infer_liquidity_from_market_stats({"total_amount": "abc"}) is None

    def test_none_input_returns_none(self) -> None:
        assert _infer_liquidity_from_market_stats(None) is None  # type: ignore[arg-type]

    def test_non_dict_input_returns_none(self) -> None:
        assert _infer_liquidity_from_market_stats("not_a_dict") is None  # type: ignore[arg-type]
        assert _infer_liquidity_from_market_stats([1, 2, 3]) is None  # type: ignore[arg-type]


class TestInferMonetaryPolicyFromIndices:
    """monetary_policy 推断（基于主要指数涨跌幅均值）"""

    @pytest.fixture
    def strong_up_indices(self) -> list[dict]:
        return [
            {"code": "000300", "change_pct": 3.0},
            {"code": "399006", "change_pct": 4.0},
            {"code": "000001", "change_pct": 2.5},
        ]

    @pytest.fixture
    def strong_down_indices(self) -> list[dict]:
        return [
            {"code": "000300", "change_pct": -3.0},
            {"code": "399006", "change_pct": -2.5},
        ]

    def test_accommodative_strong_up(self, strong_up_indices) -> None:
        assert _infer_monetary_policy_from_indices(strong_up_indices) == "accommodative"

    def test_tight_strong_down(self, strong_down_indices) -> None:
        assert _infer_monetary_policy_from_indices(strong_down_indices) == "tight"

    def test_neutral_mid(self) -> None:
        result = _infer_monetary_policy_from_indices(
            [{"code": "000300", "change_pct": 0.5}]
        )
        assert result == "neutral"

    def test_neutral_threshold_above(self) -> None:
        """边界值 > threshold → accommodative"""
        result = _infer_monetary_policy_from_indices(
            [{"code": "000300", "change_pct": MONETARY_ACCOMMODATIVE_PCT + 0.5}]
        )
        assert result == "accommodative"

    def test_neutral_threshold_below(self) -> None:
        """边界值 < threshold → tight"""
        result = _infer_monetary_policy_from_indices(
            [{"code": "000300", "change_pct": MONETARY_TIGHT_PCT - 0.5}]
        )
        assert result == "tight"

    def test_neutral_threshold_exact(self) -> None:
        """边界值 = threshold → neutral（开区间严格比较）"""
        result = _infer_monetary_policy_from_indices(
            [{"code": "000300", "change_pct": MONETARY_ACCOMMODATIVE_PCT}]
        )
        assert result == "neutral"

    def test_alternate_field_name_change(self) -> None:
        """支持 'change' 字段别名"""
        result = _infer_monetary_policy_from_indices(
            [{"code": "000300", "change": 3.0}]
        )
        assert result == "accommodative"

    def test_non_target_code_ignored(self) -> None:
        """非目标代码（如 999999）即使涨 50% 也不影响"""
        result = _infer_monetary_policy_from_indices(
            [{"code": "999999", "change_pct": 50.0}]
        )
        assert result is None

    def test_target_code_with_sh_prefix(self) -> None:
        """sh 前缀的代码也能被识别"""
        result = _infer_monetary_policy_from_indices(
            [
                {"code": "sh000300", "change_pct": 3.0},
                {"code": "sz399006", "change_pct": 4.0},
            ]
        )
        assert result == "accommodative"

    def test_target_code_with_sz_prefix(self) -> None:
        """sz 前缀的代码也能被识别"""
        result = _infer_monetary_policy_from_indices(
            [{"code": "sz399001", "change_pct": -3.0}]
        )
        assert result == "tight"

    def test_target_code_with_bj_prefix_ignored(self) -> None:
        """bj 前缀 + 非目标代码被忽略"""
        result = _infer_monetary_policy_from_indices(
            [{"code": "bj999999", "change_pct": 3.0}]
        )
        # bj 前缀 + 不在白名单 → 忽略 → 返回 None
        assert result is None

    def test_mixed_prefix_formats(self) -> None:
        """sh/sz/无前缀混合，应都识别"""
        result = _infer_monetary_policy_from_indices(
            [
                {"code": "sh000300", "change_pct": 3.0},  # sh
                {"code": "sz399006", "change_pct": 4.0},  # sz
                {"code": "000001", "change_pct": 2.5},  # 无前缀
            ]
        )
        assert result == "accommodative"

    def test_neutral_in_real_today_data(self) -> None:
        """真实今日数据：所有指数 -0.5% ~ -5.0%，均值 -1.7% → neutral"""
        result = _infer_monetary_policy_from_indices(
            [
                {"code": "sh000001", "change_pct": -0.59},
                {"code": "sh000300", "change_pct": -0.981},
                {"code": "sz399006", "change_pct": -1.238},
            ]
        )
        assert result == "neutral"

    def test_empty_list_returns_none(self) -> None:
        assert _infer_monetary_policy_from_indices([]) is None

    def test_none_input_returns_none(self) -> None:
        assert _infer_monetary_policy_from_indices(None) is None  # type: ignore[arg-type]

    def test_missing_change_returns_none(self) -> None:
        assert _infer_monetary_policy_from_indices([{"code": "000300"}]) is None

    def test_mixed_target_and_non_target(self, strong_down_indices) -> None:
        """混合目标 + 非目标，目标代码应被采纳"""
        mixed = strong_down_indices + [
            {"code": "999999", "change_pct": 50.0},  # 不影响均值
        ]
        assert _infer_monetary_policy_from_indices(mixed) == "tight"

    def test_invalid_types_in_list(self) -> None:
        """列表中含非法类型时跳过"""
        result = _infer_monetary_policy_from_indices(
            [
                "not_a_dict",
                None,
                42,
                {"code": "000300", "change_pct": 3.0},
            ]
        )
        assert result == "accommodative"

    def test_codes_in_list_with_and_without_codes(self) -> None:
        """有 code 字段且匹配 + 有 code 字段不匹配 + 无 code 字段"""
        result = _infer_monetary_policy_from_indices(
            [
                {"code": "000300", "change_pct": 3.0},  # 匹配
                {"code": "999999", "change_pct": 50.0},  # 不匹配
                {"change_pct": 4.0},  # 无 code 字段（也计入）
            ]
        )
        assert result == "accommodative"


class TestInferObjectiveMacroIndicators:
    """infer_objective_macro_indicators 顶层函数"""

    def test_full_data(self) -> None:
        result = infer_objective_macro_indicators(
            main_indices=[
                {"code": "000300", "change_pct": 3.0},
                {"code": "399006", "change_pct": 4.0},
            ],
            market_stats={"total_amount": 18000.0},
        )
        assert result == {
            "liquidity_indicator": "abundant",
            "monetary_policy": "accommodative",
        }

    def test_only_indices(self) -> None:
        result = infer_objective_macro_indicators(
            main_indices=[{"code": "000300", "change_pct": 3.0}],
        )
        assert result["monetary_policy"] == "accommodative"
        assert result["liquidity_indicator"] is None

    def test_only_market_stats(self) -> None:
        result = infer_objective_macro_indicators(
            market_stats={"total_amount": 18000.0},
        )
        assert result["liquidity_indicator"] == "abundant"
        assert result["monetary_policy"] is None

    def test_no_inputs(self) -> None:
        result = infer_objective_macro_indicators()
        assert result == {
            "liquidity_indicator": None,
            "monetary_policy": None,
        }

    def test_does_not_raise_on_garbage(self) -> None:
        """任意异常输入不抛异常（fail-open）"""
        result = infer_objective_macro_indicators(
            main_indices="garbage",  # type: ignore[arg-type]
            market_stats=42,  # type: ignore[arg-type]
        )
        assert result == {
            "liquidity_indicator": None,
            "monetary_policy": None,
        }

    def test_partial_indices_missing_change(self) -> None:
        """部分 index 缺 change 字段时仍能计算（基于剩余有效值）"""
        result = infer_objective_macro_indicators(
            main_indices=[
                {"code": "000300"},  # 缺 change
                {"code": "399006", "change_pct": 3.0},  # 有效
            ],
        )
        assert result["monetary_policy"] == "accommodative"


class TestThresholds:
    """阈值常量"""

    def test_liquidity_abundant_threshold(self) -> None:
        assert LIQUIDITY_ABUNDANT_THRESHOLD_YI == 15000.0

    def test_liquidity_moderate_threshold(self) -> None:
        assert LIQUIDITY_MODERATE_THRESHOLD_YI == 8000.0

    def test_monetary_accommodative_pct(self) -> None:
        assert MONETARY_ACCOMMODATIVE_PCT == 2.0

    def test_monetary_tight_pct(self) -> None:
        assert MONETARY_TIGHT_PCT == -2.0
