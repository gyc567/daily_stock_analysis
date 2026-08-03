# -*- coding: utf-8 -*-
"""P5-fix: _infer_sector_policy 多源兜底单元测试。

覆盖 4 个优先级：
1. LLM 文本 regex（语义最丰富）
2. industry_hint → 行业 KB policy_lean
3. sector_rankings 涨跌幅推断
4. 全部失败 → None
"""

from __future__ import annotations

from src.services.research_framework_integration import (
    _build_industry_hint,
    _infer_sector_policy,
    _infer_sector_policy_from_rankings,
)


class TestInferSectorPolicyPriority:
    """_infer_sector_policy 优先级测试"""

    def test_priority1_regex_over_industry_hint(self) -> None:
        """优先级 1: regex 命中时，industry_hint 不再被使用"""
        result = _infer_sector_policy(
            fundamental_text="公司获得国家政策扶持，所在行业获得产业政策利好",
            industry_drivers=[],
            industry_hint="医药",  # KB 是 restrictive
        )
        # regex 命中 supportive
        assert result == "supportive"

    def test_priority2_industry_hint_kb_match(self) -> None:
        """优先级 2: regex 不命中时，industry_hint KB 兜底"""
        result = _infer_sector_policy(
            fundamental_text="公司主营业务稳定，无重大政策变化",
            industry_drivers=[],
            industry_hint="医药",  # KB 是 restrictive
        )
        assert result == "restrictive"

    def test_priority2_industry_hint_kb_battery(self) -> None:
        result = _infer_sector_policy(
            fundamental_text="无政策相关描述",
            industry_drivers=[],
            industry_hint="锂电池",
        )
        assert result == "supportive"

    def test_priority2_industry_hint_baijiu(self) -> None:
        result = _infer_sector_policy(
            fundamental_text="无政策相关描述",
            industry_drivers=[],
            industry_hint="白酒",
        )
        assert result == "neutral"

    def test_priority3_sector_rankings_supportive(self) -> None:
        """优先级 3: sector_rankings 涨跌幅 > 2% → supportive"""
        result = _infer_sector_policy(
            fundamental_text="",
            industry_drivers=[],
            industry_hint=None,
            sector_rankings=[
                {"name": "新能源", "change_pct": 5.0},
                {"name": "医药", "change_pct": 3.0},
                {"name": "银行", "change_pct": 2.5},
            ],
        )
        assert result == "supportive"

    def test_priority3_sector_rankings_restrictive(self) -> None:
        result = _infer_sector_policy(
            fundamental_text="",
            industry_drivers=[],
            industry_hint=None,
            sector_rankings=[
                {"name": "新能源", "change_pct": -3.0},
                {"name": "医药", "change_pct": -2.5},
                {"name": "银行", "change_pct": -1.0},
            ],
        )
        assert result == "restrictive"

    def test_priority3_sector_rankings_neutral(self) -> None:
        result = _infer_sector_policy(
            fundamental_text="",
            industry_drivers=[],
            industry_hint=None,
            sector_rankings=[
                {"name": "新能源", "change_pct": 1.0},
                {"name": "医药", "change_pct": 0.5},
                {"name": "银行", "change_pct": -1.0},
            ],
        )
        assert result == "neutral"

    def test_priority4_all_missed_returns_none(self) -> None:
        result = _infer_sector_policy(
            fundamental_text="公司主营业务稳定",
            industry_drivers=[],
            industry_hint="军工",  # 不在 KB
            sector_rankings=None,
        )
        assert result is None

    def test_empty_inputs_return_none(self) -> None:
        assert (
            _infer_sector_policy(
                fundamental_text=None,
                industry_drivers=[],
                industry_hint=None,
            )
            is None
        )


class TestInferSectorPolicyFromRankings:
    """_infer_sector_policy_from_rankings 单测"""

    def test_empty_list(self) -> None:
        assert _infer_sector_policy_from_rankings([]) is None

    def test_none_list(self) -> None:
        assert _infer_sector_policy_from_rankings(None) is None

    def test_missing_change_field(self) -> None:
        assert _infer_sector_policy_from_rankings([{"name": "X"}]) is None

    def test_alternate_field_name(self) -> None:
        """支持 'change' 字段别名"""
        assert (
            _infer_sector_policy_from_rankings([{"name": "X", "change": 5.0}])
            == "supportive"
        )

    def test_invalid_types_in_list(self) -> None:
        assert (
            _infer_sector_policy_from_rankings([{"name": "X"}, "not_a_dict", None, 42])
            is None
        )

    def test_mixed_valid_invalid(self) -> None:
        # 部分有效时仍能计算
        assert (
            _infer_sector_policy_from_rankings(
                [
                    {"name": "X", "change_pct": 5.0},
                    "invalid",
                    {"name": "Y", "change_pct": 4.0},
                ]
            )
            == "supportive"
        )


class TestBuildIndustryHint:
    """_build_industry_hint 测试"""

    def test_from_sector_position(self) -> None:
        hint = _build_industry_hint(
            sector_position="公司属于半导体行业，功率器件龙头",
            boards=[],
        )
        assert hint is not None
        assert "半导体" in hint

    def test_from_boards(self) -> None:
        hint = _build_industry_hint(
            sector_position="",
            boards=[
                {"name": "半导体", "code": "BK001"},
                {"name": "创业板综", "code": "BK002"},  # 噪声，应过滤
            ],
        )
        assert hint is not None
        assert "半导体" in hint

    def test_filter_noisy_boards(self) -> None:
        """过滤"板块/概念/综/成分/罗素/股通/MSCI/央视/中盘/大盘/小盘/富时/GDR/指数/新消费" 等"""
        hint = _build_industry_hint(
            sector_position="",
            boards=[
                {"name": "半导体", "code": "BK001"},
                {"name": "深成500", "code": "BK002"},
                {"name": "MSCI中国", "code": "BK003"},
                {"name": "中证500", "code": "BK004"},
                {"name": "深股通", "code": "BK005"},
            ],
        )
        assert hint is not None
        assert "半导体" in hint
        # 噪声被过滤
        assert "综" not in hint
        assert "MSCI" not in hint

    def test_multiple_keywords(self) -> None:
        hint = _build_industry_hint(
            sector_position="公司涉及半导体+新能源电池",
            boards=[],
        )
        assert hint is not None
        assert "半导体" in hint
        assert "新能源" in hint or "锂电池" in hint or "动力电池" in hint

    def test_no_match_returns_none(self) -> None:
        hint = _build_industry_hint(
            sector_position="普通制造业",
            boards=[{"name": "上海板块", "code": "BK001"}],
        )
        # "上海板块"是噪声被过滤，"普通制造业"无关键词命中
        assert hint is None or hint == ""

    def test_limit_to_3_hints(self) -> None:
        """hint 最多 3 个关键词"""
        hint = _build_industry_hint(
            sector_position="半导体 新能源 医药 白酒 玻纤",
            boards=[],
        )
        if hint:
            # 逗号分隔不超过 3 段
            assert len(hint.split(",")) <= 3

    def test_empty_inputs(self) -> None:
        assert _build_industry_hint(sector_position="", boards=[]) is None
        assert _build_industry_hint(sector_position=None, boards=[]) is None  # type: ignore[arg-type]
