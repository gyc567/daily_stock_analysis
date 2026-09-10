# -*- coding: utf-8 -*-
"""方案 C 回归：Serenity 缓存命中时必须保留产业链实数据（审计 P0-3）。

缓存命中分支只允许叠加 report 相关字段，不允许用空数据替换
_build_supply_chain_base 的结果；缓存未命中时不得再写 pending 僵尸占位。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict

from src.services import research_framework_integration as rf

_BASE: Dict[str, Any] = {
    "data_sources": ["knowledge_base"],
    "company_position": "白酒龙头",
    "upstream": [{"name": "高粱种植"}],
    "downstream": [{"name": "经销商"}],
    "chokepoints": ["基酒产能"],
    "us_china_chain": {"segment": "消费"},
    "industry_drivers": ["消费升级"],
    "chain_map": ["原料-酿造-销售"],
    "serenity_score": None,
    "serenity_verdict": None,
}

_CACHED = {
    "id": "sc_202606271530_1",
    "md_path": "/tmp/sc_202606271530_1.md",
    "created_at": "2026-09-09T00:00:00",
}


def _result() -> SimpleNamespace:
    return SimpleNamespace(code="600519", name="贵州茅台", fundamental_analysis="")


def test_cache_hit_preserves_base_fields(monkeypatch):
    monkeypatch.setattr(rf, "_get_cached_serenity_report", lambda code: dict(_CACHED))
    monkeypatch.setattr(
        rf, "_build_supply_chain_base", lambda result, context, raw_data: dict(_BASE)
    )

    data = rf._build_supply_chain_from_analysis(_result(), {}, {})

    # 产业链实数据不得被空数据替换
    assert data["upstream"] == _BASE["upstream"]
    assert data["downstream"] == _BASE["downstream"]
    assert data["chokepoints"] == _BASE["chokepoints"]
    assert data["company_position"] == "白酒龙头"
    assert data["industry_drivers"] == _BASE["industry_drivers"]
    assert data["chain_map"] == _BASE["chain_map"]
    # 叠加 report 字段
    assert data["report_status"] == "ready"
    assert data["report_url"] == _CACHED["md_path"]
    assert data["report_id"] == _CACHED["id"]
    assert data["report_generated_at"] == _CACHED["created_at"]
    # data_sources 追加 serenity 而非虚标
    assert data["data_sources"] == ["knowledge_base", "serenity"]


def test_cache_hit_appends_serenity_once(monkeypatch):
    base = dict(_BASE, data_sources=["knowledge_base", "serenity"])
    monkeypatch.setattr(rf, "_get_cached_serenity_report", lambda code: dict(_CACHED))
    monkeypatch.setattr(
        rf, "_build_supply_chain_base", lambda result, context, raw_data: dict(base)
    )

    data = rf._build_supply_chain_from_analysis(_result(), {}, {})
    assert data["data_sources"].count("serenity") == 1


def test_cache_miss_writes_no_pending_placeholder(monkeypatch):
    """P1：pending 占位无任何消费方，未命中路径不得再写。"""
    monkeypatch.setattr(rf, "_get_cached_serenity_report", lambda code: None)
    monkeypatch.setattr(
        rf, "_build_supply_chain_base", lambda result, context, raw_data: dict(_BASE)
    )

    data = rf._build_supply_chain_from_analysis(_result(), {}, {})
    assert "report_status" not in data
    assert "report_url" not in data
    assert data["upstream"] == _BASE["upstream"]
