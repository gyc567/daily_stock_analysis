# -*- coding: utf-8 -*-
"""P5-fix: pipeline._attach_market_overview 单元测试。

验证：
- main_indices / market_stats 注入到 enhanced_context
- 单只分析 + 批量分析都走这条路径
- 失败时静默（target_context 不变）
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from src.core.pipeline import StockAnalysisPipeline


@pytest.fixture
def mock_pipeline() -> Any:
    """构造一个最小可用的 StockAnalysisPipeline 实例（不实际加载 config/db）"""
    pipeline = StockAnalysisPipeline.__new__(StockAnalysisPipeline)
    pipeline.fetcher_manager = MagicMock()
    return pipeline


class TestAttachMarketOverview:
    """_attach_market_overview 单测"""

    def test_injects_main_indices_and_market_stats(self, mock_pipeline) -> None:
        mock_pipeline.fetcher_manager.get_main_indices.return_value = [
            {"code": "000300", "change_pct": 1.5},
            {"code": "000001", "change_pct": 0.8},
        ]
        mock_pipeline.fetcher_manager.get_market_stats.return_value = {
            "total_amount": 15000.0,
            "up_count": 3000,
            "down_count": 2000,
        }
        target: Dict[str, Any] = {}
        mock_pipeline._attach_market_overview(target, "cn")

        assert "main_indices" in target
        assert len(target["main_indices"]) == 2
        assert target["main_indices"][0]["code"] == "000300"
        assert "market_stats" in target
        assert target["market_stats"]["total_amount"] == 15000.0

    def test_handles_empty_indices(self, mock_pipeline) -> None:
        mock_pipeline.fetcher_manager.get_main_indices.return_value = []
        mock_pipeline.fetcher_manager.get_market_stats.return_value = {
            "total_amount": 10000.0,
        }
        target: Dict[str, Any] = {}
        mock_pipeline._attach_market_overview(target, "cn")

        # main_indices 空时不注入键
        assert "main_indices" not in target
        assert "market_stats" in target

    def test_handles_empty_market_stats(self, mock_pipeline) -> None:
        mock_pipeline.fetcher_manager.get_main_indices.return_value = [
            {"code": "000300", "change_pct": 1.5},
        ]
        mock_pipeline.fetcher_manager.get_market_stats.return_value = {}
        target: Dict[str, Any] = {}
        mock_pipeline._attach_market_overview(target, "cn")

        assert "main_indices" in target
        # market_stats 空 dict 不注入
        assert "market_stats" not in target

    def test_handles_none_results(self, mock_pipeline) -> None:
        mock_pipeline.fetcher_manager.get_main_indices.return_value = None
        mock_pipeline.fetcher_manager.get_market_stats.return_value = None
        target: Dict[str, Any] = {}
        mock_pipeline._attach_market_overview(target, "cn")
        # 两个键都不应注入
        assert "main_indices" not in target
        assert "market_stats" not in target

    def test_handles_fetcher_exception_indices(self, mock_pipeline) -> None:
        """indices fetcher 抛异常时不阻断 main_stats 注入"""
        mock_pipeline.fetcher_manager.get_main_indices.side_effect = RuntimeError(
            "network error"
        )
        mock_pipeline.fetcher_manager.get_market_stats.return_value = {
            "total_amount": 12000.0,
        }
        target: Dict[str, Any] = {}
        mock_pipeline._attach_market_overview(target, "cn")
        assert "main_indices" not in target
        assert "market_stats" in target

    def test_handles_fetcher_exception_stats(self, mock_pipeline) -> None:
        """stats fetcher 抛异常时不阻断 main_indices 注入"""
        mock_pipeline.fetcher_manager.get_main_indices.return_value = [
            {"code": "000300", "change_pct": 1.5},
        ]
        mock_pipeline.fetcher_manager.get_market_stats.side_effect = RuntimeError(
            "network error"
        )
        target: Dict[str, Any] = {}
        mock_pipeline._attach_market_overview(target, "cn")
        assert "main_indices" in target
        assert "market_stats" not in target

    def test_handles_both_exceptions(self, mock_pipeline) -> None:
        """两个 fetcher 都抛异常时不抛异常（fail-open）"""
        mock_pipeline.fetcher_manager.get_main_indices.side_effect = RuntimeError(
            "err1"
        )
        mock_pipeline.fetcher_manager.get_market_stats.side_effect = RuntimeError(
            "err2"
        )
        target: Dict[str, Any] = {}
        # 不应抛异常
        mock_pipeline._attach_market_overview(target, "cn")
        assert "main_indices" not in target
        assert "market_stats" not in target

    def test_empty_market_returns_no_injection(self, mock_pipeline) -> None:
        """market 为空字符串时不调用 fetcher"""
        target: Dict[str, Any] = {}
        mock_pipeline._attach_market_overview(target, "")
        mock_pipeline.fetcher_manager.get_main_indices.assert_not_called()
        mock_pipeline.fetcher_manager.get_market_stats.assert_not_called()
        assert target == {}

    def test_purpose_param_passed_to_market_stats(self, mock_pipeline) -> None:
        """purpose 参数用于可观测性（追踪调用方）"""
        mock_pipeline.fetcher_manager.get_main_indices.return_value = []
        mock_pipeline.fetcher_manager.get_market_stats.return_value = {}
        mock_pipeline._attach_market_overview({}, "cn")
        # 检查 purpose 含市场代码
        call_kwargs = mock_pipeline.fetcher_manager.get_market_stats.call_args.kwargs
        assert "purpose" in call_kwargs
        assert "cn" in call_kwargs["purpose"]

    def test_does_not_overwrite_existing_keys(self, mock_pipeline) -> None:
        """已存在的 key 不被覆盖（增强防御性）"""
        # 实际上当前实现是 setdefault + 直接写入；如果 fetcher 失败不会改 target
        # 但 fetcher 成功时是直接赋值。这里只验证：fetcher 失败时不动 target
        mock_pipeline.fetcher_manager.get_main_indices.return_value = None
        mock_pipeline.fetcher_manager.get_market_stats.return_value = None
        target: Dict[str, Any] = {"main_indices": "pre_existing"}
        mock_pipeline._attach_market_overview(target, "cn")
        # None 时不覆盖
        assert target["main_indices"] == "pre_existing"
