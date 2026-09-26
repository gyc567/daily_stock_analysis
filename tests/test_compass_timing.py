# -*- coding: utf-8 -*-
"""Tests for L4 timing signals (engine.derive_l4, plan §13.8)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from src.services.compass.engine import _candidate_is_extreme, _swing_extremes, derive_l4

_WEEKDAY_START = date(2026, 6, 1)  # Monday


def _frame(closes: list[float], lows: list[float] | None = None,
           highs: list[float] | None = None) -> pd.DataFrame:
    """Build an OHLCV frame; default low/high hug the close by ±1%."""
    n = len(closes)
    idx = pd.DatetimeIndex(
        [_WEEKDAY_START + timedelta(days=i) for i in range(n)], name="date"
    )
    low = lows if lows is not None else [c * 0.99 for c in closes]
    high = highs if highs is not None else [c * 1.01 for c in closes]
    return pd.DataFrame(
        {
            "open": closes,
            "high": high,
            "low": low,
            "close": closes,
            "volume": [1e6] * n,
        },
        index=idx,
    )


def _base_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "weekly": "weekly_bull",
        "annual": "annual_bull",
        "segment": "alive",
        "rhythm": "healthy",
        "phase": "trend_expanding",
        "bar_status": "closed",
        "timing_enabled": True,  # tests opt in explicitly; global default is off
    }
    base.update(overrides)
    return base


class TestSwingHelpers:
    def test_swing_extremes_confirmed_only(self) -> None:
        lows = pd.Series([5.0, 4.0, 5.0, 6.0, 4.5, 5.0, 6.0, 3.0, 5.0, 6.0])
        points = _swing_extremes(lows, find_low=True)
        # index 4 and 7 are confirmed minima of their 5-bar windows;
        # index 1 is too close to the start to confirm (right=2 bars needed).
        assert [i for i, _ in points] == [4, 7]

    def test_candidate_extreme_last_bar(self) -> None:
        lows = pd.Series([5.0, 4.0, 5.0, 6.0, 3.5])
        assert _candidate_is_extreme(lows, find_low=True) is True
        assert _candidate_is_extreme(lows, find_low=False) is False


class TestPullbackEntry:
    def _uptrend_with_dip(self) -> pd.DataFrame:
        closes = [100.0 + i * 0.2 for i in range(50)]  # → 109.8 steady rise
        dip = [110.5, 107.5, 104.5, 105.0, 108.0]      # 回踩 EMA20 后收复
        closes = closes + dip
        lows = [c * 0.99 for c in closes]
        for i in range(-5, 0):
            lows[i] = closes[i] - 2.0  # deep intraday dips into the EMA20 zone
        return _frame(closes, lows=lows)

    def test_triggered_in_bull_pullback(self) -> None:
        signals = derive_l4(self._uptrend_with_dip(), **_base_kwargs())
        hits = [s for s in signals if s.type == "pullback_entry"]
        assert len(hits) == 1
        s = hits[0]
        assert s.status == "triggered"
        assert s.countertrend is False
        assert s.position_hint == "full"
        assert s.trigger_price is not None and s.invalidation_price is not None
        assert s.invalidation_price < s.trigger_price

    def test_absent_under_weekly_bear(self) -> None:
        signals = derive_l4(
            self._uptrend_with_dip(), **_base_kwargs(weekly="weekly_bear")
        )
        assert [s for s in signals if s.type == "pullback_entry"] == []


class TestBottomFishing:
    def _downtrend_with_divergence(self) -> pd.DataFrame:
        # 两段下跌夹一段弱反弹：第二段价格新低但跌速放缓（RSI 低点抬高）+ 末日止跌。
        leg1 = [100.0 - i * 0.8 for i in range(20)]          # → 84.8
        bounce = [85.5, 86.5, 87.0, 86.5]                     # 弱反弹
        leg2 = [86.0 - i * 0.5 for i in range(7)]             # → 83.0 更慢、价格新低
        hover = [81.45, 81.55, 81.65, 81.75, 81.85, 81.95]    # 低位企稳
        closes = leg1 + bounce + leg2 + hover
        closes[-1] = closes[-2] + 1.2                         # 末日收阳止跌
        lows = [c * 0.99 for c in closes]
        lows[-1] = closes[-1] - 1.0                           # 长下影
        for i in range(-7, -1):
            lows[i] = closes[i] - 0.9
        return _frame(closes, lows=lows)

    def test_triggered_countertrend_light_position(self) -> None:
        signals = derive_l4(
            self._downtrend_with_divergence(),
            **_base_kwargs(weekly="weekly_bear", annual="annual_bear",
                           phase="transitioning"),
        )
        hits = [s for s in signals if s.type == "bottom_fishing"]
        assert len(hits) == 1
        s = hits[0]
        assert s.status == "triggered"
        assert s.countertrend is True
        assert s.position_hint == "light"
        assert "weekly_bear_bottom_fishing_pass" in s.reason_codes
        assert "bottom_fishing_time_stop" in s.reason_codes
        assert s.invalidation_price is not None and s.trigger_price is not None
        assert s.invalidation_price < s.trigger_price

    def test_grinding_decline_without_divergence_stays_silent(self) -> None:
        # 匀速阴跌：价格低点下移且 RSI 低点同步下移（钝化），不得出抄底信号。
        closes = [120.0 - i * 0.5 for i in range(60)]
        signals = derive_l4(
            _frame(closes), **_base_kwargs(weekly="weekly_bear")
        )
        assert [s for s in signals if s.type == "bottom_fishing"] == []

    def test_broken_segment_blocks_bottom(self) -> None:
        signals = derive_l4(
            self._downtrend_with_divergence(),
            **_base_kwargs(segment="broken", weekly="weekly_bear"),
        )
        assert [s for s in signals if s.type == "bottom_fishing"] == []


class TestTopEscape:
    def _blowoff_stall(self) -> pd.DataFrame:
        # 缓涨后末端急拉、小幅回落再二次冲高：价格新高但 RSI 不新高（顶背离）。
        base = [100.0 + i * 0.15 for i in range(40)]
        rally1 = [106.0, 107.5, 109.0, 110.5, 112.0, 113.5]
        pull = [112.5, 111.5, 110.8, 110.2]
        rally2 = [111.0, 112.2, 113.4, 114.4, 115.2]          # 价格新高、动能衰减
        return _frame(base + rally1 + pull + rally2)

    def test_divergence_triggers_escape(self) -> None:
        signals = derive_l4(
            self._blowoff_stall(),
            **_base_kwargs(annual="annual_bear", segment="broken",
                           rhythm="noisy", phase="transitioning"),
        )
        hits = [s for s in signals if s.type == "top_escape"]
        assert len(hits) == 1
        s = hits[0]
        assert s.status == "triggered"
        assert "top_escape_divergence" in s.reason_codes
        assert s.invalidation_price is not None and s.trigger_price is not None
        assert s.invalidation_price > s.trigger_price

    def test_shielded_healthy_bull_has_no_escape(self) -> None:
        signals = derive_l4(self._blowoff_stall(), **_base_kwargs())
        assert [s for s in signals if s.type == "top_escape"] == []


class TestGates:
    def test_intraday_bars_yield_nothing(self) -> None:
        closes = [100.0 + i * 0.45 for i in range(52)] + [121.0, 119.0, 117.5, 118.0, 121.5]
        signals = derive_l4(
            _frame(closes), **_base_kwargs(bar_status="intraday_unconfirmed")
        )
        assert signals == ()

    def test_disabled_yields_nothing(self) -> None:
        closes = [100.0 + i * 0.45 for i in range(52)] + [121.0, 119.0, 117.5, 118.0, 121.5]
        signals = derive_l4(
            _frame(closes), **_base_kwargs(timing_enabled=False)
        )
        assert signals == ()

    def test_too_short_series_yields_nothing(self) -> None:
        signals = derive_l4(_frame([100.0] * 20), **_base_kwargs())
        assert signals == ()
