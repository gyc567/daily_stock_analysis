# -*- coding: utf-8 -*-
"""
[Supply Chain v2] 测试 fixture。
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.schemas.supply_chain import KBHitRef
from src.services.supply_chain.kb_retriever import SupplyChainKBResult


def make_kb_hit(
    document_id: str = "kb_test_001",
    document_title: str = "测试产业链纪要",
    chunk_id: str = "c1",
    content: str = "贵州茅台上游主要为糯高粱、小麦供应商，下游为高端消费者。",
    score: float = 0.85,
    raw_score: float = -1.5,
    tag_weight: float = 3.0,
    stock_match_weight: float = 1.5,
    recency_weight: float = 1.0,
    kb_doc_age_days: int = 30,
    validation_status: str = "待核验",
) -> KBHitRef:
    """构造 KBHitRef fixture。"""
    return KBHitRef(
        document_id=document_id,
        document_title=document_title,
        chunk_id=chunk_id,
        content=content,
        score=score,
        raw_score=raw_score,
        tag_weight=tag_weight,
        stock_match_weight=stock_match_weight,
        recency_weight=recency_weight,
        validation_status=validation_status,
        kb_doc_age_days=kb_doc_age_days,
    )


def make_kb_result(
    aggregate_score: float = 0.85,
    hits: List[KBHitRef] = None,
) -> SupplyChainKBResult:
    """构造 SupplyChainKBResult fixture。"""
    if hits is None:
        hits = [make_kb_hit()]
    return SupplyChainKBResult(hits=hits, aggregate_score=aggregate_score)


def make_supply_chain_v2(
    ticker: str = "600519",
    company: str = "贵州茅台",
    industry: str = "高端白酒",
    upstream_names: List[str] = None,
    downstream_names: List[str] = None,
) -> Dict[str, Any]:
    """构造 SupplyChainDataService.fetch_all_v2 风格 fixture 数据。"""
    if upstream_names is None:
        upstream_names = ["糯高粱", "小麦", "包装材料"]
    if downstream_names is None:
        downstream_names = ["高端消费者", "商务宴请"]
    return {
        "ticker": ticker,
        "company": company,
        "industry_hint": industry,
        "fundamental_analysis": f"{company}上游主要为{','.join(upstream_names)}；下游为{','.join(downstream_names)}。",
    }
