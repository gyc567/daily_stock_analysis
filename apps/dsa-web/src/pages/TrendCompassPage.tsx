import { useState } from 'react';
import { AppPage, Badge, Button, Card, EmptyState, Loading, PageHeader } from '../components/common';
import { ReportMarkdownBody } from '../components/report/ReportMarkdownBody';
import { StockAutocomplete } from '../components/StockAutocomplete';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { trendCompassApi } from '../api/trendCompass';
import type { CompassAction, CompassAnalyzeResult } from '../api/trendCompass';
import { cn } from '../utils/cn';

type Lang = 'zh' | 'en';

// Domain labels are contract enums (plan v2 §8), kept zh/en side by side (§13.6).
const ACTION_TEXT: Record<CompassAction, Record<Lang, string>> = {
  buy: { zh: '买入', en: 'Buy' },
  watch: { zh: '观望', en: 'Watch' },
  sell: { zh: '卖出', en: 'Sell' },
};

const ACTION_CLASS: Record<CompassAction, string> = {
  buy: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  watch: 'border-amber-500/50 bg-amber-500/10 text-amber-600 dark:text-amber-400',
  sell: 'border-rose-500/50 bg-rose-500/10 text-rose-600 dark:text-rose-400',
};

const LAYER_TEXT: Record<string, Record<Lang, string>> = {
  weekly_bull: { zh: '周线多头', en: 'Weekly bull' },
  weekly_bear: { zh: '周线空头', en: 'Weekly bear' },
  weekly_transition: { zh: '周线转换', en: 'Weekly transition' },
  weekly_disabled: { zh: '周线样本不足', en: 'Weekly disabled' },
  annual_bull: { zh: '年线多头', en: 'Annual bull' },
  annual_bear: { zh: '年线空头', en: 'Annual bear' },
  annual_transition: { zh: '年线转换', en: 'Annual transition' },
  annual_disabled: { zh: '年线样本不足', en: 'Annual disabled' },
  alive: { zh: '趋势段仍在', en: 'Alive' },
  resting: { zh: '休整（回踩/反抽）', en: 'Resting' },
  flattening: { zh: '收口', en: 'Flattening' },
  broken: { zh: '结构破坏', en: 'Broken' },
  healthy: { zh: '节奏健康', en: 'Healthy' },
  cooling: { zh: '节奏降温', en: 'Cooling' },
  exhausted: { zh: '节奏失配', en: 'Exhausted' },
  noisy: { zh: '数据嘈杂', en: 'Noisy' },
};

const PHASE_TEXT: Record<string, Record<Lang, string>> = {
  trend_expanding: { zh: '趋势扩张', en: 'Trend expanding' },
  trend_holding: { zh: '趋势持有', en: 'Trend holding' },
  trend_tiring: { zh: '趋势疲惫', en: 'Trend tiring' },
  coiling: { zh: '收敛蓄力', en: 'Coiling' },
  transitioning: { zh: '阶段切换', en: 'Transitioning' },
};

const BAR_STATUS_TEXT: Record<string, Record<Lang, string>> = {
  closed: { zh: '收盘确认', en: 'Closed bar' },
  intraday_unconfirmed: { zh: '盘中未确认', en: 'Intraday unconfirmed' },
  stale: { zh: '数据停滞', en: 'Stale' },
  suspended: { zh: '停牌', en: 'Suspended' },
};

const POSITION_TEXT: Record<string, Record<Lang, string>> = {
  full: { zh: '允许重仓波段', en: 'Full position allowed' },
  half: { zh: '半仓上限', en: 'Half position cap' },
  none: { zh: '禁止买入', en: 'No buying allowed' },
};

const HORIZON_TEXT: Record<string, Record<Lang, string>> = {
  '1w': { zh: '执行窗：未来 1 周', en: 'Execution window: 1 week' },
  '2w': { zh: '节奏窗：未来 2 周', en: 'Rhythm window: 2 weeks' },
  '1m': { zh: '主趋势窗：未来 1 个月', en: 'Segment window: 1 month' },
};

// Reason-code chain copy for the rewrite panel. Mirrors the backend i18n
// _REASON table (src/services/compass/i18n.py); kept here for instant
// rendering — keep the two semantically in sync.
const REASON_STEP_TEXT: Record<string, Record<Lang, { title: string; detail: string }>> = {
  data_missing: {
    zh: { title: '数据缺失或停滞', detail: '行情数据不可用，按最保守处理，降级为观望' },
    en: { title: 'Data missing or stale', detail: 'Market data unusable; downgraded to watch as the conservative fallback' },
  },
  intraday_unconfirmed_buy_blocked: {
    zh: { title: '盘中 K 线未收盘确认', detail: 'T+1 制度下盘中买入没有纠错权，否决新建买入' },
    en: { title: 'Intraday bar unconfirmed', detail: 'Under T+1 an intraday buy cannot be corrected; fresh buys blocked' },
  },
  weekly_bear_buy_blocked: {
    zh: { title: '周线空头结构', detail: '价格仍在 200 周线之下，周线过滤器否决新建买入' },
    en: { title: 'Weekly bear structure', detail: 'Price holds below the 200-week EMA; the weekly filter vetoes fresh buying' },
  },
  weekly_transition_buy_blocked: {
    zh: { title: '周线转换期', detail: '周线方向未定，买入降级（预留规则）' },
    en: { title: 'Weekly transition', detail: 'Weekly direction undecided; buys downgraded (reserved rule)' },
  },
  l1_disabled_buy_blocked: {
    zh: { title: '年线样本不足', detail: '样本不够，不信任趋势扩张，否决买入' },
    en: { title: 'Annual line sample too small', detail: 'Insufficient samples to trust trend expansion; buys blocked' },
  },
  coiling_transitioning_buy_downgraded: {
    zh: { title: '阶段处于收敛/切换', detail: '此阶段方向未明，不追买，买入降级为观望' },
    en: { title: 'Coiling / transitioning phase', detail: 'Direction unclear in this phase; no chasing, buys downgraded to watch' },
  },
  tiring_buy_downgraded: {
    zh: { title: '趋势动能疲惫', detail: '上涨动能先弱，不追买，买入降级为观望' },
    en: { title: 'Trend tiring', detail: 'Momentum weakening first; no chasing, buys downgraded to watch' },
  },
  resting_sell_blocked: {
    zh: { title: '主趋势段只是休整', detail: '休整是回踩而非反转，否决卖出' },
    en: { title: 'Segment merely resting', detail: 'A pullback is not a reversal; sells blocked' },
  },
  l2_broken_bear_allow_sell: {
    zh: { title: '空头结构破坏', detail: '年线为空、主趋势段破坏且当日收盘确认，允许离场' },
    en: { title: 'Bearish structure broken', detail: 'Annual bear + segment broken + confirmed close; exit allowed' },
  },
  l2_broken_bull_sell_blocked: {
    zh: { title: '多头段内正常回调', detail: '破坏发生在多头段内部，属于回调而非反转，否决恐慌卖出' },
    en: { title: 'Pullback inside a bull segment', detail: 'The break is a pullback, not a reversal; panic sells blocked' },
  },
  l1_l2_bear_sell_default: {
    zh: { title: '年线与趋势段双空头', detail: '双重空头结构，默认卖出' },
    en: { title: 'Double bear (annual + segment)', detail: 'Dual-bear structure; default to sell' },
  },
  l3_exhausted_sell_downgraded: {
    zh: { title: '节奏已失配', detail: '节奏层不支持顺势卖出，卖出降级为观望' },
    en: { title: 'Rhythm exhausted', detail: 'The rhythm layer does not support selling; sell downgraded to watch' },
  },
  l1_l2_l3_healthy_buy_allowed: {
    zh: { title: '全多头健康结构', detail: '三层全多头，屏蔽与趋势冲突的卖出' },
    en: { title: 'Healthy full-bull stack', detail: 'All three layers bullish; trend-fighting sells blocked' },
  },
  market_guardrail_softened: {
    zh: { title: '大盘环境护栏', detail: '大盘环境不佳，已软化买入动作' },
    en: { title: 'Market-context guardrail', detail: 'Weak market context softened the buy' },
  },
  phase_guardrail_suppressed: {
    zh: { title: '交易时段护栏', detail: '当前交易时段不支持该动作，已压制' },
    en: { title: 'Phase guardrail', detail: 'The current trading phase does not support the action; suppressed' },
  },
  bottom_fishing_time_stop: {
    zh: { title: '时间止损纪律', detail: '硬止损按失效价执行，另设 5 个交易日时间止损，不反弹即离场' },
    en: { title: 'Time-stop discipline', detail: 'Hard stop at the invalidation price plus a 5-trading-day time stop: exit if no bounce' },
  },
  weekly_bear_bottom_fishing_pass: {
    zh: { title: '空头下抄底放行', detail: '周线空头下的超卖抄底信号放行：属逆势博弈仓，轻仓严格止损，与趋势仓位分开管理；仅解除周线否决，阶段/样本等其余硬约束照常生效' },
    en: { title: 'Bottom-fishing pass under weekly bear', detail: 'Oversold bottom-fishing signal passes under weekly bear: a counter-trend sleeve, light size with strict stops, managed apart from trend positions; only the weekly veto is lifted — phase/sample hard constraints still apply' },
  },
  top_escape_exhaustion: {
    zh: { title: '超买衰竭', detail: 'RSI 升至 75 以上且 EMA20 斜率转负，上攻动能衰竭' },
    en: { title: 'Overbought exhaustion', detail: 'RSI above 75 with the EMA20 slope turning negative; upside momentum spent' },
  },
  top_escape_divergence: {
    zh: { title: '顶背离', detail: '价格新高但 RSI 高点下移，动能与价格背离' },
    en: { title: 'Bearish divergence', detail: 'Price makes a new high while the RSI high shifts down' },
  },
  top_escape_ema_loss: {
    zh: { title: '跌破 EMA20', detail: '收盘跌破 EMA20 且斜率转负、RSI 跌出强势区，趋势转弱确认' },
    en: { title: 'EMA20 lost', detail: 'Close below the EMA20 with a negative slope and RSI out of the strong zone' },
  },
};

// L4 timing signal labels (plan §13.8); mirrors backend i18n timing tables.
const TIMING_TYPE_TEXT: Record<string, Record<Lang, string>> = {
  pullback_entry: { zh: '顺势回踩入场', en: 'Pullback entry' },
  bottom_fishing: { zh: '超卖抄底', en: 'Bottom fishing' },
  top_escape: { zh: '高位逃顶', en: 'Top escape' },
};

const TIMING_STATUS_TEXT: Record<string, Record<Lang, string>> = {
  armed: { zh: '待触发', en: 'Armed' },
  triggered: { zh: '已触发', en: 'Triggered' },
};

const POSITION_HINT_TEXT: Record<string, Record<Lang, string>> = {
  light: { zh: '轻仓', en: 'Light size' },
  medium: { zh: '中等仓位', en: 'Medium size' },
  full: { zh: '仓位上限内', en: 'Within position cap' },
};

const LAYER_HEADINGS: { key: 'weekly' | 'annual' | 'segment' | 'rhythm'; zh: string; en: string }[] = [
  { key: 'weekly', zh: 'L0 周线过滤', en: 'L0 Weekly filter' },
  { key: 'annual', zh: 'L1 年线（半年-一年）', en: 'L1 Annual filter' },
  { key: 'segment', zh: 'L2 主趋势段（1-3 个月）', en: 'L2 Segment (1-3 months)' },
  { key: 'rhythm', zh: 'L3 节奏（2-6 周）', en: 'L3 Rhythm (2-6 weeks)' },
];

const EXAMPLE_CODES = ['600519', '300750', '002594', 'sh000300'];

const fmt = (value: number | null | undefined, digits = 2): string =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—';

export default function TrendCompassPage() {
  const { t, language } = useUiLanguage();
  const lang: Lang = language === 'en' ? 'en' : 'zh';
  const [query, setQuery] = useState('');
  const [selectedName, setSelectedName] = useState<string | undefined>(undefined);
  const [draft, setDraft] = useState<CompassAction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CompassAnalyzeResult | null>(null);

  const analyze = async (code: string, name?: string) => {
    const normalized = code.trim();
    if (!normalized || loading) return;
    setLoading(true);
    setError(null);
    try {
      const data = await trendCompassApi.analyze({
        code: normalized,
        stockName: name ?? selectedName,
        draftAction: draft,
        lang,
      });
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const compass = result?.compass;
  // 防御旧后端/异常 payload：老版本 API 可能不下发 timing 字段。
  const timing = compass?.timing ?? [];
  const finalAction: CompassAction | null = result?.rewrite?.final_action ?? null;
  const rewriteSteps = result?.rewrite?.steps ?? [];

  return (
    <AppPage>
      <PageHeader
        title={t('layout.nav.trendCompass')}
        description={t('trendCompass.subtitle')}
      />

      <Card className="mt-4">
        <div className="flex flex-col gap-3">
          <StockAutocomplete
            value={query}
            onChange={setQuery}
            onSubmit={(code, name) => {
              setSelectedName(name);
              setQuery(code);
              void analyze(code, name);
            }}
            disabled={loading}
            placeholder={t('trendCompass.inputPlaceholder')}
          />
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-secondary-text">{t('trendCompass.draftLabel')}</span>
            {([null, 'buy', 'watch', 'sell'] as const).map((option) => (
              <button
                key={option ?? 'none'}
                type="button"
                onClick={() => setDraft(option)}
                className={cn(
                  'rounded-full border px-3 py-1 text-xs transition-colors',
                  draft === option
                    ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]'
                    : 'border-border/60 text-secondary-text hover:border-border'
                )}
              >
                {option === null ? t('trendCompass.draftNone') : ACTION_TEXT[option][lang]}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_CODES.map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => {
                  setQuery(code);
                  setSelectedName(undefined);
                  void analyze(code);
                }}
                disabled={loading}
                className="rounded-full border border-border/60 px-3 py-1 text-xs text-secondary-text transition-colors hover:border-border hover:text-foreground"
              >
                {code}
              </button>
            ))}
          </div>
          <div>
            <Button onClick={() => void analyze(query)} disabled={loading || !query.trim()}>
              {loading ? t('trendCompass.analyzing') : t('trendCompass.analyze')}
            </Button>
          </div>
        </div>
      </Card>

      {loading ? <Loading className="mt-8" /> : null}

      {error ? (
        <Card className="mt-4 border-rose-500/40">
          <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>
        </Card>
      ) : null}

      {!loading && !error && !result ? (
        <EmptyState
          className="mt-8"
          title={t('trendCompass.emptyTitle')}
          description={t('trendCompass.emptyHint')}
        />
      ) : null}

      {compass ? (
        <div className="mt-4 flex flex-col gap-4">
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-foreground">
                    {compass.name ?? compass.code}
                  </h2>
                  <span className="text-sm text-secondary-text">{compass.code}</span>
                </div>
                <p className="mt-1 text-xs text-secondary-text">
                  {t('trendCompass.asOf')} {compass.as_of_trade_date} ·{' '}
                  {BAR_STATUS_TEXT[compass.bar_status]?.[lang] ?? compass.bar_status}
                </p>
              </div>
              {finalAction ? (
                <span className={cn('rounded-2xl border px-5 py-2 text-xl font-semibold', ACTION_CLASS[finalAction])}>
                  {ACTION_TEXT[finalAction][lang]}
                </span>
              ) : null}
            </div>
            {compass.quality.limitations.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {compass.quality.limitations.map((item) => (
                  <Badge key={item} variant="warning">{item}</Badge>
                ))}
              </div>
            ) : null}
          </Card>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {LAYER_HEADINGS.map(({ key, zh, en }) => (
              <Card key={key} title={lang === 'en' ? en : zh} padding="sm">
                <p className="text-sm font-medium text-foreground">
                  {LAYER_TEXT[compass[key]]?.[lang] ?? compass[key]}
                </p>
              </Card>
            ))}
          </div>

          <Card title={lang === 'en' ? 'Phase synthesis' : '阶段合成'}>
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-base font-semibold text-foreground">
                {PHASE_TEXT[compass.phase]?.[lang] ?? compass.phase}
              </span>
              <Badge variant="info">{HORIZON_TEXT[compass.observe_horizon]?.[lang] ?? compass.observe_horizon}</Badge>
              <Badge variant="default">{POSITION_TEXT[compass.position_filter]?.[lang] ?? compass.position_filter}</Badge>
            </div>
          </Card>

          {result?.rewrite ? (
            <Card
              title={lang === 'en' ? 'Action rewrite · hard-constraint rules' : '动作改写 · 硬约束规则'}
            >
              {/* 规则表出处（§4.5.2）留在 tooltip，界面不显示文档编号；原始 reason code 也仅在 hover 时可见 */}
              <div title={lang === 'en' ? 'Hard-constraint table: plan §4.5.2' : '规则表出处：设计文档 §4.5.2'}>
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-secondary-text">{lang === 'en' ? 'Draft: ' : '初稿动作：'}</span>
                  <span className={cn('rounded-lg border px-3 py-1', ACTION_CLASS[result.rewrite.initial_action])}>
                    {ACTION_TEXT[result.rewrite.initial_action][lang]}
                  </span>
                </div>
                {rewriteSteps.length > 0 ? (
                  <ol className="mt-3 space-y-2 text-sm">
                    {rewriteSteps.map((step, idx) => {
                      const prev =
                        idx === 0 ? result.rewrite!.initial_action : rewriteSteps[idx - 1].action_after;
                      const info = REASON_STEP_TEXT[step.reason_code]?.[lang];
                      const changed = prev !== step.action_after;
                      const transition = changed
                        ? lang === 'zh'
                          ? `，动作由「${ACTION_TEXT[prev].zh}」改为「${ACTION_TEXT[step.action_after].zh}」`
                          : ` — action changed from ${ACTION_TEXT[prev].en} to ${ACTION_TEXT[step.action_after].en}`
                        : lang === 'zh'
                          ? `，动作维持「${ACTION_TEXT[step.action_after].zh}」`
                          : ` — action stays ${ACTION_TEXT[step.action_after].en}`;
                      return (
                        <li
                          key={`${step.reason_code}-${idx}`}
                          title={step.reason_code}
                          className="flex gap-2"
                        >
                          <span className="shrink-0 font-semibold text-secondary-text">{idx + 1}.</span>
                          <span>
                            <span className="font-medium text-foreground">{info?.title ?? step.reason_code}</span>
                            {info?.detail ? (
                              <span className="text-secondary-text"> —— {info.detail}</span>
                            ) : null}
                            <span className="text-secondary-text">{transition}</span>
                          </span>
                        </li>
                      );
                    })}
                  </ol>
                ) : (
                  <p className="mt-3 text-sm text-secondary-text">
                    {lang === 'en'
                      ? 'No hard constraint triggered; the draft passes through unchanged.'
                      : '未命中任何硬约束，初稿原样通过。'}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3 text-sm">
                  <span className="text-secondary-text">{lang === 'en' ? 'Final: ' : '最终结果：'}</span>
                  <span className={cn('rounded-lg border px-3 py-1', ACTION_CLASS[result.rewrite.final_action])}>
                    {ACTION_TEXT[result.rewrite.final_action][lang]}
                  </span>
                  <Badge variant="default">
                    {lang === 'en' ? 'Conclusion: ' : '投资结论：'}
                    {result.rewrite.investment_action}
                  </Badge>
                </div>
                <p className="mt-2 text-xs text-secondary-text">
                  {lang === 'en' ? 'Basis: ' : '判定依据：'}
                  {[
                    [lang === 'en' ? 'Weekly' : '周线', LAYER_TEXT[compass.weekly]?.[lang] ?? compass.weekly],
                    [lang === 'en' ? 'Annual' : '年线', LAYER_TEXT[compass.annual]?.[lang] ?? compass.annual],
                    [lang === 'en' ? 'Segment' : '主趋势段', LAYER_TEXT[compass.segment]?.[lang] ?? compass.segment],
                    [lang === 'en' ? 'Rhythm' : '节奏', LAYER_TEXT[compass.rhythm]?.[lang] ?? compass.rhythm],
                    [lang === 'en' ? 'Phase' : '阶段', PHASE_TEXT[compass.phase]?.[lang] ?? compass.phase],
                    [lang === 'en' ? 'Bar' : 'K线', BAR_STATUS_TEXT[compass.bar_status]?.[lang] ?? compass.bar_status],
                  ]
                    .map(([k, v]) => `${k}=${v}`)
                    .join(' · ')}
                </p>
              </div>
            </Card>
          ) : null}

          <Card title={lang === 'en' ? 'Timing signals · daily L4' : '择时信号 · 日线 L4'}>
            {/* 择时信号是条件触发的交易计划（触发价+失效价），不是价格预测；§13.8 */}
            {timing.length === 0 ? (
              <p className="text-sm text-secondary-text">
                {lang === 'en'
                  ? 'No timing signals currently. A signal appears only when the daily setup (pullback reset / oversold divergence / overbought exhaustion) aligns with the trend gates.'
                  : '当前无择时信号。仅在日线形态（回踩复位 / 超卖背离 / 超买衰竭）与趋势门控同时满足时出现。'}
              </p>
            ) : (
              <div className="space-y-3">
                {timing.map((signal, idx) => (
                  <div
                    key={`${signal.type}-${idx}`}
                    className="rounded-lg border border-border/60 p-3"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-foreground">
                        {TIMING_TYPE_TEXT[signal.type]?.[lang] ?? signal.type}
                      </span>
                      <Badge
                        variant={signal.status === 'triggered'
                          ? (signal.type === 'top_escape' ? 'danger' : 'success')
                          : 'default'}
                      >
                        {TIMING_STATUS_TEXT[signal.status]?.[lang] ?? signal.status}
                      </Badge>
                      {signal.countertrend ? (
                        <Badge variant="warning">
                          {lang === 'en'
                            ? 'Counter-trend sleeve: separate from trend positions'
                            : '逆势博弈仓：与趋势仓位分开管理'}
                        </Badge>
                      ) : null}
                    </div>
                    {signal.reason_codes.length > 0 ? (
                      <ul className="mt-2 space-y-1 text-sm">
                        {signal.reason_codes.map((code) => {
                          const info = REASON_STEP_TEXT[code]?.[lang];
                          return (
                            <li key={code} title={code} className="text-secondary-text">
                              <span className="font-medium text-foreground">{info?.title ?? code}</span>
                              {info?.detail ? <span> —— {info.detail}</span> : null}
                            </li>
                          );
                        })}
                      </ul>
                    ) : null}
                    <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
                      <div className="flex items-center justify-between border-b border-border/40 pb-1">
                        <dt className="text-secondary-text">{lang === 'en' ? 'Trigger' : '触发价'}</dt>
                        <dd className="font-medium text-foreground">
                          {signal.trigger_price !== null ? fmt(signal.trigger_price) : `—（${TIMING_STATUS_TEXT.armed[lang]}）`}
                        </dd>
                      </div>
                      <div className="flex items-center justify-between border-b border-border/40 pb-1">
                        <dt className="text-secondary-text">{lang === 'en' ? 'Invalidation' : '失效价'}</dt>
                        <dd className="font-medium text-foreground">
                          {signal.invalidation_price !== null ? fmt(signal.invalidation_price) : '—'}
                        </dd>
                      </div>
                      <div className="flex items-center justify-between border-b border-border/40 pb-1">
                        <dt className="text-secondary-text">{lang === 'en' ? 'Valid for' : '有效期'}</dt>
                        <dd className="font-medium text-foreground">
                          {signal.horizon_days} {lang === 'en' ? 'trading days' : '个交易日'}
                        </dd>
                      </div>
                    </dl>
                    <p className="mt-2 text-xs text-secondary-text">
                      {lang === 'en' ? 'Position hint: ' : '仓位提示：'}
                      {POSITION_HINT_TEXT[signal.position_hint]?.[lang] ?? signal.position_hint}
                    </p>
                  </div>
                ))}
                <p className="text-xs text-secondary-text">
                  {lang === 'en'
                    ? 'Timing signals are condition-triggered trade plans, not price predictions: the plan is void once the invalidation price trades — no averaging down, no holding through stops.'
                    : '择时信号是条件触发的交易计划，非价格预测：跌破失效价计划立即作废，不补仓、不扛单。'}
                </p>
              </div>
            )}
          </Card>

          <Card title={lang === 'en' ? 'Indicators' : '指标快照'}>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
              {(
                [
                  ['EMA20', fmt(compass.indicators.ema20)],
                  ['EMA50', fmt(compass.indicators.ema50)],
                  ['EMA100', fmt(compass.indicators.ema100)],
                  ['EMA200', fmt(compass.indicators.ema200)],
                  ['RSI(14)', fmt(compass.indicators.rsi14, 1)],
                  [lang === 'en' ? 'Close' : '收盘价', fmt(compass.indicators.price)],
                  ['EMA20 10d', fmt(compass.indicators.slope_ema20_10d, 3)],
                  ['EMA50 20d', fmt(compass.indicators.slope_ema50_20d, 3)],
                  ['EMA200 40d', fmt(compass.indicators.slope_ema200_40d, 3)],
                ] as const
              ).map(([label, value]) => (
                <div key={label} className="flex items-center justify-between border-b border-border/40 pb-1">
                  <dt className="text-secondary-text">{label}</dt>
                  <dd className="font-medium text-foreground">{value}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 text-xs text-secondary-text">{result?.short_card}</p>
          </Card>

          <Card title={lang === 'en' ? 'Full report' : '完整长卡'}>
            <ReportMarkdownBody content={result?.long_card ?? ''} />
            <p className="mt-4 border-t border-border/40 pt-3 text-xs text-secondary-text">
              {compass.disclaimer}
            </p>
          </Card>
        </div>
      ) : null}
    </AppPage>
  );
}
