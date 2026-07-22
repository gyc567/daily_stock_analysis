# -*- coding: utf-8 -*-
"""v2 schema 契约测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.supply_chain import (
    ChainNodeV3,
    DataCompleteness,
    KBHitRef,
    SupplyChainGraph,
    SupplyChainV2,
)


class TestChainNodeV3:
    def test_basic(self):
        n = ChainNodeV3(
            name="宁德时代",
            layer="upstream",
            relationship="核心",
            concentration_pct=15.0,
            concentration_source="tool",
        )
        assert n.name == "宁德时代"
        assert n.concentration_source == "tool"

    def test_concentration_without_source_fails(self):
        """契约：concentration_pct 非空时必须标注来源。"""
        with pytest.raises(ValidationError) as ei:
            ChainNodeV3(name="X", layer="upstream", concentration_pct=10.0)
        assert "concentration_source" in str(ei.value)

    def test_name_source_kb_without_doc_id_fails(self):
        with pytest.raises(ValidationError):
            ChainNodeV3(name="X", layer="upstream", name_source="kb")

    def test_frozen(self):
        n = ChainNodeV3(name="X", layer="upstream")
        with pytest.raises(ValidationError):
            n.name = "Y"  # type: ignore[misc]


class TestSupplyChainGraph:
    def test_basic(self):
        n = ChainNodeV3(name="锂矿", layer="upstream")
        g = SupplyChainGraph(
            ticker="300750",
            company="宁德时代",
            industry="动力电池",
            position="动力电池制造",
            upstream=[n],
            upstream_depth=1,
            downstream_depth=1,
        )
        assert g.upstream_depth == 1
        assert len(g.upstream) == 1
        # 默认 DataCompleteness 全 0（schema 是值对象，不算逻辑）
        assert g.data_completeness.upstream_total == 0

    def test_upstream_without_depth_fails(self):
        n = ChainNodeV3(name="锂矿", layer="upstream")
        with pytest.raises(ValidationError):
            SupplyChainGraph(
                ticker="300750",
                company="X",
                industry="X",
                position="X",
                upstream=[n],
                upstream_depth=0,
            )


class TestDataCompleteness:
    def test_summary_with_zero(self):
        dc = DataCompleteness()
        s = dc.summary()
        assert s["upstream_total"] == 0
        assert s["upstream_with_concentration_pct"] == 0.0

    def test_summary_with_data(self):
        dc = DataCompleteness(
            upstream_total=4,
            upstream_with_concentration=2,
            downstream_total=2,
            downstream_with_concentration=1,
            kb_hit_count=3,
            kb_coverage_score=0.6,
            aggregate_confidence="medium",
        )
        s = dc.summary()
        assert s["upstream_with_concentration_pct"] == 50.0
        assert s["downstream_with_concentration_pct"] == 50.0


class TestKBHitRef:
    def test_raw_score_can_be_negative(self):
        """BM25 原始得分是负数（越小越相关）。"""
        h = KBHitRef(
            document_id="d1",
            document_title="t",
            chunk_id="c1",
            content="x",
            score=0.5,
            raw_score=-2.5,
        )
        assert h.raw_score == -2.5


class TestSupplyChainV2:
    def test_basic(self):
        v2 = SupplyChainV2(company_position="高端白酒")
        assert v2.company_position == "高端白酒"
        assert v2.upstream == []
        assert v2.graph is None
        assert v2.serenity_score is None
