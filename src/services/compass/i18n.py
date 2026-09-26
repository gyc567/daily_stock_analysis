# -*- coding: utf-8 -*-
"""i18n labels for the midterm trend compass.

Issue scope: docs/midterm-trend-compass-plan.md §3.1.
Single source for phase / action / L0..L3 / bar status zh-en labels,
plus long-card copy (section titles, principles, guides, reason codes).

Note: reason-code explanations intentionally mirror REASON_TEXT in
apps/dsa-web/src/pages/TrendCompassPage.tsx — the frontend keeps its own
copy for instant rendering; keep the two tables semantically in sync.
"""

from __future__ import annotations

from typing import Literal, Optional

from src.schemas.compass import (
    ActionReasonCode,
    L0Status,
    L1Status,
    L2Status,
    L3Status,
    BarStatus,
    CompassAction,
    ObserveHorizon,
    Phase,
    PositionFilter,
)

Language = Literal["zh", "en"]
_PhaseChange = Literal["up", "down", "flat"]
_Cross = Literal["above", "below", "touched"]
_QualityStatus = Literal["ok", "degraded"]


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


_SECTION_TITLES: dict[int, dict[Language, str]] = {
    1: {"zh": "周线过滤 (L0)", "en": "Weekly Filter (L0)"},
    2: {"zh": "日线阶段与观察量级", "en": "Daily Phase & Observation Horizon"},
    3: {"zh": "年线 / 主趋势段 / 节奏 (L1/L2/L3)", "en": "Annual / Segment / Rhythm (L1/L2/L3)"},
    4: {"zh": "失效条件", "en": "Invalidation Conditions"},
    5: {"zh": "系统动作", "en": "System Action"},
    6: {"zh": "较昨日变化", "en": "Change vs Previous Session"},
    7: {"zh": "风险与数据限制", "en": "Risks & Data Limits"},
    8: {"zh": "其它模块（独立并列）", "en": "Other Modules (Independent)"},
    9: {"zh": "择时信号（日线 L4）", "en": "Timing Signals (Daily L4)"},
}


_SECTION_PRINCIPLE: dict[int, dict[Language, str]] = {
    1: {
        "zh": "只有价格站上 200 周线且 50 周线向上，才允许周线级买入；否则仓位上限逐级收紧。L0 是第一硬过滤器，否决权高于一切日线信号。",
        "en": "Weekly-level buying is allowed only when price holds above the 200-week EMA with the 50-week EMA rising; otherwise the position cap tightens step by step. L0 is the first hard filter and overrides every daily signal.",
    },
    2: {
        "zh": "阶段由日线均线排列与斜率推导，决定这笔交易看多远；观察量级只改变时间窗，不改变方向结论。",
        "en": "The phase is derived from daily EMA alignment and slopes and sets how far this trade can look; the observation horizon only changes the time window, never the directional call.",
    },
    3: {
        "zh": "年线定牛熊底色，主趋势段定持仓资格，节奏层定加减速；三层相互独立，某一层恶化只影响对应动作。",
        "en": "The annual line sets the bull/bear backdrop, the segment decides holding eligibility, and the rhythm layer governs acceleration; the layers are independent, and deterioration in one only affects its own action.",
    },
    4: {
        "zh": "以下任一条件触发，本卡结论即刻作废，需等待下一根已确认 K 线重新评估。",
        "en": "If any condition below triggers, this card's conclusions are void immediately; wait for the next confirmed bar before re-evaluating.",
    },
    5: {
        "zh": "动作由阶段结论经硬约束重写得出；约束只负责否决或降级，不会把观望升级成买入。",
        "en": "The action is the phase verdict passed through hard constraints; constraints can only veto or downgrade, never upgrade watch into buy.",
    },
    6: {
        "zh": "与上一交易日已确认快照对比，仅展示阶段与层级变化，不追溯更早历史。",
        "en": "Compared against the latest confirmed snapshot of the previous session; only phase and layer changes are shown, no deeper history.",
    },
    7: {
        "zh": "样本量不足或数据陈旧时，对应层级标记为「-」并自动降级结论，宁缺毋滥。",
        "en": "When samples are insufficient or data is stale, the affected layer is marked \"-\" and its conclusion is downgraded — missing data beats wrong data.",
    },
    8: {
        "zh": "缠论、波浪等其它模块与本罗盘互不读取；结论冲突时以各自模块的免责声明为准。",
        "en": "Chan theory, Elliott wave and other modules do not read the compass and vice versa; when conclusions conflict, each module's own disclaimer governs.",
    },
}


_L0_VERDICT: dict[L0Status, dict[Language, str]] = {
    "weekly_bull": {
        "zh": "周线多头结构，允许在仓位上限内执行买入",
        "en": "Weekly bull structure; buying allowed within the position cap",
    },
    "weekly_bear": {
        "zh": "过滤器否决新建买入",
        "en": "Filter vetoes fresh buying",
    },
    "weekly_transition": {
        "zh": "周线方向未定，买入一律降级为观望",
        "en": "Weekly direction undecided; buys downgraded to watch",
    },
    "weekly_disabled": {
        "zh": "周线样本不足，本层不参与决策",
        "en": "Insufficient weekly samples; layer excluded from decisions",
    },
}


_POSITION_CAP: dict[PositionFilter, dict[Language, str]] = {
    "full": {"zh": "允许重仓波段", "en": "Full position allowed"},
    "half": {"zh": "半仓上限", "en": "Half position cap"},
    "none": {"zh": "禁止买入", "en": "No buying allowed"},
}


_POSITION_GUIDE: dict[PositionFilter, dict[Language, str]] = {
    "full": {
        "zh": "仓位上限=允许重仓波段：回调至关键均线企稳可分批介入；触发第 4 节失效条件即离场。",
        "en": "Cap = full position allowed: scale in on pullbacks that stabilize at key EMAs; exit once any §4 invalidation triggers.",
    },
    "half": {
        "zh": "仓位上限=半仓：只做波段不加仓，留一半资金应对失效；突破确认后再评估上调。",
        "en": "Cap = half position: trade the range without adding; keep the other half for invalidation risk; reassess only on a confirmed breakout.",
    },
    "none": {
        "zh": "仓位上限=禁止买入：空仓者等待周线重新转多；持仓者按第 4 节失效条件离场。",
        "en": "Cap = no buying: stay flat until the weekly filter turns bullish again; holders exit per §4 invalidation.",
    },
}


_HORIZON: dict[ObserveHorizon, dict[Language, str]] = {
    "1w": {"zh": "执行窗：未来 1 周", "en": "Execution window: 1 week"},
    "2w": {"zh": "节奏窗：未来 2 周", "en": "Rhythm window: 2 weeks"},
    "1m": {"zh": "主趋势窗：未来 1 个月", "en": "Segment window: 1 month"},
}


_HORIZON_GUIDE: dict[ObserveHorizon, dict[Language, str]] = {
    "1w": {
        "zh": "信号有效期约 1 周，到期需重新评估，不隔夜恋战。",
        "en": "Signal valid for ~1 week; re-evaluate on expiry instead of holding on.",
    },
    "2w": {
        "zh": "按 2 周节奏跟踪，中途不追涨杀跌。",
        "en": "Track on a 2-week rhythm; no chasing or panic moves in between.",
    },
    "1m": {
        "zh": "以月度级别持有为主，忽略日内噪音。",
        "en": "Hold at the monthly level; ignore intraday noise.",
    },
}


_CHANGE: dict[_PhaseChange, dict[Language, str]] = {
    "up": {"zh": "转强", "en": "Stronger"},
    "down": {"zh": "转弱", "en": "Weaker"},
    "flat": {"zh": "持平", "en": "Flat"},
}


_CROSS: dict[_Cross, dict[Language, str]] = {
    "above": {"zh": "EMA20 位于 EMA50 上方", "en": "EMA20 above EMA50"},
    "below": {"zh": "EMA20 位于 EMA50 下方", "en": "EMA20 below EMA50"},
    "touched": {"zh": "EMA20 与 EMA50 刚接触", "en": "EMA20 touching EMA50"},
}


_QUALITY: dict[_QualityStatus, dict[Language, str]] = {
    "ok": {"zh": "正常", "en": "OK"},
    "degraded": {"zh": "降级", "en": "Degraded"},
}


# Mirrors REASON_TEXT in apps/dsa-web/src/pages/TrendCompassPage.tsx; keep in sync.
_REASON: dict[ActionReasonCode, dict[Language, str]] = {
    "data_missing": {"zh": "数据缺失或停滞，降级为观望", "en": "Data missing or stale; downgraded to watch"},
    "intraday_unconfirmed_buy_blocked": {"zh": "盘中 K 线未确认，禁止新建买入（T+1 无纠错权）", "en": "Unconfirmed intraday bar; fresh buys blocked (T+1)"},
    "weekly_bear_buy_blocked": {"zh": "周线空头结构，过滤器不允许买入", "en": "Weekly bear structure; buying blocked by filter"},
    "weekly_transition_buy_blocked": {"zh": "周线转换期降级（预留）", "en": "Weekly transition downgrade (reserved)"},
    "l1_disabled_buy_blocked": {"zh": "年线样本不足，不信任趋势扩张", "en": "L1 sample too small; trend expansion not trusted"},
    "coiling_transitioning_buy_downgraded": {"zh": "收敛/切换阶段，买入降级为观望", "en": "Coiling/transitioning phase; buy downgraded to watch"},
    "tiring_buy_downgraded": {"zh": "趋势疲惫阶段，不追买", "en": "Trend tiring; no chasing buys"},
    "resting_sell_blocked": {"zh": "主趋势段休整而非反转，禁止卖出", "en": "Segment resting, not reversing; sell blocked"},
    "l2_broken_bear_allow_sell": {"zh": "空头结构破坏，允许离场", "en": "Bearish structure broken; exit allowed"},
    "l2_broken_bull_sell_blocked": {"zh": "多头段内结构破坏，禁止恐慌卖出", "en": "Break inside bull segment; panic sell blocked"},
    "l1_l2_bear_sell_default": {"zh": "年线+趋势段双空头，默认卖出", "en": "Double-bear (L1+L2); default sell"},
    "l3_exhausted_sell_downgraded": {"zh": "节奏已失配，卖出降级为观望", "en": "Rhythm exhausted; sell downgraded to watch"},
    "l1_l2_l3_healthy_buy_allowed": {"zh": "全多头健康结构，屏蔽与趋势冲突的卖出", "en": "Healthy full-bull stack; trend-fighting sell blocked"},
    "market_guardrail_softened": {"zh": "大盘环境护栏已软化买入", "en": "Market-context guardrail softened the buy"},
    "phase_guardrail_suppressed": {"zh": "交易时段护栏已压制动作", "en": "Phase guardrail suppressed the action"},
    "weekly_bear_bottom_fishing_pass": {"zh": "周线空头下的超卖抄底信号放行：属逆势博弈仓，轻仓严格止损", "en": "Oversold bottom-fishing signal passes under weekly bear: counter-trend sleeve, light position with hard stop"},
    "bottom_fishing_time_stop": {"zh": "纪律：硬止损按失效价执行，另设 5 个交易日时间止损，不反弹即离场", "en": "Discipline: hard stop at the invalidation price plus a 5-trading-day time stop; exit if no rebound"},
    "top_escape_exhaustion": {"zh": "超买衰竭：RSI 升至 75 以上且 EMA20 斜率转负，上攻动能衰竭", "en": "Overbought exhaustion: RSI above 75 with the EMA20 slope turning negative; upside momentum spent"},
    "top_escape_divergence": {"zh": "顶背离：价格新高但 RSI 高点下移，动能与价格背离", "en": "Bearish divergence: price makes a new high while the RSI high shifts down"},
    "top_escape_ema_loss": {"zh": "跌破 EMA20：收盘破位且斜率转负、RSI 跌出强势区，趋势转弱确认", "en": "EMA20 lost: close below the EMA20 with a negative slope and RSI out of the strong zone"},
}


_DISCLAIMER: dict[Language, str] = {
    "zh": "本模块不提供无约束的短期价格预测；择时信号为条件触发的交易计划（触发价+失效价），受趋势结构门控。",
    "en": "This module makes no unconstrained short-term price predictions; timing signals are condition-triggered trade plans (trigger + invalidation price) gated by trend structure.",
}


_TIMING_TYPE: dict[str, dict[Language, str]] = {
    "pullback_entry": {"zh": "顺势入场（回踩企稳）", "en": "Pullback entry"},
    "bottom_fishing": {"zh": "超卖抄底", "en": "Bottom fishing"},
    "top_escape": {"zh": "高位逃顶", "en": "Top escape"},
}


_TIMING_STATUS: dict[str, dict[Language, str]] = {
    "armed": {"zh": "观察中（条件未齐）", "en": "Armed (conditions incomplete)"},
    "triggered": {"zh": "已触发（收盘确认）", "en": "Triggered (confirmed close)"},
}


_POSITION_HINT: dict[str, dict[Language, str]] = {
    "light": {"zh": "轻仓（≤1 成，博弈仓）", "en": "Light (≤10%, speculative sleeve)"},
    "medium": {"zh": "中等仓位（按计划仓位减半）", "en": "Medium (half of planned size)"},
    "full": {"zh": "按仓位上限执行", "en": "Full (up to the position cap)"},
}


_CARD_LABELS: dict[Language, dict[str, str]] = {
    "zh": {
        "as_of": "数据截至",
        "w50": "50周线",
        "w200": "200周线",
        "weekly_samples": "周K样本",
        "daily_samples": "日线样本",
        "close": "收盘",
        "slopes": "斜率",
        "phase": "阶段",
        "horizon": "观察量级",
        "l1": "L1 年线",
        "l2": "L2 主趋势段",
        "l3": "L3 节奏",
        "cap": "仓位上限",
        "prev_date": "上一交易日",
        "phase_chg": "阶段变化",
        "l0_chg": "周线变化",
        "l2_chg": "主趋势段变化",
        "bar_status": "K线状态",
        "quality": "数据状态",
        "triggered": "触发约束",
        "no_snapshot": "（无上一交易日已确认快照，本节留空）",
        "no_constraints": "未命中任何硬约束，初稿原样通过。",
        "no_draft": "未指定初稿动作，本节为罗盘默认中性结论。",
        "disclaimer": "免责声明",
        "no_timing": "当前无择时信号",
        "timing_trigger": "触发价",
        "timing_invalidate": "失效价",
        "timing_horizon": "有效期",
        "timing_days_unit": "个交易日",
        "timing_countertrend": "逆势博弈仓：与趋势仓位分开管理，轻仓、硬止损、到期离场。",
        "timing_principle": "择时信号是条件触发的交易计划，非价格预测：触发价是计划生效参考，跌破失效价立即作废，不补仓不扛单。",
    },
    "en": {
        "as_of": "As of",
        "w50": "50W EMA",
        "w200": "200W EMA",
        "weekly_samples": "Weekly",
        "daily_samples": "Daily",
        "close": "Close",
        "slopes": "Slopes",
        "phase": "Phase",
        "horizon": "Horizon",
        "l1": "L1 Annual",
        "l2": "L2 Segment",
        "l3": "L3 Rhythm",
        "cap": "Position cap",
        "prev_date": "Previous session",
        "phase_chg": "Phase change",
        "l0_chg": "Weekly change",
        "l2_chg": "Segment change",
        "bar_status": "Bar status",
        "quality": "Data status",
        "triggered": "Triggered constraints",
        "no_snapshot": "(No confirmed snapshot from the previous session; this section is empty)",
        "no_constraints": "No hard constraint triggered; the draft passes through unchanged.",
        "no_draft": "No draft action supplied; this section shows the compass default neutral verdict.",
        "disclaimer": "Disclaimer",
        "no_timing": "No timing signals currently",
        "timing_trigger": "Trigger",
        "timing_invalidate": "Invalidation",
        "timing_horizon": "Valid for",
        "timing_days_unit": "trading days",
        "timing_countertrend": "Counter-trend sleeve: separate from trend positions; light size, hard stop, exit on expiry.",
        "timing_principle": "Timing signals are condition-triggered trade plans, not price predictions: the trigger is the reference entry, the plan is void once the invalidation price trades — no averaging down, no holding through stops.",
    },
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


def section_title(num: int, lang: Language = "zh") -> str:
    return _SECTION_TITLES[num][lang]


def section_principle(num: int, lang: Language = "zh") -> str:
    return _SECTION_PRINCIPLE[num][lang]


def l0_verdict(status: L0Status, lang: Language = "zh") -> str:
    return _L0_VERDICT[status][lang]


def position_cap(pf: PositionFilter, lang: Language = "zh") -> str:
    return _POSITION_CAP[pf][lang]


def position_guide(pf: PositionFilter, lang: Language = "zh") -> str:
    return _POSITION_GUIDE[pf][lang]


def horizon_text(horizon: ObserveHorizon, lang: Language = "zh") -> str:
    return _HORIZON[horizon][lang]


def horizon_guide(horizon: ObserveHorizon, lang: Language = "zh") -> str:
    return _HORIZON_GUIDE[horizon][lang]


def change_text(change: _PhaseChange, lang: Language = "zh") -> str:
    return _CHANGE[change][lang]


def cross_text(cross: Optional[_Cross], lang: Language = "zh") -> str:
    if cross is None:
        return "—" if lang == "zh" else "n/a"
    return _CROSS[cross][lang]


def quality_status_text(status: _QualityStatus, lang: Language = "zh") -> str:
    return _QUALITY[status][lang]


def reason_text(code: ActionReasonCode, lang: Language = "zh") -> str:
    return _REASON[code][lang]


def disclaimer_text(lang: Language = "zh") -> str:
    return _DISCLAIMER[lang]


def card_label(key: str, lang: Language = "zh") -> str:
    return _CARD_LABELS[lang][key]


def timing_type_text(signal_type: str, lang: Language = "zh") -> str:
    return _TIMING_TYPE[signal_type][lang]


def timing_status_text(status: str, lang: Language = "zh") -> str:
    return _TIMING_STATUS[status][lang]


def position_hint_text(hint: str, lang: Language = "zh") -> str:
    return _POSITION_HINT[hint][lang]
