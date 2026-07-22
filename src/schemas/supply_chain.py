# -*- coding: utf-8 -*-
"""
Supply Chain Schema (v2 deep-optimization).

类型-契约-数据三层防御（按 docs/type-contract-data-defense.md）：
- 类型：所有公共字段加类型注解 + 不用裸 tuple/dict/list
- 数据：Pydantic v2 + ConfigDict(strict=True, frozen=True, validate_assignment=True)
- 契约：ChainNodeV3 / SupplyChainGraph / SupplyChainV2 用 @model_validator 守业务不变式

与 v1 兼容：保留 ChainNode / Chokepoint / USChinaChain / SupplyChain 不删，
SupplyChainDataService.fetch_all 默认返回 SupplyChainV2，legacy=True 走旧结构。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


# ============================================================
# v1 兼容：保留旧 schema
# ============================================================


class ChainNode(BaseModel):
    """[v1] Supply chain node (保留向后兼容)"""

    level: str = Field(..., description="Level")
    companies: List[str] = Field(default_factory=list)
    concentration: Optional[str] = Field(None)


class Chokepoint(BaseModel):
    """[v1+v2] Bottleneck/chokepoint"""

    type: Literal["patent", "capacity", "geo", "tech", "cert"] = Field(...)
    description: str = Field(...)
    confidence: Literal["high", "medium", "low"] = Field("medium")


class USChinaChain(BaseModel):
    """[v1+v2] US-China dual chain"""

    role: str = Field(..., description="Role in dual chain")
    substitution_progress: Optional[str] = Field(None)
    sanction_risk: Optional[str] = Field(None)
    dual_chain_impact: Optional[str] = Field(None)


class SupplyChain(BaseModel):
    """[v1] Supply chain analysis (保留向后兼容)"""

    chain_map: List[ChainNode] = Field(default_factory=list)
    chokepoints: List[Chokepoint] = Field(default_factory=list)
    company_position: str = Field(..., description="Company's position in chain")
    upstream: List[str] = Field(default_factory=list)
    downstream: List[str] = Field(default_factory=list)
    bargaining_power: Optional[str] = Field(None)
    us_china_chain: Optional[USChinaChain] = Field(None)


# ============================================================
# v2 新增：结构化供应链节点
# ============================================================


# 字段来源标注（v2 关键血缘追踪）
FieldSource = Literal["kb", "llm", "tool", "industry_default", "unknown"]

EvidenceStrength = Literal[
    "primary",  # 交易所文件/年报/电话会/官方订单
    "media",  # 可信媒体/行业刊
    "analysis",  # 一级研究 / 深度分析
    "social",  # 社交媒体
    "rumor",  # 传闻
    "kb_doc",  # 用户知识库文档
]


class ChainNodeV3(BaseModel):
    """[v2] 结构化供应链节点。

    与 v1 ChainNode 区别：
    - 每个字段标注来源（kb/llm/tool/industry_default/unknown）
    - 关系强度量化（relationship + concentration_pct + substitutability）
    - 证据强度 + 衰减时间戳
    - 字段来源一致性契约（@model_validator 守）

    字段优先级：4 个核心字段（name/code/concentration_pct/geographic_distribution）
    其他字段可选，缺字段时报告「数据完整性披露」章节显式说明。
    """

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        validate_assignment=True,
        extra="forbid",
    )

    # ---- 基础识别 ----
    name: str = Field(..., min_length=1, max_length=80, description="公司/品类名")
    code: Optional[str] = Field(
        default=None,
        pattern=r"^(\d{6}|[A-Z]{1,5}(\.[A-Z])?)$",
        description="股票代码（6 位 A 股 / 美股 ticker）",
    )
    layer: Literal["upstream", "midstream", "downstream"] = Field(...)
    sub_layer: Optional[str] = Field(
        default=None, max_length=40, description="细分子层（如『硅片』『光刻胶』）"
    )

    # ---- 关系强度（v2 关键：v1 完全缺失的量化字段） ----
    relationship: Literal["核心", "重要", "一般", "潜在"] = Field(default="一般")
    concentration_pct: Optional[float] = Field(
        default=None, ge=0, le=100, description="占该环节供应商/客户的比例（0-100）"
    )
    substitutability: Literal["高", "中", "低", "不可替代", "未知"] = Field(
        default="未知"
    )
    geographic_distribution: List[str] = Field(
        default_factory=list, description="产地/市场地理分布"
    )

    # ---- 来源血缘（v2 关键：每个字段可追溯） ----
    name_source: FieldSource = Field(default="llm")
    name_source_doc_id: Optional[str] = Field(default=None, description="KB 文档 ID")

    concentration_source: Optional[FieldSource] = Field(
        default=None, description="concentration_pct 来源"
    )
    concentration_doc_id: Optional[str] = Field(default=None)
    concentration_tool: Optional[str] = Field(
        default=None, description="调用了哪个工具（如 tushare.top10_holders）"
    )

    # ---- 证据链 ----
    evidence_strength: EvidenceStrength = Field(default="analysis")
    source_url: Optional[str] = Field(default=None, max_length=2048)
    confidence: Literal["high", "medium", "low"] = Field(default="medium")

    # ---- 衰减（v2 新增） ----
    kb_doc_id: Optional[str] = Field(
        default=None, description="来自知识库的关联文档 ID"
    )
    kb_doc_age_days: Optional[int] = Field(
        default=None, ge=0, description="KB 文档距今天数（用于衰减）"
    )

    @model_validator(mode="after")
    def _check_field_source_consistency(self) -> "ChainNodeV3":
        """契约：concentration_pct 非空时必须标注来源。"""
        if self.concentration_pct is not None and self.concentration_source is None:
            raise ValueError(
                "ChainNodeV3 契约违反：concentration_pct 非空时必须标注 "
                "concentration_source（kb/llm/tool/industry_default）"
            )
        if (
            self.name_source == "kb"
            and not self.name_source_doc_id
            and not self.kb_doc_id
        ):
            raise ValueError(
                "ChainNodeV3 契约违反：name_source=kb 时必须填 name_source_doc_id 或 kb_doc_id"
            )
        return self


# ============================================================
# v2 新增：供应链图谱（报告骨架）
# ============================================================


class KBHitRef(BaseModel):
    """知识库命中引用（用于报告「知识库参考」小节）"""

    model_config = ConfigDict(strict=True, frozen=True)

    document_id: str = Field(...)
    document_title: str = Field(...)
    chunk_id: str = Field(...)
    content: str = Field(..., max_length=2000)
    score: float = Field(..., ge=0.0, le=1.0, description="加权后最终得分（0-1）")
    raw_score: float = Field(..., description="FTS5 原始 bm25 得分（负数，越小越相关）")
    tag_weight: float = Field(1.0, ge=0.0, description="tag 加权")
    stock_match_weight: float = Field(1.0, ge=0.0, description="股票匹配加权")
    recency_weight: float = Field(1.0, ge=0.0, description="时间衰减")
    source_url: Optional[str] = Field(None, max_length=2048)
    validation_status: Literal[
        "已被公告验证", "与公开数据冲突", "仅用户资料支持", "待核验"
    ] = Field("待核验")
    kb_doc_age_days: Optional[int] = Field(None, ge=0)


class DataCompleteness(BaseModel):
    """数据完整度披露（v2 新增：让报告可信度可验证）。"""

    model_config = ConfigDict(strict=True, frozen=True)

    upstream_total: int = Field(default=0, ge=0)
    upstream_with_concentration: int = Field(default=0, ge=0)
    upstream_with_geo: int = Field(default=0, ge=0)
    upstream_with_substitutability: int = Field(default=0, ge=0)
    upstream_with_code: int = Field(default=0, ge=0)

    downstream_total: int = Field(default=0, ge=0)
    downstream_with_concentration: int = Field(default=0, ge=0)
    downstream_with_geo: int = Field(default=0, ge=0)

    kb_hit_count: int = Field(default=0, ge=0, description="KB 命中 chunk 数")
    kb_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    aggregate_confidence: Literal["high", "medium", "low"] = Field(default="low")

    def summary(self) -> Dict[str, Any]:
        """供报告 Markdown 表格使用的紧凑摘要。"""
        up_pct = (
            round(self.upstream_with_concentration / self.upstream_total * 100, 1)
            if self.upstream_total
            else 0.0
        )
        down_pct = (
            round(self.downstream_with_concentration / self.downstream_total * 100, 1)
            if self.downstream_total
            else 0.0
        )
        return {
            "upstream_total": self.upstream_total,
            "upstream_with_concentration_pct": up_pct,
            "downstream_total": self.downstream_total,
            "downstream_with_concentration_pct": down_pct,
            "kb_hit_count": self.kb_hit_count,
            "kb_coverage_score": self.kb_coverage_score,
            "aggregate_confidence": self.aggregate_confidence,
        }


def _make_empty_data_completeness() -> "DataCompleteness":
    """[v2] Module-level factory for DataCompleteness default.

    在 default_factory 中用模块级函数（而非 lambda 或类引用）让 pyright
    能正确推导返回类型，避免 strict 模式下 "Arguments missing" 误报。
    """
    return DataCompleteness()


class SupplyChainGraph(BaseModel):
    """[v2] 供应链图谱（替代 v1 SupplyChain 的 List[str] 结构）。"""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        validate_assignment=True,
    )

    ticker: str = Field(..., pattern=r"^[\w\.\-]{1,16}$")
    company: str = Field(..., min_length=1, max_length=80)
    industry: str = Field(..., min_length=1, max_length=40)
    position: str = Field(..., min_length=1, max_length=200)

    upstream: List[ChainNodeV3] = Field(default_factory=list)
    downstream: List[ChainNodeV3] = Field(default_factory=list)
    chokepoints: List[Chokepoint] = Field(default_factory=list)
    us_china_chain: Optional[USChinaChain] = Field(None)

    upstream_depth: int = Field(0, ge=0, le=10)
    downstream_depth: int = Field(0, ge=0, le=10)

    # v2 新增
    kb_coverage_score: float = Field(0.0, ge=0.0, le=1.0)
    aggregate_confidence: Literal["high", "medium", "low"] = Field("low")
    data_completeness: DataCompleteness = Field(
        default_factory=_make_empty_data_completeness
    )

    @model_validator(mode="after")
    def _check_depth(self) -> "SupplyChainGraph":
        """契约：upstream_depth 至少能容纳上游节点的最大子层深度。"""
        # 简化校验：至少 1 个上游时 depth >= 1
        if self.upstream and self.upstream_depth < 1:
            raise ValueError(
                "SupplyChainGraph 契约违反：有上游节点时 upstream_depth 必须 >= 1"
            )
        if self.downstream and self.downstream_depth < 1:
            raise ValueError(
                "SupplyChainGraph 契约违反：有下游节点时 downstream_depth 必须 >= 1"
            )
        return self


class SupplyChainV2(BaseModel):
    """[v2] 报告输入（fetch_all 返回值）。

    同时容纳 v1 字段（company_position / upstream / downstream 字符串数组）
    和 v2 字段（graph 结构化 / kb_evidence 引用 / llm_signals / serenity_score），
    保证调用方渐进迁移。
    """

    model_config = ConfigDict(strict=True, frozen=True)

    # v1 兼容
    data_sources: List[str] = Field(default_factory=list)
    company_position: str = Field("", description="公司在产业链中的位置（短描述）")
    upstream: List[str] = Field(default_factory=list, description="[v1] 上游节点名列表")
    downstream: List[str] = Field(
        default_factory=list, description="[v1] 下游节点名列表"
    )
    chokepoints: List[Chokepoint] = Field(default_factory=list)
    us_china_chain: Optional[USChinaChain] = Field(None)
    industry_drivers: List[str] = Field(default_factory=list)

    # v2 新增
    graph: Optional[SupplyChainGraph] = Field(None, description="[v2] 结构化图谱")
    kb_evidence: List[KBHitRef] = Field(
        default_factory=list, description="[v2] 知识库命中引用"
    )
    llm_signals: Dict[str, float] = Field(
        default_factory=dict, description="[v2] LLM 因子信号 0-1"
    )
    data_completeness: DataCompleteness = Field(
        default_factory=_make_empty_data_completeness
    )

    # Serenity 评分（v2 统一入口返回）
    serenity_score: Optional[int] = Field(None, ge=0, le=100)
    serenity_verdict: Optional[str] = Field(None)
    serenity_factor_details: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    serenity_penalty_details: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    serenity_kb_bonus_applied: Dict[str, float] = Field(
        default_factory=dict, description="[v2] 哪些因子应用了 KB 加成"
    )

    fetched_at: Optional[datetime] = Field(None, description="数据拉取时间（用于审计）")


# ============================================================
# Serenity 评分卡结果（v2 统一入口返回值）
# ============================================================


FactorKey = Literal[
    "demand_inflection",
    "architecture_coupling",
    "chokepoint_severity",
    "supplier_concentration",
    "expansion_difficulty",
    "evidence_quality",
    "valuation_disconnect",
    "catalyst_timing",
]

PenaltyKey = Literal[
    "dilution_financing",
    "governance",
    "geopolitics",
    "liquidity",
    "hype_risk",
    "accounting_quality",
    "cyclicality",
    "alternative_design_risk",
]


class SerenityFactorScore(BaseModel):
    """单个 Serenity 因子的评分 + 证据链"""

    model_config = ConfigDict(strict=True, frozen=True)

    key: FactorKey = Field(...)
    rating: float = Field(..., ge=0.0, le=5.0, description="原始 0-5 评分")
    points: float = Field(..., description="加权后得分")
    weight: float = Field(..., ge=0.0, description="因子权重")
    kb_relevance: float = Field(0.0, ge=0.0, le=1.0, description="KB 相关度 0-1")
    llm_signal: float = Field(0.0, ge=0.0, le=1.0, description="LLM 信号 0-1")
    industry_prior: float = Field(0.0, ge=0.0, le=1.0, description="行业先验 0-1")
    kb_bonus_applied: float = Field(
        0.0, ge=0.0, le=0.2, description="KB 加成（上限 0.2）"
    )
    contributing_kb_doc_ids: List[str] = Field(default_factory=list)


class SerenityPenaltyScore(BaseModel):
    """单个惩罚项的评分"""

    model_config = ConfigDict(strict=True, frozen=True)

    key: PenaltyKey = Field(...)
    rating: float = Field(..., ge=0.0, le=5.0)
    points: float = Field(..., description="扣分（通常 <= 0）")
    weight: float = Field(..., ge=0.0)


class SerenityScoreResult(BaseModel):
    """[v2] Serenity 评分结果（统一入口返回值）。

    两条调用路径（SupplyChainDataService / SupplyChainExecutor）共享同一 schema。
    """

    model_config = ConfigDict(strict=True, frozen=True)

    ticker: str = Field(...)
    company: str = Field(...)
    market: str = Field("")
    factors: Dict[FactorKey, SerenityFactorScore] = Field(default_factory=dict)
    penalties: Dict[PenaltyKey, SerenityPenaltyScore] = Field(default_factory=dict)
    raw_factor_points: float = Field(default=0.0)
    penalty_points: float = Field(default=0.0)
    final_score: int = Field(default=0, ge=0, le=100)
    verdict: str = Field("", description="中文评级，如『顶级研究优先级』")
    notes: str = Field("", description="备注")

    def get(self, key: str, default: Any = None) -> Any:
        """兼容 serenity_scorecard 原生 dict 风格调用。"""
        if key in {"factors", "penalties"}:
            return getattr(self, key)
        return getattr(self, key, default)
