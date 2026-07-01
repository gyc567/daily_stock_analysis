import apiClient from './index';
import { createApiError, isApiRequestError, parseApiError } from './error';

// ============ Types ============

export type SourceType = 'text' | 'markdown' | 'pdf' | 'url';

export interface KnowledgeDocumentItem {
  id: string;
  title: string;
  source_type: SourceType;
  source_url?: string;
  file_path?: string;
  content_hash: string;
  tags: string[];
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeChunkHit {
  document_id: string;
  document_title: string;
  source_type: SourceType;
  source_url?: string;
  chunk_id: string;
  content: string;
  score: number;
  created_at: string;
  validation_status: 'VERIFIED' | 'CONFLICT' | 'USER_ONLY' | 'PENDING';
}

export interface KnowledgeSearchRequest {
  query: string;
  stock_code?: string;
  stock_name?: string;
  tags?: string[];
  top_k?: number;
}

export interface KnowledgeSearchResponse {
  available: boolean;
  total: number;
  query: string;
  hits: KnowledgeChunkHit[];
  message?: string;
}

export interface KnowledgeDocumentCreate {
  title: string;
  source_type: SourceType;
  content: string;
  source_url?: string;
  tags?: string[];
}

export interface FileUploadResponse {
  document_id: string;
  title: string;
  source_type: SourceType;
  chunk_count: number;
  content_hash: string;
  status: 'success' | 'failed';
  message: string;
}

// ============ API Client ============

export const knowledgeBaseApi = {
  /**
   * 获取知识库状态
   */
  async getStatus(): Promise<{ available: boolean; document_count: number }> {
    const response = await apiClient.get<{
      available: boolean;
      document_count: number;
    }>('/api/v1/knowledge-base/status');
    return response.data;
  },

  /**
   * 列出文档
   */
  async listDocuments(params?: {
    source_type?: string;
    tag?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ total: number; documents: KnowledgeDocumentItem[] }> {
    const response = await apiClient.get<{
      total: number;
      documents: KnowledgeDocumentItem[];
    }>('/api/v1/knowledge-base/documents', { params });
    return response.data;
  },

  /**
   * 获取文档详情
   */
  async getDocument(documentId: string): Promise<KnowledgeDocumentItem & { chunks: unknown[] }> {
    const response = await apiClient.get<KnowledgeDocumentItem & { chunks: unknown[] }>(
      `/api/v1/knowledge-base/documents/${documentId}`,
    );
    return response.data;
  },

  /**
   * 创建文本文档
   */
  async createDocument(data: KnowledgeDocumentCreate): Promise<KnowledgeDocumentItem> {
    const response = await apiClient.post<KnowledgeDocumentItem>(
      '/api/v1/knowledge-base/documents/text',
      data,
    );
    return response.data;
  },

  /**
   * 上传文件
   */
  async uploadFile(
    file: File,
    options?: { title?: string; tags?: string[] },
  ): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.title) formData.append('title', options.title);
    if (options?.tags) formData.append('tags', options.tags.join(','));

    try {
      const response = await fetch('/api/v1/knowledge-base/documents/upload', {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw createApiError(
          parseApiError({ response: { status: response.status, data: errorData } }),
          { response: { status: response.status, data: errorData } },
        );
      }

      return (await response.json()) as FileUploadResponse;
    } catch (error) {
      if (isApiRequestError(error)) throw error;
      throw createApiError(parseApiError(error), { cause: error });
    }
  },

  /**
   * 从 URL 创建文档
   */
  async createFromUrl(
    url: string,
    options?: { title?: string; tags?: string[] },
  ): Promise<FileUploadResponse> {
    const params = new URLSearchParams({ url });
    if (options?.title) params.append('title', options.title);
    if (options?.tags) params.append('tags', options.tags.join(','));

    const response = await apiClient.post<FileUploadResponse>(
      `/api/v1/knowledge-base/documents/url?${params.toString()}`,
    );
    return response.data;
  },

  /**
   * 删除文档
   */
  async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/api/v1/knowledge-base/documents/${documentId}`);
  },

  /**
   * 搜索知识库
   */
  async search(request: KnowledgeSearchRequest): Promise<KnowledgeSearchResponse> {
    try {
      const response = await apiClient.post<KnowledgeSearchResponse>(
        '/api/v1/knowledge-base/search',
        request,
      );
      return response.data;
    } catch (error) {
      // 搜索失败返回空结果
      return {
        available: false,
        total: 0,
        query: request.query,
        hits: [],
        message: error instanceof Error ? error.message : 'Search failed',
      };
    }
  },
};
