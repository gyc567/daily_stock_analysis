# -*- coding: utf-8 -*-
"""Serenity 评分器测试。"""

from __future__ import annotations

from src.services.supply_chain.kb_retriever import KBHitRef, SupplyChainKBResult
from src.services.supply_chain.serenity_scorer import (
    INDUSTRY_PRIOR_FACTORS,
    KB_BONUS_CAP,
    KB_BONUS_MIN_KB_SCORE,
    KB_DRIVEN_FACTORS,
    SerenityScorer,
)
from src.schemas.supply_chain import SupplyChainGraph, ChainNodeV3


def make_graph(
    kb_coverage: float = 0.5, n_up: int = 3, n_down: int = 2
) -> SupplyChainGraph:
    up = [ChainNodeV3(name=f"上游{i}", layer="upstream") for i in range(n_up)]
    down = [ChainNodeV3(name=f"下游{i}", layer="downstream") for i in range(n_down)]
    return SupplyChainGraph(
        ticker="600519",
        company="贵州茅台",
        industry="高端白酒",
        position="高端白酒生产",
        upstream=up,
        downstream=down,
        upstream_depth=max(1, n_up),
        downstream_depth=max(1, n_down),
        kb_coverage_score=kb_coverage,
    )


def make_kb_hit_kw(text: str, score: float = 0.9) -> KBHitRef:
    return KBHitRef(
        document_id="kb_001",
        document_title="t",
        chunk_id="c1",
        content=text,
        score=score,
        raw_score=-1.5,
        tag_weight=3.0,
        stock_match_weight=1.5,
        recency_weight=1.0,
    )


class TestSerenityScorer:
    def test_score_range(self):
        kb_result = SupplyChainKBResult(hits=[], aggregate_score=0.0)
        graph = make_graph()
        scorer = SerenityScorer()
        result = scorer.score(
            ticker="600519",
            company="贵州茅台",
            market="A-share",
            graph=graph,
            kb_result=kb_result,
        )
        assert 0 <= result.final_score <= 100
        assert result.verdict in (
            "顶级研究优先级",
            "高研究优先级",
            "值得跟踪",
            "早期线索或低优先级",
        )

    def test_kb_bonus_triggers_only_for_kb_driven_with_high_kb(self):
        """KB 加成仅在 KB_DRIVEN 因子 + aggregate_score ≥ 0.6 + kb_relevance ≥ 0.6 时触发。"""
        # 文本覆盖 chokepoint_severity 的 5 个关键词中的 4 个（卡点/瓶颈/不可替代/国产化率）
        text = "卡点严重，瓶颈显著，不可替代，国产化率极低"
        kb_hit = make_kb_hit_kw(text, score=0.9)
        kb_result = SupplyChainKBResult(hits=[kb_hit], aggregate_score=0.8)
        graph = make_graph()

        scorer = SerenityScorer()
        result = scorer.score(
            ticker="688981",
            company="中芯国际",
            market="A-share",
            graph=graph,
            kb_result=kb_result,
            industry_hint="半导体",
        )
        chokepoint = result.factors["chokepoint_severity"]
        # kw_cov=4/5=0.8, avg_chunk_score=0.9 → kb_rel=0.8 * (0.5+0.45)=0.76 → 触发 bonus
        assert chokepoint.kb_relevance >= 0.6, (
            f"期望 kb_relevance >= 0.6（触发 bonus），实际 {chokepoint.kb_relevance}"
        )
        assert chokepoint.kb_bonus_applied > 0, (
            f"期望 KB bonus 触发，实际 {chokepoint.kb_bonus_applied}"
        )

        # demand_inflection 是 INDUSTRY_PRIOR → 不应有 KB bonus
        demand = result.factors["demand_inflection"]
        assert demand.kb_bonus_applied == 0.0

    def test_no_bonus_when_low_kb(self):
        """KB aggregate_score < 0.6 时不应触发加成。"""
        kb_hit = make_kb_hit_kw("卡点严重", score=0.9)
        kb_result = SupplyChainKBResult(hits=[kb_hit], aggregate_score=0.4)
        graph = make_graph()
        scorer = SerenityScorer()
        result = scorer.score(
            ticker="X",
            company="X",
            graph=graph,
            kb_result=kb_result,
        )
        for fkey, fscore in result.factors.items():
            if fkey in KB_DRIVEN_FACTORS:
                assert fscore.kb_bonus_applied == 0.0

    def test_legacy_fallback(self, monkeypatch):
        """SERENITY_SCORER_V2=false 时回退到 legacy stub。"""
        monkeypatch.setenv("SERENITY_SCORER_V2", "false")
        kb_result = SupplyChainKBResult(hits=[], aggregate_score=0.0)
        graph = make_graph()
        scorer = SerenityScorer()
        result = scorer.score(ticker="X", company="X", graph=graph, kb_result=kb_result)
        assert result.verdict == "早期线索或低优先级"

    def test_factor_classification(self):
        """KB_DRIVEN / INDUSTRY_PRIOR 分类无重叠。"""
        assert set(KB_DRIVEN_FACTORS.keys()).isdisjoint(
            set(INDUSTRY_PRIOR_FACTORS.keys())
        )

    def test_bonus_capped(self):
        """KB bonus 上限 0.2。"""
        assert KB_BONUS_CAP == 0.2
        assert KB_BONUS_MIN_KB_SCORE == 0.6
