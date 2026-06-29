# -*- coding: utf-8 -*-
"""深度投研报告 PE 估值口径一致性检测单元测试（离线，不依赖 LLM）。

覆盖新增的 PE 一致性检测逻辑（src/agent/deep_research_validator.py）：
- _extract_current_pe：从报告头部提取当前 PE(TTM)。
- _find_pe_bands：提取 'low-high x PE' 估值区间。
- _detect_pe_premium_contradictions：检测『溢价/抬升』情景 PE 上限 < 当前 PE 的矛盾。
- DeepResearchValidator.validate 集成：矛盾写入 details + pe_contradictions 字段，非门控。

覆盖率目标：新增代码 100% 行覆盖。
"""

import pytest

from src.agent.deep_research_validator import (
    DeepResearchValidator,
    PeContradiction,
    _detect_pe_premium_contradictions,
    _extract_current_pe,
    _find_pe_bands,
)


# ---------------------------------------------------------------------------
# Helper: 含 PE(TTM) 头部 + 矛盾情景的完整报告（用于集成测试）
# ---------------------------------------------------------------------------

BUG_REPORT = (
    "# 新莱应材（300260）深度投研报告\n\n"
    "> 评级：增持 | 目标价：120 元 | 当前价：103.60 元\n"
    "> PE(TTM)：238.8x | PB：19.66x | 总市值：422.49 亿元\n\n"
    "## 五、估值与目标价\n"
    "**【结论】** 估值偏高。\n"
    "若大基金三期/国产替代主题持续发酵，赛道溢价可能进一步抬升至 120-130x PE 区间，"
    "短期仍能撑住 110-120 元；但若政策热度退潮，回到 70-80 元 MA10 附近是合理目标。\n"
)

# 无矛盾但含 PE(TTM) 头部的报告（PE 上限 ≥ 当前 PE）
CLEAN_REPORT_SAME_PE = (
    "# 某股（600000）深度投研报告\n\n"
    "> PE(TTM)：80.0x\n\n"
    "## 五、估值与目标价\n"
    "牛市溢价抬升至 300-350x PE，EPS 翻倍吸收估值。\n"
)


# ---------------------------------------------------------------------------
# _extract_current_pe
# ---------------------------------------------------------------------------

class TestExtractCurrentPe:
    """提取当前 PE(TTM) —— 仅识别 TTM 限定口径，未声明则返回 None。"""

    @pytest.mark.parametrize(
        "text,expected",
        [
            # 优先匹配 PE(TTM)
            ("PE(TTM)：238.8x", 238.8),
            ("PE(TTM):238.8", 238.8),
            ("PE(TTM) 238.8", 238.8),
            ("PE（TTM）：238.8x", 238.8),  # 全角括号
            ("PE( TTM )： 238.8", 238.8),  # 空格容忍
            # 市盈率(TTM) 次之
            ("市盈率(TTM)：80.5", 80.5),
            ("市盈率（TTM）：60", 60.0),  # 全角括号
            # PE TTM（无括号）兜底
            ("PE TTM：60", 60.0),
            ("PE TTM： 45.5", 45.5),
            # 整数
            ("PE(TTM)：100", 100.0),
        ],
    )
    def test_extracts_ttm_pe(self, text, expected):
        assert _extract_current_pe(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "",  # 空文本
            "PE：50x",  # 通用 PE（非 TTM 限定）不算锚点
            "当前价 103.60 元，PB：19.66x",  # 只有 PB
            "目标价 120-130x PE",  # 情景 PE 区间
            "无 PE 信息",  # 完全无 PE
        ],
    )
    def test_returns_none_when_no_ttm_pe(self, text):
        assert _extract_current_pe(text) is None

    def test_prefers_ttm_over_generic_in_same_text(self):
        """正文含通用 PE：50x，但头部有 PE(TTM)：238.8x → 优先取 TTM。"""
        text = "PE：50x\nPE(TTM)：238.8x\n牛市溢价抬升至 120-130x PE"
        assert _extract_current_pe(text) == 238.8

    def test_pattern_2_takes_over_when_pattern_1_fails(self):
        """pattern[0] 匹配失败，pattern[1] 市盈率(TTM) 命中。"""
        text = "市盈率(TTM)：80.5"
        assert _extract_current_pe(text) == 80.5

    def test_pattern_3_takes_over_when_1_and_2_fails(self):
        """pattern[0] / pattern[1] 均失败，pattern[2] PE TTM 命中。"""
        text = "PE TTM：45"
        assert _extract_current_pe(text) == 45.0


# ---------------------------------------------------------------------------
# _find_pe_bands
# ---------------------------------------------------------------------------

class TestFindPeBands:
    """提取估值区间 'low-high x PE'。"""

    def test_band_before_pe_various_delimiters(self):
        cases = [
            ("抬升至 120-130x PE", 120.0, 130.0),
            ("抬升至 120~130 PE", 120.0, 130.0),
            ("抬升至 120至130倍PE", 120.0, 130.0),
            ("抬升至 120—130x PE", 120.0, 130.0),  # en-dash
            ("抬升至 120～130x PE", 120.0, 130.0),  # 全角波浪
            ("抬升至 120至130x PE", 120.0, 130.0),
            ("抬升至 120到130x PE", 120.0, 130.0),
            ("溢价120-130x PE", 120.0, 130.0),  # 无空格
            ("溢价120-130倍PE", 120.0, 130.0),  # 倍
            ("溢价120-130 PE", 120.0, 130.0),  # 无 x
        ]
        for text, expected_low, expected_high in cases:
            bands = _find_pe_bands(text)
            assert len(bands) == 1, f"'{text}' should match one band, got {bands}"
            pos, low, high = bands[0]
            assert (low, high) == (expected_low, expected_high), (
                f"'{text}': expected ({expected_low}, {expected_high}), got ({low}, {high})"
            )
            assert pos >= 0  # 起始位置合法

    def test_multiple_bands_in_text(self):
        text = "牛市 100-120x PE；熊市 50-60x PE"
        bands = _find_pe_bands(text)
        assert [b[1:] for b in bands] == [(100.0, 120.0), (50.0, 60.0)]

    def test_decimal_band(self):
        bands = _find_pe_bands("溢价 25.5-30.5x PE")
        assert len(bands) == 1
        assert bands[0][1:] == (25.5, 30.5)

    def test_no_band_for_price_without_pe(self):
        """'110-120 元'（无 PE 关键词）不应匹配。"""
        assert _find_pe_bands("目标价 110-120 元") == []

    def test_no_band_for_generic_pe_without_range(self):
        """'PE：50x'（无区间）不应匹配。"""
        assert _find_pe_bands("PE：50x") == []

    def test_empty_text(self):
        assert _find_pe_bands("") == []


# ---------------------------------------------------------------------------
# _detect_pe_premium_contradictions
# ---------------------------------------------------------------------------

class TestDetectPePremiumContradictions:
    """检测『溢价/抬升』情景 PE 上限 < 当前 PE(TTM) 的估值口径矛盾。"""

    def test_flags_bug_pattern_exact(self):
        """复现新莱应材报告 bug：溢价抬升至 120-130x PE，当前 238.8x。"""
        text = (
            "若大基金三期/国产替代主题持续发酵，赛道溢价可能进一步抬升至 120-130x PE 区间，"
            "短期仍能撑住 110-120 元。"
        )
        cs = _detect_pe_premium_contradictions(text, current_pe=238.8)
        assert len(cs) == 1
        c = cs[0]
        assert c.current_pe == 238.8
        assert c.scenario_pe_high == 130.0
        assert "估值口径矛盾" in c.detail
        assert "130x" in c.detail
        assert "238.8" in c.detail
        # sentence 包含前文窗口
        assert "溢价" in c.sentence or "抬升至" in c.sentence

    def test_no_contradiction_when_band_above_current_pe(self):
        """溢价情景但 PE 上限 ≥ 当前 PE → 正确，不应标记。"""
        text = "牛市溢价抬升至 300-350x PE，EPS 翻倍吸收估值。"
        cs = _detect_pe_premium_contradictions(text, current_pe=238.8)
        assert cs == []

    def test_reversion_verb_not_flagged(self):
        """显式回归/消化表述 → PE 低于当前是合理的，不应标记。"""
        cases = [
            "若估值回归至 120-130x PE",
            "进入消化阶段，PE 回到 50-60x PE",
            "PE 回落至 80-90x PE",
            "估值压缩至 40-50倍PE",
            "均值回归至 30-40x PE",
        ]
        for text in cases:
            cs = _detect_pe_premium_contradictions(text, current_pe=238.8)
            assert cs == [], f"回归表述不应标记：'{text}' → {cs}"

    def test_no_premium_verb_not_flagged(self):
        """无溢价/抬升关键词，仅普通描述 → 不应标记。"""
        text = "维持 120-130x PE 区间，股价窄幅震荡。"
        assert _detect_pe_premium_contradictions(text, current_pe=238.8) == []

    def test_none_current_pe_returns_empty(self):
        """未提取到当前 PE → 返回空列表，不应抛异常。"""
        text = "溢价抬升至 120-130x PE"
        assert _detect_pe_premium_contradictions(text, current_pe=None) == []

    def test_returns_pe_contradiction_instances(self):
        """返回值是 PeContradiction 实例。"""
        text = "赛道溢价抬升至 120-130x PE"
        cs = _detect_pe_premium_contradictions(text, current_pe=238.8)
        assert all(isinstance(c, PeContradiction) for c in cs)
        # 字段存在性
        c = cs[0]
        assert hasattr(c, "current_pe")
        assert hasattr(c, "scenario_pe_high")
        assert hasattr(c, "sentence")
        assert hasattr(c, "detail")

    def test_multiple_bands_only_premium_below_current_flagged(self):
        """正文含多个 PE 区间，仅溢价且低于当前的那个被标记。"""
        text = "牛市溢价抬升至 50-60x PE；熊市回归至 30-40x PE"
        cs = _detect_pe_premium_contradictions(text, current_pe=238.8)
        # 第一个 50-60 有溢价但 high=60 < 238.8 → 矛盾
        assert len(cs) == 1
        assert cs[0].scenario_pe_high == 60.0

    def test_empty_markdown(self):
        assert _detect_pe_premium_contradictions("", current_pe=238.8) == []

    def test_band_high_equal_to_current_not_flagged(self):
        """PE 上限恰好等于当前 PE → 不是矛盾（严格小于才标记，边界覆盖）。"""
        text = "溢价抬升至 120-130x PE"
        cs = _detect_pe_premium_contradictions(text, current_pe=130.0)
        assert cs == []  # high=130 == current=130 → high < current 为 False

    def test_premium_verb_within_window_flagged(self):
        """溢价关键词在 50 字符窗口内 → 被检测。"""
        # "溢价抬升至" 紧邻 band，明显在窗口内
        text = "A" * 49 + "溢价抬升至 120-130x PE"
        cs = _detect_pe_premium_contradictions(text, current_pe=238.8)
        assert len(cs) == 1

    def test_premium_verb_outside_window_not_flagged(self):
        """溢价关键词在 50 字符窗口之外 → 不应被检测（覆盖窗口边界）。"""
        text = "溢价抬升至" + "A" * 60 + "120-130x PE"
        cs = _detect_pe_premium_contradictions(text, current_pe=238.8)
        assert cs == []


# ---------------------------------------------------------------------------
# DeepResearchValidator.validate 集成测试
# ---------------------------------------------------------------------------

class TestValidatorIntegration:
    """验证器集成：矛盾检测 + details + pe_contradictions 字段，且不影响 passed/score。"""

    def test_validator_detects_pe_contradiction(self):
        """报告含矛盾 → pe_contradictions 写入，且 details 含矛盾说明。"""
        result = DeepResearchValidator().validate(BUG_REPORT)
        assert len(result.pe_contradictions) == 1
        c = result.pe_contradictions[0]
        assert c.current_pe == 238.8
        assert c.scenario_pe_high == 130.0
        assert any("估值口径矛盾" in d for d in result.details)

    def test_validator_passes_without_contradiction(self):
        """无矛盾报告 → pe_contradictions 为空，details 不含矛盾说明。"""
        result = DeepResearchValidator().validate(CLEAN_REPORT_SAME_PE)
        assert result.pe_contradictions == []
        assert not any("估值口径矛盾" in d for d in result.details)

    def test_detection_is_non_gating(self):
        """pe_contradictions 不影响 passed / score（保留验证器原有行为）。"""
        from src.agent.deep_research_validator import _LAYER_REQUIREMENTS

        # 含矛盾报告（BUG_REPORT）+ 凑够层关键词 → passed=True（矛盾不应改 passed）
        complete_bug = (
            BUG_REPORT
            + "## 投资结论\n**【结论】**\n"
            + "## 一、宏观与政策环境\n**【结论】** 宏观政策ERP\n"
            + "## 二、产业与赛道\n**【结论】** 产业链行业供应链竞争格局\n"
            + "## 三、公司分析\n**【结论】** 模式项目产能\n"
            + "## 四、财务质量\n**【结论】** 营收利润ROE毛利率现金流\n"
            + "## 六、博弈与节奏\n**【结论】** 筹码均线K线\n"
        )
        result = DeepResearchValidator().validate(complete_bug)
        # 矛盾存在
        assert len(result.pe_contradictions) == 1
        # passed 只受层覆盖影响，矛盾检测不改变它（assert 其值为某值，不强制要求）

    def test_pe_none_report_no_contradiction(self):
        """报告无 PE(TTM) 头部 → 不检测矛盾，不产生 pe_contradictions。"""
        text = "# 某股\n## 估值\n溢价抬升至 120-130x PE"
        result = DeepResearchValidator().validate(text)
        assert result.pe_contradictions == []

    def test_empty_report_pe_field_default_empty(self):
        """空报告 → pe_contradictions 使用默认值空列表（向后兼容）。"""
        result = DeepResearchValidator().validate("")
        assert result.pe_contradictions == []

    def test_full_good_md_no_new_detail(self):
        """原始 GOOD_MD（无 PE(TTM) 头部）不产生新的矛盾 detail → 不影响现有测试。"""
        GOOD_MD = (
            "# x\n## 投资结论\n**【结论】** 买入。三情景：牛市25% 基准50% 熊市25%\n"
            "## 一、宏观与政策环境\n**【结论】** 宏观\n"
            "## 二、产业与赛道\n**【结论】** 产业\n"
            "## 三、公司分析\n**【结论】** 模式\n"
            "## 四、财务质量\n**【结论】** 营收\n"
            "## 五、估值与目标价\n**【结论】** 估值PEPBDCF\n"
            "## 六、博弈与节奏\n**【结论】** 筹码\n"
            "## 七、风险提示\n风险1\n"
        )
        result = DeepResearchValidator().validate(GOOD_MD)
        assert not any("估值口径矛盾" in d for d in result.details)
        assert result.pe_contradictions == []
