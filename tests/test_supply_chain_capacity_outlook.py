# -*- coding: utf-8 -*-
"""[v3 §10.b] 产能展望与预测的单元测试。

覆盖：
1. Schema 校验：CapacityOutlookV3 / CapacityForecastPeriodV3 / ExpansionProjectV3
2. 渲染器：render_capacity_outlook 输出格式
3. 行业模板扩展：_INDUSTRY_INFERENCE_TEMPLATES 含 capacity_unit_hint
4. 降级路径：数据不足时的 insufficient_data 处理
5. icontract 契约校验
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.schemas.supply_chain import (
    CapacityForecastPeriodV3,
    CapacityOutlookV3,
    DemandSignal,
    ExpansionProjectV3,
)


# ============================================================
# Schema 校验
# ============================================================


class TestCapacityForecastPeriodV3:
    def test_valid_near_term_forecast(self) -> None:
        f = CapacityForecastPeriodV3(
            time_window="near_term_3_6m",
            period_label="2026-10",
            predicted_utilization_pct=Decimal("88.5"),
            predicted_output_volume=Decimal("5.2"),
            predicted_output_unit="万千升",
            inference_basis="下游订单饱满+中秋旺季",
            demand_signals=["下游订单饱满", "季节性旺季"],
            capacity_change_factors=["新建产能释放"],
            confidence="high",
            evidence_strength="analysis",
        )
        assert f.time_window == "near_term_3_6m"
        assert f.predicted_utilization_pct == Decimal("88.5")

    def test_valid_mid_term_forecast(self) -> None:
        f = CapacityForecastPeriodV3(
            time_window="mid_term_6_12m",
            period_label="2026Q4",
            predicted_utilization_pct=None,
            inference_basis="扩产产能逐步释放",
            demand_signals=["行业出货量增长"],
            capacity_change_factors=["爬坡良率提升"],
            confidence="medium",
        )
        assert f.time_window == "mid_term_6_12m"
        assert f.predicted_utilization_pct is None

    def test_volume_unit_contract_violation(self) -> None:
        """volume 非空但 unit 为空 → 契约违反。"""
        with pytest.raises(ValueError, match="predicted_output_volume 非空时 必须提供 predicted_output_unit"):
            CapacityForecastPeriodV3(
                time_window="near_term_3_6m",
                period_label="2026-10",
                predicted_utilization_pct=Decimal("90.0"),
                predicted_output_volume=Decimal("5.0"),
                predicted_output_unit=None,  # 违反契约
                inference_basis="测试",
            )

    def test_decimal_range_validation(self) -> None:
        """利用率 > 100% 应被接受（超产情况）。"""
        f = CapacityForecastPeriodV3(
            time_window="near_term_3_6m",
            period_label="2026-10",
            predicted_utilization_pct=Decimal("120.0"),  # 超产
            inference_basis="旺季满产",
        )
        assert f.predicted_utilization_pct == Decimal("120.0")


class TestExpansionProjectV3:
    def test_valid_project(self) -> None:
        p = ExpansionProjectV3(
            project_name="茅台酱香产能扩建",
            expected_completion="2026Q3",
            expected_capacity_addition="1.5万千升/年",
            progress_status="ramping",
            source="年报披露",
            evidence_strength="primary",
        )
        assert p.project_name == "茅台酱香产能扩建"
        assert p.progress_status == "ramping"

    def test_planning_status(self) -> None:
        p = ExpansionProjectV3(
            project_name="新项目",
            progress_status="planning",
            evidence_strength="analysis",
        )
        assert p.progress_status == "planning"


class TestCapacityOutlookV3:
    def test_full_outlook(self) -> None:
        outlook = CapacityOutlookV3(
            ticker="600519",
            company="贵州茅台",
            fetched_at=None,
            industry_unit_hint="万千升/年",
            historical_summary="近3期均值为 85.3%",
            historical_data_quality="partial",
            forecasts=[
                CapacityForecastPeriodV3(
                    time_window="near_term_3_6m",
                    period_label="2026-10",
                    predicted_utilization_pct=Decimal("88.5"),
                    inference_basis="下游订单饱满",
                    demand_signals=["下游订单饱满"],
                    confidence="high",
                )
            ],
            trend="rising",
            trend_rationale="需求旺盛+产能逐步释放",
            capacity_bottleneck_risk="medium",
            demand_supply_balance="tight",
            expansion_plans=[
                ExpansionProjectV3(
                    project_name="茅台酱香产能扩建",
                    expected_completion="2026Q3",
                    expected_capacity_addition="1.5万千升/年",
                    progress_status="ramping",
                )
            ],
            data_source_notes="年报披露+行业数据",
            confidence="high",
        )
        assert outlook.ticker == "600519"
        assert outlook.trend == "rising"
        assert len(outlook.forecasts) == 1
        assert len(outlook.expansion_plans) == 1

    def test_insufficient_data_outlook(self) -> None:
        """无 forecasts 和 historical_summary 时 trend 默认为 insufficient_data。"""
        outlook = CapacityOutlookV3(
            ticker="600519",
            company="贵州茅台",
            trend="insufficient_data",
        )
        assert outlook.trend == "insufficient_data"
        assert outlook.forecasts == []
        assert outlook.historical_summary == ""

    def test_industry_unit_hint_optional(self) -> None:
        """industry_unit_hint 可选。"""
        outlook = CapacityOutlookV3(
            ticker="600519",
            company="贵州茅台",
        )
        assert outlook.industry_unit_hint is None


# ============================================================
# DemandSignal / CapacityChangeFactor Literal
# ============================================================


class TestDemandSignals:
    def test_valid_signals(self) -> None:
        f = CapacityForecastPeriodV3(
            time_window="near_term_3_6m",
            period_label="2026-10",
            inference_basis="测试",
            demand_signals=["下游订单饱满", "季节性旺季"],
        )
        assert "下游订单饱满" in f.demand_signals
        assert "季节性旺季" in f.demand_signals


# ============================================================
# 渲染器测试
# ============================================================


class TestRenderCapacityOutlook:
    def test_render_empty_outlook(self) -> None:
        from src.services.supply_chain.deep_dive_renderer import render_capacity_outlook

        result = render_capacity_outlook(None)
        assert result == ""

    def test_render_full_outlook(self) -> None:
        from src.services.supply_chain.deep_dive_renderer import render_capacity_outlook

        outlook = CapacityOutlookV3(
            ticker="600519",
            company="贵州茅台",
            industry_unit_hint="万千升/年",
            historical_summary="近3期均值为 85.3%",
            historical_data_quality="partial",
            forecasts=[
                CapacityForecastPeriodV3(
                    time_window="near_term_3_6m",
                    period_label="2026-10",
                    predicted_utilization_pct=Decimal("88.5"),
                    predicted_output_volume=Decimal("5.2"),
                    predicted_output_unit="万千升",
                    inference_basis="下游订单饱满+中秋旺季",
                    demand_signals=["下游订单饱满", "季节性旺季"],
                    capacity_change_factors=["新建产能释放"],
                    confidence="high",
                ),
                CapacityForecastPeriodV3(
                    time_window="mid_term_6_12m",
                    period_label="2026Q4",
                    predicted_utilization_pct=Decimal("90.0"),
                    inference_basis="扩产产能释放",
                    capacity_change_factors=["爬坡良率提升"],
                    confidence="medium",
                ),
            ],
            trend="rising",
            trend_rationale="需求旺盛+产能逐步释放",
            capacity_bottleneck_risk="medium",
            demand_supply_balance="tight",
            expansion_plans=[
                ExpansionProjectV3(
                    project_name="茅台酱香产能扩建",
                    expected_completion="2026Q3",
                    expected_capacity_addition="1.5万千升/年",
                    progress_status="ramping",
                )
            ],
            data_source_notes="年报披露+行业数据",
            confidence="high",
        )
        result = render_capacity_outlook(outlook)

        # 验证关键内容
        assert "## 10.b 产能展望与预测" in result
        assert "10.b.1 历史产能跟踪" in result
        assert "10.b.2 短期预测（未来3个月）" in result
        assert "10.b.3 中期展望（6-12个月）" in result
        assert "10.b.4 供需格局与风险提示" in result
        assert "数据质量" in result
        assert "供需格局" in result
        assert "产能瓶颈风险" in result
        assert "扩产计划跟踪" in result
        assert "近3期均值为 85.3%" in result

    def test_render_insufficient_data(self) -> None:
        from src.services.supply_chain.deep_dive_renderer import render_capacity_outlook

        outlook = CapacityOutlookV3(
            ticker="600519",
            company="贵州茅台",
            trend="insufficient_data",
            trend_rationale="数据不足，无法进行产能展望预测",
            data_source_notes="产能数据不可用",
            confidence="low",
        )
        result = render_capacity_outlook(outlook)
        assert "## 10.b 产能展望与预测" in result
        assert "数据质量" in result


# ============================================================
# 行业模板测试
# ============================================================


class TestIndustryCapacityTemplates:
    def test_semiconductor_template_has_capacity_fields(self) -> None:
        from src.services.supply_chain_data_service import _INDUSTRY_INFERENCE_TEMPLATES

        # 半导体模板
        semi_template = None
        for keywords, template in _INDUSTRY_INFERENCE_TEMPLATES:
            if "半导体" in keywords or "芯片" in keywords:
                semi_template = template
                break

        assert semi_template is not None
        assert "capacity_unit_hint" in semi_template
        assert "benchmark_utilization" in semi_template
        assert "seasonal_pattern" in semi_template
        assert semi_template["capacity_unit_hint"] == "万片/月"

    def test_baijiu_template_has_capacity_fields(self) -> None:
        from src.services.supply_chain_data_service import _INDUSTRY_INFERENCE_TEMPLATES

        # 白酒模板
        baijiu_template = None
        for keywords, template in _INDUSTRY_INFERENCE_TEMPLATES:
            if "白酒" in keywords or "茅台" in keywords:
                baijiu_template = template
                break

        assert baijiu_template is not None
        assert baijiu_template["capacity_unit_hint"] == "万千升/年"
        assert baijiu_template["benchmark_utilization"] == 75.0

    def test_battery_template_has_capacity_fields(self) -> None:
        from src.services.supply_chain_data_service import _INDUSTRY_INFERENCE_TEMPLATES

        # 电池模板
        battery_template = None
        for keywords, template in _INDUSTRY_INFERENCE_TEMPLATES:
            if "新能源" in keywords or "锂电池" in keywords:
                battery_template = template
                break

        assert battery_template is not None
        assert battery_template["capacity_unit_hint"] == "GWh/年"
        assert battery_template["benchmark_utilization"] == 80.0
