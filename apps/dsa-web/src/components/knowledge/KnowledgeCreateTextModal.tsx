import type React from 'react';
import { Loader2, Plus, X } from 'lucide-react';
import { cn } from '../../utils/cn';

interface KnowledgeCreateTextModalProps {
  isOpen: boolean;
  loading: boolean;
  title: string;
  content: string;
  tags: string;
  sourceUrl: string;
  sourceType: 'text' | 'markdown';
  error: string | null;
  onClose: () => void;
  onTitleChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onTagsChange: (value: string) => void;
  onSourceUrlChange: (value: string) => void;
  onSourceTypeChange: (value: 'text' | 'markdown') => void;
  onSubmit: () => void;
}

const MAX_TITLE_LENGTH = 120;
const MAX_CONTENT_LENGTH = 200000;
const MAX_TAGS_COUNT = 20;

export const KnowledgeCreateTextModal: React.FC<KnowledgeCreateTextModalProps> = ({
  isOpen,
  loading,
  title,
  content,
  tags,
  sourceUrl,
  sourceType,
  error,
  onClose,
  onTitleChange,
  onContentChange,
  onTagsChange,
  onSourceUrlChange,
  onSourceTypeChange,
  onSubmit,
}) => {
  if (!isOpen) return null;

  const parsedTags = tags
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean);
  const tagsError = parsedTags.length > MAX_TAGS_COUNT ? `最多 ${MAX_TAGS_COUNT} 个标签` : null;
  const titleError = title.length > MAX_TITLE_LENGTH ? `标题最多 ${MAX_TITLE_LENGTH} 字符` : null;
  const contentError = content.length > MAX_CONTENT_LENGTH ? `内容最多 ${MAX_CONTENT_LENGTH} 字符` : null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!titleError && !contentError && !tagsError && !loading) {
      onSubmit();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-text-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={handleKeyDown}
    >
      <div className="max-h-[85vh] w-full max-w-xl overflow-hidden rounded-2xl border border-white/8 bg-card/95 shadow-soft-card">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/5 p-5">
          <div className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-cyan" aria-hidden="true" />
            <h2 id="create-text-modal-title" className="text-lg font-semibold">创建文档</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="rounded-lg p-2 text-muted-text hover:bg-white/5 hover:text-secondary-text focus:outline-none focus:ring-2 focus:ring-cyan/50"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="max-h-[calc(85vh-80px)] overflow-y-auto p-5">
          <div className="space-y-4">
            {/* Error */}
            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Title */}
            <div>
              <label htmlFor="doc-title" className="mb-1 block text-sm text-secondary-text">
                标题 <span className="text-red-400">*</span>
              </label>
              <input
                id="doc-title"
                type="text"
                value={title}
                onChange={(e) => onTitleChange(e.target.value)}
                placeholder="文档标题"
                maxLength={MAX_TITLE_LENGTH}
                className={cn(
                  'w-full rounded-lg border bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-text focus:outline-none',
                  titleError ? 'border-red-500/50 focus:border-red-500/50' : 'border-white/10 focus:border-cyan/50',
                )}
                aria-invalid={!!titleError}
                aria-describedby={titleError ? 'title-error' : undefined}
              />
              {titleError && (
                <p id="title-error" className="mt-1 text-xs text-red-400">{titleError}</p>
              )}
              <p className="mt-1 text-xs text-muted-text">{title.length}/{MAX_TITLE_LENGTH} 字符</p>
            </div>

            {/* Content type & Tags */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="doc-source-type" className="mb-1 block text-sm text-secondary-text">
                  内容类型
                </label>
                <select
                  id="doc-source-type"
                  value={sourceType}
                  onChange={(e) => onSourceTypeChange(e.target.value as 'text' | 'markdown')}
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground focus:border-cyan/50 focus:outline-none"
                >
                  <option value="markdown">Markdown</option>
                  <option value="text">纯文本</option>
                </select>
              </div>
              <div>
                <label htmlFor="doc-tags" className="mb-1 block text-sm text-secondary-text">
                  标签
                </label>
                <input
                  id="doc-tags"
                  type="text"
                  value={tags}
                  onChange={(e) => onTagsChange(e.target.value)}
                  placeholder="华为, 半导体 (逗号分隔)"
                  className={cn(
                    'w-full rounded-lg border bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-text focus:outline-none',
                    tagsError ? 'border-red-500/50 focus:border-red-500/50' : 'border-white/10 focus:border-cyan/50',
                  )}
                  aria-invalid={!!tagsError}
                  aria-describedby={tagsError ? 'tags-error' : 'tags-hint'}
                />
                {tagsError && (
                  <p id="tags-error" className="mt-1 text-xs text-red-400">{tagsError}</p>
                )}
                <p id="tags-hint" className="mt-1 text-xs text-muted-text">
                  {parsedTags.length}/{MAX_TAGS_COUNT} 个标签
                </p>
              </div>
            </div>

            {/* Source URL */}
            <div>
              <label htmlFor="doc-source-url" className="mb-1 block text-sm text-secondary-text">
                来源 URL <span className="text-muted-text">(可选)</span>
              </label>
              <input
                id="doc-source-url"
                type="url"
                value={sourceUrl}
                onChange={(e) => onSourceUrlChange(e.target.value)}
                placeholder="https://example.com/article"
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-text focus:border-cyan/50 focus:outline-none"
              />
              <p className="mt-1 text-xs text-muted-text">仅支持 http/https 链接</p>
            </div>

            {/* Content */}
            <div>
              <label htmlFor="doc-content" className="mb-1 block text-sm text-secondary-text">
                内容 <span className="text-red-400">*</span>
              </label>
              <textarea
                id="doc-content"
                value={content}
                onChange={(e) => onContentChange(e.target.value)}
                placeholder="输入文档内容..."
                rows={10}
                maxLength={MAX_CONTENT_LENGTH}
                className={cn(
                  'w-full rounded-lg border bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-text focus:outline-none',
                  contentError ? 'border-red-500/50 focus:border-red-500/50' : 'border-white/10 focus:border-cyan/50',
                )}
                aria-invalid={!!contentError}
                aria-describedby={contentError ? 'content-error' : undefined}
              />
              {contentError && (
                <p id="content-error" className="mt-1 text-xs text-red-400">{contentError}</p>
              )}
              <p className="mt-1 text-xs text-muted-text">{content.length}/{MAX_CONTENT_LENGTH} 字符</p>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-secondary-text transition-colors hover:bg-white/5"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading || !title.trim() || !content.trim() || !!titleError || !!contentError || !!tagsError}
              className="inline-flex items-center gap-2 rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-black transition-colors hover:bg-cyan/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Plus className="h-4 w-4" aria-hidden="true" />
              )}
              {loading ? '创建中...' : '创建文档'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
