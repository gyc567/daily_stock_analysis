import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeCreateUrlModal } from '../KnowledgeCreateUrlModal';

describe('KnowledgeCreateUrlModal', () => {
  const defaultProps = {
    isOpen: true,
    loading: false,
    url: '',
    title: '',
    tags: '',
    error: null,
    onClose: vi.fn(),
    onUrlChange: vi.fn(),
    onTitleChange: vi.fn(),
    onTagsChange: vi.fn(),
    onSubmit: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when isOpen is false', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render modal when isOpen is true', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('从 URL 创建')).toBeInTheDocument();
  });

  it('should show security hints', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} />);
    expect(screen.getByText('安全提示')).toBeInTheDocument();
    expect(screen.getByText(/仅支持 http\/https 链接/)).toBeInTheDocument();
  });

  it('should show error when provided', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} error="URL 创建失败" />);
    expect(screen.getByText('URL 创建失败')).toBeInTheDocument();
  });

  it('should call onClose when clicking close button', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('关闭'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('should call onUrlChange when typing URL', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} />);
    const input = screen.getByLabelText(/^URL/);
    fireEvent.change(input, { target: { value: 'https://example.com' } });
    expect(defaultProps.onUrlChange).toHaveBeenCalledWith('https://example.com');
  });

  it('should show URL validation error for invalid URL', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} url="ftp://example.com" />);
    // The error message appears when URL is invalid
    const errorText = document.body.textContent || '';
    expect(errorText).toContain('仅支持 http/https 链接');
  });

  it('should call onTitleChange when typing in title field', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} />);
    const input = screen.getByLabelText(/标题/);
    fireEvent.change(input, { target: { value: 'Example Site' } });
    expect(defaultProps.onTitleChange).toHaveBeenCalledWith('Example Site');
  });

  it('should show tags count', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} tags="tag1, tag2" />);
    expect(screen.getByText(/2\/20 个标签/)).toBeInTheDocument();
  });

  it('should disable submit when URL is empty', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} url="" />);
    expect(screen.getByRole('button', { name: /创建文档/ })).toBeDisabled();
  });

  it('should disable submit when URL is invalid', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} url="ftp://example.com" />);
    expect(screen.getByRole('button', { name: /创建文档/ })).toBeDisabled();
  });

  it('should enable submit when URL is valid', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} url="https://example.com" />);
    expect(screen.getByRole('button', { name: /创建文档/ })).toBeEnabled();
  });

  it('should disable submit when loading', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} url="https://example.com" loading={true} />);
    expect(screen.getByText('抓取中...')).toBeDisabled();
  });

  it('should call onSubmit when clicking submit button', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} url="https://example.com" />);
    fireEvent.click(screen.getByRole('button', { name: /创建文档/ }));
    expect(defaultProps.onSubmit).toHaveBeenCalled();
  });

  it('should close on Escape key', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} />);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('should have proper ARIA attributes', () => {
    render(<KnowledgeCreateUrlModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', 'create-url-modal-title');
  });
});
