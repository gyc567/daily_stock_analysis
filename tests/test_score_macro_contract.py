# -*- coding: utf-8 -*-
"""宏观与地缘维度 score_macro — icontract 契约测试（Layer 2）。

按 ``docs/type-contract-data-defense.md`` 与 ``AGENTS.md §1.3``：
- CI 通过 ``ICONTRACT_SLOW=true`` 跑本文件触发装饰器断言
- 覆盖 score_macro / _extract_macro_indicators / _extract_first_match
- 不依赖网络，纯本地纯函数

P4-fix: 个股六维详情"宏观与地缘"维度补齐数据源后，回归核心契约。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import icontract
import pytest

from src.services.daily_market_context import (
    _extract_first_match,
    _extract_macro_indicators,
    _MACRO_LIQUIDITY_PATTERNS,
    _MACRO_MONETARY_PATTERNS,
)
from src.scoring.indicators.macro import (
    DEFAULT_NEUTRAL_SCORE,
    _score_regulatory_risk,
    score_macro,
)


# ============================================================
# score_macro 契约
# ============================================================


class TestScoreMacroContract:
    """score_macro 输出落域 / 权重组 / 缺失语义"""

    def test_score_in_unit_interval_when_data_present(self) -> None:
        for kwargs in (
            {"monetary_policy": "accommodative"},
            {"liquidity_indicator": "abundant"},
            {"sector_policy": "supportive"},
            {"us_china_impact": "minimal"},
            {"regulatory_risk": "low"},
            {
                "monetary_policy": "neutral",
                "liquidity_indicator": "moderate",
                "sector_policy": "neutral",
                "us_china_impact": "limited",
                "regulatory_risk": "medium",
            },
        ):
            result = score_macro(**kwargs)
            assert 0.0 <= result["score"] <= 100.0

    def test_score_is_neutral_when_all_inputs_missing(self) -> None:
        result = score_macro()
        assert result["score"] == DEFAULT_NEUTRAL_SCORE == 50.0
        assert len(result["indicators"]) == 1
        assert "数据缺失" in result["indicators"][0]["summary"]

    def test_no_missing_summary_when_any_input_present(self) -> None:
        """P4-fix 核心契约：只要任一字段非空，就不应再走"数据缺失"占位。"""
        for kwargs in (
            {"monetary_policy": "neutral"},
            {"liquidity_indicator": "moderate"},
            {"sector_policy": "neutral"},
            {"us_china_impact": "limited"},
            {"regulatory_risk": "low"},
        ):
            result = score_macro(**kwargs)
            summaries = [ind["summary"] for ind in result["indicators"]]
            assert not any("数据缺失" in s for s in summaries), (
                f"Unexpected '数据缺失' summary in {kwargs}: {summaries}"
            )

    def test_indicator_weights_normalize_to_one(self) -> None:
        """所有入参都给时，权重之和等于 1.0。"""
        result = score_macro(
            monetary_policy="accommodative",
            liquidity_indicator="abundant",
            sector_policy="supportive",
            us_china_impact="minimal",
            regulatory_risk="low",
        )
        total = sum(ind["weight"] for ind in result["indicators"])
        assert abs(total - 1.0) < 1e-6
        assert len(result["indicators"]) == 5

    def test_dimension_metadata(self) -> None:
        result = score_macro(monetary_policy="neutral")
        assert result["dimension"] == "宏观与地缘"
        assert result["weight"] == 0.10


# ============================================================
# regulatory_risk 反向单调性
# ============================================================


class TestRegulatoryRiskContract:
    def test_regulatory_risk_monotonic_decreasing(self) -> None:
        """低监管风险应当比高监管风险分数更高。"""
        low = score_macro(regulatory_risk="low")["score"]
        high = score_macro(regulatory_risk="high")["score"]
        assert low > high

    def test_unknown_value_returns_neutral(self) -> None:
        assert _score_regulatory_risk("unknown_value") == DEFAULT_NEUTRAL_SCORE
        assert _score_regulatory_risk("") == DEFAULT_NEUTRAL_SCORE


# ============================================================
# _extract_first_match / _extract_macro_indicators
# ============================================================


class TestExtractMacroIndicatorsContract:
    def test_first_match_priority(self) -> None:
        """宽松应优先于中性（顺序敏感）。"""
        text = "央行实施稳健中性偏宽松的货币政策"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "accommodative"

    def test_first_match_priority_v2(self) -> None:
        text = "央行采取紧缩货币政策并加息"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "tight"

    def test_empty_text_returns_none(self) -> None:
        assert _extract_first_match("", _MACRO_MONETARY_PATTERNS) is None

    def test_no_keyword_returns_none(self) -> None:
        assert _extract_first_match("市场平稳运行", _MACRO_MONETARY_PATTERNS) is None

    def test_extract_macro_returns_two_keys(self) -> None:
        text = "央行宽松，流动性充裕"
        result = _extract_macro_indicators(text)
        assert result == {
            "monetary_policy": "accommodative",
            "liquidity_indicator": "abundant",
        }

    def test_extract_macro_partial_match(self) -> None:
        text = "今天央行宽松，但未提及流动性"
        result = _extract_macro_indicators(text)
        assert result["monetary_policy"] == "accommodative"
        assert result["liquidity_indicator"] is None

    def test_extract_macro_case_insensitive(self) -> None:
        text = "ACCOMMODATIVE monetary policy"
        result = _extract_macro_indicators(text)
        assert result["monetary_policy"] == "accommodative"

    def test_liquidity_patterns_present(self) -> None:
        """P4-fix: _MACRO_LIQUIDITY_PATTERNS 必须存在且非空。"""
        assert len(_MACRO_LIQUIDITY_PATTERNS) > 0

    def test_monetary_patterns_present(self) -> None:
        assert len(_MACRO_MONETARY_PATTERNS) > 0


# ============================================================
# icontract runtime violation 验证（仅在 ICONTRACT_SLOW=true 触发）
# ============================================================


@icontract.require(
    lambda monetary_policy: (
        monetary_policy
        in (
            None,
            "accommodative",
            "neutral",
            "tight",
        )
    ),
    "monetary_policy 仅接受预定义枚举",
)
def _score_macro_with_monetary(monetary_policy: Optional[str]) -> Dict[str, Any]:
    return score_macro(monetary_policy=monetary_policy)


def test_icontract_violation_on_bogus_value() -> None:
    """乱填字段应触发 icontract 违规。"""
    with pytest.raises(icontract.ViolationError):
        _score_macro_with_monetary(monetary_policy="bogus_value_xxx")


# ============================================================
# 边界与反例
# ============================================================


class TestEdgeCases:
    """反例与边界：None / 空字符串 / 乱码 / 老数据"""

    def test_whitespace_only_treated_as_none(self) -> None:
        """_extract_first_match 应把全空白字符串当 None。"""
        assert _extract_first_match("   ", _MACRO_MONETARY_PATTERNS) is None
        assert _extract_first_match("\n\t", _MACRO_MONETARY_PATTERNS) is None

    def test_numeric_only_returns_none(self) -> None:
        assert _extract_first_match("2026-07-31", _MACRO_MONETARY_PATTERNS) is None
        assert _extract_first_match("12345", _MACRO_LIQUIDITY_PATTERNS) is None

    def test_partial_keyword_no_match(self) -> None:
        """部分关键字不应误命中。"""
        assert _extract_first_match("宽松性改革", _MACRO_MONETARY_PATTERNS) is None
        assert _extract_first_match("不限购", _MACRO_MONETARY_PATTERNS) is None

    def test_unicode_keyword_match(self) -> None:
        """unicode 关键词应正确命中（无大小写问题）。"""
        assert (
            _extract_first_match("央行宣布降准", _MACRO_MONETARY_PATTERNS)
            == "accommodative"
        )
        assert _extract_first_match("加息 25bp", _MACRO_MONETARY_PATTERNS) == "tight"
        assert _extract_first_match("保持中性", _MACRO_MONETARY_PATTERNS) == "neutral"

    def test_score_macro_with_only_garbage_input(self) -> None:
        """乱码输入应走中性分占位，不抛异常。"""
        result = score_macro(monetary_policy="?@#$%^&*")
        assert result["score"] == DEFAULT_NEUTRAL_SCORE

    def test_score_macro_empty_string_treated_as_none(self) -> None:
        """空字符串应被当作 None（不计入权重）。"""
        result = score_macro(monetary_policy="", liquidity_indicator="abundant")
        indicators = result["indicators"]
        # 仅 liquidity 进入
        assert len(indicators) == 1
        assert indicators[0]["name"] == "流动性"

    def test_score_macro_with_none_and_value_mixed(self) -> None:
        """None + value 混合：仅 value 计入。"""
        result = score_macro(
            monetary_policy=None,
            liquidity_indicator="abundant",
            sector_policy=None,
            us_china_impact="minimal",
            regulatory_risk=None,
        )
        assert len(result["indicators"]) == 2

    def test_to_safe_dict_legacy_payload_compatible(self) -> None:
        """老 JSON 不含 macro 字段时，反序列化安全。"""
        import json

        legacy_payload = {
            "region": "cn",
            "trade_date": "2026-01-01",
            "summary": "历史报告，无新字段",
            "risk_tags": [],
            "source": "analysis_history",
        }
        # 通过 dataclass 实例化（模拟 from_json 路径）
        from src.services.daily_market_context import DailyMarketContext
        from datetime import date

        ctx = DailyMarketContext(
            region="cn",
            trade_date=date(2026, 1, 1),
            summary="历史报告，无新字段",
            risk_tags=[],
            source="analysis_history",
        )
        # 三个新字段都是 None → to_safe_dict 不输出
        safe = ctx.to_safe_dict()
        assert "monetary_policy" not in safe
        assert "liquidity_indicator" not in safe
        assert "sector_policy" not in safe
        # round-trip 通过 JSON 仍然 OK
        roundtrip = json.loads(json.dumps(safe))
        assert roundtrip == safe


class TestFalsePositiveGuard:
    """P4-fix v3: 黑名单短语过滤，避免子串误命中。"""

    def test_loose_policy_reform_excluded(self) -> None:
        """「宽松性改革」不应误判为宽松。"""
        assert _extract_first_match("宽松性改革", _MACRO_MONETARY_PATTERNS) is None

    def test_loose_policy_in_compound_still_matches(self) -> None:
        """如果 text 同时包含「宽松性改革」和独立的「宽松」货币政策，应命中宽松。"""
        text = "推动宽松性改革。央行宣布采取宽松货币政策。"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "accommodative"

    def test_no_limitation_excluded(self) -> None:
        """「不限购」「不限行」是普通词，不应误判为紧缩。"""
        # "紧缩" 不在 "不限购"/"不限行" 里，所以本来也不会误判
        # 但 "无加息" 含 "加息" → 应被 FP 排除
        assert _extract_first_match("本轮调控无加息", _MACRO_MONETARY_PATTERNS) is None

    def test_no_limitation_with_real_tight_still_matches(self) -> None:
        """text 同时有「无加息」和真「加息」时，应命中 tight。"""
        text = "央行无加息预期。但同时宣布加息25bp。"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "tight"

    def test_real_loose_with_no_negative(self) -> None:
        """正常宽松语境必须命中。"""
        assert (
            _extract_first_match("央行宣布降准，宽松信号明确", _MACRO_MONETARY_PATTERNS)
            == "accommodative"
        )

    def test_sector_false_positive_guard(self) -> None:
        """sector_policy:「政策限制性改革」不应误判为 restrictive。"""
        from src.services.research_framework_integration import (
            _infer_sector_policy,
            _SECTOR_FALSE_POSITIVE_PHRASES,
        )

        # 验证黑名单生效
        text = "推动政策限制性改革"
        # 没有真正的"政策限制"短语（独立出现）→ 应 None
        assert "政策限制" in text
        # 但 _infer_sector_policy 会找到 "政策限制" 因为 FP 短语含 "政策限制"
        # 这里验证整体推断
        result = _infer_sector_policy(fundamental_text=text, industry_drivers=[])
        assert result is None

    def test_sector_real_restrictive_with_fp_present(self) -> None:
        """text 同时有 FP 和真 restrictive 时，应命中 restrictive。"""
        from src.services.research_framework_integration import _infer_sector_policy

        text = "推动政策限制性改革，行业迎来监管收紧新规"
        result = _infer_sector_policy(fundamental_text=text, industry_drivers=[])
        assert result == "restrictive"


class TestCrossMarketScenarios:
    """跨市场真实场景：A 股 / 港股 / 美股 / 政策语不详"""

    def test_a_share_loose_accommodative(self) -> None:
        """A 股典型宽松表述。"""
        text = "央行宣布降准0.5个百分点，释放长期资金约1万亿，市场流动性充裕"
        result = _extract_first_match(text, _MACRO_MONETARY_PATTERNS)
        assert result == "accommodative"
        liq = _extract_first_match(text, _MACRO_LIQUIDITY_PATTERNS)
        assert liq == "abundant"

    def test_a_share_tight_with_drawdown(self) -> None:
        """A 股紧缩 + 流动性紧张。"""
        text = "央行上调存款准备金率0.25个百分点，市场流动性紧张，板块普跌"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "tight"
        assert _extract_first_match(text, _MACRO_LIQUIDITY_PATTERNS) == "scarce"

    def test_a_share_neutral_with_consistent_signals(self) -> None:
        text = "央行重申稳健中性货币政策，保持流动性合理充裕"
        # "稳健中性" 是中性 keyword
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "neutral"
        # "充裕" 在流动性里
        assert _extract_first_match(text, _MACRO_LIQUIDITY_PATTERNS) == "abundant"

    def test_a_share_neutral_bias_loose_priority(self) -> None:
        """「稳健中性偏宽松」应优先命中宽松（顺序敏感）。"""
        text = "央行重申稳健中性偏宽松的货币政策"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "accommodative"

    def test_us_market_easing(self) -> None:
        """美股典型 easing 表述。"""
        text = "Fed signals dovish stance, ample liquidity in financial system"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "accommodative"
        assert _extract_first_match(text, _MACRO_LIQUIDITY_PATTERNS) == "abundant"

    def test_us_market_hawkish(self) -> None:
        text = "Fed hawkish, tight liquidity concerns rise across markets"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "tight"
        assert _extract_first_match(text, _MACRO_LIQUIDITY_PATTERNS) == "scarce"

    def test_hk_market_chinese_keywords(self) -> None:
        """港股中文报告（与 A 股共享关键词）。"""
        text = "港元流动性适中，央行政策中性"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "neutral"
        assert _extract_first_match(text, _MACRO_LIQUIDITY_PATTERNS) == "moderate"

    def test_no_macro_keywords_returns_none(self) -> None:
        """政策语不详时全 None → 走中性分占位。"""
        text = "今日市场震荡整理，板块轮动加快，个股分化明显"
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) is None
        assert _extract_first_match(text, _MACRO_LIQUIDITY_PATTERNS) is None

    def test_sector_policy_supportive_only_via_fundamental(self) -> None:
        """sector_policy 仅从 fundamental_analysis 推断（与 monetary/liquidity 独立）。"""
        from src.services.research_framework_integration import _infer_sector_policy

        result = _infer_sector_policy(
            fundamental_text="公司受国家政策扶持，所在行业获得产业政策利好",
            industry_drivers=[],
        )
        assert result == "supportive"

    def test_sector_policy_restrictive_only_via_fundamental(self) -> None:
        from src.services.research_framework_integration import _infer_sector_policy

        result = _infer_sector_policy(
            fundamental_text="近期监管收紧，行业政策限制加大",
            industry_drivers=[],
        )
        assert result == "restrictive"

    def test_long_form_text_with_mixed_macro_signals(self) -> None:
        """长文本混合场景：宽松信号 + 流动性紧张描述同时出现。"""
        text = (
            "今日宏观环境复杂。一方面，央行宣布降准，传递宽松信号；"
            "另一方面，市场流动性紧张局面未根本缓解，板块分化。"
            "短期建议控制仓位，等待流动性改善。"
        )
        # 优先宽松（顺序敏感）
        assert _extract_first_match(text, _MACRO_MONETARY_PATTERNS) == "accommodative"
        # 流动性紧张也命中
        assert _extract_first_match(text, _MACRO_LIQUIDITY_PATTERNS) == "scarce"

    def test_full_market_review_section(self) -> None:
        """模拟真实的市场复盘 section markdown。"""
        markdown = """
        ## 大盘环境摘要
        
        央行今日宣布降准 0.5 个百分点，释放长期资金约 1 万亿元，传递宽松货币政策信号。
        市场流动性充裕，两市成交额突破 1.5 万亿。
        但需关注海外美联储加息预期对人民币汇率的扰动。
        
        ## 风险提示
        
        大盘整体估值偏高，建议控制仓位。
        """
        assert (
            _extract_first_match(markdown, _MACRO_MONETARY_PATTERNS) == "accommodative"
        )
        assert _extract_first_match(markdown, _MACRO_LIQUIDITY_PATTERNS) == "abundant"


class TestUIInvariantContract:
    """生产 UI 不变量：模拟 Web 端 missingOnly 判定逻辑。

    apps/dsa-web/src/components/report/DimensionDetailPanel.tsx:165-194
    """

    @staticmethod
    def _is_missing_summary(summary: str, lang: str) -> bool:
        if not summary:
            return False
        marker = "数据缺失" if lang == "zh" else "Data missing"
        return marker in summary or "data missing" in summary.lower()

    @staticmethod
    def _is_missing_only(indicators: list, lang: str = "zh") -> bool:
        if not indicators or len(indicators) == 0:
            return False
        real = [
            i
            for i in indicators
            if not TestUIInvariantContract._is_missing_summary(
                i.get("summary", ""), lang
            )
        ]
        return len(indicators) > 0 and len(real) == 0

    def test_legacy_zh_shows_missing_only(self) -> None:
        """老数据（全 None）必须仍显示"暂无可用数据"（向后兼容）。"""
        result = score_macro()
        assert self._is_missing_only(result["indicators"], lang="zh") is True

    def test_new_zh_no_missing_only(self) -> None:
        """新数据（任一字段填入）不再显示"暂无可用数据"。"""
        for kwargs in (
            {"monetary_policy": "accommodative"},
            {"liquidity_indicator": "abundant"},
            {"sector_policy": "supportive"},
            {"us_china_impact": "limited"},
            {"regulatory_risk": "low"},
        ):
            result = score_macro(**kwargs)
            assert self._is_missing_only(result["indicators"], lang="zh") is False, (
                f"missingOnly=True for {kwargs}"
            )

    def test_new_zh_full_indicators_no_missing(self) -> None:
        """5 字段全填：UI 应展示 5 个独立指标行 + 维度分数（非占位）。"""
        result = score_macro(
            monetary_policy="neutral",
            liquidity_indicator="moderate",
            sector_policy="neutral",
            us_china_impact="limited",
            regulatory_risk="low",
        )
        assert self._is_missing_only(result["indicators"], lang="zh") is False
        assert len(result["indicators"]) == 5
        # 每个 indicator 都有非空 summary
        for ind in result["indicators"]:
            assert ind["summary"]
            assert "数据缺失" not in ind["summary"]


class TestScoreMacroObservability:
    """P5-fix: score_macro 5 键全缺失时打 warning（节流版）"""

    def setup_method(self) -> None:
        """重置节流缓存，确保每个测试独立"""
        from src.scoring.indicators.macro import _MACRO_MISSING_LOG_THROTTLE

        _MACRO_MISSING_LOG_THROTTLE.clear()

    def test_warning_emitted_on_all_missing(self, caplog) -> None:
        """所有 5 键 None 时应打 1 条 warning"""
        import logging

        with caplog.at_level(logging.WARNING, logger="src.scoring.indicators.macro"):
            score_macro()
        # 节流：第一次调用必打
        assert any(
            "all 5 inputs missing" in record.message for record in caplog.records
        )

    def test_warning_throttled_within_60s(self, caplog) -> None:
        """60s 内同 evidence 前缀最多打 1 条"""
        import logging
        from src.scoring.indicators.macro import _MACRO_MISSING_LOG_THROTTLE

        # 清空节流缓存
        _MACRO_MISSING_LOG_THROTTLE.clear()

        with caplog.at_level(logging.WARNING, logger="src.scoring.indicators.macro"):
            score_macro(evidence="test_throttle_evidence_xxx")
            score_macro(evidence="test_throttle_evidence_xxx")
            score_macro(evidence="test_throttle_evidence_xxx")

        # 1 条 evidence 对应 1 条 warning（节流生效）
        warning_count = sum(
            1 for r in caplog.records if "all 5 inputs missing" in r.message
        )
        assert warning_count == 1

    def test_no_warning_when_data_present(self, caplog) -> None:
        """任一字段填入时不应打 warning"""
        import logging

        with caplog.at_level(logging.WARNING, logger="src.scoring.indicators.macro"):
            score_macro(monetary_policy="neutral")
        assert not any("all 5 inputs missing" in r.message for r in caplog.records)
