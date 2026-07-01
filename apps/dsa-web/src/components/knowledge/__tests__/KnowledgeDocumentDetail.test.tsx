import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { KnowledgeDocumentDetail } from '../KnowledgeDocumentDetail';

describe('KnowledgeDocumentDetail', () => {
  const mockDocument = {
    id: 'doc-1',
    title: '测试文档',
    source_type: 'markdown' as const,
    tags: ['华为', '半导体'],
    chunk_count: 2,
    content_hash: 'abc123',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    chunks: [
      { content: '这是第一个 chunk', chunk_index: 0 },
      { content: '这是第二个 chunk', chunk_index: 1 },
    ],
  };

  const defaultProps = {
    document: null,
    loading: false,
    onClose: vi.fn(),
    onCopy: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show loading state', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} loading={true} />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should render document details', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} document={mockDocument} />);
    expect(screen.getByText('测试文档')).toBeInTheDocument();
    expect(screen.getByText('markdown')).toBeInTheDocument();
    expect(screen.getByText('2 chunks')).toBeInTheDocument();
  });

  it('should render tags', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} document={mockDocument} />);
    expect(screen.getByText('华为')).toBeInTheDocument();
    expect(screen.getByText('半导体')).toBeInTheDocument();
  });

  it('should render chunks', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} document={mockDocument} />);
    expect(screen.getByText('这是第一个 chunk')).toBeInTheDocument();
    expect(screen.getByText('这是第二个 chunk')).toBeInTheDocument();
  });

  it('should call onClose when clicking close button', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} document={mockDocument} />);
    fireEvent.click(screen.getByLabelText('关闭'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('should call onCopy when clicking copy button on chunk', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} document={mockDocument} />);
    const copyBtns = screen.getAllByLabelText('复制内容');
    fireEvent.click(copyBtns[0]);
    expect(defaultProps.onCopy).toHaveBeenCalledWith('这是第一个 chunk');
  });

  it('should show source URL when present', () => {
    const docWithUrl = {
      ...mockDocument,
      source_url: 'https://example.com/article',
    };
    render(<KnowledgeDocumentDetail {...defaultProps} document={docWithUrl} />);
    expect(screen.getByText('https://example.com/article')).toBeInTheDocument();
  });

  it('should not render when no document and not loading', () => {
    const { container } = render(
      <KnowledgeDocumentDetail {...defaultProps} document={null} loading={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('should render loading state even when no document', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} document={null} loading={true} />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should close on backdrop click', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} document={mockDocument} />);
    const backdrop = document.querySelector('.fixed.inset-0.z-50');
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(defaultProps.onClose).toHaveBeenCalled();
    }
  });

  it('should have proper ARIA attributes', () => {
    render(<KnowledgeDocumentDetail {...defaultProps} document={mockDocument} />);
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', 'document-detail-title');
  });
});
