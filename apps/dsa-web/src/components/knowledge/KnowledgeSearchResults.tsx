import type React from 'react';
import { AlertCircle, Copy, Info, Loader2, Search } from 'lucide-react';
import { cn } from '../../utils/cn';
import type { KnowledgeSearchResponse } from '../../api/knowledgeBase';

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
  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 py-8 text-muted-text', className)}>
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
        <span>搜索中...</span>
      </div>
    );
  }

  if (!query.trim()) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12 text-muted-text', className)}>
        <Search className="mb-3 h-12 w-12 opacity-50" aria-hidden="true" />
        <p className="text-center">输入关键词搜索知识库</p>
        <p className="mt-1 text-center text-xs">
          支持股票代码、行业、主题等关键词
        </p>
      </div>
    );
  }

  if (results && !results.available) {
    return (
      <div className={cn('rounded-xl border border-red-500/30 bg-red-500/10 p-4', className)}>
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" aria-hidden="true" />
          <div>
            <p className="font-medium text-red-400">搜索暂不可用</p>
            <p className="mt-1 text-sm text-red-300/80">{results.message || '服务暂时不可用，请稍后重试'}</p>
          </div>
        </div>
      </div>
    );
  }

  if (results && results.hits.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12 text-muted-text', className)}>
        <Info className="mb-3 h-12 w-12 opacity-50" aria-hidden="true" />
        <p className="text-center">未找到相关文档</p>
        <p className="mt-1 text-center text-xs">
          尝试其他关键词，或上传相关文档
        </p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-12 text-muted-text', className)}>
        <Search className="mb-3 h-12 w-12 opacity-50" aria-hidden="true" />
        <p className="text-center">输入关键词搜索知识库</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center gap-2">
        <Search className="h-5 w-5 text-cyan" aria-hidden="true" />
        <h2 className="text-lg font-semibold">搜索结果</h2>
        <span className="text-sm text-muted-text">{results.total} 个结果</span>
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
                  相似度 {Math.round(hit.score * 100)}%
                </span>
                <span className="rounded bg-white/5 px-2 py-0.5 text-xs text-muted-text">
                  {hit.source_type}
                </span>
                {hit.validation_status && (
                  <span className="rounded bg-white/5 px-2 py-0.5 text-xs text-secondary-text">
                    {hit.validation_status}
                  </span>
                )}
              </div>
              {hit.source_url && (
                <a
                  href={hit.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 block text-xs text-cyan hover:underline"
                >
                  {hit.source_url}
                </a>
              )}
            </div>
            <button
              type="button"
              onClick={() => onCopy(hit.content)}
              aria-label="复制内容"
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
