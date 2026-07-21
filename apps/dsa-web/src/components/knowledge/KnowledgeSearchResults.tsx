import type React from 'react';
import { AlertCircle, Copy, Info, Loader2, Search } from 'lucide-react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';
import type { KnowledgeSearchResponse } from '../../api/knowledgeBase';
import {
  KNOWLEDGE_SOURCE_TYPE_LABELS,
  KNOWLEDGE_TEXT,
  KNOWLEDGE_VALIDATION_STATUS_LABELS,
  formatKnowledgeText,
} from '../../locales/knowledgeText';

interface KnowledgeSearchResultsProps {
  results: KnowledgeSearchResponse | null;
  loading: boolean;
  query: string;
  onCopy: (content: string) => void;
  className?: string;
}

export const KnowledgeSearchResults: React.FC<KnowledgeSearchResultsProps> = ({
  results,
  loading,
  query,
  onCopy,
  className = '',
}) => {
  const { language } = useUiLanguage();
  const text = KNOWLEDGE_TEXT[language];
  const sourceTypeLabels = KNOWLEDGE_SOURCE_TYPE_LABELS[language];
  const validationLabels = KNOWLEDGE_VALIDATION_STATUS_LABELS[language];

  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 py-8 text-muted-text', className)}>
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
        <span>{text.searching}</span>
      </div>
    );
  }

  if (!query.trim()) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12 text-muted-text', className)}>
        <Search className="mb-3 h-12 w-12 opacity-50" aria-hidden="true" />
        <p className="text-center">{text.emptyQueryTitle}</p>
        <p className="mt-1 text-center text-xs">{text.emptyQueryHint}</p>
      </div>
    );
  }

  if (results && !results.available) {
    return (
      <div className={cn('rounded-xl border border-red-500/30 bg-red-500/10 p-4', className)}>
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" aria-hidden="true" />
          <div>
            <p className="font-medium text-red-400">{text.unavailableTitle}</p>
            <p className="mt-1 text-sm text-red-300/80">{results.message || text.unavailableFallback}</p>
          </div>
        </div>
      </div>
    );
  }

  if (results && results.hits.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12 text-muted-text', className)}>
        <Info className="mb-3 h-12 w-12 opacity-50" aria-hidden="true" />
        <p className="text-center">{text.emptyResultsTitle}</p>
        <p className="mt-1 text-center text-xs">{text.emptyResultsHint}</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12 text-muted-text', className)}>
        <Search className="mb-3 h-12 w-12 opacity-50" aria-hidden="true" />
        <p className="text-center">{text.emptyQueryTitle}</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center gap-2">
        <Search className="h-5 w-5 text-cyan" aria-hidden="true" />
        <h2 className="text-lg font-semibold">{text.resultsHeading}</h2>
        <span className="text-sm text-muted-text">
          {formatKnowledgeText(text.resultsCount, { count: results.total })}
        </span>
      </div>

      {results.hits.map((hit) => (
        <div
          key={hit.chunk_id}
          className="rounded-xl border border-white/8 bg-card/82 p-4"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h3 className="truncate font-medium text-foreground">{hit.document_title}</h3>
              <p className="mt-1 text-sm text-muted-text line-clamp-3 whitespace-pre-wrap">
                {hit.content}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="rounded bg-cyan/15 px-2 py-0.5 text-xs text-cyan">
                  {formatKnowledgeText(text.similarity, { percent: Math.round(hit.score * 100) })}
                </span>
                <span className="rounded bg-white/5 px-2 py-0.5 text-xs text-muted-text">
                  {sourceTypeLabels[hit.source_type] ?? hit.source_type}
                </span>
                {hit.validation_status && (
                  <span className="rounded bg-white/5 px-2 py-0.5 text-xs text-secondary-text">
                    {validationLabels[hit.validation_status] ?? hit.validation_status}
                  </span>
                )}
              </div>
              {hit.source_url && (
                <a
                  href={hit.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={text.openSourceLink}
                  className="mt-2 block text-xs text-cyan hover:underline"
                >
                  {hit.source_url}
                </a>
              )}
            </div>
            <button
              type="button"
              onClick={() => onCopy(hit.content)}
              aria-label={text.copyContent}
              className="rounded-lg p-2 text-muted-text hover:bg-white/5 hover:text-secondary-text focus:outline-none focus:ring-2 focus:ring-cyan/50"
            >
              <Copy className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
