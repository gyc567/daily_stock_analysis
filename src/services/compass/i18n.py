# -*- coding: utf-8 -*-
"""i18n labels for the midterm trend compass.

Issue scope: docs/midterm-trend-compass-plan.md §3.1.
Single source for phase / action / L0..L3 / bar status zh-en labels.
"""

from __future__ import annotations

from typing import Literal

from src.schemas.compass import (
    L0Status,
    L1Status,
    L2Status,
    L3Status,
    BarStatus,
    CompassAction,
    Phase,
)

Language = Literal["zh", "en"]


_PHASE: dict[Phase, dict[Language, str]] = {
    "trend_expanding":  {"zh": "趋势扩张",  "en": "Expanding"},
    "trend_holding":    {"zh": "同轮持有",  "en": "Holding"},
    "trend_tiring":     {"zh": "动能先弱",  "en": "Tiring"},
    "coiling":          {"zh": "收口震荡",  "en": "Coiling"},
    "transitioning":    {"zh": "结构切换",  "en": "Transitioning"},
}


_ACTION: dict[CompassAction, dict[Language, str]] = {
    "buy":   {"zh": "买入", "en": "Buy"},
    "watch": {"zh": "观望", "en": "Watch"},
    "sell":  {"zh": "卖出", "en": "Sell"},
}


_L0: dict[L0Status, dict[Language, str]] = {
    "weekly_bull":       {"zh": "周多",   "en": "W-Bull"},
    "weekly_bear":       {"zh": "周空",   "en": "W-Bear"},
    "weekly_transition": {"zh": "周转",   "en": "W-Trans"},
    "weekly_disabled":   {"zh": "周-",    "en": "W-Off"},
}


_L1: dict[L1Status, dict[Language, str]] = {
    "annual_bull":       {"zh": "年多",   "en": "Y-Bull"},
    "annual_bear":       {"zh": "年空",   "en": "Y-Bear"},
    "annual_transition": {"zh": "年转",   "en": "Y-Trans"},
    "annual_disabled":   {"zh": "年-",    "en": "Y-Off"},
}


_L2: dict[L2Status, dict[Language, str]] = {
    "alive":      {"zh": "持主段", "en": "Alive"},
    "resting":    {"zh": "休整",   "en": "Resting"},
    "flattening": {"zh": "收口",   "en": "Flatten"},
    "broken":     {"zh": "破坏",   "en": "Broken"},
}


_L3: dict[L3Status, dict[Language, str]] = {
    "healthy":   {"zh": "节奏健康", "en": "Healthy"},
    "cooling":   {"zh": "节奏降温", "en": "Cooling"},
    "exhausted": {"zh": "动能乏力", "en": "Exhausted"},
    "noisy":     {"zh": "节奏失配", "en": "Noisy"},
}


_BAR: dict[BarStatus, dict[Language, str]] = {
    "closed":               {"zh": "已收",   "en": "Closed"},
    "intraday_unconfirmed": {"zh": "盘中",   "en": "Intraday"},
    "stale":                {"zh": "陈旧",   "en": "Stale"},
    "suspended":            {"zh": "停牌",   "en": "Suspended"},
}


_INDEX_ACTION = {
    "zh": {"bullish": "偏多观察", "neutral": "中性", "bearish": "偏空观察"},
    "en": {"bullish": "Bullish Watch", "neutral": "Neutral", "bearish": "Bearish Watch"},
}


def phase_text(phase: Phase, lang: Language = "zh") -> str:
    return _PHASE[phase][lang]


def action_text(action: CompassAction, lang: Language = "zh") -> str:
    return _ACTION[action][lang]


def l0_text(status: L0Status, lang: Language = "zh") -> str:
    return _L0[status][lang]


def l1_text(status: L1Status, lang: Language = "zh") -> str:
    return _L1[status][lang]


def l2_text(status: L2Status, lang: Language = "zh") -> str:
    return _L2[status][lang]


def l3_text(status: L3Status, lang: Language = "zh") -> str:
    return _L3[status][lang]


def bar_text(bar: BarStatus, lang: Language = "zh") -> str:
    return _BAR[bar][lang]


def index_action_text(tone: Literal["bullish", "neutral", "bearish"], lang: Language = "zh") -> str:
    return _INDEX_ACTION[lang][tone]
