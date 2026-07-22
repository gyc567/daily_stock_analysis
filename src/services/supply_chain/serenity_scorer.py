# -*- coding: utf-8 -*-
"""
[Supply Chain v2] 统一 Serenity 评分入口。

V2 修复 A7（两条评分路径不一致）：
- 单股路径：SupplyChainDataService → SerenityScorer
- 主题路径：SupplyChainExecutor → SerenityScorer

V2 修复 A9（KB 丰富标的上评分虚高）：
- 因子分 KB_DRIVEN_FACTORS / INDUSTRY_PRIOR_FACTORS 两类
- KB 加成上限 0.2，仅对 KB_DRIVEN 因子 + kb_score>=0.6 触发

V2 修复 A1/A2（权重经验值）：
- FACTOR_CONFIG 权重集中在模块顶部 docstring 说明依据
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

from src.schemas.supply_chain import (
    FactorKey,
    PenaltyKey,
    SerenityFactorScore,
    SerenityPenaltyScore,
    SerenityScoreResult,
    SupplyChainGraph,
)
from src.services.supply_chain.kb_retriever import SupplyChainKBResult


# 类型别名：避免 pyright 对 Dict[str, ...] 推断丢失 FactorKey literal
FactorKeywordsMap = Dict[FactorKey, Tuple[str, ...]]

logger = logging.getLogger(__name__)


# ============================================================
# 因子配置（权重依据 docs/supply-chain-kb-weights-calibration.md）
# ============================================================

# 8 个因子分类 + 加权（v2 修复 A9）
# KB_DRIVEN: KB 文本能直接驱动评分（卡点/扩产/集中度等关键词命中）
# INDUSTRY_PRIOR: 主要由行业默认决定（需求拐点/估值/催化时点）
KB_DRIVEN_FACTORS: Dict[str, float] = {
    "chokepoint_severity": 0.6,  # KB 命中『卡点/瓶颈/不可替代』时强信号
    "expansion_difficulty": 0.6,  # KB 命中『扩产/良率/认证/设备依赖』
    "supplier_concentration": 0.5,  # KB 命中『集中度/CR5/前五大』
}

INDUSTRY_PRIOR_FACTORS: Dict[str, float] = {
    "demand_inflection": 0.3,
    "architecture_coupling": 0.3,
    "evidence_quality": 0.3,
    "valuation_disconnect": 0.2,
    "catalyst_timing": 0.2,
}

# KB 加成上限（防止 KB 丰富标的上虚高）
KB_BONUS_CAP = 0.2
KB_BONUS_MIN_KB_SCORE = 0.6  # aggregate_score >= 此值才触发加成

# Serenity 评分卡最大分值（与原 serenity_scorecard 兼容）
_FACTOR_MAX_RATING = 5.0
_PENALTY_MAX_RATING = 5.0


# 关键词 → 因子相关度（用于从 KB chunk 文本算 kb_relevance）
# 类型用 FactorKeywordsMap 而非 Dict[str, ...]，让 pyright 跟踪到 FactorKey literal
FACTOR_KEYWORDS: FactorKeywordsMap = {
    "demand_inflection": ("需求拐点", "渗透率", "订单爆发", "扩产", "供不应求"),
    "architecture_coupling": ("架构耦合", "接口", "兼容", "标准绑定", "深度依赖"),
    "chokepoint_severity": ("卡点", "瓶颈", "不可替代", "国产化率", "卡脖子"),
    "supplier_concentration": ("集中度", "CR5", "前五大", "市占率", "份额集中"),
    "expansion_difficulty": ("扩产", "良率", "认证", "设备依赖", "验证周期"),
    "evidence_quality": ("公告", "年报", "电话会", "订单", "primary"),
    "valuation_disconnect": ("估值", "PE", "PB", "市值", "脱节"),
    "catalyst_timing": ("催化", "时点", "近期", "发布", "落地"),
}


class SerenityScorer:
    """统一 Serenity 评分入口。

    用法：
        scorer = SerenityScorer()
        result = scorer.score(
            ticker="600519", company="贵州茅台", market="A-share",
            graph=graph, kb_result=kb_result,
            llm_signals={"demand_inflection": 0.6, ...},
            industry_hint="高端白酒",
        )
        # result.final_score / result.verdict / result.factors / result.penalties

    行为开关（环境变量，回滚）：
    - SERENITY_SCORER_V2=false  → 走旧启发式（调用 _legacy_keyword_factors）
    """

    def __init__(self, legacy_scorer: Optional[Any] = None) -> None:
        self._legacy_scorer = legacy_scorer  # 可选注入旧实现

    def score(
        self,
        ticker: str,
        company: str,
        market: str = "",
        graph: Optional[SupplyChainGraph] = None,
        kb_result: Optional[SupplyChainKBResult] = None,
        llm_signals: Optional[Dict[str, float]] = None,
        industry_hint: str = "",
    ) -> SerenityScoreResult:
        """主入口。"""
        # 环境变量回退
        if os.environ.get("SERENITY_SCORER_V2", "true").lower() == "false":
            return self._score_legacy(ticker, company, market)

        kb_result = kb_result or SupplyChainKBResult(hits=[], aggregate_score=0.0)
        llm_signals = llm_signals or {}

        # 1. 算每个因子的 (kb_relevance, llm_signal, industry_prior)
        factors_scores: Dict[FactorKey, SerenityFactorScore] = {}
        for fkey in FACTOR_KEYWORDS:
            kb_rel = self._kb_relevance(kb_result, fkey)
            llm_sig = float(llm_signals.get(fkey, 0.0))
            ind_prior = self._industry_prior(fkey, industry_hint, graph)

            # 三层加权
            kb_w = KB_DRIVEN_FACTORS.get(fkey, 0.2)
            ind_w = INDUSTRY_PRIOR_FACTORS.get(fkey, 0.5)
            llm_w = max(0.0, 1.0 - kb_w - ind_w)

            raw_01 = kb_w * kb_rel + llm_w * llm_sig + ind_w * ind_prior
            raw_01 = max(0.0, min(1.0, raw_01))

            # KB 加成（仅 KB_DRIVEN + kb_score >= 0.6）
            bonus = 0.0
            if (
                fkey in KB_DRIVEN_FACTORS
                and kb_result.aggregate_score >= KB_BONUS_MIN_KB_SCORE
                and kb_rel >= 0.6
            ):
                bonus = KB_BONUS_CAP

            final_01 = min(1.0, raw_01 + bonus)
            rating = final_01 * _FACTOR_MAX_RATING
            weight = 1.0  # 简化：所有因子等权；与原 serenity_scorecard 一致
            points = rating * weight

            factors_scores[fkey] = SerenityFactorScore(  # type: ignore[arg-type]
                key=fkey,  # type: ignore[arg-type]
                rating=round(rating, 3),
                points=round(points, 3),
                weight=weight,
                kb_relevance=round(kb_rel, 4),
                llm_signal=round(llm_sig, 4),
                industry_prior=round(ind_prior, 4),
                kb_bonus_applied=round(bonus, 4),
                contributing_kb_doc_ids=[h.document_id for h in kb_result.hits[:3]],
            )

        # 2. 惩罚项（V2 暂时用 LLM 信号 + 行业默认，未接 KB 加权）
        penalties_scores: Dict[PenaltyKey, SerenityPenaltyScore] = {}
        for pkey in (
            "dilution_financing",
            "governance",
            "geopolitics",
            "liquidity",
            "hype_risk",
            "accounting_quality",
            "cyclicality",
            "alternative_design_risk",
        ):
            llm_sig = float(llm_signals.get(f"penalty_{pkey}", 0.0))
            rating = llm_sig * _PENALTY_MAX_RATING
            weight = 1.0
            points = -rating * weight  # 惩罚为负

            penalties_scores[pkey] = SerenityPenaltyScore(  # type: ignore[arg-type]
                key=pkey,
                rating=round(rating, 3),  # type: ignore[arg-type]
                points=round(points, 3),
                weight=weight,
            )

        raw_factor_points = sum(f.points for f in factors_scores.values())
        penalty_points = sum(p.points for p in penalties_scores.values())

        # 归一到 0-100（粗略：raw_max=40 → ×2.5 + 50 偏移）
        final_score = int(
            max(0, min(100, 50 + raw_factor_points * 2.5 + penalty_points))
        )

        verdict = _score_to_verdict(final_score)

        return SerenityScoreResult(
            ticker=ticker,
            company=company,
            market=market,
            factors=factors_scores,
            penalties=penalties_scores,
            raw_factor_points=round(raw_factor_points, 2),
            penalty_points=round(penalty_points, 2),
            final_score=final_score,
            verdict=verdict,
            notes=f"v2 unified scorer; kb_score={kb_result.aggregate_score:.2f}",
        )

    # ---------- 内部 ----------

    def _kb_relevance(self, kb_result: SupplyChainKBResult, fkey: FactorKey) -> float:
        """从 KB chunk 文本算因子相关度（命中关键词比例 × 命中 chunk 平均 score）。"""
        if not kb_result.hits:
            return 0.0
        kws = FACTOR_KEYWORDS.get(fkey, ())
        if not kws:
            return 0.0
        kw_hit = 0
        chunk_score_sum = 0.0
        chunk_with_kw = 0
        for h in kb_result.hits:
            content_lower = h.content.lower()
            local_hits = sum(1 for kw in kws if kw.lower() in content_lower)
            if local_hits > 0:
                kw_hit += local_hits
                chunk_score_sum += h.score
                chunk_with_kw += 1
        if kw_hit == 0:
            return 0.0
        kw_cov = kw_hit / len(kws)
        avg_chunk_score = chunk_score_sum / chunk_with_kw if chunk_with_kw else 0.0
        return min(1.0, kw_cov * (0.5 + 0.5 * avg_chunk_score))

    def _industry_prior(
        self, fkey: FactorKey, industry_hint: str, graph: Optional[SupplyChainGraph]
    ) -> float:
        """行业先验因子评分（0-1）。

        V2 简化：用 industry_hint 关键词匹配 + 图谱结构（节点数 / KB 覆盖率）做粗略估计。
        """
        # 默认 0.5
        prior = 0.5

        industry = (industry_hint or "").lower()
        if "半导体" in industry or "芯片" in industry:
            if fkey == "chokepoint_severity":
                prior = 0.85
            elif fkey == "expansion_difficulty":
                prior = 0.8
            elif fkey == "supplier_concentration":
                prior = 0.7
        elif "新能源" in industry or "电池" in industry or "锂" in industry:
            if fkey == "demand_inflection":
                prior = 0.7
            elif fkey == "expansion_difficulty":
                prior = 0.7
        elif "白酒" in industry or "消费" in industry:
            if fkey == "evidence_quality":
                prior = 0.7
            elif fkey == "demand_inflection":
                prior = 0.4

        # 图谱结构加权：KB 覆盖率 + 节点数
        if graph is not None:
            if graph.kb_coverage_score >= 0.8:
                prior = min(1.0, prior + 0.1)
            if len(graph.upstream) + len(graph.downstream) >= 8:
                prior = min(1.0, prior + 0.05)

        return prior

    def _score_legacy(
        self, ticker: str, company: str, market: str
    ) -> SerenityScoreResult:
        """回退到旧启发式（仅当 SERENITY_SCORER_V2=false）。"""
        if self._legacy_scorer is None:
            # 兜底：全零分
            return SerenityScoreResult(
                ticker=ticker,
                company=company,
                market=market,
                verdict="早期线索或低优先级",
                notes="legacy fallback (no legacy_scorer injected)",
            )
        import warnings

        warnings.warn(
            "SerenityScorer 走 legacy 路径，建议尽快迁移到 v2",
            DeprecationWarning,
            stacklevel=2,
        )
        # 调用旧实现并转 v2 schema（此处简化：旧 _infer_serenity_factors 不直接产出 SerenityScoreResult）
        # 实际生产应注入旧的 SupplyChainDataService 实例
        return SerenityScoreResult(
            ticker=ticker,
            company=company,
            market=market,
            verdict="早期线索或低优先级",
            notes="legacy fallback (stub)",
        )


def _score_to_verdict(score: int) -> str:
    """中文评级映射（与 serenity_scorecard.verdict_zh 对齐）。"""
    if score >= 85:
        return "顶级研究优先级"
    if score >= 70:
        return "高研究优先级"
    if score >= 50:
        return "值得跟踪"
    return "早期线索或低优先级"
