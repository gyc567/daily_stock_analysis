# -*- coding: utf-8 -*-
"""郑希投研数据层与工具层单元测试。

不依赖 LLM 与网络，只验证纯计算与本地数据读取。
数据来源：data/fund_manager_views/zhengxi/（随仓库一起）。
"""

from __future__ import annotations

import pytest

from src.services.zhengxi import corpus, fund_data, scoring, synonyms
from src.agent.tools.zhengxi_tools import (
    _handle_get_zhengxi_fund_data,
    _handle_score_fund_zhengxi,
    _handle_search_zhengxi_views,
)


# ============================================================
# 同义词扩展
# ============================================================

class TestSynonyms:
    def test_expand_canonical_returns_group(self):
        group = synonyms.expand_keyword("光通信")
        assert "光通信" in group and "光模块" in group

    def test_expand_member_back_to_group(self):
        # “光模块”是“光通信”组成员，应映射回整组
        group = synonyms.expand_keyword("光模块")
        assert "光通信" in group

    def test_expand_unknown_returns_self(self):
        assert synonyms.expand_keyword("查无此词XYZ") == ["查无此词XYZ"]


# ============================================================
# 机械指标
# ============================================================

class TestScoring:
    def test_turnover_proxy_partial_overlap(self):
        quarters = [
            {"year": 2025, "quarter": 4, "holdings": [{"股票代码": "A"}, {"股票代码": "B"}]},
            {"year": 2026, "quarter": 1, "holdings": [{"股票代码": "A"}, {"股票代码": "C"}]},
        ]
        tp = scoring.turnover_proxy(quarters)
        # 一半重叠 → 换手代理 50.0
        assert tp == 50.0

    def test_turnover_proxy_empty(self):
        assert scoring.turnover_proxy([]) is None

    def test_concentration_sums_pct(self):
        holdings = [{"占净值比": "10%"}, {"占净值比": "5.5%"}]
        assert scoring.concentration(holdings) == 15.5

    def test_concentration_empty(self):
        assert scoring.concentration([]) is None

    def test_max_drawdown(self):
        nav = [(0, 100.0), (1, 120.0), (2, 90.0)]
        # 峰值 120 → 谷值 90 ⇒ 回撤 25%
        assert scoring.max_drawdown(nav) == 25.0

    def test_max_drawdown_empty(self):
        assert scoring.max_drawdown([]) is None

    def test_year_return_empty(self):
        assert scoring.year_return([]) is None


# ============================================================
# 语料检索
# ============================================================

class TestCorpus:
    def test_search_hit_with_source(self):
        hits = corpus.search_corpus(["光通信"], max_results=3)
        assert len(hits) >= 1
        first = hits[0]
        assert {"date", "type", "title", "snippet", "matched"} <= set(first)

    def test_search_synonym_expansion(self):
        # “光模块”在原文未必逐字出现，但同属光通信组，扩展后应命中
        hits = corpus.search_corpus(["光模块"], max_results=3)
        assert len(hits) >= 1

    def test_search_empty_keywords(self):
        assert corpus.search_corpus([]) == []

    def test_search_match_any_vs_all(self):
        any_hits = corpus.search_corpus(["光通信", "ROE"], match_all=False, max_results=50)
        all_hits = corpus.search_corpus(["光通信", "ROE"], match_all=True, max_results=50)
        # OR 命中应不少于 AND
        assert len(any_hits) >= len(all_hits)


# ============================================================
# 基金数据
# ============================================================

class TestFundData:
    def test_resolve_by_code(self):
        fund = fund_data.resolve_fund("001513")
        assert fund and fund["code"] == "001513"

    def test_resolve_by_name_keyword(self):
        fund = fund_data.resolve_fund("信息产业")
        assert fund and fund["code"] == "001513"

    def test_resolve_unknown(self):
        assert fund_data.resolve_fund("查无此基XYZ") is None

    def test_latest_holdings_has_metrics(self):
        latest = fund_data.latest_holdings("001513")
        assert latest is not None
        assert {"top10", "concentration_top10_pct", "turnover_proxy_pct"} <= set(latest)

    def test_performance_summary_has_returns(self):
        summary = fund_data.load_performance_summary("001513")
        assert summary["fund_code"] == "001513"
        assert "max_drawdown_pct" in summary
        assert "data_cutoff_note" in summary  # 静态快照声明


# ============================================================
# Agent 工具 handler
# ============================================================

class TestZhengxiTools:
    def test_search_tool_returns_usage_note(self):
        result = _handle_search_zhengxi_views(["光通信"], max_results=2)
        assert result["total_hits"] >= 1
        assert "usage_note" in result  # 引导 LLM 标注出处

    def test_fund_data_tool_holdings(self):
        result = _handle_get_zhengxi_fund_data("001513", sections=["holdings"])
        assert result["fund_code"] == "001513"
        assert "latest_holdings" in result

    def test_fund_data_tool_unknown_returns_supported(self):
        result = _handle_get_zhengxi_fund_data("查无此基XYZ")
        assert "error" in result
        assert len(result["supported_funds"]) == 8

    def test_score_tool_six_dimensions(self):
        result = _handle_score_fund_zhengxi("001513")
        assert result["fund_code"] == "001513"
        assert len(result["six_dimensions"]) == 6
        assert sum(d["max"] for d in result["six_dimensions"]) == 100
        assert "scoring_purpose" in result  # 契合度非优劣声明
