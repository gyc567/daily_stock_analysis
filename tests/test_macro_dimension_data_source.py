# -*- coding: utf-8 -*-
"""P4-fix: DailyMarketContext → 宏观与地缘维度入参端到端测试。

验证：
- daily_market_context payload 含 monetary_policy / liquidity_indicator 时被注入 raw_data
- sector_policy 从 fundamental_analysis + industry_drivers 推断
- 最终 score_macro 输出不再命中"数据缺失"占位
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from src.analyzer import AnalysisResult


def _make_result(
    *,
    fundamental_analysis: str = "受国家政策支持，公司加大研发投入，行业增长。",
    technical_analysis: str = "MA5>MA10>MA20 多头排列",
) -> AnalysisResult:
    return AnalysisResult(
        code="600519",
        name="贵州茅台",
        sentiment_score=70,
        trend_prediction="看多",
        operation_advice="持有",
        analysis_summary="基本面稳健",
        fundamental_analysis=fundamental_analysis,
        technical_analysis=technical_analysis,
        news_summary="无重大利空",
        risk_warning="市场风险偏好下降",
    )


def test_extract_raw_data_injects_daily_market_context_macro_fields() -> None:
    from src.services.research_framework_integration import (
        _extract_raw_data_from_context,
    )

    result = _make_result()
    context: Dict[str, Any] = {
        "daily_market_context": {
            "monetary_policy": "accommodative",
            "liquidity_indicator": "abundant",
            "risk_tags": ["high_risk"],
            "region": "cn",
        }
    }

    raw_data = _extract_raw_data_from_context(result, context)

    assert raw_data["monetary_policy"] == "accommodative"
    assert raw_data["liquidity_indicator"] == "abundant"


def test_extract_raw_data_infers_sector_policy_supportive() -> None:
    from src.services.research_framework_integration import (
        _extract_raw_data_from_context,
    )

    result = _make_result(fundamental_analysis="公司获得国家政策扶持，行业政策利好")
    context: Dict[str, Any] = {}

    raw_data = _extract_raw_data_from_context(result, context)

    assert raw_data.get("sector_policy") == "supportive"


def test_extract_raw_data_infers_sector_policy_restrictive() -> None:
    from src.services.research_framework_integration import (
        _extract_raw_data_from_context,
    )

    result = _make_result(fundamental_analysis="监管收紧，监管限制持续，行业政策不利")
    context: Dict[str, Any] = {}

    raw_data = _extract_raw_data_from_context(result, context)

    assert raw_data.get("sector_policy") == "restrictive"


def test_extract_raw_data_no_macro_keeps_missing() -> None:
    """无 daily_market_context 且 fundamental_analysis 无政策关键词时，
    monetary/liquidity/sector_policy 均不入 raw_data（继续走中性分占位）。
    """
    from src.services.research_framework_integration import (
        _extract_raw_data_from_context,
    )

    result = _make_result(fundamental_analysis="公司业绩稳健增长")
    context: Dict[str, Any] = {}

    raw_data = _extract_raw_data_from_context(result, context)

    assert "monetary_policy" not in raw_data
    assert "liquidity_indicator" not in raw_data
    assert "sector_policy" not in raw_data


def test_full_pipeline_macro_not_missing_summary() -> None:
    """端到端：从 raw_data → ResearchScoringService → framework_score。

    当 raw_data 含宏观键值时，宏观维度的 indicators 不应再走"数据缺失"占位。
    """
    from src.services.research_scoring_service import ResearchScoringService

    raw_data: Dict[str, Any] = {
        # 产业链定位
        "chain_position": "midstream",
        "moat_type": "brand",
        "moat_strength": "strong",
        # 基本面
        "pe_percentile": 30,
        "pb_percentile": 30,
        "roe": 20,
        # 资金面
        "institutional_holding_change": 5,
        # 技术面
        "ma_alignment": "bullish",
        # 情绪
        "analyst_consensus": "outperform",
        # 宏观（P4-fix）
        "monetary_policy": "accommodative",
        "liquidity_indicator": "abundant",
        "sector_policy": "supportive",
    }

    with patch(
        "src.services.research_scoring_service.DatabaseManager"
    ) as mock_db_manager:
        mock_db = MagicMock()
        mock_db_manager.get_instance.return_value._SessionLocal.return_value = mock_db

        service = ResearchScoringService()
        result = service.process(
            stock_code="600519",
            stock_name="贵州茅台",
            market="cn",
            raw_data=raw_data,
        )

    framework = result["framework_score"]
    macro_dim = next(
        d for d in framework["dimensions"] if d["dimension"] == "宏观与地缘"
    )

    # 关键断言：indicators 不能全是"数据缺失"占位
    summaries: List[str] = [
        ind.get("summary", "") for ind in macro_dim.get("indicators", [])
    ]
    assert not any("数据缺失" in s for s in summaries), (
        f"宏观与地缘仍包含'数据缺失'占位: {summaries}"
    )
    # 分数应明显高于中性 50
    assert macro_dim["score"] > 60.0
    # indicators 至少有 3 个真实打分项
    assert len(macro_dim["indicators"]) >= 3


# ============================================================
# P5-fix: 客观 macro 指标从 main_indices/market_stats 推断
# ============================================================


class TestObjectiveMacroIndicatorsIntegration:
    """P5-fix: _extract_raw_data_from_context 接入 main_indices/market_stats"""

    def test_macro_liquidity_injected_from_market_stats(self) -> None:
        """无 daily_market_context 时，从 market_stats 推断 liquidity_indicator"""
        from src.services.research_framework_integration import (
            _extract_raw_data_from_context,
        )
        result = _make_result(fundamental_analysis="公司主营业务稳定")
        context = {
            "market_stats": {"total_amount": 18000.0},  # 1.8万亿 → abundant
            "main_indices": [],  # 空
        }
        raw_data = _extract_raw_data_from_context(result, context)
        assert raw_data.get("liquidity_indicator") == "abundant"

    def test_macro_monetary_injected_from_indices(self) -> None:
        """无 daily_market_context 时，从 main_indices 推断 monetary_policy"""
        from src.services.research_framework_integration import (
            _extract_raw_data_from_context,
        )
        result = _make_result(fundamental_analysis="公司主营业务稳定")
        context = {
            "market_stats": {},  # 空
            "main_indices": [
                {"code": "000300", "change_pct": 3.0},
                {"code": "399006", "change_pct": 4.0},
            ],
        }
        raw_data = _extract_raw_data_from_context(result, context)
        assert raw_data.get("monetary_policy") == "accommodative"

    def test_macro_daily_market_context_takes_priority(self) -> None:
        """P4 daily_market_context 路径优先于 P5 客观推断"""
        from src.services.research_framework_integration import (
            _extract_raw_data_from_context,
        )
        result = _make_result(fundamental_analysis="无政策描述")
        context = {
            "daily_market_context": {
                "monetary_policy": "tight",  # P4 显式值
                "liquidity_indicator": "scarce",
            },
            "main_indices": [
                {"code": "000300", "change_pct": 3.0},  # P5 推断会是 accommodative
            ],
            "market_stats": {"total_amount": 18000.0},  # P5 推断会是 abundant
        }
        raw_data = _extract_raw_data_from_context(result, context)
        # P4 值应保留（setdefault 不覆盖）
        assert raw_data.get("monetary_policy") == "tight"
        assert raw_data.get("liquidity_indicator") == "scarce"

    def test_macro_all_sources_present(self) -> None:
        """完整 5 键 macro 注入（4 个客观 + 1 个 LLM 路径占位）"""
        from src.services.research_framework_integration import (
            _extract_raw_data_from_context,
        )
        result = _make_result(
            fundamental_analysis="公司主营业务稳定增长"
        )
        context = {
            "market_stats": {"total_amount": 18000.0},
            "main_indices": [
                {"code": "000300", "change_pct": 3.0},
                {"code": "399006", "change_pct": 4.0},
            ],
            "fundamental_context": {
                "boards": [
                    {"name": "半导体", "code": "BK001"},
                ],
            },
        }
        raw_data = _extract_raw_data_from_context(result, context)
        assert raw_data.get("monetary_policy") == "accommodative"
        assert raw_data.get("liquidity_indicator") == "abundant"
        assert raw_data.get("sector_policy") == "supportive"  # 半导体 KB

    def test_macro_no_data_no_crash(self) -> None:
        """无任何 macro 数据时仍正常返回（走中性分占位）"""
        from src.services.research_framework_integration import (
            _extract_raw_data_from_context,
        )
        result = _make_result(fundamental_analysis="无政策描述")
        context = {}  # 完全空
        raw_data = _extract_raw_data_from_context(result, context)
        # monetary/liquidity/sector 都应 None（不抛异常）
        assert raw_data.get("monetary_policy") is None
        assert raw_data.get("liquidity_indicator") is None
        assert raw_data.get("sector_policy") is None
