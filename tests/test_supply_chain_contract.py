# -*- coding: utf-8 -*-
"""供应链核心业务公式契约测试（Layer 2：icontract）。

按 ``docs/type-contract-data-defense.md`` 与 ``AGENTS.md §1.3``：
- CI 通过 ``ICONTRACT_SLOW=true`` 跑本文件触发装饰器断言
- 每个契约测试用反例验证业务不变式 / 边界 / 落域
- 不依赖网络，纯本地纯函数 / 工厂方法

覆盖：
- SerenityScorer.score / _kb_relevance / _industry_prior
- cross_source.normalize_a_share_code / board_match_level / constituent_overlap_ratio / judge_verification
- kb_retriever.recency_weight
- SupplyChainDeepDiveV3.compute_aggregate_confidence
"""

from __future__ import annotations

from typing import Any, Tuple

import icontract
import pytest

from data_provider.supply_chain.cross_source import (
    SourceEvidence,
    board_match_level,
    constituent_overlap_ratio,
    judge_verification,
    normalize_a_share_code,
)
from src.schemas.supply_chain import (
    EvidenceStrength,
    IndustryOutlookV3,
    KBHitRef,
    KeyPartnerV3,
    MarketPositionV3,
    ProductLineV3,
    SerenityScoreResult,
    SupplyChainDeepDiveV3,
)
from src.services.supply_chain.kb_retriever import (
    RECENCY_HALF_LIFE_DAYS,
    SupplyChainKBResult,
    recency_weight,
)
from src.services.supply_chain.serenity_scorer import (
    KB_DRIVEN_FACTORS,
    SerenityScorer,
)


# ============================================================
# cross_source.normalize_a_share_code
# ============================================================


class TestNormalizeAShareCodeContract:
    """normalize_a_share_code 必须返回 None 或合法 6 位 A 股代码（首位 0/3/4/6/8/9）。"""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("600519", "600519"),
            ("sz300750", "300750"),
            ("300750.SZ", "300750"),
            ("SH600519", "600519"),
            ("sh600519", "600519"),
            ("bj920748", "920748"),
            ("600519.SH", "600519"),
            ("300750.SZ", "300750"),
        ],
    )
    def test_valid_ashare_codes_normalize(self, raw: str, expected: str) -> None:
        assert normalize_a_share_code(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "HK00700",
            "AAPL",
            "12345",
            "1234567",
            "100000",
            "200000",
            "500000",
            "700000",
            "",
            "abc",
        ],
    )
    def test_non_ashare_returns_none(self, raw: Any) -> None:
        assert normalize_a_share_code(raw) is None

    def test_non_string_returns_none(self) -> None:
        assert normalize_a_share_code(None) is None  # type: ignore[arg-type]
        assert normalize_a_share_code(600519) is None  # type: ignore[arg-type]
        assert normalize_a_share_code([]) is None  # type: ignore[arg-type]

    def test_postcondition_holds_for_many_inputs(self) -> None:
        """icontract @ensure 在每次调用时验证落域。"""
        for raw in [
            "600519",
            "sh300750",
            "HK00700",
            "AAPL",
            "12345",
            None,
            "",
            "abcdef",
        ]:
            result = normalize_a_share_code(raw)  # type: ignore[arg-type]
            assert result is None or (
                isinstance(result, str)
                and len(result) == 6
                and result.isdigit()
                and result[0] in "034689"
            )


# ============================================================
# cross_source.board_match_level
# ============================================================


class TestBoardMatchLevelContract:
    """board_match_level 返回 None / 'exact' / 'contains'。"""

    def test_exact_match(self) -> None:
        assert board_match_level("白酒", "白酒") == "exact"
        assert board_match_level("  白 酒 ", "白酒") == "exact"

    def test_contains_match(self) -> None:
        assert board_match_level("高端白酒", "白酒") == "contains"
        assert board_match_level("白酒", "高端白酒") == "contains"

    def test_no_match(self) -> None:
        assert board_match_level("新能源", "白酒") is None

    def test_empty_or_whitespace(self) -> None:
        assert board_match_level("", "白酒") is None
        assert board_match_level("白酒", "") is None
        assert board_match_level("   ", "白酒") is None


# ============================================================
# cross_source.constituent_overlap_ratio
# ============================================================


class TestConstituentOverlapRatioContract:
    """constituent_overlap_ratio ∈ [0, 1]。"""

    def test_identical_sets_full_overlap(self) -> None:
        assert (
            constituent_overlap_ratio(["600519", "300750"], ["600519", "300750"]) == 1.0
        )

    def test_disjoint_sets_zero_overlap(self) -> None:
        assert constituent_overlap_ratio(["600519"], ["300750"]) == 0.0

    def test_partial_overlap(self) -> None:
        assert constituent_overlap_ratio(["600519"], ["600519", "300750"]) == 0.5

    def test_both_empty_returns_zero(self) -> None:
        assert constituent_overlap_ratio([], []) == 0.0

    def test_one_empty_one_nonempty_returns_zero(self) -> None:
        assert constituent_overlap_ratio([], ["600519"]) == 0.0
        assert constituent_overlap_ratio(["600519"], []) == 0.0

    def test_invalid_codes_filtered_out(self) -> None:
        result = constituent_overlap_ratio(["HK00700"], ["HK00700"])
        assert result == 0.0
        result = constituent_overlap_ratio(["600519", "HK00700"], ["600519"])
        assert result == 1.0

    def test_normalized_codes_match(self) -> None:
        assert constituent_overlap_ratio(["sz300750"], ["300750.SZ"]) == 1.0


# ============================================================
# cross_source.judge_verification
# ============================================================


def _em(
    available: bool = True,
    matched: bool = False,
    boards: Tuple[str, ...] = (),
    constituents: Tuple[str, ...] = (),
) -> SourceEvidence:
    return SourceEvidence(
        source="eastmoney",
        available=available,
        matched=matched,
        boards=boards,
        constituents=constituents,
    )


def _ths(
    available: bool = True,
    matched: bool = False,
    boards: Tuple[str, ...] = (),
    constituents: Tuple[str, ...] = (),
) -> SourceEvidence:
    return SourceEvidence(
        source="ths",
        available=available,
        matched=matched,
        boards=boards,
        constituents=constituents,
    )


class TestJudgeVerificationContract:
    """judge_verification.status 落 5 档；.confidence 落 3 档；.overlap_ratio ∈ [0, 1]。"""

    def test_both_hit_returns_confirmed_high(self) -> None:
        r = judge_verification(
            "600519",
            "贵州茅台",
            _em(matched=True, boards=("白酒",), constituents=("600519",)),
            _ths(matched=True, boards=("白酒",), constituents=("600519",)),
            "白酒",
        )
        assert r.status == "confirmed"
        assert r.confidence == "high"

    def test_one_available_other_unavailable_partial(self) -> None:
        r = judge_verification(
            "600519",
            "贵州茅台",
            _em(matched=True, boards=("白酒",), constituents=("600519",)),
            _ths(available=False),
            "白酒",
        )
        assert r.status == "partial"
        assert r.confidence == "medium"

    def test_both_available_both_unhit_unverified(self) -> None:
        r = judge_verification(
            "600519",
            "贵州茅台",
            _em(matched=False, boards=("白酒",)),
            _ths(matched=False, boards=("白酒",)),
            "白酒",
        )
        assert r.status == "unverified"
        assert r.confidence == "low"

    def test_both_found_but_contradict_conflict(self) -> None:
        r = judge_verification(
            "600519",
            "贵州茅台",
            _em(matched=False, boards=("白酒",)),
            _ths(matched=True, boards=("白酒",), constituents=("600519",)),
            "白酒",
        )
        assert r.status == "conflict"
        assert r.confidence == "low"

    def test_both_unavailable_returns_unverified(self) -> None:
        r = judge_verification(
            "600519",
            "贵州茅台",
            _em(available=False),
            _ths(available=False),
            "白酒",
        )
        assert r.status == "unverified"
        assert r.confidence == "low"

    def test_overlap_ratio_within_unit_interval(self) -> None:
        cases = [
            (_em(), _em()),
            (
                _em(matched=True, constituents=("600519",)),
                _ths(matched=True, constituents=("600519",)),
            ),
            (_em(constituents=("600519",)), _ths()),
        ]
        for em, ths in cases:
            r = judge_verification("600519", "X", em, ths, "")
            assert 0.0 <= r.overlap_ratio <= 1.0


# ============================================================
# kb_retriever.recency_weight
# ============================================================


class TestRecencyWeightContract:
    """recency_weight 返回 (0, 1]。"""

    def test_zero_age_returns_one(self) -> None:
        assert recency_weight(0) == 1.0

    def test_half_life_age_returns_half(self) -> None:
        assert abs(recency_weight(RECENCY_HALF_LIFE_DAYS) - 0.5) < 1e-9

    def test_negative_age_returns_one(self) -> None:
        assert recency_weight(-1) == 1.0
        assert recency_weight(-100) == 1.0

    def test_none_age_returns_one(self) -> None:
        assert recency_weight(None) == 1.0

    def test_zero_half_life_returns_one(self) -> None:
        assert recency_weight(100, half_life_days=0) == 1.0
        assert recency_weight(100, half_life_days=-1) == 1.0

    def test_strictly_decreasing_with_age(self) -> None:
        prev = recency_weight(0)
        for age in (1, 30, 90, 180, 365, 730):
            cur = recency_weight(age)
            assert cur < prev
            prev = cur

    def test_postcondition_unit_interval(self) -> None:
        for age in [None, -1, 0, 1, 30, 180, 730, 3650]:
            w = recency_weight(age)
            assert 0.0 < w <= 1.0


# ============================================================
# SerenityScorer.score / _kb_relevance / _industry_prior
# ============================================================


def _empty_kb() -> SupplyChainKBResult:
    return SupplyChainKBResult(hits=[], aggregate_score=0.0)


class TestSerenityScorerContract:
    """SerenityScorer.score 必须产出 final_score ∈ [0, 100] 且 verdict 4 档之一。"""

    def test_final_score_in_unit_interval_with_empty_kb(self) -> None:
        scorer = SerenityScorer()
        result = scorer.score(
            ticker="600519",
            company="贵州茅台",
            market="A-share",
            kb_result=_empty_kb(),
            llm_signals={},
            industry_hint="高端白酒",
        )
        assert isinstance(result, SerenityScoreResult)
        assert 0 <= result.final_score <= 100
        assert result.verdict in {
            "顶级研究优先级",
            "高研究优先级",
            "值得跟踪",
            "早期线索或低优先级",
        }

    def test_kb_bonus_only_for_kb_driven_with_high_aggregate(self) -> None:
        """KB 加成仅对 KB_DRIVEN 因子 + aggregate_score >= 0.6 触发。

        反例：aggregate_score=0.0 时不应有任何 kb_bonus_applied。
        """
        scorer = SerenityScorer()
        result = scorer.score(
            ticker="600519",
            company="贵州茅台",
            kb_result=_empty_kb(),
            llm_signals={"chokepoint_severity": 0.5},
            industry_hint="半导体",
        )
        for factor in result.factors.values():
            assert factor.kb_bonus_applied == 0.0

    def test_industry_prior_within_unit_interval(self) -> None:
        scorer = SerenityScorer()
        for hint in ["半导体", "新能源", "白酒", "消费", "未知行业", ""]:
            for fkey in KB_DRIVEN_FACTORS.keys():
                p = scorer._industry_prior(fkey, hint, None)  # type: ignore[arg-type]
                assert 0.0 <= p <= 1.0

    def test_kb_relevance_returns_zero_when_no_hits(self) -> None:
        scorer = SerenityScorer()
        v = scorer._kb_relevance(_empty_kb(), "chokepoint_severity")  # type: ignore[arg-type]
        assert v == 0.0

    def test_kb_relevance_within_unit_interval_when_hits_present(self) -> None:
        hits = [
            KBHitRef.model_validate(
                {
                    "document_id": f"d{i}",
                    "document_title": f"t{i}",
                    "chunk_id": f"c{i}",
                    "content": "卡点" if i % 2 == 0 else "扩产",
                    "score": 0.8,
                    "raw_score": -1.0,
                }
            )
            for i in range(3)
        ]
        kb = SupplyChainKBResult(hits=hits, aggregate_score=0.8)
        scorer = SerenityScorer()
        v = scorer._kb_relevance(kb, "chokepoint_severity")  # type: ignore[arg-type]
        assert 0.0 <= v <= 1.0

    def test_score_rejects_empty_ticker(self) -> None:
        scorer = SerenityScorer()
        with pytest.raises(icontract.ViolationError):
            scorer.score(ticker="", company="X")

    def test_score_rejects_empty_company(self) -> None:
        scorer = SerenityScorer()
        with pytest.raises(icontract.ViolationError):
            scorer.score(ticker="600519", company="   ")

    def test_score_with_extreme_llm_signals_clamps_to_unit_interval(self) -> None:
        """极端 LLM 信号（=1）下 final_score 仍落在 [0, 100]。

        注：SerenityFactorScore.llm_signal 有 le=1.0 约束（schema layer 3），
        所以这里取 schema 合法上限 1.0。
        """
        scorer = SerenityScorer()
        extreme = {
            f: 1.0
            for f in [
                "demand_inflection",
                "architecture_coupling",
                "chokepoint_severity",
                "supplier_concentration",
                "expansion_difficulty",
                "evidence_quality",
                "valuation_disconnect",
                "catalyst_timing",
            ]
        }
        extreme.update(
            {
                f"penalty_{p}": 1.0
                for p in [
                    "dilution_financing",
                    "governance",
                    "geopolitics",
                    "liquidity",
                    "hype_risk",
                    "accounting_quality",
                    "cyclicality",
                    "alternative_design_risk",
                ]
            }
        )
        r = scorer.score(
            ticker="600519",
            company="贵州茅台",
            kb_result=_empty_kb(),
            llm_signals=extreme,
        )
        assert 0 <= r.final_score <= 100


# ============================================================
# SupplyChainDeepDiveV3.compute_aggregate_confidence
# ============================================================


def _de_product(name: str, ev: EvidenceStrength = "analysis") -> ProductLineV3:
    return ProductLineV3(name=name, category="core", evidence_strength=ev)


def _mp(name: str, ev: EvidenceStrength = "analysis") -> MarketPositionV3:
    return MarketPositionV3(subsegment=name, evidence_strength=ev)


def _kp(side: str, name: str, ev: EvidenceStrength = "analysis") -> KeyPartnerV3:
    return KeyPartnerV3(side=side, name=name, evidence_strength=ev)  # type: ignore[arg-type]


def _io(name: str, ev: EvidenceStrength = "analysis") -> IndustryOutlookV3:
    return IndustryOutlookV3(subsegment=name, evidence_strength=ev)


class TestDeepDiveAggregateConfidenceContract:
    """compute_aggregate_confidence 必须返回 high/medium/low 三档之一。"""

    def test_less_than_three_executed_returns_low(self) -> None:
        d = SupplyChainDeepDiveV3(ticker="600519", company="贵州茅台")
        assert d.compute_aggregate_confidence() == "low"

    def test_three_executed_with_analysis_returns_medium(self) -> None:
        d = SupplyChainDeepDiveV3(
            ticker="600519",
            company="X",
            product_matrix=[_de_product("A")],
            sections_executed=["product_matrix", "market_position", "industry_outlook"],
            market_position=[_mp("B")],
            industry_outlook=[_io("C")],
        )
        assert d.compute_aggregate_confidence() in ("medium", "high")

    def test_four_executed_with_three_strong_returns_high(self) -> None:
        d = SupplyChainDeepDiveV3(
            ticker="600519",
            company="X",
            product_matrix=[_de_product("A", ev="primary")],
            market_position=[_mp("B", ev="analysis")],
            key_customers=[_kp("customer", "C", ev="media")],
            industry_outlook=[_io("D", ev="kb_doc")],
            sections_executed=[
                "product_matrix",
                "market_position",
                "key_partners",
                "industry_outlook",
            ],
        )
        assert d.compute_aggregate_confidence() == "high"

    def test_five_executed_all_strong_returns_high(self) -> None:
        from src.schemas.supply_chain import FinancialQualityV3

        d = SupplyChainDeepDiveV3(
            ticker="600519",
            company="X",
            product_matrix=[_de_product("A", ev="primary")],
            market_position=[_mp("B", ev="analysis")],
            key_customers=[_kp("customer", "C", ev="media")],
            key_suppliers=[_kp("supplier", "D", ev="kb_doc")],
            industry_outlook=[_io("E", ev="primary")],
            financial_quality=[
                FinancialQualityV3(period="2024Q3", evidence_strength="primary")
            ],
            sections_executed=[
                "product_matrix",
                "market_position",
                "key_partners",
                "industry_outlook",
                "financial_quality",
            ],
        )
        assert d.compute_aggregate_confidence() == "high"

    def test_social_or_rumor_evidence_does_not_count_as_strong(self) -> None:
        """social/rumor 不在 strong_levels 内。"""
        d = SupplyChainDeepDiveV3(
            ticker="600519",
            company="X",
            product_matrix=[_de_product("A", ev="social")],
            market_position=[_mp("B", ev="rumor")],
            key_customers=[_kp("customer", "C", ev="social")],
            industry_outlook=[_io("D", ev="rumor")],
            sections_executed=[
                "product_matrix",
                "market_position",
                "key_partners",
                "industry_outlook",
            ],
        )
        assert d.compute_aggregate_confidence() == "medium"


# ============================================================
# SupplyChainReportService._validate_deep_dive_payload — datetime ISO 转换契约
# ============================================================


class TestDeepDivePayloadDatetimeContract:
    """_validate_deep_dive_payload 应使用 ``model_dump(mode='json')``，让 datetime
    转 ISO 字符串，确保下游 ``json.dumps`` 不抛 ``TypeError``。

    回归测试：曾因 ``model_dump()`` 返回 dict 含 datetime 实例，导致
    ``json.dumps`` 抛 ``TypeError``，整条 ``generate_report`` 流程失败。

    覆盖：
    1. 含 datetime 的 payload → 返回 dict 的 datetime 字段是 ISO 字符串
    2. 不含 datetime 的 payload → 行为不变（None/缺省）
    3. 完整 round-trip：返回的 dict 可直接 ``json.dumps`` 成功
    4. 反例：datetime 字符串形式输入 → 校验失败走备份层
    """

    def test_datetime_field_serialized_to_iso_string(self) -> None:
        """datetime fetched_at → 落盘 dict 应是 ISO 字符串，可直接 json.dumps。"""
        from datetime import datetime, timezone

        from src.services.supply_chain_report_service import (
            SupplyChainReportService,
        )

        fetched_at = datetime(2026, 7, 31, 10, 0, 0, tzinfo=timezone.utc)
        payload = {
            "ticker": "600519",
            "company": "贵州茅台",
            "fetched_at": fetched_at,
            "sections_executed": ["product_matrix"],
        }
        out = SupplyChainReportService._validate_deep_dive_payload(payload)

        assert out is not None
        # 关键契约：datetime 字段是 ISO 字符串（不是 datetime 实例）
        assert isinstance(out["fetched_at"], str)
        assert out["fetched_at"].startswith("2026-07-31T10:00:00")

    def test_dict_output_is_json_serializable(self) -> None:
        """返回的 dict 可被 ``json.dumps`` 直接序列化（不抛 TypeError）。"""
        from datetime import datetime, timezone
        import json

        from src.services.supply_chain_report_service import (
            SupplyChainReportService,
        )

        payload = {
            "ticker": "600519",
            "company": "贵州茅台",
            "fetched_at": datetime(2026, 7, 31, 10, 0, 0, tzinfo=timezone.utc),
        }
        out = SupplyChainReportService._validate_deep_dive_payload(payload)
        assert out is not None

        # 这是关键契约：可 json.dumps 不报错
        serialized = json.dumps(out, ensure_ascii=False)
        assert isinstance(serialized, str)

        # 反向解析后 fetched_at 应是 ISO 字符串
        reparsed = json.loads(serialized)
        assert isinstance(reparsed["fetched_at"], str)

    def test_naive_datetime_also_serializes(self) -> None:
        """无时区的 datetime（naive）也应被序列化为 ISO 字符串。"""
        from datetime import datetime

        from src.services.supply_chain_report_service import (
            SupplyChainReportService,
        )

        payload = {
            "ticker": "600519",
            "company": "贵州茅台",
            "fetched_at": datetime(2026, 7, 31, 10, 0, 0),
        }
        out = SupplyChainReportService._validate_deep_dive_payload(payload)
        assert out is not None
        assert isinstance(out["fetched_at"], str)
        assert out["fetched_at"].startswith("2026-07-31T10:00:00")

    def test_no_datetime_field_unchanged(self) -> None:
        """无 datetime 字段时行为不变（schema 默认 None）。"""
        from src.services.supply_chain_report_service import (
            SupplyChainReportService,
        )

        payload = {
            "ticker": "600519",
            "company": "贵州茅台",
            "sections_executed": [],
        }
        out = SupplyChainReportService._validate_deep_dive_payload(payload)
        assert out is not None
        # fetched_at 默认 None
        assert out["fetched_at"] is None
        assert out["sections_executed"] == []

    def test_datetime_iso_string_input_fails_validation(self) -> None:
        """反例：datetime 字段以 ISO 字符串输入应校验失败（schema 期望 datetime 实例）。"""
        from src.services.supply_chain_report_service import (
            SupplyChainReportService,
        )

        payload = {
            "ticker": "600519",
            "company": "贵州茅台",
            "fetched_at": "2026-07-31T10:00:00+00:00",  # 字符串，不是 datetime
            "sections_executed": ["product_matrix"],
        }
        out = SupplyChainReportService._validate_deep_dive_payload(payload)
        # 校验失败 → 返回 None（走备份层）
        assert out is None
