# -*- coding: utf-8 -*-
"""``src/services/report_filename.py`` 单元测试（按 docs/pdf-download-filename-plan.md）。"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from src.services.report_filename import (
    format_stock_report_pdf_filename,
    format_topic_report_pdf_filename,
    _clean_filename_part,
    _format_date,
)


# ============================================================
# 单股报告 — 基础命名
# ============================================================


class TestFormatStockReport:
    def test_deep_research_full(self):
        """文档示例：科瑞技术（002957）深度投研报告20260630.pdf"""
        result = format_stock_report_pdf_filename(
            stock_name="科瑞技术",
            stock_code="002957",
            report_type="deep_research",
            created_at="2026-06-30T12:30:00",
        )
        assert result == "科瑞技术（002957）深度投研报告20260630.pdf"

    def test_policy_minesweeper_full(self):
        """文档示例：科瑞技术（002957）政策与公告排雷报告20260630.pdf"""
        result = format_stock_report_pdf_filename(
            stock_name="科瑞技术",
            stock_code="002957",
            report_type="policy_minesweeper",
            created_at="2026-06-30T12:30:00",
        )
        assert result == "科瑞技术（002957）政策与公告排雷报告20260630.pdf"

    def test_stock_name_fallback_to_code(self):
        """股票名为空时 fallback 到股票代码（按文档要求）。"""
        result = format_stock_report_pdf_filename(
            stock_name=None,
            stock_code="600519",
            report_type="deep_research",
            created_at="2026-06-30T12:30:00",
        )
        assert result == "600519（600519）深度投研报告20260630.pdf"

    def test_empty_stock_name_fallback(self):
        result = format_stock_report_pdf_filename(
            stock_name="",
            stock_code="600519",
            report_type="policy_minesweeper",
            created_at="2026-07-01T18:00:00",
        )
        assert result == "600519（600519）政策与公告排雷报告20260701.pdf"

    def test_iso_with_microseconds(self):
        """ISO 字符串带 .microseconds 也应解析正确。"""
        result = format_stock_report_pdf_filename(
            stock_name="贵州茅台",
            stock_code="600519",
            report_type="deep_research",
            created_at="2026-06-30T12:30:00.123456",
        )
        assert result == "贵州茅台（600519）深度投研报告20260630.pdf"

    def test_date_only_iso(self):
        result = format_stock_report_pdf_filename(
            stock_name="贵州茅台",
            stock_code="600519",
            report_type="deep_research",
            created_at="2026-06-30",
        )
        assert result == "贵州茅台（600519）深度投研报告20260630.pdf"


# ============================================================
# 非法字符清理
# ============================================================


class TestCleanFilename:
    def test_strip_invalid_chars(self):
        """移除 / \\ : * ? " < > |"""
        assert _clean_filename_part("贵州/茅台\\") == "贵州茅台"
        assert _clean_filename_part('A:B*C?D"E<F>G|H') == "ABCDEFGH"

    def test_strip_control_chars(self):
        # 控制字符 \n \t 直接被移除（不留空格），前后如无空格则不补
        assert _clean_filename_part("贵州\n茅台\tCo") == "贵州茅台Co"

    def test_strip_ascii_parens(self):
        """业务只保留中文括号，ASCII 括号应剥除（避免与中文括号混淆）。"""
        assert _clean_filename_part("科瑞(002957)技术") == "科瑞002957技术"

    def test_compress_whitespace(self):
        assert _clean_filename_part("贵州  茅台   Co") == "贵州 茅台 Co"

    def test_empty(self):
        assert _clean_filename_part("") == ""
        assert _clean_filename_part(None) == ""


# ============================================================
# 非法字符清理 — 集成到 format_stock_report
# ============================================================


class TestStockReportCleanup:
    def test_cleanup_in_name(self):
        """股票名含非法字符应清理。"""
        result = format_stock_report_pdf_filename(
            stock_name="贵州/茅台",
            stock_code="600519",
            report_type="deep_research",
            created_at="2026-06-30T12:30:00",
        )
        assert result == "贵州茅台（600519）深度投研报告20260630.pdf"

    def test_keep_chinese_parens(self):
        """中文括号（  ） 应保留。"""
        result = format_stock_report_pdf_filename(
            stock_name="科瑞（技术）",
            stock_code="002957",
            report_type="deep_research",
            created_at="2026-06-30T12:30:00",
        )
        assert result == "科瑞（技术）（002957）深度投研报告20260630.pdf"


# ============================================================
# 主题型报告（供应链）
# ============================================================


class TestFormatTopicReport:
    def test_basic(self):
        """文档示例：A股AI半导体供应链供应链分析报告20260630.pdf"""
        result = format_topic_report_pdf_filename(
            topic="A股AI半导体供应链",
            created_at="2026-06-30T14:13:18",
        )
        assert result == "A股AI半导体供应链供应链分析报告20260630.pdf"

    def test_long_topic(self):
        """文档示例：中际旭创是不是CPO核心卡点供应链分析报告20260630.pdf"""
        result = format_topic_report_pdf_filename(
            topic="中际旭创是不是CPO核心卡点",
            created_at="2026-06-30T12:30:00",
        )
        assert result == "中际旭创是不是CPO核心卡点供应链分析报告20260630.pdf"

    def test_empty_topic_fallback(self):
        result = format_topic_report_pdf_filename(
            topic="",
            created_at="2026-06-30T12:30:00",
        )
        assert result == "供应链分析供应链分析报告20260630.pdf"

    def test_topic_with_invalid_chars(self):
        result = format_topic_report_pdf_filename(
            topic="AI:半导体/行业",
            created_at="2026-06-30T12:30:00",
        )
        assert result == "AI半导体行业供应链分析报告20260630.pdf"


# ============================================================
# 日期解析
# ============================================================


class TestFormatDate:
    def test_datetime_object(self):
        from datetime import datetime

        assert _format_date(datetime(2026, 6, 30, 12, 30)) == "20260630"

    def test_iso_with_t(self):
        assert _format_date("2026-06-30T12:30:00") == "20260630"

    def test_iso_with_space(self):
        assert _format_date("2026-06-30 12:30:00") == "20260630"

    def test_date_only(self):
        assert _format_date("2026-06-30") == "20260630"

    def test_none_fallback_to_today(self):
        result = _format_date(None)
        import re

        assert re.match(r"^\d{8}$", result)

    def test_empty_string_fallback_to_today(self):
        result = _format_date("")
        import re

        assert re.match(r"^\d{8}$", result)
