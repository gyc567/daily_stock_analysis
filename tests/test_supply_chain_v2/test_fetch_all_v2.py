# -*- coding: utf-8 -*-
"""fetch_all_v2 端到端测试。"""

from __future__ import annotations

from src.services.supply_chain_data_service import SupplyChainDataService


class TestFetchAllV2:
    def test_legacy_code_match(self):
        """_get_stock_knowledge_base 命中代码时能拿到 position。"""
        svc = SupplyChainDataService()
        v2 = svc.fetch_all_v2(
            stock_code="300750",
            stock_name="宁德时代",
            fundamental_analysis="宁德时代上游主要为锂矿、钴镍、隔膜、电解液、铜箔。",
            industry_hint="动力电池",
            enable_serenity=True,
        )
        assert v2.company_position  # 非空
        assert v2.graph is not None
        assert v2.serenity_score is not None
        assert v2.serenity_verdict in (
            "顶级研究优先级",
            "高研究优先级",
            "值得跟踪",
            "早期线索或低优先级",
        )

    def test_completeness_disclosure(self):
        """v2 必须披露数据完整度。"""
        svc = SupplyChainDataService()
        v2 = svc.fetch_all_v2(
            stock_code="600519",
            stock_name="贵州茅台",
            fundamental_analysis="",
            industry_hint="高端白酒",
        )
        s = v2.data_completeness.summary()
        assert "upstream_total" in s
        assert "kb_hit_count" in s
        assert "aggregate_confidence" in s

    def test_v1_compat(self):
        """fetch_all 仍按原行为返回 dict。"""
        svc = SupplyChainDataService()
        v1 = svc.fetch_all(
            stock_code="300750",
            stock_name="宁德时代",
            fundamental_analysis="",
            enable_serenity=False,
        )
        assert "upstream" in v1
        assert isinstance(v1["upstream"], list)

    def test_legacy_compat_returns_both(self):
        """fetch_all_v2_legacy_compat 同时返回 v1 字段 + v2 字段。"""
        svc = SupplyChainDataService()
        merged = svc.fetch_all_v2_legacy_compat(
            stock_code="300750",
            stock_name="宁德时代",
            fundamental_analysis="",
            industry_hint="动力电池",
        )
        # v1 字段
        assert "upstream" in merged
        # v2 字段
        assert "graph" in merged
        assert "data_completeness" in merged
