import type React from 'react';
import { AlertTriangle, Info, Link, Loader2, X } from 'lucide-react';
import { cn } from '../../utils/cn';

interface KnowledgeCreateUrlModalProps {
  isOpen: boolean;
  loading: boolean;
  url: string;
  title: string;
  tags: string;
  error: string | null;
  onClose: () => void;
  onUrlChange: (value: string) => void;
  onTitleChange: (value: string) => void;
  onTagsChange: (value: string) => void;
  onSubmit: () => void;
}

const MAX_TITLE_LENGTH = 120;
const MAX_TAGS_COUNT = 20;
const URL_PATTERN = /^https?:\/\//i;

export const KnowledgeCreateUrlModal: React.FC<KnowledgeCreateUrlModalProps> = ({
  isOpen,
  loading,
  url,
  title,
  tags,
  error,
  onClose,
  onUrlChange,
  onTitleChange,
  onTagsChange,
  onSubmit,
}) => {
  if (!isOpen) return null;

  const parsedTags = tags
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean);
  const tagsError = parsedTags.length > MAX_TAGS_COUNT ? `最多 ${MAX_TAGS_COUNT} 个标签` : null;
  const urlError = url && !URL_PATTERN.test(url) ? '仅支持 http/https 链接' : null;
  const titleError = title.length > MAX_TITLE_LENGTH ? `标题最多 ${MAX_TITLE_LENGTH} 字符` : null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlError && !titleError && !tagsError && !loading && url.trim()) {
      onSubmit();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  const isValid = url.trim() && !urlError;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-url-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={handleKeyDown}
    >
      <div className="max-h-[85vh] w-full max-w-lg overflow-hidden rounded-2xl border border-white/8 bg-card/95 shadow-soft-card">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/5 p-5">
          <div className="flex items-center gap-2">
            <Link className="h-5 w-5 text-cyan" aria-hidden="true" />
            <h2 id="create-url-modal-title" className="text-lg font-semibold">从 URL 创建</h2>
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
            {/* Security notice */}
            <div className="flex gap-3 rounded-lg border border-cyan/20 bg-cyan/10 p-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-cyan" aria-hidden="true" />
              <div className="text-xs text-secondary-text">
                <p className="font-medium text-cyan">安全提示</p>
                <ul className="mt-1 space-y-0.5 text-muted-text">
                  <li>• 仅支持 http/https 链接</li>
                  <li>• 内网地址、localhost、file 协议会被拒绝</li>
                  <li>• URL 抓取为 best-effort，无法保证成功</li>
                </ul>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* URL */}
            <div>
              <label htmlFor="url-input" className="mb-1 block text-sm text-secondary-text">
                URL <span className="text-red-400">*</span>
              </label>
              <input
                id="url-input"
                type="url"
                value={url}
                onChange={(e) => onUrlChange(e.target.value)}
                placeholder="https://example.com/article"
                className={cn(
                  'w-full rounded-lg border bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-text focus:outline-none',
                  urlError ? 'border-red-500/50 focus:border-red-500/50' : 'border-white/10 focus:border-cyan/50',
                )}
                aria-invalid={!!urlError}
                aria-describedby={urlError ? 'url-error' : undefined}
              />
              {urlError && (
                <p id="url-error" className="mt-1 text-xs text-red-400">{urlError}</p>
              )}
            </div>

            {/* Title */}
            <div>
              <label htmlFor="url-title" className="mb-1 block text-sm text-secondary-text">
                标题 <span className="text-muted-text">(可选)</span>
              </label>
              <input
                id="url-title"
                type="text"
                value={title}
                onChange={(e) => onTitleChange(e.target.value)}
                placeholder="留空则由系统自动推断"
                maxLength={MAX_TITLE_LENGTH}
                className={cn(
                  'w-full rounded-lg border bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-text focus:outline-none',
                  titleError ? 'border-red-500/50 focus:border-red-500/50' : 'border-white/10 focus:border-cyan/50',
                )}
                aria-invalid={!!titleError}
              />
              {titleError && (
                <p className="mt-1 text-xs text-red-400">{titleError}</p>
              )}
              <p className="mt-1 text-xs text-muted-text">{title.length}/{MAX_TITLE_LENGTH} 字符</p>
            </div>

            {/* Tags */}
            <div>
              <label htmlFor="url-tags" className="mb-1 block text-sm text-secondary-text">
                标签 <span className="text-muted-text">(可选)</span>
              </label>
              <input
                id="url-tags"
                type="text"
                value={tags}
                onChange={(e) => onTagsChange(e.target.value)}
                placeholder="华为, 半导体 (逗号分隔)"
                className={cn(
                  'w-full rounded-lg border bg-white/5 px-3 py-2 text-sm text-foreground placeholder:text-muted-text focus:outline-none',
                  tagsError ? 'border-red-500/50 focus:border-red-500/50' : 'border-white/10 focus:border-cyan/50',
                )}
                aria-invalid={!!tagsError}
              />
              {tagsError && (
                <p className="mt-1 text-xs text-red-400">{tagsError}</p>
              )}
              <p className="mt-1 text-xs text-muted-text">
                {parsedTags.length}/{MAX_TAGS_COUNT} 个标签
              </p>
            </div>

            {/* Info */}
            <div className="flex gap-2 rounded-lg border border-white/5 bg-white/2 p-3">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-text" aria-hidden="true" />
              <p className="text-xs text-muted-text">
                抓取失败时会保留 URL 信息，可在后续重新抓取或手动编辑。
              </p>
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
              disabled={loading || !isValid || !!urlError || !!titleError || !!tagsError}
              className="inline-flex items-center gap-2 rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-black transition-colors hover:bg-cyan/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Link className="h-4 w-4" aria-hidden="true" />
              )}
              {loading ? '抓取中...' : '创建文档'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
