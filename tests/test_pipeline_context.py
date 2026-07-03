# -*- coding: utf-8 -*-
"""``src.core.pipeline_context`` TypedDict 契约测试。

TypedDict 是声明性的，这里只验证：
- 字段存在性 / total=False 行为
- 继承组合（``PipelineContextDict`` 继承 ``_ServiceFields``）
- ``NotRequired`` 字段可选性
"""

from __future__ import annotations

import pytest

from src.core.pipeline_context import (
    DailyMarketContextDict,
    PipelineContextDict,
)


def test_pipeline_context_required_keys() -> None:
    ctx: PipelineContextDict = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "report_type": "full",
        "report_language": "zh",
        "fundamental_context": {"pe": 30.5},
    }
    assert ctx["stock_code"] == "600519"
    assert ctx["fundamental_context"]["pe"] == 30.5


def test_pipeline_context_optional_keys() -> None:
    ctx: PipelineContextDict = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "report_type": "full",
        "report_language": "zh",
        "fundamental_context": {},
    }
    ctx["portfolio_context"] = {"cash": 100000.0}
    assert ctx["portfolio_context"]["cash"] == 100000.0


def test_pipeline_context_service_field_inherited() -> None:
    """``search_service`` 来自父类 ``_ServiceFields``，应为 NotRequired。"""
    ctx: PipelineContextDict = {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "report_type": "full",
        "report_language": "zh",
        "fundamental_context": {},
        "search_service": object(),
    }
    assert ctx["search_service"] is not None


def test_pipeline_context_missing_required() -> None:
    """total=False 意味着所有键都是可选的，构造时不应强制要求必填键。

    这一行为是设计选择：运行期上下文是逐步填充的，TypedDict 仅为下游
    提供类型提示，不强制完整性检查。
    """
    ctx: PipelineContextDict = {}
    assert "stock_code" not in ctx


def test_daily_market_context_dict_all_optional() -> None:
    ctx: DailyMarketContextDict = {}
    assert ctx == {}


def test_daily_market_context_dict_partial() -> None:
    ctx: DailyMarketContextDict = {"market_phase": "bullish"}
    assert ctx["market_phase"] == "bullish"


@pytest.mark.parametrize(
    "field", ["portfolio_context", "market_phase_context", "skills"]
)
def test_pipeline_context_supports_runtime_injection(field: str) -> None:
    ctx: PipelineContextDict = {
        "stock_code": "x",
        "stock_name": "y",
        "report_type": "t",
        "report_language": "zh",
        "fundamental_context": {},
    }
    ctx[field] = "injected"  # type: ignore[literal-required]
    assert field in ctx
