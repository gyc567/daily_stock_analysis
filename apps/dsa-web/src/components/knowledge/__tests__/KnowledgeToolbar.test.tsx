import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeToolbar } from '../KnowledgeToolbar';

describe('KnowledgeToolbar', () => {
  const defaultProps = {
    searchQuery: '',
    onSearchChange: vi.fn(),
    onSearch: vi.fn(),
    searchLoading: false,
    documentCount: 0,
    onUploadClick: vi.fn(),
    onTextClick: vi.fn(),
    onUrlClick: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render search input', () => {
    render(<KnowledgeToolbar {...defaultProps} />);
    expect(screen.getByLabelText('搜索知识库')).toBeInTheDocument();
  });

  it('should render action buttons', () => {
    render(<KnowledgeToolbar {...defaultProps} />);
    expect(screen.getByLabelText('上传文件')).toBeInTheDocument();
    expect(screen.getByLabelText('粘贴文本')).toBeInTheDocument();
    expect(screen.getByLabelText('从 URL 创建')).toBeInTheDocument();
  });

  it('should display document count', () => {
    render(<KnowledgeToolbar {...defaultProps} documentCount={10} />);
    expect(screen.getByText('10 篇文档')).toBeInTheDocument();
  });

  it('should call onSearchChange when typing', () => {
    render(<KnowledgeToolbar {...defaultProps} />);
    const input = screen.getByLabelText('搜索知识库');
    fireEvent.change(input, { target: { value: 'test query' } });
    expect(defaultProps.onSearchChange).toHaveBeenCalledWith('test query');
  });

  it('should call onSearch when pressing Enter', () => {
    render(<KnowledgeToolbar {...defaultProps} searchQuery="test" />);
    const input = screen.getByLabelText('搜索知识库');
    input.focus();
    const event = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
    input.dispatchEvent(event);
    expect(defaultProps.onSearch).toHaveBeenCalled();
  });

  it('should call onUploadClick when upload button is clicked', () => {
    render(<KnowledgeToolbar {...defaultProps} />);
    screen.getByLabelText('上传文件').click();
    expect(defaultProps.onUploadClick).toHaveBeenCalled();
  });

  it('should call onTextClick when text button is clicked', () => {
    render(<KnowledgeToolbar {...defaultProps} />);
    screen.getByLabelText('粘贴文本').click();
    expect(defaultProps.onTextClick).toHaveBeenCalled();
  });

  it('should call onUrlClick when URL button is clicked', () => {
    render(<KnowledgeToolbar {...defaultProps} />);
    screen.getByLabelText('从 URL 创建').click();
    expect(defaultProps.onUrlClick).toHaveBeenCalled();
  });

  it('should disable search button when searchLoading is true', () => {
    render(<KnowledgeToolbar {...defaultProps} searchLoading={true} searchQuery="test" />);
    expect(screen.getByLabelText('搜索')).toBeDisabled();
  });

  it('should disable search button when query is empty', () => {
    render(<KnowledgeToolbar {...defaultProps} searchQuery="" />);
    expect(screen.getByLabelText('搜索')).toBeDisabled();
  });

  it('should apply custom className', () => {
    const { container } = render(<KnowledgeToolbar {...defaultProps} className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
