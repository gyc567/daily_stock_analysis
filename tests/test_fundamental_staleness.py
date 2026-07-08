# -*- coding: utf-8 -*-
"""
Tests for fundamental payload staleness detection.

The staleness heuristic prevents snapshot blocks from being labeled ``ok`` when
their text content references years that are clearly outdated (e.g. a 2020
forecast stored in a 2026 snapshot).
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_provider.base import DataFetcherManager


class TestPayloadStaleness(unittest.TestCase):
    def test_empty_payload_is_not_stale(self) -> None:
        self.assertFalse(
            DataFetcherManager._detect_payload_staleness({}, current_year=2026)
        )
        self.assertFalse(
            DataFetcherManager._detect_payload_staleness(None, current_year=2026)
        )
        self.assertFalse(
            DataFetcherManager._detect_payload_staleness(
                {"revenue_yoy": None}, current_year=2026
            )
        )

    def test_recent_year_is_not_stale(self) -> None:
        payload = {
            "earnings": {
                "data": {
                    "forecast_summary": "预计2025年1-3月归属于上市公司股东的净利润盈利:5,000万元,同比上年增长:10%。",
                    "quick_report_summary": "2025-04-14",
                }
            }
        }
        self.assertFalse(
            DataFetcherManager._detect_payload_staleness(payload, current_year=2026)
        )

    def test_year_at_threshold_is_not_stale(self) -> None:
        # current_year=2026, lookback=1 -> threshold=2025. 2025 must be fresh.
        payload = {"earnings": {"data": {"forecast_summary": "预计2025年..."}}}
        self.assertFalse(
            DataFetcherManager._detect_payload_staleness(payload, current_year=2026)
        )

    def test_year_below_threshold_is_stale(self) -> None:
        payload = {
            "earnings": {
                "data": {
                    "forecast_summary": "预计2020年1-3月归属于上市公司股东的净利润盈利:3,963万元至4,308万元,同比上年增长:15%至25%。",
                    "quick_report_summary": "2023-04-14",
                }
            }
        }
        self.assertTrue(
            DataFetcherManager._detect_payload_staleness(payload, current_year=2026)
        )

    def test_chinese_text_after_year_is_stale(self) -> None:
        # Regression: the original \b regex failed to match "2020年" because
        # \b does not see Chinese characters as word boundaries. The fix uses
        # (?<![0-9])(20[12]\d)(?![0-9]) so pure-Chinese contexts still match.
        payload = {
            "earnings": {
                "data": {
                    "forecast_summary": "预计2020年1-3月非经常性损益:800万元。",
                }
            }
        }
        self.assertTrue(
            DataFetcherManager._detect_payload_staleness(payload, current_year=2026)
        )
        self.assertEqual(DataFetcherManager._scan_latest_year(payload), 2020)

    def test_digit_neighbors_not_matched(self) -> None:
        # 12020 / 20205 are not years; regex must not over-match them.
        # Note: in "12020-2025区间", "2025" is itself a valid 4-digit year, so
        # the scanner legitimately returns 2025 — that is the *only* 4-digit
        # year, not 2020. We assert below that "12020" and "20205" do not
        # contribute.
        self.assertEqual(
            DataFetcherManager._scan_latest_year({"t": "订单号12020的数据"}), None
        )
        self.assertEqual(
            DataFetcherManager._scan_latest_year({"t": "20205号公告"}), None
        )
        self.assertEqual(
            DataFetcherManager._scan_latest_year({"t": "12020-2025区间"}), 2025
        )

    def test_nested_dict_scan(self) -> None:
        payload = {
            "level1": {
                "level2": [
                    {"text": "no year here"},
                    {"text": "as of 2019 the data ended"},
                ]
            }
        }
        self.assertTrue(
            DataFetcherManager._detect_payload_staleness(payload, current_year=2026)
        )

    def test_only_old_year_stale(self) -> None:
        # 2023 quick report + nothing newer -> stale
        payload = {"earnings": {"data": {"quick_report_summary": "2023-04-14"}}}
        self.assertTrue(
            DataFetcherManager._detect_payload_staleness(payload, current_year=2026)
        )

    def test_no_year_strings_are_not_stale(self) -> None:
        payload = {"revenue_yoy": 12.5, "net_profit_yoy": 8.3}
        self.assertFalse(
            DataFetcherManager._detect_payload_staleness(payload, current_year=2026)
        )

    def test_downgrade_only_affects_ok_status(self) -> None:
        ok_payload = {"text": "2020-01-01"}
        self.assertEqual(
            DataFetcherManager._downgrade_for_staleness("ok", ok_payload), "partial"
        )
        # Already partial / failed / not_supported -> unchanged
        self.assertEqual(
            DataFetcherManager._downgrade_for_staleness("partial", ok_payload),
            "partial",
        )
        self.assertEqual(
            DataFetcherManager._downgrade_for_staleness("failed", ok_payload),
            "failed",
        )
        self.assertEqual(
            DataFetcherManager._downgrade_for_staleness("not_supported", ok_payload),
            "not_supported",
        )
        # Fresh payload keeps status=ok
        fresh = {"text": "2025-12-31"}
        self.assertEqual(DataFetcherManager._downgrade_for_staleness("ok", fresh), "ok")


if __name__ == "__main__":
    unittest.main()
