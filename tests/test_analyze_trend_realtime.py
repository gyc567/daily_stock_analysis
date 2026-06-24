# -*- coding: utf-8 -*-
"""analyze_trend 盘中实时 bar 合并的离线单元测试。

覆盖 ``_merge_today_realtime_bar`` 守卫矩阵（不依赖网络/真实行情）：
- 盘中 + df 最后一根 < today + 实时可用 → 合并，current_price == 实时价。
- 收盘后（df 最后一根 == today）→ 不合并（零回归核心断言）。
- 非交易日 → 不合并。
- 实时失败 / price<=0 → 不合并、不抛异常、返回原 df。
- df 为空 → 原样返回。
"""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from src.agent.tools.analysis_tools import _merge_today_realtime_bar


def _make_history_df(last_date: date, rows: int = 30, base_close: float = 10.0) -> pd.DataFrame:
    """构造历史日线 df，最后一根日期为 last_date，列结构对齐 load_history_df。"""
    dates = [last_date - timedelta(days=rows - 1 - i) for i in range(rows)]
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "open": [base_close] * rows,
            "high": [base_close + 0.5] * rows,
            "low": [base_close - 0.5] * rows,
            "close": [base_close + i * 0.01 for i in range(rows)],  # 递增，末值=base_close+(rows-1)*0.01
            "volume": [1000000.0] * rows,
            "amount": [1.0e7] * rows,
            "pct_chg": [0.5] * rows,
            "ma5": [base_close] * rows,
            "ma10": [base_close] * rows,
            "ma20": [base_close] * rows,
            "volume_ratio": [1.0] * rows,
        }
    )


def _make_quote(price: float = 12.34) -> SimpleNamespace:
    """构造一个轻量 realtime quote（字段对齐 UnifiedRealtimeQuote 用法）。"""
    return SimpleNamespace(
        price=price,
        open_price=11.0,
        high=12.5,
        low=10.8,
        volume=2000000,
        amount=2.4e7,
        change_pct=8.5,
    )


class TestMergeTodayRealtimeBar:
    today = date.today()

    def test_intraday_merges_realtime_bar(self):
        """盘中（df 最后一根 = 昨天）+ 实时可用 → append 今日 bar，current_price=实时价。"""
        df = _make_history_df(self.today - timedelta(days=1))  # 昨日收盘
        before_rows = len(df)
        before_last_close = df.iloc[-1]["close"]

        with patch(
            "src.core.trading_calendar.is_market_open", return_value=True
        ), patch(
            "src.core.trading_calendar.get_market_for_stock", return_value="cn"
        ), patch(
            "src.agent.tools.data_tools._get_fetcher_manager"
        ) as mock_mgr:
            mock_mgr.return_value.get_realtime_quote.return_value = _make_quote(64.82)
            merged = _merge_today_realtime_bar("600176", df)

        assert len(merged) == before_rows + 1, "应 append 一根今日 bar"
        assert pd.Timestamp(merged.iloc[-1]["date"]).date() == self.today
        assert float(merged.iloc[-1]["close"]) == 64.82
        # 历史部分未被破坏
        assert float(merged.iloc[-2]["close"]) == before_last_close

    def test_postmarket_no_merge(self):
        """收盘后（df 最后一根 == today）→ 不合并，行数不变（零回归核心断言）。"""
        df = _make_history_df(self.today)
        before_rows = len(df)

        with patch(
            "src.agent.tools.data_tools._get_fetcher_manager"
        ) as mock_mgr:
            merged = _merge_today_realtime_bar("600519", df)
            # fetcher_manager 不应被调用（今日已入库，提前返回）
            mock_mgr.assert_not_called()

        assert len(merged) == before_rows
        assert pd.Timestamp(merged.iloc[-1]["date"]).date() == self.today

    def test_future_dated_df_no_merge(self):
        """df 最后一根日期 > today（异常未来数据）→ 不合并。"""
        df = _make_history_df(self.today + timedelta(days=1))
        merged = _merge_today_realtime_bar("600519", df)
        assert len(merged) == len(df)

    def test_non_trading_day_no_merge(self):
        """非交易日（is_market_open=False）→ 不合并。"""
        df = _make_history_df(self.today - timedelta(days=1))
        with patch(
            "src.core.trading_calendar.is_market_open", return_value=False
        ), patch(
            "src.core.trading_calendar.get_market_for_stock", return_value="cn"
        ), patch(
            "src.agent.tools.data_tools._get_fetcher_manager"
        ) as mock_mgr:
            merged = _merge_today_realtime_bar("600176", df)
            mock_mgr.assert_not_called()
        assert len(merged) == len(df)

    def test_realtime_failure_fallback_no_raise(self):
        """实时获取抛异常 → 不合并、不抛异常、返回原 df。"""
        df = _make_history_df(self.today - timedelta(days=1))
        with patch(
            "src.core.trading_calendar.is_market_open", return_value=True
        ), patch(
            "src.core.trading_calendar.get_market_for_stock", return_value="cn"
        ), patch(
            "src.agent.tools.data_tools._get_fetcher_manager"
        ) as mock_mgr:
            mock_mgr.return_value.get_realtime_quote.side_effect = RuntimeError("net down")
            merged = _merge_today_realtime_bar("600176", df)  # 不应抛异常
        assert len(merged) == len(df)

    @pytest.mark.parametrize("bad_quote", [None, SimpleNamespace(price=None), SimpleNamespace(price=0)])
    def test_invalid_price_no_merge(self, bad_quote):
        """price 为 None / 0 → 不合并。"""
        df = _make_history_df(self.today - timedelta(days=1))
        with patch(
            "src.core.trading_calendar.is_market_open", return_value=True
        ), patch(
            "src.core.trading_calendar.get_market_for_stock", return_value="cn"
        ), patch(
            "src.agent.tools.data_tools._get_fetcher_manager"
        ) as mock_mgr:
            mock_mgr.return_value.get_realtime_quote.return_value = bad_quote
            merged = _merge_today_realtime_bar("600176", df)
        assert len(merged) == len(df)

    def test_empty_df_passthrough(self):
        """df 为空 → 原样返回（不抛异常）。"""
        assert _merge_today_realtime_bar("600519", None) is None
        empty = pd.DataFrame()
        result = _merge_today_realtime_bar("600519", empty)
        assert result is empty

    def test_merged_bar_columns_aligned(self):
        """合并后的今日 bar 只含 df 已有列，缺失列自动 NaN（不破坏 df 结构）。"""
        df = _make_history_df(self.today - timedelta(days=1))
        with patch(
            "src.core.trading_calendar.is_market_open", return_value=True
        ), patch(
            "src.core.trading_calendar.get_market_for_stock", return_value="cn"
        ), patch(
            "src.agent.tools.data_tools._get_fetcher_manager"
        ) as mock_mgr:
            mock_mgr.return_value.get_realtime_quote.return_value = _make_quote(15.0)
            merged = _merge_today_realtime_bar("600176", df)
        # 列集合不变
        assert set(merged.columns) == set(df.columns)
        # 最后一根的 OHLC 来自实时行情
        last = merged.iloc[-1]
        assert float(last["close"]) == 15.0
        assert float(last["high"]) == 12.5
