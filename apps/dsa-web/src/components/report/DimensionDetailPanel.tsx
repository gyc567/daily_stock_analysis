import React from 'react';
import { Card, Badge } from '../common';
import {
  Link2,
  TrendingUp,
  Wallet,
  LineChart,
  Brain,
  Globe,
  type LucideIcon,
} from 'lucide-react';
import type { ReportLanguage } from '../../types/analysis';
import {
  getReportText,
  normalizeReportLanguage,
  localizeDimensionName,
  localizeEnumInSummary,
  translateSixDimensionEnum,
} from '../../utils/reportLanguage';

interface IndicatorDetail {
  name: string;
  score: number;
  weight: number;
  basis: string;
  confidence?: string;
  summary?: string;
}

interface DimensionDetail {
  dimension: string;
  weight: number;
  score: number;
  indicators?: IndicatorDetail[];
  warnings?: string[];
}

interface DimensionDetailPanelProps {
  dimensions?: DimensionDetail[];
  showIndicators?: boolean;
  reportLanguage?: ReportLanguage;
}

// ============================================================================
// Six-dimension visual identity
// ----------------------------------------------------------------------------
// Each dimension gets a stable color + icon so users can recognize them at a
// glance. Colors are Tailwind tokens (resolved via theme.extend.colors). Use the
// full ring/border/text tokens below for consistent treatment.
// ============================================================================
interface DimensionTheme {
  /** Hex used for the left border, icon background and accent text */
  accent: string;
  /** Tailwind background class — tinted surface for the card */
  surface: string;
  /** Tailwind border class — thin outline to differentiate from background */
  outline: string;
  /** Hover / strong tint variant for the icon chip */
  iconBg: string;
  /** Lucide icon component */
  Icon: LucideIcon;
  /** Short id used as `aria-describedby` for screen readers */
  shortId: string;
}

const DIMENSION_THEMES: Record<string, DimensionTheme> = {
  supplyChain: {
    accent: '#3b82f6', // blue-500
    surface: 'bg-blue-500/5 dark:bg-blue-500/10',
    outline: 'border-blue-500/20 dark:border-blue-500/30',
    iconBg: 'bg-blue-500/15 text-blue-600 dark:text-blue-300',
    Icon: Link2,
    shortId: 'supply-chain',
  },
  fundamental: {
    accent: '#10b981', // emerald-500
    surface: 'bg-emerald-500/5 dark:bg-emerald-500/10',
    outline: 'border-emerald-500/20 dark:border-emerald-500/30',
    iconBg: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-300',
    Icon: TrendingUp,
    shortId: 'fundamental',
  },
  capital: {
    accent: '#f59e0b', // amber-500
    surface: 'bg-amber-500/5 dark:bg-amber-500/10',
    outline: 'border-amber-500/20 dark:border-amber-500/30',
    iconBg: 'bg-amber-500/15 text-amber-600 dark:text-amber-300',
    Icon: Wallet,
    shortId: 'capital',
  },
  technical: {
    accent: '#8b5cf6', // violet-500
    surface: 'bg-violet-500/5 dark:bg-violet-500/10',
    outline: 'border-violet-500/20 dark:border-violet-500/30',
    iconBg: 'bg-violet-500/15 text-violet-600 dark:text-violet-300',
    Icon: LineChart,
    shortId: 'technical',
  },
  sentiment: {
    accent: '#ec4899', // pink-500
    surface: 'bg-pink-500/5 dark:bg-pink-500/10',
    outline: 'border-pink-500/20 dark:border-pink-500/30',
    iconBg: 'bg-pink-500/15 text-pink-600 dark:text-pink-300',
    Icon: Brain,
    shortId: 'sentiment',
  },
  macro: {
    accent: '#64748b', // slate-500
    surface: 'bg-slate-500/5 dark:bg-slate-500/10',
    outline: 'border-slate-500/20 dark:border-slate-500/30',
    iconBg: 'bg-slate-500/15 text-slate-600 dark:text-slate-300',
    Icon: Globe,
    shortId: 'macro',
  },
};

/**
 * Map a backend dimension key to its theme. Falls back to a neutral slate
 * theme when no match is found (e.g. backend adds a new dimension in the
 * future).
 */
function themeForDimension(dimensionKey: string): DimensionTheme {
  if (DIMENSION_THEMES[dimensionKey]) return DIMENSION_THEMES[dimensionKey];
  for (const [k, v] of Object.entries(DIMENSION_THEMES)) {
    if (k === dimensionKey) return v;
  }
  // Match by partial Chinese keyword as a fallback (in case backend renames
  // a dimension, e.g. "基本面与价值" → contains "基本面").
  if (dimensionKey.includes('产业链')) return DIMENSION_THEMES.supplyChain;
  if (dimensionKey.includes('基本面')) return DIMENSION_THEMES.fundamental;
  if (dimensionKey.includes('资金')) return DIMENSION_THEMES.capital;
  if (dimensionKey.includes('技术')) return DIMENSION_THEMES.technical;
  if (dimensionKey.includes('情绪') || dimensionKey.includes('认知'))
    return DIMENSION_THEMES.sentiment;
  if (dimensionKey.includes('宏观') || dimensionKey.includes('地缘'))
    return DIMENSION_THEMES.macro;
  // Last-resort neutral theme (reuses macro colors so the card isn't
  // invisible).
  return DIMENSION_THEMES.macro;
}

/**
 * Pick a palette color for a 0-100 score so the gradient flows through
 * green → amber → red regardless of which dimension we're in.
 */
const SCORE_PALETTE = (score: number): string => {
  if (score >= 75) return 'var(--home-price-up)';
  if (score >= 50) return 'var(--home-accent)';
  if (score >= 25) return 'var(--home-price-flat)';
  return 'var(--home-price-down)';
};

const SCORE_SIGNAL = (score: number): { glyph: string; tone: string } => {
  if (score >= 75) return { glyph: '▲', tone: 'text-[var(--home-price-up)]' };
  if (score >= 50) return { glyph: '◆', tone: 'text-[var(--home-accent)]' };
  if (score >= 25) return { glyph: '–', tone: 'text-[var(--home-price-flat)]' };
  return { glyph: '▼', tone: 'text-[var(--home-price-down)]' };
};

function basisLabel(basis: string, language: ReportLanguage): string {
  const translated = translateSixDimensionEnum(basis, language);
  return translated || basis;
}

const MISSING_SUMMARY_KEYS: Record<ReportLanguage, string> = {
  zh: '数据缺失',
  en: 'Data missing',
};

const isMissingSummary = (summary: string | undefined, language: ReportLanguage) => {
  if (!summary) return false;
  const marker = MISSING_SUMMARY_KEYS[language];
  return summary.includes(marker) || summary.toLowerCase().includes('data missing');
};

interface DimensionCardProps {
  dimension: DimensionDetail;
  theme: DimensionTheme;
  language: ReportLanguage;
  showIndicators: boolean;
  text: ReturnType<typeof getReportText>;
}

const DimensionCard: React.FC<DimensionCardProps> = ({
  dimension,
  theme,
  language,
  showIndicators,
  text,
}) => {
  const label = localizeDimensionName(dimension.dimension, language);
  const indicators = dimension.indicators ?? [];
  const realIndicators = indicators.filter((i) => !isMissingSummary(i.summary, language));
  const missingOnly = indicators.length > 0 && realIndicators.length === 0;
  const Icon = theme.Icon;
  const signal = SCORE_SIGNAL(dimension.score);
  const scoreColor = SCORE_PALETTE(dimension.score);
  // Caption lookup keyed by the theme's stable shortId.
  const caption = (() => {
    const t = text as Record<string, string | undefined>;
    // Match the theme key under cap first word (eg 'supplyChain' -> dimCaptionSupplyChain).
    const map: Record<string, string> = {
      supplyChain: t.dimCaptionSupplyChain ?? '',
      fundamental: t.dimCaptionFundamental ?? '',
      capital: t.dimCaptionCapital ?? '',
      technical: t.dimCaptionTechnical ?? '',
      sentiment: t.dimCaptionSentiment ?? '',
      macro: t.dimCaptionMacro ?? '',
    };
    return map[theme.shortId] ?? '';
  })();

  return (
    <div
      role="article"
      aria-labelledby={`dim-${theme.shortId}`}
      className={`relative overflow-hidden rounded-xl border ${theme.outline} ${theme.surface} pl-4 pr-4 py-4 sm:pl-5 sm:pr-5 sm:py-5`}
    >
      {/* Left accent strip */}
      <span
        aria-hidden
        className="absolute left-0 top-0 h-full w-1 sm:w-1.5"
        style={{ background: theme.accent }}
      />
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${theme.iconBg}`}
            aria-hidden
          >
            <Icon className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h4
                id={`dim-${theme.shortId}`}
                className="text-base font-semibold leading-tight text-foreground"
              >
                {label}
              </h4>
              <Badge variant="default" className="text-[11px] font-medium">
                {text.weightPrefix} {(dimension.weight * 100).toFixed(0)}%
              </Badge>
            </div>
            {caption && (
              <p className="mt-1 text-xs text-muted-text line-clamp-2">{caption}</p>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-0.5 shrink-0" aria-label={text.scoreAriaLabel ?? 'Score'}>
          <div
            className={`font-mono text-2xl font-bold tabular-nums leading-none ${signal.tone}`}
          >
            <span aria-hidden className="text-base align-middle mr-1">
              {signal.glyph}
            </span>
            {dimension.score.toFixed(1)}
          </div>
          <span className="text-[11px] uppercase tracking-wide text-muted-text">/ 100</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-secondary/40 mb-3">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.max(0, Math.min(100, dimension.score))}%`, background: scoreColor }}
        />
      </div>

      {/* Warnings */}
      {dimension.warnings && dimension.warnings.length > 0 && (
        <ul className="mb-3 space-y-1">
          {dimension.warnings.map((w, i) => (
            <li
              key={i}
              className="rounded-md border border-warning/30 bg-warning/10 px-2.5 py-1.5 text-xs text-warning"
            >
              ⚠ {localizeEnumInSummary(w, language)}
            </li>
          ))}
        </ul>
      )}

      {/* Empty state */}
      {missingOnly && (
        <div className="rounded-lg border border-dashed border-border/60 bg-background/60 px-3 py-3 text-xs text-muted-text">
          <p>
            {language === 'zh'
              ? '该维度暂无可用数据，评分仅作参考'
              : 'No data available for this dimension; score is for reference only'}
          </p>
        </div>
      )}

      {/* Indicator grid */}
      {showIndicators && realIndicators.length > 0 && (
        <div>
          <div className="mb-2 flex items-center justify-between text-[11px] uppercase tracking-wider text-muted-text">
            <span>{text.indicatorSplitLabel}</span>
            <span>{realIndicators.length}</span>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {realIndicators.map((ind, idx) => {
              const basis = basisLabel(ind.basis, language);
              const summary =
                localizeEnumInSummary(ind.summary ?? '', language) || ind.summary;
              const indScore = SCORE_SIGNAL(ind.score);
              const indColor = SCORE_PALETTE(ind.score);
              return (
                <div
                  key={idx}
                  className="relative overflow-hidden rounded-lg border border-border/40 bg-background/80 px-3 py-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-sm font-medium text-foreground truncate max-w-full">
                          {localizeEnumInSummary(ind.name ?? '', language)}
                        </span>
                        <Badge variant="default" className="text-[10px]">
                          {basis}
                        </Badge>
                      </div>
                      {ind.confidence && (
                        <span className="text-[10px] text-muted-text">
                          ({ind.confidence} {text.confidenceSuffix})
                        </span>
                      )}
                    </div>
                    <div
                      className={`font-mono text-sm font-bold tabular-nums whitespace-nowrap ${indScore.tone}`}
                      style={{ color: indColor }}
                    >
                      {ind.score.toFixed(1)}
                    </div>
                  </div>
                  {summary && (
                    <p className="mt-1 break-words text-xs leading-relaxed text-muted-text">
                      {summary}
                    </p>
                  )}
                  {/* weight bar */}
                  <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-muted-text">
                    <span className="w-8 shrink-0">
                      {language === 'zh' ? '权重' : 'W'}: {(ind.weight * 100).toFixed(0)}%
                    </span>
                    <div className="h-1 flex-1 overflow-hidden rounded-full bg-secondary/30">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.max(0, Math.min(100, ind.score))}%`,
                          background: indColor,
                        }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export const DimensionDetailPanel: React.FC<DimensionDetailPanelProps> = ({
  dimensions = [],
  showIndicators = true,
  reportLanguage,
}) => {
  const lang = normalizeReportLanguage(reportLanguage);
  const text = getReportText(lang);

  if (dimensions.length === 0) {
    return (
      <Card variant="bordered" padding="md">
        <div className="text-center text-muted-text text-sm py-4">
          {text.noSixDimensionData}
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-foreground">{text.sixDimensionTitle}</h3>
        <div className="text-xs text-muted-text">
          {text.scoreLegend ?? ''}
          <span className="ml-2 inline-flex items-center gap-3">
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-3 rounded-sm bg-[var(--home-price-up)]" />
              <span>{text.scoreStrong ?? 'Strong'}</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-3 rounded-sm bg-[var(--home-accent)]" />
              <span>{text.scoreNeutral ?? 'Neutral'}</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-3 rounded-sm bg-[var(--home-price-down)]" />
              <span>{text.scoreWeak ?? 'Weak'}</span>
            </span>
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {dimensions.map((dim, idx) => (
          <DimensionCard
            key={`${dim.dimension}-${idx}`}
            dimension={dim}
            theme={themeForDimension(dim.dimension)}
            language={lang}
            showIndicators={showIndicators}
            text={text}
          />
        ))}
      </div>
    </div>
  );
};

export default DimensionDetailPanel;
