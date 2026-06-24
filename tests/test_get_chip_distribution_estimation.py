# -*- coding: utf-8 -*-
"""get_chip_distribution 历史K线估算降级单元测试。

覆盖 ``_estimate_chip_from_history``（纯函数）全分支 + ``_handle_get_chip_distribution``
的估算降级路径。mock fetcher manager 与 load_history_df，不依赖网络。

100% 覆盖新增逻辑：
- _estimate_chip_from_history: 正常估算 / df空 / 行数不足 / price缺(用最后close) /
  price<=0(用最后close) / 字段异常 / 零成交量
- _handle_get_chip_distribution: 真实chip可用不估算 / chip失败估算降级 / 估算失败返回error /
  历史加载异常返回error不抛
"""

from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from src.agent.tools.data_tools import (
    _estimate_chip_from_history,
    _handle_get_chip_distribution,
)


def _df(n: int = 20, base: float = 10.0, step: float = 0.5) -> pd.DataFrame:
    """构造递增收盘价、等量成交量的历史K线（close = base + i*step）。"""
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=n),
            "close": [base + i * step for i in range(n)],  # 10.0, 10.5, ..., 19.5 (n=20)
            "volume": [1000.0] * n,
        }
    )


class TestEstimateChipFromHistory:
    """_estimate_chip_from_history 全分支。"""

    def test_normal_estimation(self):
        """正常 df + price → 估算 dict，avg_cost=VWAP，estimated=True。"""
        df = _df()  # close 10.0..19.5, volume 等量 → VWAP=mean=14.75
        result = _estimate_chip_from_history("600176", df, current_price=15.0)
        assert result is not None
        assert result["estimated"] is True
        assert result["source"] == "estimated_from_history"
        assert result["code"] == "600176"
        assert result["avg_cost"] == pytest.approx(14.75, abs=0.01)
        # close<=15 的有 11 个（10.0..15.0），共 20 → profit_ratio=0.55
        assert result["profit_ratio"] == pytest.approx(0.55, abs=0.01)
        assert result["concentration_70"] > 0
        assert result["concentration_90"] > result["concentration_70"]  # 90% 区间更宽

    def test_none_df_returns_none(self):
        assert _estimate_chip_from_history("600176", None, 15.0) is None

    def test_empty_df_returns_none(self):
        assert _estimate_chip_from_history("600176", pd.DataFrame(), 15.0) is None

    def test_insufficient_rows_returns_none(self):
        """少于 10 根 → None（数据不足以估算）。"""
        assert _estimate_chip_from_history("600176", _df(n=9), 15.0) is None

    def test_missing_price_uses_last_close(self):
        """current_price=None → 用最后一根 close（19.5）→ profit_ratio=1.0。"""
        result = _estimate_chip_from_history("600176", _df(), current_price=None)
        assert result is not None
        assert result["profit_ratio"] == pytest.approx(1.0)

    def test_zero_price_uses_last_close(self):
        """current_price=0（falsy）→ 用最后一根 close。"""
        result = _estimate_chip_from_history("600176", _df(), current_price=0)
        assert result is not None
        assert result["profit_ratio"] == pytest.approx(1.0)

    def test_negative_price_uses_last_close(self):
        """current_price<=0 → 用最后一根 close。"""
        result = _estimate_chip_from_history("600176", _df(), current_price=-5)
        assert result is not None

    def test_missing_columns_returns_none(self):
        """df 无 close/volume 列 → None。"""
        bad = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=20), "foo": [1] * 20})
        assert _estimate_chip_from_history("600176", bad, 15.0) is None

    def test_zero_volume_returns_none(self):
        """成交量全 0 → total_vol<=0 → None。"""
        df = _df()
        df["volume"] = 0.0
        assert _estimate_chip_from_history("600176", df, 15.0) is None

    def test_last_close_unreadable_returns_none(self):
        """df 有效但 close 列异常 + price 缺 → 无法 fallback close → None。"""
        df = _df()
        df["close"] = "not_a_number"  # astype(float) 抛异常
        assert _estimate_chip_from_history("600176", df, None) is None


class TestHandleGetChipDistributionFallback:
    """_handle_get_chip_distribution 估算降级路径。"""

    @staticmethod
    def _manager(*, chip, price=15.0, quote_exc=None):
        mgr = SimpleNamespace()
        mgr.get_chip_distribution = lambda code: chip
        if quote_exc is not None:
            mgr.get_realtime_quote = lambda code: (_ for _ in ()).throw(quote_exc)
        else:
            mgr.get_realtime_quote = lambda code: SimpleNamespace(price=price)
        return mgr

    def test_returns_real_chip_when_available(self):
        """manager 返回真实 chip → 不估算（无 estimated 字段）。"""
        chip = SimpleNamespace(
            code="600176", date="2026-06-24", source="akshare_em",
            profit_ratio=0.6, avg_cost=55.0, cost_90_low=40, cost_90_high=70,
            concentration_90=0.5, cost_70_low=45, cost_70_high=65, concentration_70=0.3,
        )
        with patch(
            "src.agent.tools.data_tools._get_fetcher_manager",
            return_value=self._manager(chip=chip),
        ), patch(
            "src.services.history_loader.load_history_df"
        ) as mock_hist:
            r = _handle_get_chip_distribution("600176")
            mock_hist.assert_not_called()  # 有 chip 不应加载历史
        assert r["source"] == "akshare_em"
        assert "estimated" not in r
        assert r["avg_cost"] == 55.0

    def test_fallback_estimation_when_chip_none(self):
        """chip=None + 历史可用 → 估算降级（estimated=True）。"""
        with patch(
            "src.agent.tools.data_tools._get_fetcher_manager",
            return_value=self._manager(chip=None, price=15.0),
        ), patch(
            "src.services.history_loader.load_history_df",
            return_value=(_df(), "test"),
        ):
            r = _handle_get_chip_distribution("600176")
        assert r.get("estimated") is True
        assert r["source"] == "estimated_from_history"
        assert r["avg_cost"] == pytest.approx(14.75, abs=0.01)

    def test_error_when_estimation_fails(self):
        """chip=None + 历史不足 → 返回 error（不抛异常）。"""
        with patch(
            "src.agent.tools.data_tools._get_fetcher_manager",
            return_value=self._manager(chip=None),
        ), patch(
            "src.services.history_loader.load_history_df",
            return_value=(_df(n=5), "test"),  # 不足 10 根
        ):
            r = _handle_get_chip_distribution("600176")
        assert "error" in r
        assert "No chip distribution" in r["error"]

    def test_error_when_history_load_raises(self):
        """chip=None + load_history_df 抛异常 → 返回 error（不抛）。"""
        with patch(
            "src.agent.tools.data_tools._get_fetcher_manager",
            return_value=self._manager(chip=None),
        ), patch(
            "src.services.history_loader.load_history_df",
            side_effect=RuntimeError("db down"),
        ):
            r = _handle_get_chip_distribution("600176")
        assert "error" in r

    def test_error_when_quote_unavailable_uses_last_close(self):
        """chip=None + quote=None → 用历史最后 close 估算（仍降级成功）。"""
        with patch(
            "src.agent.tools.data_tools._get_fetcher_manager",
            return_value=self._manager(chip=None, price=None),
        ), patch(
            "src.services.history_loader.load_history_df",
            return_value=(_df(), "test"),
        ):
            r = _handle_get_chip_distribution("600176")
        # quote.price=None → 用最后 close 19.5 → profit_ratio=1.0
        assert r.get("estimated") is True
        assert r["profit_ratio"] == pytest.approx(1.0)
