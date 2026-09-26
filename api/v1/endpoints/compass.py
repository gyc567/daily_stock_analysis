# -*- coding: utf-8 -*-
"""中期趋势罗盘 API endpoints。

手动分析入口：复用 P2 已落地的 fetcher/engine/rewriter/action_mapper/render，
不写 history、不进 guardrail 链（§13.7：罗盘快照仅 cron 落盘）。
页面独立于 COMPASS_ENABLED 开关（§13.4 决策 3）。
"""

from __future__ import annotations

import logging
import threading
from datetime import date
from typing import Dict, Literal, Optional, Tuple

from fastapi import APIRouter, HTTPException

from api.v1.schemas.compass import (
    CompassAnalyzeRequest,
    CompassAnalyzeResponse,
    CompassRewriteView,
    RewriteStepView,
)
from src.schemas.compass import CompassAction, MidtrendCompass, SubjectType

logger = logging.getLogger(__name__)

router = APIRouter()

_MIN_DAILY_BARS = 30

# 当日缓存：罗盘对同一交易日同一标的是确定性结果，重复分析直接复用。
# key = code，value = (缓存日期, compass)；跨日自动失效，不主动清理。
_compass_cache: Dict[str, Tuple[date, MidtrendCompass]] = {}
_compass_cache_lock = threading.Lock()


def _compute_compass(code: str, subject_type: SubjectType) -> MidtrendCompass:
    """Fetch daily OHLCV and run the compass engine + L4 timing. Raises HTTPException."""
    from data_provider import DataFetcherManager
    from data_provider.base import DataFetchError
    from src.config import get_config
    from src.services.compass import engine as compass_engine
    from src.services.compass import fetcher as compass_fetcher
    from src.services.compass.render import assemble

    manager = DataFetcherManager()
    try:
        ohlcv, _source = compass_fetcher.fetch_daily_ohlcv(manager, code)
    except (DataFetchError, ValueError) as exc:
        raise HTTPException(
            status_code=404, detail=f"无法获取 {code} 的行情数据：{exc}"
        ) from exc
    if ohlcv is None or len(ohlcv) < _MIN_DAILY_BARS:
        raise HTTPException(
            status_code=404,
            detail=f"{code} 行情数据不足（需要 ≥ {_MIN_DAILY_BARS} 根日线）",
        )
    daily = ohlcv["close"].astype(float)
    weekly = compass_fetcher.derive_weekly_closes(daily)
    output = compass_engine.compute(daily, weekly)
    last_bar_date = daily.index[-1].date()
    from src.services.compass.rewriter import infer_bar_status

    bar_status = infer_bar_status(last_bar_date)
    timing = compass_engine.derive_l4(
        ohlcv,
        weekly=output.l0,
        annual=output.l1,
        segment=output.l2,
        rhythm=output.l3,
        phase=output.phase,
        bar_status=bar_status,
        timing_enabled=getattr(get_config(), "compass_timing_enabled", False),
    )
    return assemble(
        code=code,
        name=None,
        subject_type=subject_type,
        as_of_trade_date=last_bar_date,
        engine=output,
        bar_status=bar_status,
        timing=timing,
    )


def _get_compass(code: str, subject_type: SubjectType) -> MidtrendCompass:
    today = date.today()
    with _compass_cache_lock:
        cached = _compass_cache.get(code)
        if cached is not None and cached[0] == today:
            return cached[1]
    compass = _compute_compass(code, subject_type)
    with _compass_cache_lock:
        _compass_cache[code] = (today, compass)
    return compass


@router.post("/analyze", response_model=None)
def analyze_compass(request: CompassAnalyzeRequest) -> CompassAnalyzeResponse:
    try:
        compass = _get_compass(request.code, request.subject_type)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Compass analyze failed for %s: %s", request.code, exc)
        raise HTTPException(status_code=503, detail=f"罗盘计算失败：{exc}") from exc

    # 请求侧补充名称（缓存实例不存名称，冻结模型用 model_copy 覆盖展示字段）。
    if request.stock_name and request.stock_name != compass.name:
        compass = compass.model_copy(update={"name": request.stock_name})

    from src.services.compass import render as compass_render
    from src.services.compass.action_mapper import map_compass_action
    from src.services.compass.rewriter import CompassState, RewriteResult, rewrite

    rewrite_view: Optional[CompassRewriteView] = None
    rewrite_pair: Optional[tuple[CompassAction, RewriteResult]] = None
    if request.draft_action is not None:
        # §13.8 (B7): 罗盘已发出超卖抄底信号时，weekly_bear 的买入否决被
        # 放行为逆势博弈仓；其余信号不改变改写链语义。
        timing_signal: Optional[Literal["bottom_fishing"]] = (
            "bottom_fishing"
            if any(s.type == "bottom_fishing" for s in compass.timing)
            else None
        )
        result = rewrite(
            request.draft_action,
            CompassState(
                weekly=compass.weekly,
                annual=compass.annual,
                segment=compass.segment,
                rhythm=compass.rhythm,
                phase=compass.phase,
                bar_status=compass.bar_status,
                timing_signal=timing_signal,
            ),
        )
        mapped = map_compass_action(result.final_action)
        rewrite_view = CompassRewriteView(
            initial_action=request.draft_action,
            final_action=result.final_action,
            reason_codes=list(result.reason_codes),
            steps=[RewriteStepView(reason_code=s.reason_code, action_after=s.action_after) for s in result.steps],
            decision_action=mapped.action,
            investment_action=mapped.investment_action,
        )
        rewrite_pair = (request.draft_action, result)

    return CompassAnalyzeResponse(
        compass=compass.model_dump(mode="json"),
        short_card=compass_render.short_card(compass, lang=request.lang),
        long_card=compass_render.long_card(compass, lang=request.lang, rewrite=rewrite_pair),
        rewrite=rewrite_view,
    )
