import type React from 'react';
import { FileText, Link, Loader2, Search, Upload } from 'lucide-react';
import { cn } from '../../utils/cn';

export type ActiveDialog = 'text' | 'url' | 'upload' | null;

interface KnowledgeToolbarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSearch: () => void;
  searchLoading: boolean;
  documentCount: number;
  onUploadClick: () => void;
  onTextClick: () => void;
  onUrlClick: () => void;
  className?: string;
}

export const KnowledgeToolbar: React.FC<KnowledgeToolbarProps> = ({
  searchQuery,
  onSearchChange,
  onSearch,
  searchLoading,
  documentCount,
  onUploadClick,
  onTextClick,
  onUrlClick,
  className = '',
}) => {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  return (
    <header className={cn('flex-shrink-0', className)}>
      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-text"
            aria-hidden="true"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="搜索知识库..."
            aria-label="搜索知识库"
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-text focus:border-cyan/50 focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={onSearch}
          disabled={searchLoading || !searchQuery.trim()}
          aria-label="搜索"
          className="inline-flex items-center gap-2 rounded-xl bg-cyan px-4 py-2.5 text-sm font-semibold text-black transition-colors hover:bg-cyan/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {searchLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Search className="h-4 w-4" aria-hidden="true" />
          )}
          搜索
        </button>
      </div>

      {/* Action buttons */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onUploadClick}
          aria-label="上传文件"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-secondary-text transition-colors hover:bg-white/5"
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          上传文件
        </button>
        <button
          type="button"
          onClick={onTextClick}
          aria-label="粘贴文本"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-secondary-text transition-colors hover:bg-white/5"
        >
          <FileText className="h-4 w-4" aria-hidden="true" />
          粘贴文本
        </button>
        <button
          type="button"
          onClick={onUrlClick}
          aria-label="从 URL 创建"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-secondary-text transition-colors hover:bg-white/5"
        >
          <Link className="h-4 w-4" aria-hidden="true" />
          从 URL 创建
        </button>

        {/* Document count */}
        <span className="ml-auto text-sm text-muted-text">
          {documentCount} 篇文档
        </span>
      </div>
    </header>
  );
};
