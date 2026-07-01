import type React from 'react';
import { FileText, Loader2, Trash2 } from 'lucide-react';
import { cn } from '../../utils/cn';
import type { KnowledgeDocumentItem } from '../../api/knowledgeBase';

interface KnowledgeDocumentListProps {
  documents: KnowledgeDocumentItem[];
  loading: boolean;
  selectedDocId?: string | null;
  onSelect: (doc: KnowledgeDocumentItem) => void;
  onDelete: (docId: string) => void;
  className?: string;
}

export const KnowledgeDocumentList: React.FC<KnowledgeDocumentListProps> = ({
  documents,
  loading,
  selectedDocId,
  onSelect,
  onDelete,
  className = '',
}) => {
  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 py-8 text-muted-text', className)}>
        <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
        <span>加载中...</span>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className={cn('py-8 text-center text-muted-text', className)}>
        <FileText className="mx-auto mb-2 h-10 w-10 opacity-50" aria-hidden="true" />
        <p>暂无文档</p>
        <p className="mt-1 text-xs">上传文件或粘贴文本创建文档</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      {documents.map((doc) => (
        <div
          key={doc.id}
          role="button"
          tabIndex={0}
          onClick={() => onSelect(doc)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onSelect(doc);
            }
          }}
          className={cn(
            'group cursor-pointer rounded-xl border p-4 transition-colors',
            selectedDocId === doc.id
              ? 'border-cyan/50 bg-cyan/5'
              : 'border-white/8 bg-card/82 hover:border-white/15',
          )}
          aria-selected={selectedDocId === doc.id}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h3 className="truncate font-medium text-foreground">{doc.title}</h3>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-text">
                <span className="rounded bg-white/5 px-1.5 py-0.5">{doc.source_type}</span>
                <span>·</span>
                <span>{doc.chunk_count} chunks</span>
                <span>·</span>
                <span>{new Date(doc.created_at).toLocaleDateString()}</span>
              </div>
              {doc.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {doc.tags.slice(0, 5).map((tag) => (
                    <span
                      key={tag}
                      className="rounded bg-white/5 px-2 py-0.5 text-xs text-secondary-text"
                    >
                      {tag}
                    </span>
                  ))}
                  {doc.tags.length > 5 && (
                    <span className="text-xs text-muted-text">+{doc.tags.length - 5}</span>
                  )}
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(doc.id);
              }}
              aria-label={`删除文档: ${doc.title}`}
              className="rounded p-2 text-muted-text opacity-0 transition-all hover:bg-white/5 hover:text-red-400 focus:opacity-100 group-hover:opacity-100"
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
