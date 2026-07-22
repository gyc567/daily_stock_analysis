# -*- coding: utf-8 -*-
"""
[Supply Chain v2] 供应链图谱构建器。

合并 KB / LLM / 公开数据 → SupplyChainGraph，含：
- 上下游结构化节点（ChainNodeV3）
- 数据完整度披露（DataCompleteness）
- KB 覆盖率（kb_coverage_score）
- 总体置信度（aggregate_confidence）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.schemas.supply_chain import (
    ChainNodeV3,
    DataCompleteness,
    SupplyChainGraph,
    Chokepoint,
    USChinaChain,
)
from src.services.supply_chain.kb_retriever import (
    ColdStartStrategy,
    SupplyChainKBResult,
)
from src.services.supply_chain.two_pass_extractor import TwoPassSupplyChainExtractor

logger = logging.getLogger(__name__)


class SupplyChainGraphBuilder:
    """图谱构建器入口。

    用法：
        builder = SupplyChainGraphBuilder(extractor=extractor)
        graph = builder.build(
            ticker="600519", company="贵州茅台", industry="高端白酒",
            position="高端白酒生产",
            kb_result=kb_result,
            llm_first_pass={"upstream": [...], "downstream": [...], "chokepoints": [...]},
            industry_hint="高端白酒",
        )
    """

    def __init__(
        self,
        extractor: Optional[TwoPassSupplyChainExtractor] = None,
    ) -> None:
        self._extractor = extractor or TwoPassSupplyChainExtractor()

    def build(
        self,
        ticker: str,
        company: str,
        industry: str,
        position: str,
        kb_result: SupplyChainKBResult,
        llm_first_pass: Dict[str, Any],
        industry_hint: str = "",
        chokepoints: Optional[List[Chokepoint]] = None,
        us_china_chain: Optional[USChinaChain] = None,
    ) -> SupplyChainGraph:
        upstream_nodes, downstream_nodes = self._extractor.extract(
            ticker=ticker,
            company=company,
            kb_result=kb_result,
            llm_first_pass=llm_first_pass,
            industry_hint=industry_hint,
        )

        # 数据完整度
        completeness = self._compute_completeness(
            upstream_nodes=upstream_nodes,
            downstream_nodes=downstream_nodes,
            kb_result=kb_result,
        )

        # KB 覆盖率
        kb_coverage = self._compute_kb_coverage(upstream_nodes, downstream_nodes)

        # 总体置信度（按 cold start 策略）
        cold = ColdStartStrategy(kb_result.aggregate_score)
        agg_conf: str = (
            "high"
            if cold.tier == "rich"
            else ("medium" if cold.tier in ("partial", "sparse") else "low")
        )

        # chokepoints 兜底
        if not chokepoints:
            chokepoints = []

        return SupplyChainGraph(
            ticker=ticker,
            company=company,
            industry=industry,
            position=position,
            upstream=upstream_nodes,
            downstream=downstream_nodes,
            chokepoints=chokepoints,
            us_china_chain=us_china_chain,
            upstream_depth=max(
                1 if upstream_nodes else 0,
                self._estimate_depth(upstream_nodes),
            ),
            downstream_depth=max(
                1 if downstream_nodes else 0,
                self._estimate_depth(downstream_nodes),
            ),
            kb_coverage_score=kb_coverage,
            aggregate_confidence=agg_conf,  # type: ignore[arg-type]
            data_completeness=completeness,
        )

    # ---------- 内部 ----------

    def _compute_completeness(
        self,
        upstream_nodes: List[ChainNodeV3],
        downstream_nodes: List[ChainNodeV3],
        kb_result: SupplyChainKBResult,
    ) -> DataCompleteness:
        def _count(nodes: List[ChainNodeV3]) -> Dict[str, int]:
            return {
                "total": len(nodes),
                "concentration": sum(
                    1 for n in nodes if n.concentration_pct is not None
                ),
                "geo": sum(1 for n in nodes if n.geographic_distribution),
                "substitutability": sum(
                    1 for n in nodes if n.substitutability not in ("未知", "")
                ),
                "code": sum(1 for n in nodes if n.code is not None),
            }

        up = _count(upstream_nodes)
        down = _count(downstream_nodes)

        return DataCompleteness(
            upstream_total=up["total"],
            upstream_with_concentration=up["concentration"],
            upstream_with_geo=up["geo"],
            upstream_with_substitutability=up["substitutability"],
            upstream_with_code=up["code"],
            downstream_total=down["total"],
            downstream_with_concentration=down["concentration"],
            downstream_with_geo=down["geo"],
            kb_hit_count=len(kb_result.hits),
            kb_coverage_score=kb_result.aggregate_score,
            aggregate_confidence="high"
            if kb_result.aggregate_score >= 0.6
            else ("medium" if kb_result.aggregate_score >= 0.3 else "low"),
        )

    def _compute_kb_coverage(
        self, upstream: List[ChainNodeV3], downstream: List[ChainNodeV3]
    ) -> float:
        """KB 来源节点占总节点的比例。"""
        total = len(upstream) + len(downstream)
        if total == 0:
            return 0.0
        from_kb = sum(1 for n in upstream + downstream if n.name_source == "kb")
        return round(from_kb / total, 4)

    def _estimate_depth(self, nodes: List[ChainNodeV3]) -> int:
        """估算上下游追溯层级数（简化：sub_layer 不同种类数）。"""
        if not nodes:
            return 0
        layers = set()
        for n in nodes:
            layers.add(n.sub_layer or "未分类")
        return min(len(layers), 5)
