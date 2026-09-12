import apiClient from './index';

export type CompassAction = 'buy' | 'watch' | 'sell';
export type DecisionAction = 'buy' | 'add' | 'hold' | 'reduce' | 'sell' | 'watch' | 'avoid' | 'alert';

export interface CompassAnalyzeParams {
  code: string;
  stockName?: string;
  subjectType?: 'stock' | 'etf' | 'index';
  draftAction?: CompassAction | null;
  lang: 'zh' | 'en';
}

export interface CompassData {
  compass_version: string;
  code: string;
  name?: string | null;
  market: string;
  subject_type: string;
  as_of_trade_date: string;
  calculated_at: string;
  bar_status: 'closed' | 'intraday_unconfirmed' | 'stale' | 'suspended';
  quality: {
    sample_size: number;
    weekly_sample_size: number;
    l0_available: boolean;
    l1_available: boolean;
    status: 'ok' | 'degraded';
    limitations: string[];
  };
  indicators: {
    price?: number | null;
    ema20?: number | null;
    ema50?: number | null;
    ema100?: number | null;
    ema200?: number | null;
    rsi14?: number | null;
    slope_ema20_10d?: number | null;
    slope_ema50_20d?: number | null;
    slope_ema200_40d?: number | null;
    cross_ema20_ema50?: 'above' | 'below' | 'touched' | null;
  };
  weekly: string;
  annual: string;
  segment: string;
  rhythm: string;
  phase: string;
  observe_horizon: string;
  position_filter: string;
  risks: string[];
  disclaimer: string;
  timing: TimingSignal[];
}

export type TimingSignalType = 'pullback_entry' | 'bottom_fishing' | 'top_escape';
export type TimingSignalStatus = 'armed' | 'triggered';
export type PositionHint = 'light' | 'medium' | 'full';

export interface TimingSignal {
  type: TimingSignalType;
  status: TimingSignalStatus;
  countertrend: boolean;
  reason_codes: string[];
  trigger_price: number | null;
  invalidation_price: number | null;
  position_hint: PositionHint;
  horizon_days: number;
  as_of_bar_date: string;
}

export interface CompassRewriteStep {
  reason_code: string;
  action_after: CompassAction;
}

export interface CompassRewriteResult {
  initial_action: CompassAction;
  final_action: CompassAction;
  reason_codes: string[];
  steps?: CompassRewriteStep[];
  decision_action: DecisionAction;
  investment_action: string;
}

export interface CompassAnalyzeResult {
  compass: CompassData;
  short_card: string;
  long_card: string;
  rewrite: CompassRewriteResult | null;
}

/**
 * 中期趋势罗盘 API 客户端。
 *
 * 路径前缀 `/api/v1/compass/...`（继承全局 AuthMiddleware）。
 * 手动分析：不写 history、不进 guardrail 链（§13.7 仅 cron 落盘）。
 */
export const trendCompassApi = {
  async analyze(params: CompassAnalyzeParams): Promise<CompassAnalyzeResult> {
    const response = await apiClient.post<CompassAnalyzeResult>('/api/v1/compass/analyze', {
      code: params.code,
      stock_name: params.stockName,
      subject_type: params.subjectType ?? 'stock',
      draft_action: params.draftAction ?? null,
      lang: params.lang,
    });
    return response.data;
  },
};
