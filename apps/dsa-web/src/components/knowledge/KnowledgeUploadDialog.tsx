import type React from 'react';
import { AlertTriangle, FileText, Loader2, Upload, X } from 'lucide-react';
import { cn } from '../../utils/cn';

interface KnowledgeUploadDialogProps {
  isOpen: boolean;
  loading: boolean;
  file: File | null;
  tags: string;
  onClose: () => void;
  onFileSelect: (file: File | null) => void;
  onTagsChange: (value: string) => void;
  onUpload: () => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
}

const ACCEPTED_TYPES = ['.pdf', '.md', '.markdown', '.txt'];
const MAX_FILE_SIZE_MB = 20;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
const MAX_TAGS_COUNT = 20;

export const KnowledgeUploadDialog: React.FC<KnowledgeUploadDialogProps> = ({
  isOpen,
  loading,
  file,
  tags,
  onClose,
  onFileSelect,
  onTagsChange,
  onUpload,
  fileInputRef,
}) => {
  if (!isOpen) return null;

  const parsedTags = tags
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean);
  const tagsError = parsedTags.length > MAX_TAGS_COUNT ? `最多 ${MAX_TAGS_COUNT} 个标签` : null;
  const fileSizeError = file && file.size > MAX_FILE_SIZE_BYTES
    ? `文件大小不能超过 ${MAX_FILE_SIZE_MB}MB`
    : null;
  const fileTypeError = file && !isValidFileType(file.name)
    ? `不支持的文件类型，仅支持: ${ACCEPTED_TYPES.join(', ')}`
    : null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileSizeError && !fileTypeError && !tagsError && !loading && file) {
      onUpload();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    onFileSelect(selectedFile);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-dialog-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onKeyDown={handleKeyDown}
    >
      <div className="max-h-[85vh] w-full max-w-lg overflow-hidden rounded-2xl border border-white/8 bg-card/95 shadow-soft-card">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/5 p-5">
          <div className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-cyan" aria-hidden="true" />
            <h2 id="upload-dialog-title" className="text-lg font-semibold">上传文件</h2>
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
            {/* File type hints */}
            <div className="flex gap-3 rounded-lg border border-white/5 bg-white/2 p-3">
              <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-text" aria-hidden="true" />
              <div className="text-xs text-muted-text">
                <p className="font-medium text-secondary-text">支持的文件类型</p>
                <p className="mt-1">PDF、Markdown (.md/.markdown)、纯文本 (.txt)</p>
                <p className="mt-0.5">最大文件大小：{MAX_FILE_SIZE_MB}MB</p>
              </div>
            </div>

            {/* File input */}
            <div>
              <label htmlFor="file-input" className="mb-2 block text-sm text-secondary-text">
                选择文件
              </label>
              <input
                id="file-input"
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_TYPES.join(',')}
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-white/20 px-4 py-6 text-sm text-muted-text transition-colors hover:border-cyan/50 hover:text-cyan disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Upload className="h-5 w-5" aria-hidden="true" />
                {file ? '更换文件' : '点击选择文件'}
              </button>

              {/* Selected file info */}
              {file && (
                <div className="mt-3 flex items-center justify-between rounded-lg border border-white/10 bg-white/5 p-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-foreground">{file.name}</p>
                    <p className="mt-0.5 text-xs text-muted-text">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onFileSelect(null)}
                    disabled={loading}
                    className="ml-2 shrink-0 rounded p-1 text-muted-text hover:bg-white/5 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-60"
                    aria-label="移除文件"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              )}

              {/* File errors */}
              {(fileSizeError || fileTypeError) && (
                <div className="mt-2 flex items-start gap-2 text-xs text-red-400">
                  <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />
                  <span>{fileSizeError || fileTypeError}</span>
                </div>
              )}
            </div>

            {/* Tags */}
            <div>
              <label htmlFor="upload-tags" className="mb-1 block text-sm text-secondary-text">
                标签 <span className="text-muted-text">(可选)</span>
              </label>
              <input
                id="upload-tags"
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
          </div>

          {/* Actions */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-secondary-text transition-colors hover:bg-white/5 disabled:opacity-60"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading || !file || !!fileSizeError || !!fileTypeError || !!tagsError}
              className="inline-flex items-center gap-2 rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-black transition-colors hover:bg-cyan/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Upload className="h-4 w-4" aria-hidden="true" />
              )}
              {loading ? '上传中...' : '上传'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

function isValidFileType(filename: string): boolean {
  const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'));
  return ACCEPTED_TYPES.includes(ext);
}
