# -*- coding: utf-8 -*-
"""KB 检索器 / 衰减 / cold start 测试。"""

from __future__ import annotations

from src.services.supply_chain.kb_retriever import (
    PARTIAL_THRESHOLD,
    SPARSE_THRESHOLD,
    ColdStartStrategy,
    SupplyChainKBResult,
    recency_weight,
)


class TestRecencyWeight:
    def test_zero_age(self):
        assert recency_weight(0) == 1.0

    def test_half_life(self):
        # half_life=180 → 180 天衰减到 0.5
        assert abs(recency_weight(180) - 0.5) < 0.01

    def test_quarter_life(self):
        # 90 天 → ≈0.71
        assert 0.70 < recency_weight(90) < 0.72

    def test_two_years(self):
        # 730 天 → ≈0.06
        assert 0.05 < recency_weight(730) < 0.07

    def test_none_age_no_decay(self):
        """无时间戳不衰减（避免误杀未记录 created_at 的旧文档）。"""
        assert recency_weight(None) == 1.0

    def test_negative_age_no_decay(self):
        assert recency_weight(-1) == 1.0

    def test_custom_half_life(self):
        # half_life=90
        assert abs(recency_weight(90, half_life_days=90) - 0.5) < 0.01


class TestColdStartStrategy:
    def test_cold_start(self):
        s = ColdStartStrategy(0.0)
        assert s.tier == "cold_start"
        assert s.confidence_boost == 1.0
        assert s.llm_fallback == "aggressive"

    def test_sparse(self):
        s = ColdStartStrategy(0.2)
        assert s.tier == "sparse"
        assert s.llm_fallback == "moderate"

    def test_partial(self):
        s = ColdStartStrategy(0.5)
        assert s.tier == "partial"
        assert s.confidence_boost == 1.2
        assert s.llm_fallback == "selective"

    def test_rich(self):
        s = ColdStartStrategy(0.8)
        assert s.tier == "rich"
        assert s.confidence_boost == 1.5
        assert s.llm_fallback == "verify_only"

    def test_threshold_boundary(self):
        assert ColdStartStrategy(SPARSE_THRESHOLD - 0.01).tier == "sparse"
        assert ColdStartStrategy(SPARSE_THRESHOLD).tier == "partial"
        assert ColdStartStrategy(PARTIAL_THRESHOLD - 0.01).tier == "partial"
        assert ColdStartStrategy(PARTIAL_THRESHOLD).tier == "rich"


class TestSupplyChainKBResult:
    def test_aggregate_score_clamped(self):
        r = SupplyChainKBResult(hits=[], aggregate_score=2.0)
        assert r.aggregate_score == 1.0
        r = SupplyChainKBResult(hits=[], aggregate_score=-1.0)
        assert r.aggregate_score == 0.0


class TestRetrieverWithUnavailableKB:
    def test_retrieve_when_kb_service_down(self):
        """KB 服务不可用时返回空 result（不抛异常）。"""
        from src.services.supply_chain.kb_retriever import SupplyChainKBRetriever

        class FakeUnavailableKB:
            def search(self, req):
                raise RuntimeError("DB not available")

        r = SupplyChainKBRetriever(kb_service=FakeUnavailableKB())
        result = r.retrieve(stock_code="600519", stock_name="贵州茅台")
        assert isinstance(result, SupplyChainKBResult)
        assert result.aggregate_score == 0.0
