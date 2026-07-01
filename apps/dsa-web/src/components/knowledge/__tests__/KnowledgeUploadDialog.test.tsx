import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeUploadDialog } from '../KnowledgeUploadDialog';

describe('KnowledgeUploadDialog', () => {
  const mockFile = new File(['content'], 'test.md', { type: 'text/markdown' });
  const mockRef = { current: null as HTMLInputElement | null } as React.RefObject<HTMLInputElement>;

  const defaultProps = {
    isOpen: true,
    loading: false,
    file: null,
    tags: '',
    onClose: vi.fn(),
    onFileSelect: vi.fn(),
    onTagsChange: vi.fn(),
    onUpload: vi.fn(),
    fileInputRef: mockRef,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when isOpen is false', () => {
    render(<KnowledgeUploadDialog {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render dialog when isOpen is true', () => {
    render(<KnowledgeUploadDialog {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('上传文件')).toBeInTheDocument();
  });

  it('should show supported file types', () => {
    render(<KnowledgeUploadDialog {...defaultProps} />);
    expect(screen.getByText(/PDF/)).toBeInTheDocument();
    expect(screen.getByText(/Markdown/)).toBeInTheDocument();
    expect(screen.getByText(/20MB/)).toBeInTheDocument();
  });

  it('should show file selection button', () => {
    render(<KnowledgeUploadDialog {...defaultProps} />);
    expect(screen.getByText('点击选择文件')).toBeInTheDocument();
  });

  it('should show selected file info', () => {
    render(<KnowledgeUploadDialog {...defaultProps} file={mockFile} />);
    expect(screen.getByText('test.md')).toBeInTheDocument();
    // The button shows "更换文件" when a file is selected
    expect(screen.getByText('更换文件')).toBeInTheDocument();
  });

  it('should call onClose when clicking close button', () => {
    render(<KnowledgeUploadDialog {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('关闭'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('should call onTagsChange when typing tags', () => {
    render(<KnowledgeUploadDialog {...defaultProps} />);
    const input = screen.getByLabelText(/标签/);
    fireEvent.change(input, { target: { value: 'tag1, tag2' } });
    expect(defaultProps.onTagsChange).toHaveBeenCalledWith('tag1, tag2');
  });

  it('should show tags count', () => {
    render(<KnowledgeUploadDialog {...defaultProps} tags="tag1, tag2" />);
    expect(screen.getByText(/2\/20 个标签/)).toBeInTheDocument();
  });

  it('should show tags error when exceeding limit', () => {
    const manyTags = Array.from({ length: 25 }, (_, i) => `tag${i}`).join(', ');
    render(<KnowledgeUploadDialog {...defaultProps} tags={manyTags} />);
    expect(screen.getByText(/最多 20 个标签/)).toBeInTheDocument();
  });

  it('should disable submit when no file is selected', () => {
    render(<KnowledgeUploadDialog {...defaultProps} file={null} />);
    expect(screen.getByRole('button', { name: /上传/ })).toBeDisabled();
  });

  it('should enable submit when file is selected', () => {
    render(<KnowledgeUploadDialog {...defaultProps} file={mockFile} />);
    expect(screen.getByRole('button', { name: /上传/ })).toBeEnabled();
  });

  it('should disable submit when loading', () => {
    render(<KnowledgeUploadDialog {...defaultProps} file={mockFile} loading={true} />);
    expect(screen.getByText('上传中...')).toBeDisabled();
  });

  it('should call onUpload when clicking upload button', () => {
    render(<KnowledgeUploadDialog {...defaultProps} file={mockFile} />);
    fireEvent.click(screen.getByRole('button', { name: /上传/ }));
    expect(defaultProps.onUpload).toHaveBeenCalled();
  });

  it('should call onClose when clicking cancel button', () => {
    render(<KnowledgeUploadDialog {...defaultProps} file={mockFile} />);
    fireEvent.click(screen.getByRole('button', { name: /取消/ }));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('should show error for invalid file type', () => {
    const invalidFile = new File(['content'], 'test.exe', { type: 'application/octet-stream' });
    render(<KnowledgeUploadDialog {...defaultProps} file={invalidFile} />);
    expect(screen.getByText(/不支持的文件类型/)).toBeInTheDocument();
  });

  it('should close on Escape key', () => {
    render(<KnowledgeUploadDialog {...defaultProps} />);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('should have proper ARIA attributes', () => {
    render(<KnowledgeUploadDialog {...defaultProps} />);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', 'upload-dialog-title');
  });
});
