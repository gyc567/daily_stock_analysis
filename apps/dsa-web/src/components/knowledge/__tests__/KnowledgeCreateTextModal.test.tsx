import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeCreateTextModal } from '../KnowledgeCreateTextModal';

describe('KnowledgeCreateTextModal', () => {
  const defaultProps = {
    isOpen: true,
    loading: false,
    title: '',
    content: '',
    tags: '',
    sourceUrl: '',
    sourceType: 'markdown' as const,
    error: null,
    onClose: vi.fn(),
    onTitleChange: vi.fn(),
    onContentChange: vi.fn(),
    onTagsChange: vi.fn(),
    onSourceUrlChange: vi.fn(),
    onSourceTypeChange: vi.fn(),
    onSubmit: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when isOpen is false', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should render modal when isOpen is true', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('创建文档', { selector: 'h2' })).toBeInTheDocument();
  });

  it('should show error when provided', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} error="创建失败" />);
    expect(screen.getByText('创建失败')).toBeInTheDocument();
  });

  it('should call onClose when clicking close button', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('关闭'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('should call onTitleChange when typing in title field', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} />);
    const input = screen.getByLabelText(/标题/);
    fireEvent.change(input, { target: { value: '新标题' } });
    expect(defaultProps.onTitleChange).toHaveBeenCalledWith('新标题');
  });

  it('should call onContentChange when typing in content field', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} />);
    const textarea = screen.getByRole('textbox', { name: /内容/ });
    fireEvent.change(textarea, { target: { value: '新内容' } });
    expect(defaultProps.onContentChange).toHaveBeenCalledWith('新内容');
  });

  it('should show character count for title', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} title="测试标题" />);
    expect(screen.getByText(/\/120 字符/)).toBeInTheDocument();
  });

  it('should show character count for content', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} content="测试内容" />);
    expect(screen.getByText(/200000 字符/)).toBeInTheDocument();
  });

  it('should show tags count', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} tags="tag1, tag2" />);
    expect(screen.getByText(/2\/20 个标签/)).toBeInTheDocument();
  });

  it('should show tags error when exceeding limit', () => {
    const manyTags = Array.from({ length: 25 }, (_, i) => `tag${i}`).join(', ');
    render(<KnowledgeCreateTextModal {...defaultProps} tags={manyTags} />);
    expect(screen.getByText(/最多 20 个标签/)).toBeInTheDocument();
  });

  it('should call onSourceTypeChange when changing source type', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} />);
    const select = screen.getByLabelText(/内容类型/);
    fireEvent.change(select, { target: { value: 'text' } });
    expect(defaultProps.onSourceTypeChange).toHaveBeenCalledWith('text');
  });

  it('should disable submit button when loading', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} loading={true} title="标题" content="内容" />);
    expect(screen.getByText('创建中...')).toBeDisabled();
  });

  it('should disable submit button when title is empty', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} title="" content="内容" />);
    expect(screen.getByRole('button', { name: /创建文档/ })).toBeDisabled();
  });

  it('should disable submit button when content is empty', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} title="标题" content="" />);
    expect(screen.getByRole('button', { name: /创建文档/ })).toBeDisabled();
  });

  it('should call onSubmit when clicking submit button', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} title="标题" content="内容" />);
    fireEvent.click(screen.getByRole('button', { name: /创建文档/ }));
    expect(defaultProps.onSubmit).toHaveBeenCalled();
  });

  it('should close on Escape key', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} />);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('should have proper ARIA attributes', () => {
    render(<KnowledgeCreateTextModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', 'create-text-modal-title');
  });
});
