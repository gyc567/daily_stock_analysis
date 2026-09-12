# -*- coding: utf-8 -*-
"""Tests for the midterm compass API endpoint (api/v1/endpoints/compass.py)."""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException

from api.v1.endpoints import compass as compass_endpoint
from api.v1.schemas.compass import CompassAnalyzeRequest
from src.services.compass.engine import EngineOutput
from src.services.compass.render import assemble


def _engine_output(**overrides: object) -> EngineOutput:
    base: dict[str, object] = {
        "l0": "weekly_bull",
        "l1": "annual_bull",
        "l2": "alive",
        "l3": "healthy",
        "phase": "trend_expanding",
        "observe_horizon": "1w",
        "position_filter": "full",
        "weekly_ema50": 100.0,
        "weekly_ema200": 90.0,
        "weekly_sample_size": 120,
        "daily_sample_size": 300,
        "ema20": 101.0,
        "ema50": 100.0,
        "ema100": 95.0,
        "ema200": 90.0,
        "rsi14": 55.0,
        "slope_ema20_10d": 0.5,
        "slope_ema50_20d": 0.3,
        "slope_ema200_40d": 0.1,
        "last_close": 102.0,
        "cross_ema20_ema50": "above",
    }
    base.update(overrides)
    return EngineOutput(**base)  # type: ignore[arg-type]


def _compass_fixture(**engine_overrides: object) -> object:
    yesterday = date.today() - timedelta(days=1)
    return assemble(
        code="600519",
        name="贵州茅台",
        subject_type="stock",
        as_of_trade_date=yesterday,
        engine=_engine_output(**engine_overrides),
        bar_status="closed",
    )


class TestAnalyzeEndpoint:
    def test_analyze_returns_compass_and_cards(self) -> None:
        request = CompassAnalyzeRequest(code="600519")
        with patch.object(
            compass_endpoint, "_get_compass", return_value=_compass_fixture()
        ):
            response = compass_endpoint.analyze_compass(request)
        assert response.compass["code"] == "600519"
        assert response.compass["phase"] == "trend_expanding"
        assert response.compass["timing"] == []
        assert "中期趋势罗盘" in response.long_card
        assert response.short_card
        assert response.rewrite is None

    def test_analyze_english_cards(self) -> None:
        request = CompassAnalyzeRequest(code="600519", lang="en")
        with patch.object(
            compass_endpoint, "_get_compass", return_value=_compass_fixture()
        ):
            response = compass_endpoint.analyze_compass(request)
        assert "Midterm Trend Compass" in response.long_card

    def test_analyze_with_draft_rewrite(self) -> None:
        request = CompassAnalyzeRequest(code="600519", draft_action="buy")
        compass = _compass_fixture(l0="weekly_bear", phase="trend_holding")
        with patch.object(compass_endpoint, "_get_compass", return_value=compass):
            response = compass_endpoint.analyze_compass(request)
        assert response.rewrite is not None
        assert response.rewrite.initial_action == "buy"
        assert response.rewrite.final_action == "watch"
        assert "weekly_bear_buy_blocked" in response.rewrite.reason_codes
        assert [(s.reason_code, s.action_after) for s in response.rewrite.steps] == [
            ("weekly_bear_buy_blocked", "watch"),
        ]
        assert response.rewrite.decision_action == "watch"
        assert response.rewrite.investment_action == "观察"

    def test_analyze_draft_clean_passes_through(self) -> None:
        request = CompassAnalyzeRequest(code="600519", draft_action="buy")
        with patch.object(
            compass_endpoint, "_get_compass", return_value=_compass_fixture()
        ):
            response = compass_endpoint.analyze_compass(request)
        assert response.rewrite is not None
        assert response.rewrite.final_action == "buy"
        assert response.rewrite.reason_codes == []

    def test_analyze_draft_buy_passes_with_bottom_fishing_signal(self) -> None:
        # §13.8 (B7): 周线空头下罗盘已发出超卖抄底信号时，初稿买入被放行
        # 为逆势博弈仓（reason 标注 weekly_bear_bottom_fishing_pass）。
        from src.schemas.compass import TimingSignal

        compass = _compass_fixture(l0="weekly_bear", phase="trend_holding")
        compass = compass.model_copy(update={"timing": [
            TimingSignal(
                type="bottom_fishing", status="triggered", countertrend=True,
                reason_codes=["bottom_fishing_time_stop",
                              "weekly_bear_bottom_fishing_pass"],
                trigger_price=80.0, invalidation_price=78.0,
                position_hint="light", horizon_days=5,
                as_of_bar_date=date.today() - timedelta(days=1),
            ),
        ]})
        request = CompassAnalyzeRequest(code="600519", draft_action="buy")
        with patch.object(compass_endpoint, "_get_compass", return_value=compass):
            response = compass_endpoint.analyze_compass(request)
        assert response.rewrite is not None
        assert response.rewrite.final_action == "buy"
        assert "weekly_bear_bottom_fishing_pass" in response.rewrite.reason_codes
        assert "weekly_bear_buy_blocked" not in response.rewrite.reason_codes

    def test_stock_name_overrides_cached_name(self) -> None:
        request = CompassAnalyzeRequest(code="600519", stock_name="茅台")
        with patch.object(
            compass_endpoint, "_get_compass", return_value=_compass_fixture()
        ):
            response = compass_endpoint.analyze_compass(request)
        assert response.compass["name"] == "茅台"

    def test_invalid_request_rejected_by_schema(self) -> None:
        with pytest.raises(Exception):
            CompassAnalyzeRequest(code="bad code!")


class TestComputeCompass:
    def _mock_daily(self):
        import pandas as pd

        dates = pd.date_range(end=pd.Timestamp(date.today()), periods=60, freq="B")
        return pd.Series(range(60), index=dates, dtype=float, name="close")

    def test_fetch_failure_raises_404(self) -> None:
        from data_provider.base import DataFetchError

        with patch("data_provider.DataFetcherManager") as manager_mock:
            manager_mock.return_value.get_daily_data.side_effect = DataFetchError(
                "all sources failed"
            )
            with pytest.raises(HTTPException) as exc_info:
                compass_endpoint._compute_compass("600519", "stock")
        assert exc_info.value.status_code == 404

    def test_insufficient_bars_raises_404(self) -> None:
        import pandas as pd

        with patch("data_provider.DataFetcherManager") as manager_mock:
            df = pd.DataFrame({"date": ["2026-01-01"], "close": [1.0]})
            manager_mock.return_value.get_daily_data.return_value = (df, "mock")
            with pytest.raises(HTTPException) as exc_info:
                compass_endpoint._compute_compass("600519", "stock")
        assert exc_info.value.status_code == 404

    def test_cache_same_day_hit(self) -> None:
        compass = _compass_fixture()
        compass_endpoint._compass_cache.clear()
        with patch.object(
            compass_endpoint, "_compute_compass", return_value=compass
        ) as compute_mock:
            first = compass_endpoint._get_compass("600519", "stock")
            second = compass_endpoint._get_compass("600519", "stock")
        assert first is second
        compute_mock.assert_called_once()

    def test_unexpected_error_becomes_503(self) -> None:
        request = CompassAnalyzeRequest(code="600519")
        with patch.object(
            compass_endpoint, "_get_compass", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(HTTPException) as exc_info:
                compass_endpoint.analyze_compass(request)
        assert exc_info.value.status_code == 503
