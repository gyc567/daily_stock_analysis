import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeDocumentList } from '../KnowledgeDocumentList';

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
  });

  it('should show loading state', () => {
    render(<KnowledgeDocumentList {...defaultProps} loading={true} />);
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('should show empty state when no documents', () => {
    render(<KnowledgeDocumentList {...defaultProps} documents={[]} />);
    expect(screen.getByText('暂无文档')).toBeInTheDocument();
    expect(screen.getByText('上传文件或粘贴文本创建文档')).toBeInTheDocument();
  });

  it('should render document list', () => {
    render(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} />);
    expect(screen.getByText('测试文档')).toBeInTheDocument();
    expect(screen.getByText('markdown')).toBeInTheDocument();
    expect(screen.getByText('5 chunks')).toBeInTheDocument();
  });

  it('should render tags', () => {
    render(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} />);
    expect(screen.getByText('华为')).toBeInTheDocument();
    expect(screen.getByText('半导体')).toBeInTheDocument();
  });

  it('should highlight selected document', () => {
    render(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} selectedDocId="doc-1" />);
    const docElement = screen.getByText('测试文档').closest('[role="button"]');
    expect(docElement).toHaveAttribute('aria-selected', 'true');
  });

  it('should call onSelect when clicking document', () => {
    render(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} />);
    fireEvent.click(screen.getByText('测试文档'));
    expect(defaultProps.onSelect).toHaveBeenCalledWith(mockDocument);
  });

  it('should call onDelete when clicking delete button', () => {
    render(<KnowledgeDocumentList {...defaultProps} documents={[mockDocument]} />);
    const deleteBtn = screen.getByLabelText(`删除文档: ${mockDocument.title}`);
    fireEvent.click(deleteBtn);
    expect(defaultProps.onDelete).toHaveBeenCalledWith('doc-1');
  });

  it('should show "+N" when tags exceed 5', () => {
    const docWithManyTags = {
      ...mockDocument,
      tags: ['tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6'],
    };
    render(<KnowledgeDocumentList {...defaultProps} documents={[docWithManyTags]} />);
    expect(screen.getByText('+1')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = render(
      <KnowledgeDocumentList
        documents={[]}
        loading={false}
        selectedDocId={null}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        className="custom-class"
      />
    );
    expect(container.firstChild).toHaveClass('custom-class');
  });
});
