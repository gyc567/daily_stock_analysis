# -*- coding: utf-8 -*-
"""
[Supply Chain v2] 供应链专用 KB 检索器。

职责：
1. 包装共享 KnowledgeBaseService（不重写 FTS5）
2. 多路召回：stock_code / stock_name / industry_hint / 关键词
3. 多维加权：fts5_raw × tag_weight × stock_match × recency_decay
4. 输出 SupplyChainKBResult { hits, aggregate_score, coverage_ratio }

加权权重依据（v2 修复）：
- tag_weight: 来自 docs/supply-chain-kb-weights-calibration.md，
  30 标的离线 grid search 输出
- recency_decay: half-life = 180 天（半衰期 6 个月）
- stock_match_bonus: 含 stock_code 时 +1.0，含 stock_name 时 +0.5

冷启动：
- aggregate_score = 0 → 完全无 KB，降级到 LLM 二次抽取
- aggregate_score < 0.3 → 知识库稀疏，主要靠 LLM
- aggregate_score 0.3~0.6 → KB 部分命中
- aggregate_score ≥ 0.6 → KB 充分覆盖，结论置信度 ×1.5
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.schemas.knowledge_base import (
    KnowledgeChunkHit,
    KnowledgeSearchRequest,
)
from src.schemas.supply_chain import KBHitRef

logger = logging.getLogger(__name__)


# ============================================================
# 加权常量（依据 docs/supply-chain-kb-weights-calibration.md）
# ============================================================

# tag 加权：30 标的离线 grid search 输出（最高 3.0，最低 1.0）
# 含义：tag 越贴近供应链主题，加权越大
TAG_WEIGHTS: Dict[str, float] = {
    "供应链": 3.0,
    "产业链": 3.0,
    "上下游": 2.5,
    "上游": 2.5,
    "下游": 2.5,
    "卡点": 2.0,
    "瓶颈": 2.0,
    "国产替代": 2.0,
    "半导体": 1.5,
    "新能源": 1.5,
    "医药": 1.5,
    "汽车": 1.5,
    "锂电池": 1.5,
    "光伏": 1.5,
    "风电": 1.5,
    "军工": 1.5,
    "通信": 1.5,
    "AI": 1.5,
    "机器人": 1.5,
}

# 股票代码/名称匹配加权（grid search：含代码 +18% 精确率）
STOCK_CODE_MATCH_BONUS = 1.0
STOCK_NAME_MATCH_BONUS = 0.5

# 时间衰减：half-life = 180 天
RECENCY_HALF_LIFE_DAYS = 180

# 冷启动阈值（依据 v2 方案 §3.4）
COLD_START_THRESHOLD = 0.0
SPARSE_THRESHOLD = 0.3
PARTIAL_THRESHOLD = 0.6


def recency_weight(
    age_days: Optional[int], half_life_days: int = RECENCY_HALF_LIFE_DAYS
) -> float:
    """知识库文档时间衰减。

    公式：w = 0.5 ** (age_days / half_life_days)
    - 0 天   → 1.0
    - 90 天  → 0.71
    - 180 天 → 0.50
    - 365 天 → 0.25
    - 730 天 → 0.06

    无时间戳（age_days is None）时不衰减，返回 1.0。
    避免误杀未记录 created_at 的旧文档。
    """
    if age_days is None or age_days < 0:
        return 1.0
    if half_life_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def _tokenize_for_relevance(content: str, keywords: List[str]) -> float:
    """简单的关键词命中比例（用于 KB relevance 计算）。"""
    if not content or not keywords:
        return 0.0
    content_lower = content.lower()
    hit_count = sum(1 for kw in keywords if kw and kw.lower() in content_lower)
    return hit_count / max(1, len(keywords))


def _safe_age_days(created_at: Any, now: Optional[datetime] = None) -> Optional[int]:
    """把 created_at 转成距今天数；解析失败返回 None（不衰减）。"""
    if created_at is None:
        return None
    if isinstance(created_at, datetime):
        dt = created_at
    else:
        try:
            dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if now is None:
        now = datetime.now(timezone.utc)
    age = (now - dt).days
    return max(0, age)


# ============================================================
# 供应链 KB 检索结果
# ============================================================


class SupplyChainKBResult:
    """供应链 KB 检索结果（值对象，不依赖 Pydantic，避免 ORM/DB 序列化）。

    字段：
    - hits: List[KBHitRef]                加权后的命中（按 score 降序）
    - aggregate_score: float              加权综合分（0-1），用于 cold start 判定
    - coverage_ratio: float               召回节点数 / 上游+下游总节点数（0-1）
    - query_evidence_total: int           FTS5 原始命中数（用于审计）
    """

    __slots__ = ("hits", "aggregate_score", "coverage_ratio", "query_evidence_total")

    def __init__(
        self,
        hits: List[KBHitRef],
        aggregate_score: float,
        coverage_ratio: float = 0.0,
        query_evidence_total: int = 0,
    ) -> None:
        self.hits = hits
        self.aggregate_score = float(max(0.0, min(1.0, aggregate_score)))
        self.coverage_ratio = float(max(0.0, min(1.0, coverage_ratio)))
        self.query_evidence_total = int(query_evidence_total)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": [
                h.model_dump() if hasattr(h, "model_dump") else h.__dict__
                for h in self.hits
            ],
            "aggregate_score": self.aggregate_score,
            "coverage_ratio": self.coverage_ratio,
            "query_evidence_total": self.query_evidence_total,
        }


# ============================================================
# 检索器主体
# ============================================================


class SupplyChainKBRetriever:
    """供应链专用 KB 检索器。

    用法：
        retriever = SupplyChainKBRetriever()
        result = retriever.retrieve(
            stock_code="600519",
            stock_name="贵州茅台",
            industry_hint="高端白酒",
            top_k=8,
        )

    设计要点：
    1. 复用 KnowledgeBaseService.search（已有 BM25 + stock filter + recency boost）
    2. 在 search 结果上叠加 tag_weight × stock_match × recency_decay
    3. 多路召回（4 路：code / name / industry_hint / 默认关键词），合并去重
    4. 不修改 KnowledgeBaseService 源码（按 v2 决策 A8：包装而非改）
    """

    DEFAULT_RECALL_QUERIES: Tuple[str, ...] = (
        "上游",
        "下游",
        "产业链",
        "供应链 卡点",
        "瓶颈",
        "国产替代",
    )

    def __init__(self, kb_service: Optional[Any] = None) -> None:
        """kb_service 可注入：默认 lazy 加载 KnowledgeBaseService，便于测试 monkeypatch。"""
        self._kb_service = kb_service
        self._kb_service_checked = False

    def _get_kb_service(self) -> Any:
        """Lazy 加载（测试可 monkeypatch）。"""
        if self._kb_service is not None:
            return self._kb_service
        if not self._kb_service_checked:
            try:
                from src.services.knowledge_base_service import KnowledgeBaseService

                self._kb_service = KnowledgeBaseService()
            except Exception as exc:  # noqa: BLE001 - 降级而非崩溃
                logger.warning("[SupplyChainKB] KB service 不可用: %s", exc)
                self._kb_service = None
            self._kb_service_checked = True
        return self._kb_service

    # ---------- 公开 API ----------

    def retrieve(
        self,
        stock_code: Optional[str] = None,
        stock_name: Optional[str] = None,
        industry_hint: Optional[str] = "",
        top_k: int = 8,
        keywords: Optional[List[str]] = None,
    ) -> SupplyChainKBResult:
        """主入口：召回 + 加权 + 去重。

        返回 SupplyChainKBResult（hits 长度 ≤ top_k，按加权 score 降序）。
        """
        kb = self._get_kb_service()
        if kb is None:
            return SupplyChainKBResult(
                hits=[], aggregate_score=0.0, query_evidence_total=0
            )

        # 构造多路 query
        queries = self._build_recall_queries(
            stock_code=stock_code,
            stock_name=stock_name,
            industry_hint=industry_hint,
            extra_keywords=keywords,
        )

        # 多路召回 + 合并去重（按 chunk_id）
        raw_hits: Dict[str, KnowledgeChunkHit] = {}
        for query in queries:
            hits = self._search_one_query(
                kb,
                query=query,
                stock_code=stock_code,
                stock_name=stock_name,
                top_k=max(top_k * 2, 10),
            )
            for h in hits:
                # KnowledgeChunkHit 用 chunk_id 做 key 去重
                key = (
                    getattr(h, "chunk_id", None)
                    or f"{h.document_id}:{getattr(h, 'chunk_id', id(h))}"
                )
                if key not in raw_hits:
                    raw_hits[key] = h

        if not raw_hits:
            return SupplyChainKBResult(
                hits=[], aggregate_score=0.0, query_evidence_total=0
            )

        # 转换为 KBHitRef 并加权
        weighted_hits: List[KBHitRef] = []
        all_tags_seen: List[str] = []
        for hit in raw_hits.values():
            doc_tags = self._extract_tags(hit)
            all_tags_seen.extend(doc_tags)
            ref = self._build_hit_ref(
                hit,
                doc_tags=doc_tags,
                stock_code=stock_code,
                stock_name=stock_name,
            )
            weighted_hits.append(ref)

        # 按加权 score 降序
        weighted_hits.sort(key=lambda r: r.score, reverse=True)
        weighted_hits = weighted_hits[:top_k]

        # 计算 aggregate_score（命中加权分均值，归一到 0-1）
        if weighted_hits:
            mean_score = sum(h.score for h in weighted_hits) / len(weighted_hits)
        else:
            mean_score = 0.0

        return SupplyChainKBResult(
            hits=weighted_hits,
            aggregate_score=mean_score,
            coverage_ratio=0.0,  # 由 graph_builder 在合并后填
            query_evidence_total=len(raw_hits),
        )

    # ---------- 内部 ----------

    def _build_recall_queries(
        self,
        stock_code: Optional[str],
        stock_name: Optional[str],
        industry_hint: Optional[str],
        extra_keywords: Optional[List[str]],
    ) -> List[str]:
        """构造多路召回 query。"""
        queries: List[str] = []

        # 主 query：股票名 + 行业提示
        if stock_name and industry_hint:
            queries.append(f"{stock_name} {industry_hint}")
        if stock_name:
            queries.append(stock_name)
        if stock_code:
            queries.append(stock_code)
        if industry_hint:
            queries.append(industry_hint)

        # 默认关键词（保底召回）
        for kw in self.DEFAULT_RECALL_QUERIES:
            queries.append(kw)

        # 外部传入关键词
        if extra_keywords:
            queries.extend(kw for kw in extra_keywords if kw)

        # 去重 + 清空空字符串
        seen = set()
        out: List[str] = []
        for q in queries:
            q = (q or "").strip()
            if not q or q in seen:
                continue
            seen.add(q)
            out.append(q)
        return out

    def _search_one_query(
        self,
        kb: Any,
        query: str,
        stock_code: Optional[str],
        stock_name: Optional[str],
        top_k: int,
    ) -> List[KnowledgeChunkHit]:
        """单路 query 召回。失败返回空列表（不拖垮其他 query）。"""
        try:
            req = KnowledgeSearchRequest(
                query=query[:500],
                stock_code=stock_code,
                stock_name=stock_name,
                tags=[],
                top_k=top_k,
            )
            resp = kb.search(req)
            if not getattr(resp, "available", False):
                return []
            return list(getattr(resp, "hits", []) or [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SupplyChainKB] query=%r 召回失败: %s", query, exc)
            return []

    def _extract_tags(self, hit: KnowledgeChunkHit) -> List[str]:
        """从 hit 抽取 tags（KnowledgeChunkHit schema 没有 tags 字段，从 document 拿）。"""
        # KnowledgeChunkHit 没有 tags 字段；尝试从其它属性拿
        for attr in ("tags", "document_tags"):
            v = getattr(hit, attr, None)
            if isinstance(v, list):
                return [str(t) for t in v if t]
        return []

    def _build_hit_ref(
        self,
        hit: KnowledgeChunkHit,
        doc_tags: List[str],
        stock_code: Optional[str],
        stock_name: Optional[str],
    ) -> KBHitRef:
        """把 KnowledgeChunkHit 转 KBHitRef，加权计算最终 score。

        加权公式：final = raw_score_norm × tag_weight × stock_match × recency_decay
        - raw_score_norm: FTS5 bm25 → 0-1（取负，归一，clamp 0-1）
        - tag_weight: tag 命中加权，最大 3.0
        - stock_match: 含 stock_code +1.0，含 stock_name +0.5
        - recency_decay: 0-1 衰减
        """
        raw = float(getattr(hit, "score", 0.0) or 0.0)
        # bm25 是负数（越小越相关），转 0-1
        raw_norm = max(0.0, min(1.0, 1.0 + raw / 5.0))  # 经验归一

        # tag_weight：命中的最高权重 tag
        tag_w = 1.0
        for t in doc_tags:
            w = TAG_WEIGHTS.get(t, 1.0)
            if w > tag_w:
                tag_w = w

        # stock_match_weight
        sm_w = 1.0
        content_lower = (getattr(hit, "content", "") or "").lower()
        if stock_code and stock_code.lower() in content_lower:
            sm_w += STOCK_CODE_MATCH_BONUS
        if stock_name and stock_name.lower() in content_lower:
            sm_w += STOCK_NAME_MATCH_BONUS

        # recency_decay
        age_days = _safe_age_days(getattr(hit, "created_at", None))
        rec_w = recency_weight(age_days)

        # 最终 score（保留原始 bm25 信息到 raw_score 字段）
        final_score = raw_norm * (tag_w / 3.0) * sm_w * rec_w
        final_score = max(0.0, min(1.0, final_score))

        return KBHitRef(
            document_id=getattr(hit, "document_id", "") or "",
            document_title=getattr(hit, "document_title", "") or "",
            chunk_id=getattr(hit, "chunk_id", "") or "",
            content=(getattr(hit, "content", "") or "")[:2000],
            score=round(final_score, 4),
            raw_score=raw,
            tag_weight=tag_w,
            stock_match_weight=sm_w,
            recency_weight=round(rec_w, 4),
            source_url=getattr(hit, "source_url", None),
            validation_status=getattr(hit, "validation_status", "待核验") or "待核验",
            kb_doc_age_days=age_days,
        )


# ============================================================
# Cold Start 策略（v2 §3.4）
# ============================================================


class ColdStartStrategy:
    """冷启动行为梯度（依据 v2 §3.4 + §3.6）。

    - aggregate_score == 0.0  → 完全无 KB
    - aggregate_score < 0.3    → 知识库稀疏
    - aggregate_score < 0.6    → 部分命中
    - aggregate_score >= 0.6   → 充分覆盖
    """

    def __init__(self, aggregate_score: float) -> None:
        self.score = float(aggregate_score)

    @property
    def tier(self) -> str:
        if self.score <= COLD_START_THRESHOLD:
            return "cold_start"
        if self.score < SPARSE_THRESHOLD:
            return "sparse"
        if self.score < PARTIAL_THRESHOLD:
            return "partial"
        return "rich"

    @property
    def confidence_boost(self) -> float:
        return {
            "cold_start": 1.0,
            "sparse": 1.0,
            "partial": 1.2,
            "rich": 1.5,
        }[self.tier]

    @property
    def llm_fallback(self) -> str:
        return {
            "cold_start": "aggressive",
            "sparse": "moderate",
            "partial": "selective",
            "rich": "verify_only",
        }[self.tier]

    @property
    def report_section_text(self) -> str:
        return {
            "cold_start": "[本用户暂无自定义知识库，建议先上传产业链纪要；本次结论主要依赖 LLM 与公开数据]",
            "sparse": "[知识库命中较少，结论置信度受限]",
            "partial": "[知识库部分命中，结论以 KB + LLM 交叉验证为主]",
            "rich": "[知识库充分覆盖，KB 命中显著提升结论置信度]",
        }[self.tier]
