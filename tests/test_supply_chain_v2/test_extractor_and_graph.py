# -*- coding: utf-8 -*-
"""两轮抽取 + 公开数据补全测试。"""

from __future__ import annotations

from src.services.supply_chain.field_enrichment import SupplyChainFieldEnricher
from src.services.supply_chain.graph_builder import SupplyChainGraphBuilder
from src.services.supply_chain.kb_retriever import (
    SupplyChainKBResult,
    SupplyChainKBRetriever,
)
from src.services.supply_chain.two_pass_extractor import (
    TwoPassSupplyChainExtractor,
)

from tests.test_supply_chain_v2 import make_kb_hit


class TestTwoPassExtractor:
    def test_extract_returns_nodes(self):
        kb_hit = make_kb_hit(
            content="贵州茅台上游主要为糯高粱、小麦供应商，下游为高端消费者。"
        )
        kb_result = SupplyChainKBResult(hits=[kb_hit], aggregate_score=0.85)
        extractor = TwoPassSupplyChainExtractor(kb_retriever=SupplyChainKBRetriever())

        up, down = extractor.extract(
            ticker="600519",
            company="贵州茅台",
            kb_result=kb_result,
            llm_first_pass={
                "upstream": ["包装材料"],
                "downstream": ["商务宴请"],
            },
            industry_hint="高端白酒",
        )

        # KB 命中 + LLM 补充
        names_up = [n.name for n in up]
        names_down = [n.name for n in down]
        assert "糯高粱" in names_up
        assert "小麦" in names_up
        assert "包装材料" in names_up  # LLM 补充
        assert "高端消费者" in names_down
        assert "商务宴请" in names_down

    def test_empty_inputs(self):
        kb_result = SupplyChainKBResult(hits=[], aggregate_score=0.0)
        extractor = TwoPassSupplyChainExtractor(kb_retriever=SupplyChainKBRetriever())
        up, down = extractor.extract(
            ticker="X",
            company="X",
            kb_result=kb_result,
            llm_first_pass={"upstream": [], "downstream": []},
        )
        assert up == []
        assert down == []

    def test_dedup(self):
        kb_hit = make_kb_hit(content="贵州茅台上游为糯高粱")
        kb_result = SupplyChainKBResult(hits=[kb_hit], aggregate_score=0.85)
        extractor = TwoPassSupplyChainExtractor()
        up, down = extractor.extract(
            ticker="600519",
            company="贵州茅台",
            kb_result=kb_result,
            llm_first_pass={"upstream": ["糯高粱"], "downstream": []},
        )
        # "糯高粱" 应只出现一次
        names = [n.name for n in up]
        assert names.count("糯高粱") == 1


class TestFieldEnricher:
    def test_no_concentration_no_field(self):
        """concentration_pct 为 None 时不写 concentration_source。"""
        n = make_node_no_concentration()
        enricher = SupplyChainFieldEnricher()
        out = enricher.enrich(n)
        assert out.concentration_source is None

    def test_enrich_all_no_crash(self):
        """enrich_all 在 enrich 失败时回退到原节点，不拖垮整体。"""
        n1 = make_node_no_concentration()
        enricher = SupplyChainFieldEnricher()
        out = enricher.enrich_all([n1])
        assert len(out) == 1


def make_node_no_concentration():
    from src.schemas.supply_chain import ChainNodeV3

    return ChainNodeV3(name="锂矿", layer="upstream")


class TestGraphBuilder:
    def test_build_basic(self):
        kb_hit = make_kb_hit(
            content="宁德时代上游为锂矿、隔膜供应商，下游为新能源汽车。"
        )
        kb_result = SupplyChainKBResult(hits=[kb_hit], aggregate_score=0.7)
        builder = SupplyChainGraphBuilder()
        graph = builder.build(
            ticker="300750",
            company="宁德时代",
            industry="动力电池",
            position="动力电池制造",
            kb_result=kb_result,
            llm_first_pass={"upstream": ["锂矿", "隔膜"], "downstream": ["新能源汽车"]},
            industry_hint="动力电池",
        )
        assert graph.ticker == "300750"
        assert len(graph.upstream) >= 2
        assert graph.kb_coverage_score >= 0.0
        assert graph.data_completeness.upstream_total >= 2

    def test_empty_returns_minimal_graph(self):
        kb_result = SupplyChainKBResult(hits=[], aggregate_score=0.0)
        builder = SupplyChainGraphBuilder()
        graph = builder.build(
            ticker="X",
            company="X",
            industry="X",
            position="X",
            kb_result=kb_result,
            llm_first_pass={},
        )
        assert graph.upstream == []
        assert graph.downstream == []
        assert graph.upstream_depth == 0
        assert graph.aggregate_confidence == "low"
