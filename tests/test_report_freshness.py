# -*- coding: utf-8 -*-
"""
Tests for the report renderer's data-freshness badge.

The badge is derived from each ``AnalysisResult.fundamental_context['as_of']``
and rendered into the markdown / wechat templates so users see the
"data anchored to YYYY-MM-DD" line. When the as-of year is more than
one calendar year behind, we show a "data may be stale" warning.
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.services.report_renderer as renderer_mod
from src.services.report_renderer import (
    _is_stale,
    data_freshness_line,
    render,
)


class TestStalenessHeuristic(unittest.TestCase):
    def test_fresh_year_is_not_stale(self) -> None:
        self.assertFalse(_is_stale("2025-12-31", current_year=2026))
        self.assertFalse(_is_stale("2025-12-31", current_year=2025))

    def test_exactly_one_year_old_is_not_stale(self) -> None:
        # current_year=2026, threshold=2025. 2025 is the threshold; not stale.
        self.assertFalse(_is_stale("2025-01-01", current_year=2026))

    def test_two_years_old_is_stale(self) -> None:
        self.assertTrue(_is_stale("2024-12-31", current_year=2026))
        self.assertTrue(_is_stale("2020-12-31", current_year=2026))

    def test_missing_or_invalid_is_not_stale(self) -> None:
        # Missing or unparseable values must not flip the badge to stale;
        # the template can simply omit the row.
        self.assertFalse(_is_stale(None, current_year=2026))
        self.assertFalse(_is_stale("", current_year=2026))
        self.assertFalse(_is_stale("not-a-date", current_year=2026))


class TestFreshnessLine(unittest.TestCase):
    def test_empty_returns_empty_string(self) -> None:
        self.assertEqual(data_freshness_line(None, language="zh"), "")
        self.assertEqual(data_freshness_line("", language="en"), "")

    def test_fresh_chinese(self) -> None:
        line = data_freshness_line("2025-12-31", language="zh", current_year=2026)
        self.assertIn("2025-12-31", line)
        self.assertIn("📅", line)
        self.assertNotIn("⚠", line)
        self.assertNotIn("陈旧", line)

    def test_fresh_english(self) -> None:
        line = data_freshness_line("2025-12-31", language="en", current_year=2026)
        self.assertIn("2025-12-31", line)
        self.assertIn("📅", line)
        self.assertNotIn("⚠", line)
        self.assertNotIn("stale", line.lower())

    def test_stale_chinese(self) -> None:
        line = data_freshness_line("2020-12-31", language="zh", current_year=2026)
        self.assertIn("2020-12-31", line)
        self.assertIn("⚠", line)
        self.assertIn("陈旧", line)

    def test_stale_english(self) -> None:
        line = data_freshness_line("2020-12-31", language="en", current_year=2026)
        self.assertIn("2020-12-31", line)
        self.assertIn("⚠", line)
        self.assertIn("stale", line.lower())


class TestRenderMarkdownWithFreshness(unittest.TestCase):
    """End-to-end: build a minimal AnalysisResult, render the markdown
    template, and assert the freshness badge is present.
    """

    def _make_result(
        self,
        as_of: Optional[str] = None,
        sentiment: int = 50,
        operation: str = "Hold",
    ) -> Any:
        from src.analyzer import AnalysisResult

        return AnalysisResult(
            code="600519",
            name="贵州茅台",
            sentiment_score=sentiment,
            trend_prediction="Sideways" if operation != "Sell" else "Down",
            operation_advice=operation,
            decision_type="hold" if operation == "Hold" else "buy",
            confidence_level="Medium",
            report_language="zh",
            analysis_summary="测试摘要",
            success=True,
            dashboard={
                "intelligence": {"sentiment_summary": "中性"},
                "core_conclusion": {"one_sentence": "测试一句话"},
                "battle_plan": {},
                "data_perspective": {},
            },
            fundamental_context=({"as_of": as_of} if as_of is not None else None),
        )

    def test_markdown_template_renders_fresh_badge(self) -> None:
        from src.services.report_renderer import render

        result = self._make_result(as_of="2025-12-31")
        out = render("markdown", [result], report_date="2026-07-08")
        self.assertIsNotNone(out)
        self.assertIn("2025-12-31", out)
        self.assertIn("📅", out)
        self.assertNotIn("⚠ 数据截至", out)

    def test_markdown_template_renders_stale_badge(self) -> None:
        from src.services.report_renderer import render

        result = self._make_result(as_of="2020-12-31")
        out = render("markdown", [result], report_date="2026-07-08")
        self.assertIsNotNone(out)
        self.assertIn("2020-12-31", out)
        self.assertIn("⚠", out)
        self.assertIn("陈旧", out)

    def test_markdown_template_omits_badge_when_no_as_of(self) -> None:
        from src.services.report_renderer import render

        result = self._make_result(as_of=None)
        out = render("markdown", [result], report_date="2026-07-08")
        self.assertIsNotNone(out)
        # The badge line is omitted entirely when as_of is missing.
        self.assertNotIn("数据截至", out)
        self.assertNotIn("anchored to", out)


if __name__ == "__main__":
    unittest.main()
