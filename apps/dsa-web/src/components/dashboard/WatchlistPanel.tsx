import type React from 'react';
import { cn } from '../../utils/cn';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { DashboardPanelHeader } from './DashboardPanelHeader';
import { Badge } from '../common/Badge';

export interface WatchlistPanelProps {
  /** Stock codes from STOCK_LIST. Rendered as chips, one per code. */
  codes: string[];
  /** True while the initial watchlist fetch is in flight. */
  isLoading: boolean;
  /** Click a single chip. Default behavior is to fill the search query. */
  onSelect?: (stockCode: string) => void;
  /** Optional trailing node rendered after the chips (e.g. "Analyze all" button). */
  actions?: React.ReactNode;
  className?: string;
  /** Limit how many chips render before collapsing the rest behind a "+N more" chip. */
  maxVisible?: number;
}

/**
 * Compact panel that lists the watchlist (STOCK_LIST) configured on the
 * backend. Each chip maps to one stock code. Clicking a chip hands the
 * code back to the parent (HomePage) to fill the search query and trigger
 * the existing single-stock analysis flow.
 *
 * The panel deliberately does not call the analysis API directly — that
 * would duplicate the `submitAnalysis` store action. It only emits intent.
 */
export const WatchlistPanel: React.FC<WatchlistPanelProps> = ({
  codes,
  isLoading,
  onSelect,
  actions,
  className = '',
  maxVisible = 24,
}) => {
  const { t } = useUiLanguage();
  const visible = codes.slice(0, maxVisible);
  const hidden = Math.max(0, codes.length - visible.length);

  return (
    <section
      data-testid="watchlist-panel"
      className={cn(
        'dashboard-card flex flex-col gap-2 p-3',
        className,
      )}
    >
      <DashboardPanelHeader
        eyebrow={t('home.watchlistEyebrow')}
        title={t('home.watchlistTitle')}
        actions={
          codes.length > 0 ? (
            <span className="text-[11px] text-secondary-text" data-testid="watchlist-count">
              {t('common.itemsCount', { count: codes.length })}
            </span>
          ) : null
        }
      />

      {isLoading ? (
        <p className="text-xs text-secondary-text" role="status" aria-live="polite">
          {t('common.loading')}
        </p>
      ) : codes.length === 0 ? (
        <p className="text-xs text-secondary-text" data-testid="watchlist-empty">
          {t('home.watchlistEmpty')}
        </p>
      ) : (
        <ul
          className="flex flex-wrap gap-1.5"
          data-testid="watchlist-chips"
          aria-label={t('home.watchlistTitle')}
        >
          {visible.map((code) => (
            <li key={code}>
              <button
                type="button"
                onClick={() => onSelect?.(code)}
                className="cursor-pointer rounded-full transition-transform hover:scale-[1.04] focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan/60"
                aria-label={`${t('home.watchlistAnalyze')} ${code}`}
                data-testid="watchlist-chip"
                data-stock-code={code}
              >
                <Badge variant="info" size="sm">{code}</Badge>
              </button>
            </li>
          ))}
          {hidden > 0 ? (
            <li>
              <span
                className="rounded-full border border-border/55 bg-elevated/60 px-2.5 py-1 text-xs text-secondary-text"
                data-testid="watchlist-overflow"
              >
                {t('home.watchlistOverflow', { count: hidden })}
              </span>
            </li>
          ) : null}
        </ul>
      )}

      {actions ? <div className="mt-1 flex items-center gap-2">{actions}</div> : null}
    </section>
  );
};
