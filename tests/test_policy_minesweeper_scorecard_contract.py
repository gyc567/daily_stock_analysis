# -*- coding: utf-8 -*-
"""政策与公告排雷 scorecard — icontract 契约测试。

验证 ``score()`` 的 ``@ensure`` 后置条件：综合分 ``final`` 恒落在 [-100, 100]。
对应 docs/type-contract-data-defense.md 的 Layer 2（业务契约）。
"""

from __future__ import annotations

from src.services.policy_minesweeper_scorecard import DIMENSION_KEYS, score


def _payload(dims_value: float) -> dict:
    """构造六维 + α/β 全等于 dims_value 的 payload（用于触发极端输入）。"""
    return {
        "stock_code": "600519",
        "stock_name": "示例",
        "dimensions": {k: dims_value for k in DIMENSION_KEYS},
        "alpha_score": dims_value,
        "beta_score": dims_value,
    }


class TestScoreFinalRangeContract:
    """契约：score() 的 final 综合分必须落在 [-100, 100]（@ensure 运行期守护）。"""

    def test_extreme_negative_dims_clamped_to_range(self):
        result = score(_payload(-9999), "medium")
        assert -100 <= result["final"] <= 100

    def test_extreme_positive_dims_clamped_to_range(self):
        result = score(_payload(9999), "medium")
        assert -100 <= result["final"] <= 100

    def test_zero_stays_in_range(self):
        result = score(_payload(0), "medium")
        assert result["final"] == 0

    def test_all_horizons_keep_final_in_range(self):
        for horizon in ("short", "medium", "long"):
            result = score(_payload(80), horizon)
            assert -100 <= result["final"] <= 100, f"{horizon}: {result['final']}"
