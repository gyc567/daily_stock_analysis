import type React from 'react';
import { Copy, Link, Loader2, X } from 'lucide-react';
import { cn } from '../../utils/cn';
import type { KnowledgeDocumentItem } from '../../api/knowledgeBase';

interface KnowledgeChunk {
  content?: string;
  chunk_index?: number;
}

interface KnowledgeDocumentDetailProps {
  document: (KnowledgeDocumentItem & { chunks?: KnowledgeChunk[] }) | null;
  loading: boolean;
  onClose: () => void;
  onCopy: (content: string) => void;
  className?: string;
}

export const KnowledgeDocumentDetail: React.FC<KnowledgeDocumentDetailProps> = ({
  document,
  loading,
  onClose,
  onCopy,
  className = '',
}) => {
  // 不在没有选中文档且不在 loading 时渲染（避免 backdrop 阻挡页面交互）
  if (!document && !loading) return null;

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4',
        className,
      )}
      role="dialog"
      aria-modal="true"
      aria-labelledby="document-detail-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-white/8 bg-card/95 shadow-soft-card">
        {loading ? (
          <div className="flex items-center justify-center p-12" role="progressbar" aria-label="加载中">
            <Loader2 className="h-8 w-8 animate-spin text-cyan" aria-hidden="true" />
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-start justify-between border-b border-white/5 p-5">
              <div className="min-w-0 flex-1">
                <h2
                  id="document-detail-title"
                  className="truncate text-xl font-bold text-foreground"
                >
                  {document.title}
                </h2>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-text">
                  <span className="rounded bg-cyan/15 px-2 py-0.5 text-cyan">
                    {document.source_type}
                  </span>
                  <span>{document.chunk_count} chunks</span>
                  <span>·</span>
                  <span>{new Date(document.created_at).toLocaleDateString()}</span>
                  {document.updated_at !== document.created_at && (
                    <>
                      <span>·</span>
                      <span>更新于 {new Date(document.updated_at).toLocaleDateString()}</span>
                    </>
                  )}
                </div>
                {document.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {document.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded bg-white/5 px-2 py-0.5 text-xs text-secondary-text"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="关闭"
                className="ml-4 shrink-0 rounded-lg p-2 text-muted-text hover:bg-white/5 hover:text-secondary-text focus:outline-none focus:ring-2 focus:ring-cyan/50"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>

            {/* Source URL */}
            {document.source_url && (
              <div className="border-b border-white/5 px-5 py-3">
                <a
                  href={document.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-cyan hover:underline"
                >
                  <Link className="h-4 w-4" aria-hidden="true" />
                  <span className="truncate max-w-md">{document.source_url}</span>
                </a>
              </div>
            )}

            {/* Content */}
            <div className="max-h-[calc(85vh-200px)] overflow-y-auto p-5">
              {document.chunks && document.chunks.length > 0 ? (
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-secondary-text">内容</h3>
                  {document.chunks.map((chunk, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-white/8 bg-white/2 p-4"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="min-w-0 flex-1 whitespace-pre-wrap text-sm text-secondary-text">
                          {chunk.content}
                        </p>
                        <button
                          type="button"
                          onClick={() => onCopy(chunk.content || '')}
                          aria-label="复制内容"
                          className="shrink-0 rounded p-1.5 text-muted-text hover:bg-white/5 hover:text-secondary-text focus:outline-none focus:ring-2 focus:ring-cyan/50"
                        >
                          <Copy className="h-4 w-4" aria-hidden="true" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-muted-text">暂无内容</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
