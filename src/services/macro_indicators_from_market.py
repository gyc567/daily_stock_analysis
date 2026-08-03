# -*- coding: utf-8 -*-
"""P5-fix: 客观 macro 指标从市场行情推断（不依赖 daily_market_context）。

设计目标：
- `liquidity_indicator` 从市场总成交额推断（沪深两市 tick 实时）
- `monetary_policy` 从主要指数涨跌幅推断（粗粒度近似，等真实利率数据接入后升级）
- 拿不到时返回 None，不抛异常（fail-open）

为什么是"近似"：
- `monetary_policy` 真值需要央行 OMO/利率/PMI 等数据，pipeline 暂无 fetcher
- 用指数涨跌近似是粗糙信号，但优于完全缺失；CHANGELOG 明确标注"近似值"
- 接入真实利率数据后只需替换 `_infer_monetary_policy_from_indices`

数据源：
- `DataFetcherManager.get_main_indices(region)` → list[dict]，每项含 name/code/change_pct
- `DataFetcherManager.get_market_stats(purpose=...)` → dict，含 total_amount

阈值（来自经验值，可后续按回测调整）：
- liquidity: total_amount >= 1.5 万亿→abundant / >= 0.8 万亿→moderate / < 0.8 万亿→scarce
- monetary: 沪深 300 + 创业板指 涨跌幅均值 > +2%→accommodative / <-2%→tight / 否则→neutral
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# P5-fix: 白名单常量（与 src.scoring.indicators.macro._score_*_liquid 保持一致）
_VALID_LIQUIDITY = frozenset({"abundant", "moderate", "scarce"})
_VALID_MONETARY = frozenset({"accommodative", "neutral", "tight"})

# 流动性阈值（单位：亿元；A股两市总成交额）
LIQUIDITY_ABUNDANT_THRESHOLD_YI = 15000.0
LIQUIDITY_MODERATE_THRESHOLD_YI = 8000.0

# 货币政策近似阈值（主要指数涨跌幅均值，%）
MONETARY_ACCOMMODATIVE_PCT = 2.0
MONETARY_TIGHT_PCT = -2.0


def infer_objective_macro_indicators(
    *,
    main_indices: Optional[List[Dict[str, Any]]] = None,
    market_stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[str]]:
    """P5-fix: 客观 macro 指标推断。

    Args:
        main_indices: DataFetcherManager.get_main_indices() 返回值
        market_stats: DataFetcherManager.get_market_stats() 返回值

    Returns:
        {"liquidity_indicator": "abundant" | "moderate" | "scarce" | None,
         "monetary_policy": "accommodative" | "neutral" | "tight" | None}
    """
    result: Dict[str, Optional[str]] = {
        "liquidity_indicator": None,
        "monetary_policy": None,
    }
    try:
        liq = _infer_liquidity_from_market_stats(market_stats)
        if liq:
            result["liquidity_indicator"] = liq
    except Exception as exc:  # noqa: BLE001
        logger.debug("[macro_from_market] liquidity inference failed: %s", exc)
    try:
        mono = _infer_monetary_policy_from_indices(main_indices)
        if mono:
            result["monetary_policy"] = mono
    except Exception as exc:  # noqa: BLE001
        logger.debug("[macro_from_market] monetary inference failed: %s", exc)
    return result


def _infer_liquidity_from_market_stats(
    market_stats: Optional[Dict[str, Any]],
) -> Optional[str]:
    """从市场总成交额推断 liquidity_indicator。"""
    if not isinstance(market_stats, dict):
        return None
    total = market_stats.get("total_amount")
    if not isinstance(total, (int, float)) or total <= 0:
        return None
    if total >= LIQUIDITY_ABUNDANT_THRESHOLD_YI:
        return "abundant"
    if total >= LIQUIDITY_MODERATE_THRESHOLD_YI:
        return "moderate"
    return "scarce"


def _infer_monetary_policy_from_indices(
    main_indices: Optional[List[Dict[str, Any]]],
) -> Optional[str]:
    """P5-fix (近似): 从主要指数涨跌幅推断 monetary_policy。

    ⚠️ 这是一个临时近似：指数涨跌 ≠ 货币政策，但作为缺数据时的信号
    强于 None。等真实央行/利率数据接入后只需替换本函数。

    选取指数：
    - 沪深 300 (000300)
    - 创业板指 (399006)
    - 上证指数 (000001)
    取上述指数的 change_pct 均值。
    """
    if not main_indices or not isinstance(main_indices, list):
        return None
    # 接受 6 位代码 + sh/sz/bj 前缀（不同数据源格式）
    _NORMALIZE_CODE = {
        "000001": "000001",
        "sh000001": "000001",
        "sz000001": "000001",
        "399001": "399001",
        "sz399001": "399001",
        "399006": "399006",
        "sz399006": "399006",
        "000016": "000016",
        "sh000016": "000016",
        "000300": "000300",
        "sh000300": "000300",
        "000688": "000688",
        "sh000688": "000688",
    }
    target_codes = set(_NORMALIZE_CODE.keys()) | {
        v for v in _NORMALIZE_CODE.values() if v not in _NORMALIZE_CODE
    }
    changes: List[float] = []
    for idx in main_indices:
        if not isinstance(idx, dict):
            continue
        code = str(idx.get("code", "")).strip()
        if code and code not in target_codes and code not in _NORMALIZE_CODE:
            continue
        chg = idx.get("change_pct")
        if chg is None and "change" in idx:
            chg = idx.get("change")
        if isinstance(chg, (int, float)):
            changes.append(float(chg))
    if not changes:
        return None
    avg = sum(changes) / len(changes)
    if avg > MONETARY_ACCOMMODATIVE_PCT:
        return "accommodative"
    if avg < MONETARY_TIGHT_PCT:
        return "tight"
    return "neutral"


# 暴露阈值供测试 / 监控用
__all__ = [
    "infer_objective_macro_indicators",
    "_infer_liquidity_from_market_stats",
    "_infer_monetary_policy_from_indices",
    "LIQUIDITY_ABUNDANT_THRESHOLD_YI",
    "LIQUIDITY_MODERATE_THRESHOLD_YI",
    "MONETARY_ACCOMMODATIVE_PCT",
    "MONETARY_TIGHT_PCT",
]
