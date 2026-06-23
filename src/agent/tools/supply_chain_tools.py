# -*- coding: utf-8 -*-
"""供应链分析专属工具集。

当前仅 1 个工具：``score_supply_chain_bottleneck``（包装 serenity_scorecard）。
其余数据/情报工具**复用问股的全局 ToolRegistry**（行情/新闻/基本面/技术），
通过 ``build_supply_chain_executor`` 在 factory 里合并注册（见 factory.py）。
"""

import logging
from typing import Any, Dict, List, Optional

from src.agent.tools.registry import ToolDefinition, ToolParameter

logger = logging.getLogger(__name__)

# serenity_scorecard 的 8 个加权因子 + 8 个惩罚项（各 0-5 分）
FACTOR_KEYS = (
    "demand_inflection",        # 需求拐点
    "architecture_coupling",    # 架构耦合
    "chokepoint_severity",      # 卡点严重度
    "supplier_concentration",   # 供应商集中度
    "expansion_difficulty",     # 扩产难度
    "evidence_quality",         # 证据质量
    "valuation_disconnect",     # 估值脱节
    "catalyst_timing",          # 催化时点
)
PENALTY_KEYS = (
    "dilution_financing",       # 稀释/融资
    "governance",               # 治理
    "geopolitics",              # 地缘
    "liquidity",                # 流动性
    "hype_risk",                # 炒作
    "accounting_quality",       # 会计质量
    "cyclicality",              # 周期性
    "alternative_design_risk",  # 替代路线
)

_FACTOR_HINT = {
    "demand_inflection": "需求是否处于明确拐点(0=无,5=强拐点)",
    "architecture_coupling": "是否深度耦合于系统架构变化",
    "chokepoint_severity": "卡点严重度(客户无它无法扩产)",
    "supplier_concentration": "供应商集中度(少数厂商主导)",
    "expansion_difficulty": "扩产难度(设备/许可/纯度/验证周期)",
    "evidence_quality": "证据质量(强源占比)",
    "valuation_disconnect": "估值与基本面脱节程度",
    "catalyst_timing": "催化时点临近度",
}
_PENALTY_HINT = {
    "dilution_financing": "稀释/融资压力",
    "governance": "治理问题",
    "geopolitics": "地缘/出口管制风险",
    "liquidity": "流动性差",
    "hype_risk": "炒作风险",
    "accounting_quality": "会计质量存疑",
    "cyclicality": "周期性回落风险",
    "alternative_design_risk": "替代技术路线风险",
}


def _coerce_rating(value: Any) -> float:
    """把 LLM 传入的评分强转为 0-5 的 float，非法值归 0。"""
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return 0.0
    if rating < 0:
        return 0.0
    if rating > 5:
        return 5.0
    return rating


def _normalize_ratings(raw: Optional[Dict[str, Any]], keys: tuple[str, ...]) -> Dict[str, float]:
    """补全缺失字段为 0，并把每个值规整到 0-5。"""
    raw = raw or {}
    return {key: _coerce_rating(raw.get(key, 0)) for key in keys}


# ============================================================
# score_supply_chain_bottleneck
# ============================================================

def _handle_score_supply_chain_bottleneck(
    ticker: str,
    company: str,
    market: str = "",
    factors: Optional[Dict[str, Any]] = None,
    penalties: Optional[Dict[str, Any]] = None,
    evidence: Optional[List[Dict[str, Any]]] = None,
    what_could_weaken_view: Optional[List[str]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    """按 Serenity 框架给一只标的打"供应链瓶颈"分（满分 100）。"""
    from src.services.supply_chain import scorecard

    data = {
        "ticker": ticker or "",
        "company": company or "",
        "market": market or "",
        "notes": notes or "",
        "factors": _normalize_ratings(factors, FACTOR_KEYS),
        "penalties": _normalize_ratings(penalties, PENALTY_KEYS),
        "evidence": evidence or [],
        "what_could_weaken_view": what_could_weaken_view or [],
    }
    try:
        result, verdict = scorecard.score(data)
    except Exception as exc:
        logger.error("supply chain scorecard failed for %s: %s", ticker, exc, exc_info=True)
        return {"error": f"打分失败: {exc}", "input_echo": data}

    return {
        "ticker": data["ticker"],
        "company": data["company"],
        "verdict": scorecard.verdict_zh(verdict),
        "score_report_markdown": scorecard.to_markdown_zh(result),
        "final_score": result.get("final_score"),
        "usage_note": (
            "以上为 Serenity 框架瓶颈打分卡结果。衡量『供应链卡点强度』，"
            "非买卖建议。引用时请保留证据强度标签（强/中/弱/待查），"
            "不使用内部文件名或字段名。"
        ),
    }


score_supply_chain_bottleneck_tool = ToolDefinition(
    name="score_supply_chain_bottleneck",
    description=(
        "按 Serenity 供应链框架给一只标的打『瓶颈卡点』分（满分 100）。"
        "8 个加权因子（需求拐点/架构耦合/卡点严重度/供应商集中度/扩产难度/"
        "证据质量/估值脱节/催化时点）+ 8 个惩罚项（稀释/治理/地缘/流动性/炒作/"
        "会计/周期/替代路线），各 0-5 分。返回 verdict 评级、Markdown 报告与总分。"
        "用于『给 XX 打瓶颈分』『这家卡点有多强』类量化问题。"
    ),
    parameters=[
        ToolParameter(
            name="ticker",
            type="string",
            description="标的代码（如 600519 / AAPL / hk00700）",
            required=True,
        ),
        ToolParameter(
            name="company",
            type="string",
            description="公司名称",
            required=True,
        ),
        ToolParameter(
            name="market",
            type="string",
            description="市场：US / HK / A-share / Taiwan / Japan / Korea / Europe",
            required=False,
            default="",
        ),
        ToolParameter(
            name="factors",
            type="object",
            description=(
                "8 个加权因子的 0-5 评分，key 固定："
                + "；".join(f"{k}({h})" for k, h in _FACTOR_HINT.items())
            ),
            required=True,
        ),
        ToolParameter(
            name="penalties",
            type="object",
            description=(
                "8 个惩罚项的 0-5 评分（越高扣越多），key 固定："
                + "；".join(f"{k}({h})" for k, h in _PENALTY_HINT.items())
            ),
            required=False,
            default=None,
        ),
        ToolParameter(
            name="evidence",
            type="array",
            description="证据列表，每项 {claim, source, strength(primary/media/analysis/social/rumor)}",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="what_could_weaken_view",
            type="array",
            description="可能削弱判断的因素（证伪条件）列表",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="notes",
            type="string",
            description="备注（可选）",
            required=False,
            default="",
        ),
    ],
    handler=_handle_score_supply_chain_bottleneck,
    category="analysis",
)


ALL_SUPPLY_CHAIN_TOOLS = [score_supply_chain_bottleneck_tool]
