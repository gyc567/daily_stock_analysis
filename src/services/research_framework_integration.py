# -*- coding: utf-8 -*-
"""
Research Framework Integration Helper.

提供将长线投研框架集成到现有分析流水线的工具函数。
"""

import logging
from typing import Dict, Any, Optional, List

from src.analyzer import AnalysisResult

logger = logging.getLogger(__name__)


def integrate_research_framework(
    result: AnalysisResult,
    context: Dict[str, Any],
    enable_research_framework: bool = True,
) -> AnalysisResult:
    """
    将长线投研框架集成到分析结果中。

    此函数作为后处理步骤，在主分析完成后调用。
    它从分析结果和上下文中提取数据，调用 ResearchScoringService，
    并将结果注入到 AnalysisResult 的五段式长线投研字段。

    Args:
        result: 主分析产生的 AnalysisResult
        context: 分析上下文（包含技术指标、基本面数据等）
        enable_research_framework: 是否启用长线投研框架

    Returns:
        带有五段式长线投研框架数据的 AnalysisResult
    """
    if not enable_research_framework:
        logger.debug("Research framework disabled, skipping")
        return result

    try:
        from src.services.research_scoring_service import ResearchScoringService

        raw_data = _extract_raw_data_from_context(result, context)

        # P2-fix: 也从 LLM 的 dashboard / raw_result 里取主观维度键值
        _enrich_raw_data_from_llm_output(raw_data, result)

        scoring_service = ResearchScoringService()
        scoring_result = scoring_service.process_with_p2_enrichment(
            stock_code=result.code,
            stock_name=result.name,
            market=_infer_market(result.code),
            raw_data=raw_data,
            market_implied_p=_estimate_market_implied_p(result),
            enrich_with_providers=True,
        )

        result.research_framework = scoring_result.get("framework_score")
        result.bayesian_framework = scoring_result.get("bayesian_result")
        result.supply_chain = _build_supply_chain_from_analysis(
            result, context, raw_data
        )
        result.value_scenarios = _build_value_scenarios_from_analysis(
            result, context, scoring_result
        )
        result.investment_conclusion = _build_investment_conclusion(
            result,
            scoring_result.get("bayesian_result"),
            scoring_result.get("framework_score"),
        )

        logger.info(
            f"[ResearchFramework] Stock {result.code} processed: "
            f"dimension_total={scoring_result.get('framework_score', {}).get('dimension_total', 'N/A')}, "
            f"edge={scoring_result.get('bayesian_result', {}).get('edge', 'N/A')}"
        )

    except ImportError as e:
        logger.warning(f"[ResearchFramework] Module not available: {e}")
    except Exception as e:
        logger.warning(f"[ResearchFramework] Integration failed: {e}")

    return result


def _build_supply_chain_from_analysis(
    result: AnalysisResult,
    context: Dict[str, Any],
    raw_data: Dict[str, Any],
) -> Dict[str, Any]:
    """从分析结果构建产业链解读数据

    使用 SupplyChainDataService 获取数据：
    - 知识库: 常见股票的供应链信息
    - LLM推断: 从基本面分析文本中提取
    - Serenity: 瓶颈评分卡 (可选，需 enable_serenity=True)
    """
    try:
        from src.services.supply_chain_data_service import SupplyChainDataService

        market = _infer_market(result.code)
        fundamental_text = result.fundamental_analysis or ""

        sc_service = SupplyChainDataService()
        sc_data = sc_service.fetch_all(
            stock_code=result.code,
            stock_name=result.name,
            fundamental_analysis=fundamental_text,
            market=market,
            enable_serenity=False,
        )

        supply_chain_data = {
            "data_sources": sc_data.get("data_sources", []),
            "company_position": sc_data.get("company_position")
            or _extract_company_position(result),
            "upstream": sc_data.get("upstream")
            or _extract_upstream_from_analysis(result),
            "downstream": sc_data.get("downstream")
            or _extract_downstream_from_analysis(result),
            "chokepoints": sc_data.get("chokepoints")
            or _extract_chokepoints(result, raw_data),
            "us_china_chain": sc_data.get("us_china_chain")
            or _extract_us_china_chain(result),
            "industry_drivers": sc_data.get("industry_drivers")
            or _extract_industry_drivers(result, context),
            "chain_map": _build_chain_map_from_context(context),
            "serenity_score": sc_data.get("serenity_score"),
            "serenity_verdict": sc_data.get("serenity_verdict"),
        }

        logger.info(
            f"[ResearchFramework] Supply chain for {result.code}: "
            f"sources={sc_data.get('data_sources', [])}, "
            f"upstream={len(supply_chain_data['upstream'])}, "
            f"downstream={len(supply_chain_data['downstream'])}"
        )

        return supply_chain_data

    except ImportError as e:
        logger.warning(f"[ResearchFramework] SupplyChainDataService not available: {e}")
    except Exception as e:
        logger.warning(f"[ResearchFramework] Supply chain fetch failed: {e}")

    supply_chain_data = {
        "company_position": _extract_company_position(result),
        "upstream": _extract_upstream_from_analysis(result),
        "downstream": _extract_downstream_from_analysis(result),
        "chokepoints": _extract_chokepoints(result, raw_data),
        "us_china_chain": _extract_us_china_chain(result),
        "industry_drivers": _extract_industry_drivers(result, context),
        "chain_map": _build_chain_map_from_context(context),
    }

    if result.fundamental_analysis and len(result.fundamental_analysis) > 50:
        has_placeholders = _has_supply_chain_placeholders(supply_chain_data)
        if has_placeholders:
            llm_enriched = _enrich_supply_chain_with_llm(
                result.code, result.name, result.fundamental_analysis, supply_chain_data
            )
            if llm_enriched:
                supply_chain_data = llm_enriched

    return supply_chain_data


def _has_supply_chain_placeholders(supply_chain_data: Dict[str, Any]) -> bool:
    """检查产业链数据是否包含占位符值"""
    placeholder_keywords = ["待分析", "待详细", "待评估", "待挖掘"]

    if supply_chain_data.get("company_position") in placeholder_keywords:
        return True

    for key in ["upstream", "downstream"]:
        values = supply_chain_data.get(key, [])
        if isinstance(values, list):
            for v in values:
                if any(pk in str(v) for pk in placeholder_keywords):
                    return True

    chokepoints = supply_chain_data.get("chokepoints", [])
    for cp in chokepoints:
        if isinstance(cp, dict):
            desc = cp.get("description", "")
            if any(pk in str(desc) for pk in placeholder_keywords):
                return True

    us_china = supply_chain_data.get("us_china_chain", {})
    for v in us_china.values():
        if any(pk in str(v) for pk in placeholder_keywords):
            return True

    drivers = supply_chain_data.get("industry_drivers", [])
    for d in drivers:
        if any(pk in str(d) for pk in placeholder_keywords):
            return True

    return False


def _enrich_supply_chain_with_llm(
    stock_code: str,
    stock_name: str,
    fundamental_text: str,
    supply_chain_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """使用LLM从基本面分析文本中提取产业链信息来丰富数据"""
    try:
        from src.services.research_scoring_service import ResearchScoringService

        scoring_service = ResearchScoringService()
        llm_result = scoring_service.extract_supply_chain_from_llm(
            stock_code, stock_name, fundamental_text
        )

        if not llm_result:
            return None

        enriched = supply_chain_data.copy()

        if llm_result.get("chain_position"):
            enriched["company_position"] = llm_result.get("chain_position")

        if llm_result.get("upstream"):
            upstream_list = llm_result.get("upstream", [])
            if isinstance(upstream_list, list) and upstream_list:
                current_upstream = enriched.get("upstream", [])
                if not any(
                    pk in str(v)
                    for v in current_upstream
                    for pk in ["待分析", "待详细"]
                ):
                    pass
                else:
                    enriched["upstream"] = upstream_list[:3]

        if llm_result.get("downstream"):
            downstream_list = llm_result.get("downstream", [])
            if isinstance(downstream_list, list) and downstream_list:
                current_downstream = enriched.get("downstream", [])
                if not any(
                    pk in str(v)
                    for v in current_downstream
                    for pk in ["待分析", "待详细"]
                ):
                    pass
                else:
                    enriched["downstream"] = downstream_list[:3]

        if llm_result.get("chokepoint_type"):
            chokepoints = enriched.get("chokepoints", [])
            has_placeholder = False
            for cp in chokepoints:
                if isinstance(cp, dict) and any(
                    pk in str(cp.get("description", "")) for pk in ["待详细", "unknown"]
                ):
                    has_placeholder = True
                    break
            if has_placeholder:
                enriched["chokepoints"] = [
                    {
                        "type": llm_result.get("chokepoint_type", "tech"),
                        "description": llm_result.get(
                            "chokepoint_desc", "基于LLM分析提取的瓶颈点"
                        ),
                        "confidence": "medium",
                    }
                ]

        if llm_result.get("us_business_ratio") or llm_result.get("sanction_risk"):
            current_us = enriched.get("us_china_chain", {})
            if any(
                pk in str(v) for v in current_us.values() for pk in ["待分析", "待评估"]
            ):
                enriched["us_china_chain"] = {
                    "role": llm_result.get("us_business_ratio", "待分析"),
                    "substitution_progress": llm_result.get(
                        "substitution_progress", "待分析"
                    ),
                    "sanction_risk": llm_result.get("sanction_risk", "待观察"),
                    "dual_chain_impact": llm_result.get("dual_chain_impact", "待分析"),
                }

        if llm_result.get("industry_drivers"):
            drivers = llm_result.get("industry_drivers", [])
            if isinstance(drivers, list) and drivers:
                current_drivers = enriched.get("industry_drivers", [])
                if any(
                    pk in str(d) for d in current_drivers for pk in ["待详细", "待分析"]
                ):
                    enriched["industry_drivers"] = drivers[:3]

        logger.info(f"[ResearchFramework] LLM enrichment applied for {stock_code}")
        return enriched

    except Exception as e:
        logger.warning(f"[ResearchFramework] LLM enrichment failed: {e}")
        return None


def _build_value_scenarios_from_analysis(
    result: AnalysisResult,
    context: Dict[str, Any],
    scoring_result: Dict[str, Any],
) -> Dict[str, Any]:
    """从分析结果构建长期价值与情景数据"""
    fundamental = context.get("fundamental", {})
    current_price = context.get("current_price") or fundamental.get("current_price")

    scenarios = []
    if current_price:
        upside = fundamental.get("upside_potential", 30)
        scenarios = [
            {
                "type": "optimistic",
                "probability": 0.25,
                "value_anchor": round(current_price * (1 + upside / 100 * 1.5), 2),
                "description": "乐观情景：产业高速增长，产能利用率提升",
            },
            {
                "type": "neutral",
                "probability": 0.50,
                "value_anchor": round(current_price * (1 + upside / 100), 2),
                "description": "中性情景：稳定增长，份额保持",
            },
            {
                "type": "pessimistic",
                "probability": 0.25,
                "value_anchor": round(current_price * (1 - upside / 100 * 0.5), 2),
                "description": "悲观情景：竞争加剧，盈利承压",
            },
        ]

    horizons = {}
    if current_price:
        upside = fundamental.get("upside_potential", 30)
        range_factor = 0.15
        for years, multiplier in [(1, 1), (3, 1.5), (5, 2)]:
            base_value = current_price * (1 + upside / 100 * multiplier)
            low = round(base_value * (1 - range_factor), 2)
            high = round(base_value * (1 + range_factor), 2)
            horizons[f"horizon_{years}y"] = f"{low}~{high} 元"

    value_scenarios_data = {
        "industry_space": _extract_industry_space(result, context),
        "competitive_evolution": _extract_competitive_evolution(result),
        "scenarios": scenarios,
        "horizons": horizons,
        "catalysts": _extract_catalysts(result),
        "risks": _extract_risks(result),
    }
    return value_scenarios_data


def _extract_company_position(result: AnalysisResult) -> str:
    """提取公司在产业链中的定位"""
    if result.fundamental_analysis:
        analysis = result.fundamental_analysis[:200]
        return f"基于基本面分析：{analysis}"
    return "产业链定位待详细分析"


def _extract_upstream_from_analysis(result: AnalysisResult) -> List[str]:
    """提取上游供应商信息"""
    if not result.fundamental_analysis:
        return []

    upstream_keywords = ["上游", "供应商", "原材料", "采购"]
    upstream = []
    text = result.fundamental_analysis
    for kw in upstream_keywords:
        if kw in text:
            idx = text.find(kw)
            start = max(0, idx - 20)
            end = min(len(text), idx + 50)
            snippet = text[start:end]
            upstream.append(snippet.strip())
            break
    return upstream if upstream else ["上游信息待详细分析"]


def _extract_downstream_from_analysis(result: AnalysisResult) -> List[str]:
    """提取下游客户信息"""
    if not result.fundamental_analysis:
        return []

    downstream_keywords = ["下游", "客户", "应用", "终端"]
    downstream = []
    text = result.fundamental_analysis
    for kw in downstream_keywords:
        if kw in text:
            idx = text.find(kw)
            start = max(0, idx - 20)
            end = min(len(text), idx + 50)
            snippet = text[start:end]
            downstream.append(snippet.strip())
            break
    return downstream if downstream else ["下游信息待详细分析"]


def _extract_chokepoints(
    result: AnalysisResult, raw_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """提取瓶颈点信息"""
    chokepoints = []

    if raw_data.get("chokepoint_type"):
        chokepoints.append(
            {
                "type": raw_data.get("chokepoint_type", "unknown"),
                "description": raw_data.get(
                    "supply_chain_evidence", "基于分析提取的瓶颈点"
                ),
                "confidence": "medium",
            }
        )

    moat = raw_data.get("moat_assessment", "")
    if "strong" in moat.lower() or "强" in moat:
        chokepoints.append(
            {
                "type": "patent",
                "description": "护城河较强，专利壁垒明显",
                "confidence": "medium",
            }
        )

    return (
        chokepoints
        if chokepoints
        else [
            {
                "type": "unknown",
                "description": "瓶颈点待详细产业链分析",
                "confidence": "low",
            }
        ]
    )


def _extract_us_china_chain(result: AnalysisResult) -> Dict[str, str]:
    """提取中美双链位置"""
    if result.fundamental_analysis:
        text = result.fundamental_analysis.lower()
        if any(kw in text for kw in ["国产", "替代", "自主"]):
            return {
                "role": "中国链",
                "substitution_progress": "国产替代进行中",
                "sanction_risk": "低",
                "dual_chain_impact": "受益",
            }
        if any(kw in text for kw in ["出口", "海外", "美国"]):
            return {
                "role": "双链节点",
                "substitution_progress": "国际化布局",
                "sanction_risk": "中",
                "dual_chain_impact": "中性",
            }

    return {
        "role": "待分析",
        "substitution_progress": "待分析",
        "sanction_risk": "待评估",
        "dual_chain_impact": "待评估",
    }


def _extract_industry_drivers(
    result: AnalysisResult, context: Dict[str, Any]
) -> List[str]:
    """提取产业驱动根因"""
    drivers = []

    if result.fundamental_analysis:
        text = result.fundamental_analysis
        driver_keywords = ["增长", "需求", "政策", "技术", "创新", "扩产"]
        for kw in driver_keywords:
            if kw in text:
                drivers.append(f"驱动因素：{kw}")

    trend = context.get("trend", {})
    if trend.get("trend_direction") == "up":
        drivers.append("趋势驱动：长期上升通道")

    return drivers if drivers else ["产业驱动因素待详细分析"]


def _build_chain_map_from_context(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从上下文构建供应链地图"""
    fundamental = context.get("fundamental", {})
    sector = fundamental.get("industry", "")

    return [
        {
            "level": "下游应用",
            "companies": [f"{sector}相关应用领域"] if sector else ["下游应用"],
            "concentration": None,
        },
        {
            "level": "中游制造",
            "companies": [],
            "concentration": None,
        },
        {
            "level": "上游组件",
            "companies": [],
            "concentration": None,
        },
    ]


def _extract_industry_space(result: AnalysisResult, context: Dict[str, Any]) -> str:
    """提取产业长期空间"""
    if result.fundamental_analysis:
        return result.fundamental_analysis[:200]
    return "产业空间待详细分析"


def _extract_competitive_evolution(result: AnalysisResult) -> str:
    """提取竞争格局演变"""
    if result.fundamental_analysis:
        return f"基于基本面分析，竞争格局分析：{result.fundamental_analysis[:150]}..."
    return "竞争格局演变待详细分析"


def _extract_catalysts(result: AnalysisResult) -> List[str]:
    """提取潜在催化事件"""
    catalysts = []

    if result.market_sentiment:
        catalysts.append("消息面：存在正面催化剂")

    if result.sentiment_score and result.sentiment_score >= 70:
        catalysts.append("情绪面：市场情绪偏乐观")

    return catalysts if catalysts else ["潜在催化事件待详细分析"]


def _extract_risks(result: AnalysisResult) -> List[str]:
    """提取主要风险"""
    risks = []

    if result.operation_advice == "观望":
        risks.append("操作建议观望，注意短期风险")

    if result.sentiment_score and result.sentiment_score < 50:
        risks.append("情绪评分偏低，市场信心不足")

    return risks if risks else ["风险因素待详细分析"]


def _extract_raw_data_from_context(
    result: AnalysisResult,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """从分析结果和上下文中提取评分所需的数据

    P2-fix: 原实现只查 ``context["fundamental"]`` / ``context["trend"]`` /
    ``context["capital_flow"]`` 这三个**顶层 key**，但 Pipeline 实际产出的
    ``enhanced_context`` 里没有这些顶层 key——它们分别被存放在
    ``enhanced_context.fundamental_context`` /
    ``enhanced_context.trend_analysis`` / ``enhanced_context.realtime`` 等
    嵌套位置。新实现在两层都能读取（向后兼容顶层写法），并新增
    valuation/growth/earnings 字段映射、以及基于日线 + 实时价推算
    ma250 偏离 / 52周高点距离 / 量能趋势 / 趋势持续月份。
    """
    raw_data = {}

    # ---- legacy: context["fundamental"] (顶层) ----
    if context.get("fundamental"):
        fund = context["fundamental"]
        _fundament_merge(raw_data, fund)

    # ---- legacy: context["trend"] ----
    if context.get("trend"):
        trend = context["trend"]
        raw_data["price_vs_ma250"] = trend.get("price_vs_ma250")
        raw_data["distance_from_high"] = trend.get("distance_from_high")
        _ma_alignment_from_text(raw_data, trend.get("ma_alignment"))

    # ---- legacy: context["capital_flow"] ----
    if context.get("capital_flow"):
        cap = context["capital_flow"]
        _capital_merge(raw_data, cap)

    # ---- new: enhanced_context.realtime ----
    rt = context.get("realtime") or {}
    if isinstance(rt, dict):
        if rt.get("pe_ratio") is not None and rt["pe_ratio"] > 0:
            pe_pctile = _pe_to_percentile(rt["pe_ratio"])
            if pe_pctile is not None:
                raw_data.setdefault("pe_percentile", pe_pctile)
        if rt.get("pb_ratio") is not None and rt["pb_ratio"] > 0:
            pb_pctile = _pb_to_percentile(rt["pb_ratio"])
            if pb_pctile is not None:
                raw_data.setdefault("pb_percentile", pb_pctile)
        if rt.get("turnover_rate") is not None:
            raw_data["turnover_rate"] = rt["turnover_rate"]

    # ---- new: enhanced_context.fundamental_context → valuation / growth / earnings ----
    fc = context.get("fundamental_context") or {}
    if isinstance(fc, dict):
        # fundamental_context 自身没有 "data" key；数据分别在各 block 的 data 里
        _v = fc.get("valuation")
        _g = fc.get("growth")
        _e = fc.get("earnings")
        valuation_block: Dict[str, Any] = _v if isinstance(_v, dict) else {}
        growth_block: Dict[str, Any] = _g if isinstance(_g, dict) else {}
        earnings_block: Dict[str, Any] = _e if isinstance(_e, dict) else {}

        if valuation_block.get("status") in ("ok", "partial"):
            _valuation_merge(raw_data, valuation_block.get("data") or {}, rt)
        if growth_block.get("status") in ("ok", "partial"):
            _growth_merge(raw_data, growth_block.get("data") or {})
        if earnings_block.get("status") in ("ok", "partial"):
            _earnings_merge(raw_data, earnings_block.get("data") or {})

    # ---- new: enhanced_context.trend_analysis → ma_alignment + derive extra indicators ----
    ta = context.get("trend_analysis") or {}
    if isinstance(ta, dict):
        if not raw_data.get("ma_alignment"):
            _ma_alignment_from_text(
                raw_data, ta.get("trend_status") or ta.get("ma_alignment")
            )
        raw_data.setdefault("bias_ma5", _safe_num(ta.get("bias_ma5")))
        if isinstance(ta.get("volume_status"), str):
            _volume_status_to_trend(raw_data, ta["volume_status"])

    # ---- new: derive ma250 + 52w high from daily + realtime ----
    today = context.get("today") or {}
    yesterday = context.get("yesterday") or {}
    if isinstance(today, dict):
        _derive_technical_indicators(raw_data, today, yesterday, rt)

    # ---- new: news sentiment from market_sentiment text ----
    if result.market_sentiment:
        raw_data["news_sentiment"] = _infer_sentiment(result.market_sentiment)

    # ---- existing moat extraction ----
    if result.fundamental_analysis:
        moat = _extract_moat_from_analysis(result.fundamental_analysis)
        if moat:
            raw_data["moat_assessment"] = moat
        sc_ev = _extract_supply_chain_from_analysis(result.fundamental_analysis)
        if sc_ev:
            raw_data["supply_chain_evidence"] = sc_ev

    # ---- existing analyst_consensus from sentiment_score ----
    sentiment = result.sentiment_score
    if sentiment is not None:
        if sentiment >= 70:
            raw_data["analyst_consensus"] = "buy"
            raw_data["target_price_upside"] = 20.0
        elif sentiment >= 60:
            raw_data["analyst_consensus"] = "outperform"
            raw_data["target_price_upside"] = 15.0
        elif sentiment >= 40:
            raw_data["analyst_consensus"] = "neutral"
            raw_data["target_price_upside"] = 5.0
        else:
            raw_data["analyst_consensus"] = "underperform"
            raw_data["target_price_upside"] = -10.0

    # P2-fix: strip None values so scoring functions don't trigger "中性分" fallback
    # for fields that legacy schema *did* have but were empty in this stock.
    return {k: v for k, v in raw_data.items() if v is not None and v != ""}


def _enrich_raw_data_from_llm_output(
    raw_data: Dict[str, Any], result: AnalysisResult
) -> None:
    """P2-fix: 从 LLM 输出（dashboard / six_dimension_inputs）提取主观维度键值。

    主要来源（按优先级）：
    1. result.six_dimension_inputs（LLM 在根级写的 ⑥ 个长线维度键值，由
       Analyzer 解析 JSON 后透传；prompt 章节「长线六维·主观键值」触发）
    2. result.dashboard.intelligence / data_perspective（fallback）

    只在 raw_data 还没填该字段时填充，避免覆盖更准确的来源。
    """
    # ---- 1. 优先: six_dimension_inputs ----
    six = getattr(result, "six_dimension_inputs", None)
    if isinstance(six, dict):
        _merge_six_dim(raw_data, six)
    else:
        # 备用：从 dashboard 顶层找（万一 LLM 把 six_dimension_inputs 放在 dashboard 里）
        if isinstance(getattr(result, "dashboard", None), dict):
            _six_in_dash = result.dashboard.get("six_dimension_inputs")  # type: ignore[union-attr]
            if isinstance(_six_in_dash, dict):
                _merge_six_dim(raw_data, _six_in_dash)

    # ---- 2. Fallback: dashboard.data_perspective / intelligence ----
    if not isinstance(getattr(result, "dashboard", None), dict):
        return
    dash: Dict[str, Any] = result.dashboard  # type: ignore[assignment]
    _dp = dash.get("data_perspective")
    _intel = dash.get("intelligence")
    data_perspective = _dp if isinstance(_dp, dict) else {}
    intelligence = _intel if isinstance(_intel, dict) else {}
    _chip = data_perspective.get("chip_structure")
    chip_struct = _chip if isinstance(_chip, dict) else {}

    if "chip_concentration" not in raw_data:
        _conc = chip_struct.get("concentration")
        if isinstance(_conc, (int, float)):
            v = float(_conc)
            if v >= 30:
                raw_data["chip_concentration"] = "high"
            elif v >= 15:
                raw_data["chip_concentration"] = "medium"
            else:
                raw_data["chip_concentration"] = "low"

    if "news_sentiment" not in raw_data:
        for key in (
            "sentiment_summary",
            "earnings_outlook",
            "latest_news",
        ):
            val = intelligence.get(key) if isinstance(intelligence, dict) else None
            if isinstance(val, str) and val.strip():
                inferred = _infer_sentiment(val)
                if inferred:
                    raw_data["news_sentiment"] = inferred
                    break

    if "cognitive_difference" not in raw_data:
        if isinstance(intelligence, dict):
            risk_alerts = intelligence.get("risk_alerts") or []
            catalysts = intelligence.get("positive_catalysts") or []
            if isinstance(risk_alerts, list) and isinstance(catalysts, list):
                if len(catalysts) >= 2 and len(risk_alerts) == 0:
                    raw_data["cognitive_difference"] = "market_underestimating"
                elif len(risk_alerts) > len(catalysts):
                    raw_data["cognitive_difference"] = "market_overestimating"
                elif len(catalysts) > 0 or len(risk_alerts) > 0:
                    raw_data["cognitive_difference"] = "market_fair"

    # 估值分位：极少出现但留作扩展位
    if "pe_percentile" not in raw_data:
        for k in ("pe_percentile", "valuation_percentile", "pe_quantile"):
            v = data_perspective.get(k)
            if isinstance(v, (int, float)):
                raw_data["pe_percentile"] = float(v)
                break


def _merge_six_dim(raw_data: Dict[str, Any], six: Dict[str, Any]) -> None:
    """把 LLM 写的 six_dimension_inputs 复制到 raw_data（仅当还未填）。"""
    if not isinstance(six, dict):
        return
    _STR_KEYS: Dict[str, str] = {
        "chain_position": "chain_position",
        "moat_type": "moat_type",
        "moat_strength": "moat_strength",
        "us_china_risk": "us_china_risk",
        "chokepoint_type": "chokepoint_type",
        "cognitive_difference": "cognitive_difference",
        "news_sentiment": "news_sentiment",
    }
    for src_key, dst_key in _STR_KEYS.items():
        if dst_key in raw_data:
            continue
        v = six.get(src_key)
        if isinstance(v, str) and v.strip() and v.strip().lower() != "null":
            raw_data[dst_key] = v.strip()

    # 浮点字段
    for src_key, dst_key in (("customer_concentration", "customer_concentration"),):
        if dst_key in raw_data:
            continue
        v = six.get(src_key)
        try:
            if v is not None and v != "" and v != "null":
                f = float(v)
                if f == f:  # NaN guard
                    raw_data[dst_key] = f
        except (TypeError, ValueError):
            pass

    # 数组字段
    for src_key, dst_key in (("recent_catalysts", "recent_catalysts"),):
        if dst_key in raw_data:
            continue
        v = six.get(src_key)
        if isinstance(v, list) and v:
            raw_data[dst_key] = [str(x) for x in v if x is not None]

    # chip_concentration（数值 0-100 → high/medium/low）
    if "chip_concentration" not in raw_data:
        v = six.get("chip_concentration")
        try:
            if v is not None and v != "" and v != "null":
                f = float(v)
                if f >= 30:
                    raw_data["chip_concentration"] = "high"
                elif f >= 15:
                    raw_data["chip_concentration"] = "medium"
                else:
                    raw_data["chip_concentration"] = "low"
        except (TypeError, ValueError):
            pass


def _fundament_merge(raw_data: Dict[str, Any], fund: Dict[str, Any]) -> None:
    """Merge top-level context['fundamental'] keys into raw_data."""
    for key in (
        "pe_percentile",
        "pb_percentile",
        "roe",
        "revenue_growth",
        "earnings_growth",
        "gross_margin",
    ):
        v = fund.get(key)
        if v is not None:
            raw_data[key] = v


def _capital_merge(raw_data: Dict[str, Any], cap: Dict[str, Any]) -> None:
    """Merge top-level context['capital_flow'] keys into raw_data."""
    for key in (
        "northbound_flow_20d",
        "margin_balance_change",
        "foreign_ratio",
    ):
        v = cap.get(key)
        if v is not None:
            raw_data[key] = v


def _ma_alignment_from_text(raw_data: Dict[str, Any], text: Optional[str]) -> None:
    """Map Chinese/English ma_alignment text → scoring enum."""
    if not text or not isinstance(text, str):
        return
    t = text.lower()
    if "多头" in t or "bullish" in t:
        raw_data["ma_alignment"] = "bullish"
    elif "空头" in t or "bearish" in t:
        raw_data["ma_alignment"] = "bearish"
    else:
        raw_data["ma_alignment"] = "neutral"


def _volume_status_to_trend(raw_data: Dict[str, Any], status: str) -> None:
    """Map Chinese volume_status → scoring volume_trend enum."""
    s = status.strip()
    mapping = {
        "放量": "increasing",
        "放量上涨": "increasing",
        "放量杀跌": "increasing",
        "平量": "stable",
        "平量上涨": "stable",
        "平量下跌": "stable",
        "缩量": "decreasing",
        "缩量回调": "decreasing",
        "缩量下跌": "decreasing",
    }
    raw_data["volume_trend"] = mapping.get(s, s)


def _safe_num(v: Any) -> Optional[float]:
    """Safe numeric coercion; returns None for None / non-numeric / NaN."""
    if v is None or v == "" or v == "N/A":
        return None
    try:
        f = float(v)
        return f if f == f else None  # NaN guard
    except (TypeError, ValueError):
        return None


def _pe_to_percentile(pe_ratio: float) -> Optional[float]:
    """Heuristic PE → percentile (0=cheapest, 100=most expensive).

    Assumes A股 market-wide PE distribution:
    PE ≤ 0   → 90 (亏损，难判断)
    0 < PE ≤ 15  → percentile 25 (低估)
    15 < PE ≤ 30 → 50
    30 < PE ≤ 50 → 75
    PE > 50 → 95
    """
    try:
        pe = float(pe_ratio)
    except (TypeError, ValueError):
        return None
    if pe <= 0:
        return 90.0
    if pe <= 15:
        return 25.0
    if pe <= 30:
        return 50.0
    if pe <= 50:
        return 75.0
    return 95.0


def _pb_to_percentile(pb_ratio: float) -> Optional[float]:
    try:
        pb = float(pb_ratio)
    except (TypeError, ValueError):
        return None
    if pb <= 0:
        return None
    if pb <= 1.5:
        return 20.0
    if pb <= 3:
        return 45.0
    if pb <= 6:
        return 70.0
    return 90.0


def _valuation_merge(
    raw_data: Dict[str, Any],
    fund_data: Dict[str, Any],
    rt: Dict[str, Any],
) -> None:
    """Map fundamental_context.valuation.data → scoring fields."""
    if "pe_percentile" not in raw_data:
        pe = fund_data.get("pe_ratio") or (rt or {}).get("pe_ratio")
        pct = _pe_to_percentile(pe) if pe is not None else None
        if pct is not None:
            raw_data["pe_percentile"] = pct
    if "pb_percentile" not in raw_data:
        pb = fund_data.get("pb_ratio") or (rt or {}).get("pb_ratio")
        pct = _pb_to_percentile(pb) if pb is not None else None
        if pct is not None:
            raw_data["pb_percentile"] = pct
    mv = fund_data.get("total_mv") or (rt or {}).get("total_mv")
    if mv is not None:
        raw_data["total_mv"] = mv


def _growth_merge(raw_data: Dict[str, Any], fund_data: Dict[str, Any]) -> None:
    """Map growth.data + earnings.data → scoring fields."""
    revenue_yoy = fund_data.get("revenue_yoy") or fund_data.get("revenue_growth")
    if revenue_yoy is not None:
        try:
            raw_data["revenue_growth"] = float(revenue_yoy)
        except (TypeError, ValueError):
            pass
    np_yoy = fund_data.get("np_yoy") or fund_data.get("earnings_growth")
    if np_yoy is not None:
        try:
            raw_data["earnings_growth"] = float(np_yoy)
        except (TypeError, ValueError):
            pass
    roe = fund_data.get("roe") or fund_data.get("weighted_roe")
    if roe is not None:
        try:
            v = float(roe)
            if v < 1:  # 已是百分比小数，转成百分点
                v *= 100.0
            raw_data["roe"] = v
        except (TypeError, ValueError):
            pass
    gm = fund_data.get("gross_margin")
    if gm is not None:
        try:
            raw_data["gross_margin"] = float(gm)
        except (TypeError, ValueError):
            pass


def _earnings_merge(raw_data: Dict[str, Any], fund_data: Dict[str, Any]) -> None:
    """Earnings block uses same growth data fields; reserved for future splits."""
    if "earnings_growth" not in raw_data:
        np_yoy = fund_data.get("np_yoy")
        if np_yoy is not None:
            try:
                raw_data["earnings_growth"] = float(np_yoy)
            except (TypeError, ValueError):
                pass


def _derive_technical_indicators(
    raw_data: Dict[str, Any],
    today: Dict[str, Any],
    yesterday: Dict[str, Any],
    rt: Dict[str, Any],
) -> None:
    """Derive ma250 偏离 / 52周高点距离 / 趋势持续月份 from existing data.

    Today row only has ma5/10/20 (no ma250 in storage). To stay honest we set
    ``price_vs_ma250`` only when we have a higher-MA anchor (or skip and let
    the scoring function emit its 50 分 fallback, which is the truthful
    answer if we don't actually know the MA250).
    """
    close = _safe_num(today.get("close"))
    if close is None:
        return

    # 距离 52 周高点 (近似：若 today's high 接近全期 highs，则 distance_from_high≈0)
    high = _safe_num(today.get("high"))
    if high is not None and high > 0:
        # 没有 52w 高点锚点时，把今日高 当作近期高点，并允许 0~ +5% 的容差
        # 这种近似只能体现"距今日高点"，语义不准时留给"无数据"分支
        # 不强行写入 distance_from_high，由 scoring 走 50 分兜底
        pass

    # 量能趋势：今 vs 昨 volume
    today_vol = _safe_num(today.get("volume"))
    yest_vol = _safe_num(
        yesterday.get("volume") if isinstance(yesterday, dict) else None
    )
    if today_vol is not None and yest_vol is not None and yest_vol > 0:
        ratio = today_vol / yest_vol
        if ratio >= 1.2:
            trend = "increasing"
        elif ratio <= 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
        # 只在 extractor 已推断 volume_status 但未设置 volume_trend 时写入
        if "volume_trend" not in raw_data:
            raw_data["volume_trend"] = trend

    # price_vs_ma20 由 ma20 推算
    ma20 = _safe_num(today.get("ma20"))
    if ma20 is not None and ma20 > 0 and "price_vs_ma250" not in raw_data:
        # 不写 ma250（无法推算）；只标注 ma20 偏离
        raw_data.setdefault("_ma20_bias_pct", (close - ma20) / ma20 * 100.0)


def _extract_moat_from_analysis(text: str) -> str:
    """从基本面分析文本中提取护城河评估"""
    moat_keywords = ["护城河", "壁垒", "专利", "技术", "品牌", "垄断", "稀缺", "独占"]
    text_lower = text.lower()

    strong_keywords = ["强护城河", "深厚", "强大", "核心", "不可替代", "wide moat"]
    weak_keywords = ["护城河弱", "竞争激烈", "壁垒低", "易被复制"]

    for kw in strong_keywords:
        if kw.lower() in text_lower:
            return "深厚护城河，行业领先地位"
    for kw in weak_keywords:
        if kw.lower() in text_lower:
            return "护城河薄弱，面临竞争压力"

    for kw in moat_keywords:
        if kw in text:
            return "存在一定护城河（基于专利/技术优势）"

    return "护城河评估待详细分析"


def _extract_supply_chain_from_analysis(text: str) -> str:
    """从基本面分析文本中提取产业链信息"""
    chain_keywords = ["上游", "下游", "供应链", "产业链", "供应商", "客户", "议价"]

    for kw in chain_keywords:
        if kw in text:
            idx = text.find(kw)
            start = max(0, idx - 50)
            end = min(len(text), idx + 100)
            return f"...{text[start:end]}..."

    return ""


def _infer_sentiment(text: str) -> str:
    """从市场情绪文本推断情绪分类"""
    text_lower = text.lower()

    positive_keywords = ["乐观", "积极", "向好", "看好", "乐观", "bullish", "positive"]
    negative_keywords = ["悲观", "消极", "悲观", "看空", "担忧", "bearish", "negative"]

    positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
    negative_count = sum(1 for kw in negative_keywords if kw in text_lower)

    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    return "neutral"


def _estimate_market_implied_p(result: AnalysisResult) -> float:
    """从分析结果估算市场隐含概率"""
    sentiment = result.sentiment_score if result.sentiment_score is not None else 50

    sentiment_p = sentiment / 100.0

    decision_type = getattr(result, "decision_type", "hold")
    if decision_type == "buy":
        return min(1.0, sentiment_p + 0.1)
    elif decision_type == "sell":
        return max(0.0, sentiment_p - 0.1)
    return sentiment_p


def _infer_market(stock_code: str) -> str:
    """从股票代码推断市场"""
    if not stock_code:
        return "cn"

    code_upper = stock_code.upper()

    if code_upper.startswith("HK"):
        return "hk"

    if ".HK" in code_upper:
        return "hk"

    if (
        code_upper.startswith("AAPL")
        or code_upper.startswith("GOOG")
        or code_upper.startswith("MSFT")
    ):
        return "us"

    if code_upper.startswith("00") and len(stock_code) <= 4:
        return "hk"

    if len(stock_code) == 5:
        return "hk"

    return "cn"


def _build_investment_conclusion(
    result: AnalysisResult,
    bayesian_result: Optional[Dict[str, Any]],
    framework_score: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """从贝叶斯结果构建投资结论"""
    if not bayesian_result:
        return {
            "action": "观察",
            "position": "观察",
            "rationale": "暂无长线投研数据",
        }

    edge = bayesian_result.get("edge", 0)
    prior_p = bayesian_result.get("prior_p", 0.5)
    posterior_p = bayesian_result.get("posterior_p", prior_p)
    position = bayesian_result.get("position_suggestion", "0-1%")

    if edge > 0.3:
        action = "加仓" if getattr(result, "decision_type", "") == "buy" else "建仓"
    elif edge > 0.1:
        action = "持有"
    elif edge < -0.1:
        action = "减仓" if edge < -0.3 else "观察"
    else:
        action = "观察"

    chain_summary = ""
    if framework_score:
        dimensions = framework_score.get("dimensions", [])
        for dim in dimensions:
            if dim.get("dimension") == "产业链定位":
                score = dim.get("score", 0)
                chain_summary = f"产业链定位评分 {score:.1f}"
                break

    return {
        "prior_p": prior_p,
        "market_implied_p": bayesian_result.get("market_implied_p"),
        "edge": edge,
        "posterior_p": posterior_p,
        "position": position,
        "action": action,
        "chain_position_summary": chain_summary,
        "stop_conditions": bayesian_result.get("stop_conditions"),
        "rationale": _generate_rationale(result, edge, posterior_p),
    }


def _generate_rationale(result: AnalysisResult, edge: float, posterior_p: float) -> str:
    """生成投资理由"""
    parts = []

    if result.analysis_summary:
        summary = result.analysis_summary[:100]
        parts.append(f"分析摘要: {summary}...")

    if edge > 0.2:
        parts.append(f"认知差显著 ({edge * 100:.1f}%)，市场可能低估了公司价值")
    elif edge > 0.1:
        parts.append(f"存在一定认知差 ({edge * 100:.1f}%)")
    elif edge < -0.1:
        parts.append(f"认知差为负 ({edge * 100:.1f}%)，市场可能高估")

    if posterior_p > 0.7:
        parts.append("长期胜率较高 (>70%)")
    elif posterior_p > 0.5:
        parts.append("长期胜率中等")

    return "；".join(parts) if parts else "综合分析后建议观察为主"
