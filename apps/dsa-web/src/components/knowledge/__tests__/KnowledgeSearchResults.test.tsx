import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeSearchResults } from '../KnowledgeSearchResults';

describe('KnowledgeSearchResults', () => {
  const mockHit = {
    document_id: 'doc-1',
    document_title: '测试文档',
    source_type: 'markdown' as const,
    chunk_id: 'chunk-1',
    content: '这是一段测试内容',
    score: 0.85,
    created_at: '2024-01-01T00:00:00Z',
    validation_status: 'VERIFIED' as const,
  };

  const mockResults = {
    available: true,
    total: 1,
    query: '测试',
    hits: [mockHit],
  };

  const defaultProps = {
    results: null,
    loading: false,
    query: '',
    onCopy: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show loading state', () => {
    render(<KnowledgeSearchResults {...defaultProps} loading={true} />);
    expect(screen.getByText('搜索中...')).toBeInTheDocument();
  });

  it('should show initial state when query is empty', () => {
    render(<KnowledgeSearchResults {...defaultProps} query="" results={null} />);
    expect(screen.getByText('输入关键词搜索知识库')).toBeInTheDocument();
  });

  it('should show empty results state', () => {
    render(<KnowledgeSearchResults {...defaultProps} query="test" results={{ ...mockResults, hits: [], total: 0 }} />);
    expect(screen.getByText('未找到相关文档')).toBeInTheDocument();
  });

  it('should show unavailable state with message', () => {
    render(<KnowledgeSearchResults {...defaultProps} query="test" results={{ ...mockResults, available: false, message: '服务暂时不可用' }} />);
    expect(screen.getByText('搜索暂不可用')).toBeInTheDocument();
    expect(screen.getByText('服务暂时不可用')).toBeInTheDocument();
  });

  it('should render search results', () => {
    render(<KnowledgeSearchResults {...defaultProps} query="测试" results={mockResults} />);
    expect(screen.getByText('测试文档')).toBeInTheDocument();
    expect(screen.getByText('这是一段测试内容')).toBeInTheDocument();
    expect(screen.getByText(/85%/)).toBeInTheDocument();
    expect(screen.getByText('VERIFIED')).toBeInTheDocument();
  });

  it('should display hit count', () => {
    render(<KnowledgeSearchResults {...defaultProps} query="测试" results={mockResults} />);
    expect(screen.getByText('1 个结果')).toBeInTheDocument();
  });

  it('should call onCopy when clicking copy button', () => {
    render(<KnowledgeSearchResults {...defaultProps} query="测试" results={mockResults} />);
    const copyBtn = screen.getByLabelText('复制内容');
    fireEvent.click(copyBtn);
    expect(defaultProps.onCopy).toHaveBeenCalledWith('这是一段测试内容');
  });

  it('should render source URL when present', () => {
    const resultsWithUrl = {
      ...mockResults,
      hits: [{ ...mockHit, source_url: 'https://example.com' }],
    };
    render(<KnowledgeSearchResults {...defaultProps} query="测试" results={resultsWithUrl} />);
    expect(screen.getByText('https://example.com')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = render(
      <KnowledgeSearchResults
        results={null}
        loading={false}
        query=""
        onCopy={vi.fn()}
        className="custom-class"
      />
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
