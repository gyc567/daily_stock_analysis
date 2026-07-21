import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UiLanguageProvider } from '../../../contexts/UiLanguageContext';
import { KnowledgeSearchResults } from '../KnowledgeSearchResults';

const renderWithLanguage = (ui: React.ReactNode) =>
  render(<UiLanguageProvider>{ui}</UiLanguageProvider>);

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
    window.localStorage.setItem('dsa.uiLanguage', 'zh');
  });

  it('should show loading state', () => {
    renderWithLanguage(<KnowledgeSearchResults {...defaultProps} loading={true} />);
    expect(screen.getByText('搜索中…')).toBeInTheDocument();
  });

  it('should show initial state when query is empty', () => {
    renderWithLanguage(<KnowledgeSearchResults {...defaultProps} query="" results={null} />);
    expect(screen.getByText('输入关键词搜索知识库')).toBeInTheDocument();
  });

  it('should show empty results state', () => {
    renderWithLanguage(
      <KnowledgeSearchResults
        {...defaultProps}
        query="test"
        results={{ ...mockResults, hits: [], total: 0 }}
      />,
    );
    expect(screen.getByText('未找到相关文档')).toBeInTheDocument();
  });

  it('should show unavailable state with message', () => {
    renderWithLanguage(
      <KnowledgeSearchResults
        {...defaultProps}
        query="test"
        results={{ ...mockResults, available: false, message: '服务暂时不可用' }}
      />,
    );
    expect(screen.getByText('搜索暂不可用')).toBeInTheDocument();
    expect(screen.getByText('服务暂时不可用')).toBeInTheDocument();
  });

  it('should render search results with localized source type and validation status', () => {
    renderWithLanguage(<KnowledgeSearchResults {...defaultProps} query="测试" results={mockResults} />);
    expect(screen.getByText('测试文档')).toBeInTheDocument();
    expect(screen.getByText('这是一段测试内容')).toBeInTheDocument();
    expect(screen.getByText('相似度 85%')).toBeInTheDocument();
    expect(screen.getByText('Markdown')).toBeInTheDocument();
    expect(screen.getByText('已验证')).toBeInTheDocument();
    expect(screen.queryByText('VERIFIED')).not.toBeInTheDocument();
  });

  it('should display hit count', () => {
    renderWithLanguage(<KnowledgeSearchResults {...defaultProps} query="测试" results={mockResults} />);
    expect(screen.getByText('1 个结果')).toBeInTheDocument();
  });

  it('should call onCopy when clicking copy button', () => {
    renderWithLanguage(<KnowledgeSearchResults {...defaultProps} query="测试" results={mockResults} />);
    const copyBtn = screen.getByLabelText('复制内容');
    fireEvent.click(copyBtn);
    expect(defaultProps.onCopy).toHaveBeenCalledWith('这是一段测试内容');
  });

  it('should render source URL when present', () => {
    const resultsWithUrl = {
      ...mockResults,
      hits: [{ ...mockHit, source_url: 'https://example.com' }],
    };
    renderWithLanguage(
      <KnowledgeSearchResults {...defaultProps} query="测试" results={resultsWithUrl} />,
    );
    expect(screen.getByText('https://example.com')).toBeInTheDocument();
  });

  it('should render english text and English validation label when language is en', () => {
    window.localStorage.setItem('dsa.uiLanguage', 'en');
    renderWithLanguage(<KnowledgeSearchResults {...defaultProps} query="test" results={mockResults} />);
    expect(screen.getByText('Search results')).toBeInTheDocument();
    expect(screen.getByText('1 results')).toBeInTheDocument();
    expect(screen.getByText('Verified')).toBeInTheDocument();
    expect(screen.getByText('Similarity 85%')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = renderWithLanguage(
      <KnowledgeSearchResults
        results={null}
        loading={false}
        query=""
        onCopy={vi.fn()}
        className="custom-class"
      />,
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
