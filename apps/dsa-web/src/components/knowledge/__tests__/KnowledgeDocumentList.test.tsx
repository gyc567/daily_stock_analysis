import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UiLanguageProvider } from '../../../contexts/UiLanguageContext';
import { KnowledgeDocumentList } from '../KnowledgeDocumentList';

const renderWithLanguage = (ui: React.ReactNode) =>
  render(<UiLanguageProvider>{ui}</UiLanguageProvider>);

describe('KnowledgeDocumentList', () => {
  const mockDocument = {
    id: 'doc-1',
    title: '测试文档',
    source_type: 'markdown' as const,
    tags: ['华为', '半导体'],
    chunk_count: 5,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    content_hash: 'abc123',
  };

  const defaultProps = {
    documents: [],
    loading: false,
    selectedDocId: null,
    onSelect: vi.fn(),
    onDelete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.setItem('dsa.uiLanguage', 'zh');
  });

  it('should show loading state', () => {
    renderWithLanguage(<KnowledgeDocumentList {...defaultProps} loading={true} />);
    expect(screen.getByText('正在加载…')).toBeInTheDocument();
  });

  it('should show empty state when no documents', () => {
    renderWithLanguage(<KnowledgeDocumentList {...defaultProps} documents={[]} />);
    expect(screen.getByText('暂无文档')).toBeInTheDocument();
    expect(screen.getByText('上传文件或粘贴文本创建文档')).toBeInTheDocument();
  });

  it('should render document list with localized source type and chunk count', () => {
    renderWithLanguage(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} />);
    expect(screen.getByText('测试文档')).toBeInTheDocument();
    expect(screen.getByText('Markdown')).toBeInTheDocument();
    expect(screen.getByText('5 个内容片段')).toBeInTheDocument();
    expect(screen.queryByText('5 chunks')).not.toBeInTheDocument();
  });

  it('should render tags', () => {
    renderWithLanguage(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} />);
    expect(screen.getByText('华为')).toBeInTheDocument();
    expect(screen.getByText('半导体')).toBeInTheDocument();
  });

  it('should highlight selected document', () => {
    renderWithLanguage(
      <KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} selectedDocId="doc-1" />,
    );
    const docElement = screen.getByText('测试文档').closest('[role="button"]');
    expect(docElement).toHaveAttribute('aria-selected', 'true');
  });

  it('should call onSelect when clicking document', () => {
    renderWithLanguage(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} />);
    fireEvent.click(screen.getByText('测试文档'));
    expect(defaultProps.onSelect).toHaveBeenCalledWith(mockDocument);
  });

  it('should call onDelete when clicking delete button with localized aria', () => {
    renderWithLanguage(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} />);
    const deleteBtn = screen.getByLabelText('删除文档：测试文档');
    fireEvent.click(deleteBtn);
    expect(defaultProps.onDelete).toHaveBeenCalledWith('doc-1');
  });

  it('should show tag overflow count with localized text', () => {
    const docWithManyTags = {
      ...mockDocument,
      tags: ['tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6'],
    };
    renderWithLanguage(<KnowledgeDocumentList {...defaultProps} documents={[docWithManyTags]} />);
    expect(screen.getByText('其余 1 个')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = renderWithLanguage(
      <KnowledgeDocumentList
        documents={[]}
        loading={false}
        selectedDocId={null}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        className="custom-class"
      />,
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
