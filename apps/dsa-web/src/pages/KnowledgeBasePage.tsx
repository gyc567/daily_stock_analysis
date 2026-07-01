import { useCallback, useEffect, useRef, useState } from 'react';
import { BookOpen } from 'lucide-react';
import {
  knowledgeBaseApi,
  type KnowledgeDocumentItem,
  type KnowledgeSearchResponse,
} from '../api/knowledgeBase';
import { ToastContainer } from '../components/common/Toast';
import { useToast } from '../hooks/useToast';
import {
  KnowledgeToolbar,
  type ActiveDialog,
  KnowledgeDocumentList,
  KnowledgeSearchResults,
  KnowledgeDocumentDetail,
  KnowledgeCreateTextModal,
  KnowledgeCreateUrlModal,
  KnowledgeUploadDialog,
} from '../components/knowledge';

type DocumentDetail = KnowledgeDocumentItem & { chunks?: Array<{ content?: string; chunk_index?: number }> };

/**
 * 知识库管理页面
 *
 * 功能：
 * - 搜索知识库（全文检索）
 * - 文档管理（列表、创建、删除）
 * - 文档详情查看
 *
 * 优化点：
 * - 统一顶部工具栏（搜索 + 上传/文本/URL 快捷入口）
 * - 移除页内 Tab，保留全局导航
 * - 详情使用 Modal，不覆盖列表/搜索结果
 * - 统一 Toast 反馈（成功/失败/复制反馈）
 * - URL 创建使用独立接口
 * - 组件化拆分，提升可维护性
 */
export function KnowledgeBasePage() {
  // Toast 通知
  const toast = useToast(4000);

  // 列表状态
  const [documents, setDocuments] = useState<KnowledgeDocumentItem[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);

  // 搜索状态
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResponse | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);

  // 选中文档状态
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDocDetail, setSelectedDocDetail] = useState<DocumentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Dialog 状态
  const [activeDialog, setActiveDialog] = useState<ActiveDialog>(null);
  const [dialogFocusRef, setDialogFocusRef] = useState<HTMLElement | null>(null);

  // 创建文本文档表单状态
  const [createTitle, setCreateTitle] = useState('');
  const [createContent, setCreateContent] = useState('');
  const [createTags, setCreateTags] = useState('');
  const [createSourceUrl, setCreateSourceUrl] = useState('');
  const [createSourceType, setCreateSourceType] = useState<'text' | 'markdown'>('markdown');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // URL 创建表单状态
  const [urlInput, setUrlInput] = useState('');
  const [urlTitle, setUrlTitle] = useState('');
  const [urlTags, setUrlTags] = useState('');
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);

  // 文件上传状态
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTags, setUploadTags] = useState('');
  const [uploadLoading, setUploadLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 加载文档列表
  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    try {
      const result = await knowledgeBaseApi.listDocuments({ limit: 50 });
      setDocuments(result.documents);
    } catch {
      toast.error('加载文档失败');
    } finally {
      setDocumentsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  // 搜索
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;

    setSearchLoading(true);
    try {
      const results = await knowledgeBaseApi.search({ query: searchQuery, top_k: 10 });
      setSearchResults(results);
    } catch {
      setSearchResults(null);
      toast.error('搜索失败');
    } finally {
      setSearchLoading(false);
    }
  }, [searchQuery, toast]);

  // 打开 Dialog
  const openDialog = useCallback((dialog: ActiveDialog, trigger?: HTMLElement) => {
    setDialogFocusRef(trigger || document.activeElement as HTMLElement);
    setActiveDialog(dialog);
  }, []);

  // 关闭 Dialog
  const closeDialog = useCallback(() => {
    setActiveDialog(null);
    // 焦点回到触发元素
    setTimeout(() => {
      dialogFocusRef?.focus();
    }, 0);
  }, [dialogFocusRef]);

  // 创建文本文档
  const handleCreateText = useCallback(async () => {
    if (!createTitle.trim() || !createContent.trim()) {
      setCreateError('标题和内容不能为空');
      return;
    }

    setCreateLoading(true);
    setCreateError(null);

    try {
      await knowledgeBaseApi.createDocument({
        title: createTitle.trim(),
        content: createContent.trim(),
        source_type: createSourceType,
        tags: createTags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean)
          .slice(0, 20),
        source_url: createSourceUrl.trim() || undefined,
      });

      toast.success('文档创建成功');

      // 重置表单
      setCreateTitle('');
      setCreateContent('');
      setCreateTags('');
      setCreateSourceUrl('');
      closeDialog();
      void loadDocuments();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : '创建失败');
    } finally {
      setCreateLoading(false);
    }
  }, [createTitle, createContent, createSourceType, createTags, createSourceUrl, closeDialog, loadDocuments, toast]);

  // URL 创建
  const handleCreateUrl = useCallback(async () => {
    if (!urlInput.trim()) return;

    setUrlLoading(true);
    setUrlError(null);

    try {
      const result = await knowledgeBaseApi.createFromUrl(urlInput.trim(), {
        title: urlTitle.trim() || undefined,
        tags: urlTags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean)
          .slice(0, 20),
      });

      if (result.status === 'success') {
        toast.success(`文档创建成功: ${result.title}`, '文档入库');
      } else {
        toast.warning(result.message || '文档创建可能未完全成功');
      }

      // 重置表单
      setUrlInput('');
      setUrlTitle('');
      setUrlTags('');
      closeDialog();
      void loadDocuments();
    } catch (err) {
      setUrlError(err instanceof Error ? err.message : 'URL 创建失败');
    } finally {
      setUrlLoading(false);
    }
  }, [urlInput, urlTitle, urlTags, closeDialog, loadDocuments, toast]);

  // 文件上传
  const handleUpload = useCallback(async () => {
    if (!uploadFile) return;

    setUploadLoading(true);
    try {
      const result = await knowledgeBaseApi.uploadFile(uploadFile, {
        tags: uploadTags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean)
          .slice(0, 20),
      });

      if (result.status === 'success') {
        toast.success(
          `上传成功: ${result.title} (${result.chunk_count} chunks)`,
          '文件入库',
        );
      } else {
        toast.warning(result.message || '上传可能未完全成功');
      }

      setUploadFile(null);
      setUploadTags('');
      closeDialog();
      void loadDocuments();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploadLoading(false);
    }
  }, [uploadFile, uploadTags, closeDialog, loadDocuments, toast]);

  // 删除文档
  const handleDelete = useCallback(
    async (docId: string, docTitle: string) => {
      if (!window.confirm(`确定要删除文档「${docTitle}」吗？此操作不可撤销。`)) {
        return;
      }

      try {
        await knowledgeBaseApi.deleteDocument(docId);
        toast.success('文档已删除');

        // 如果删除的是当前选中的文档，清理状态
        if (selectedDocId === docId) {
          setSelectedDocId(null);
          setSelectedDocDetail(null);
        }

        // 如果搜索结果中包含该文档，清理搜索结果
        if (searchResults?.hits.some((h) => h.document_id === docId)) {
          setSearchResults((prev) => prev ? {
            ...prev,
            hits: prev.hits.filter((h) => h.document_id !== docId),
            total: prev.total - 1,
          } : null);
        }

        void loadDocuments();
      } catch {
        toast.error('删除失败');
      }
    },
    [selectedDocId, searchResults, loadDocuments, toast],
  );

  // 选择文档查看详情
  const handleSelectDocument = useCallback(async (doc: KnowledgeDocumentItem) => {
    setSelectedDocId(doc.id);
    setDetailLoading(true);
    try {
      const detail = await knowledgeBaseApi.getDocument(doc.id);
      // Cast chunks to expected type
      const typedDetail: DocumentDetail = {
        ...detail,
        chunks: (detail.chunks || []) as Array<{ content?: string; chunk_index?: number }>,
      };
      setSelectedDocDetail(typedDetail);
    } catch {
      toast.error('加载文档详情失败');
      setSelectedDocDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, [toast]);

  // 复制内容
  const handleCopy = useCallback(
    async (content: string) => {
      try {
        await navigator.clipboard.writeText(content);
        toast.success('已复制到剪贴板');
      } catch {
        toast.error('复制失败，请检查浏览器权限设置');
      }
    },
    [toast],
  );

  // 关闭详情
  const handleCloseDetail = useCallback(() => {
    setSelectedDocId(null);
    setSelectedDocDetail(null);
  }, []);

  return (
    <div className="flex h-[calc(100vh-5rem)] w-full min-w-0 flex-col overflow-hidden sm:h-[calc(100vh-5.5rem)] lg:h-[calc(100vh-2rem)]">
      {/* 页面头部 */}
      <header className="mb-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <BookOpen className="h-6 w-6 text-cyan" aria-hidden="true" />
          <h1 className="text-2xl font-bold text-foreground">知识库</h1>
        </div>
      </header>

      {/* 工具栏 */}
      <KnowledgeToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSearch={handleSearch}
        searchLoading={searchLoading}
        documentCount={documents.length}
        onUploadClick={() => openDialog('upload')}
        onTextClick={() => openDialog('text')}
        onUrlClick={() => openDialog('url')}
      />

      {/* 主内容区 */}
      <main className="flex-1 overflow-y-auto rounded-[1.25rem] border border-white/8 bg-card/82 p-5 shadow-soft-card">
        {/* 有搜索 query 时显示搜索结果，否则显示文档列表 */}
        {searchQuery.trim() ? (
          <KnowledgeSearchResults
            results={searchResults}
            loading={searchLoading}
            query={searchQuery}
            onCopy={handleCopy}
          />
        ) : (
          <KnowledgeDocumentList
            documents={documents}
            loading={documentsLoading}
            selectedDocId={selectedDocId}
            onSelect={handleSelectDocument}
            onDelete={(docId: string) => {
              const doc = documents.find((d) => d.id === docId);
              if (doc) {
                void handleDelete(docId, doc.title);
              }
            }}
          />
        )}
      </main>

      {/* 文档详情 Modal */}
      <KnowledgeDocumentDetail
        document={selectedDocDetail}
        loading={detailLoading}
        onClose={handleCloseDetail}
        onCopy={handleCopy}
      />

      {/* 创建文本文档 Modal */}
      <KnowledgeCreateTextModal
        isOpen={activeDialog === 'text'}
        loading={createLoading}
        title={createTitle}
        content={createContent}
        tags={createTags}
        sourceUrl={createSourceUrl}
        sourceType={createSourceType}
        error={createError}
        onClose={closeDialog}
        onTitleChange={setCreateTitle}
        onContentChange={setCreateContent}
        onTagsChange={setCreateTags}
        onSourceUrlChange={setCreateSourceUrl}
        onSourceTypeChange={setCreateSourceType}
        onSubmit={handleCreateText}
      />

      {/* URL 创建 Modal */}
      <KnowledgeCreateUrlModal
        isOpen={activeDialog === 'url'}
        loading={urlLoading}
        url={urlInput}
        title={urlTitle}
        tags={urlTags}
        error={urlError}
        onClose={closeDialog}
        onUrlChange={setUrlInput}
        onTitleChange={setUrlTitle}
        onTagsChange={setUrlTags}
        onSubmit={handleCreateUrl}
      />

      {/* 文件上传 Dialog */}
      <KnowledgeUploadDialog
        isOpen={activeDialog === 'upload'}
        loading={uploadLoading}
        file={uploadFile}
        tags={uploadTags}
        onClose={closeDialog}
        onFileSelect={setUploadFile}
        onTagsChange={setUploadTags}
        onUpload={handleUpload}
        fileInputRef={fileInputRef}
      />

      {/* Toast 通知 */}
      <ToastContainer toasts={toast.toasts} onDismiss={toast.dismiss} />
    </div>
  );
}

export default KnowledgeBasePage;
