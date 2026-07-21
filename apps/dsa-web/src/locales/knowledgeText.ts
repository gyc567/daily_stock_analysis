import type { UiLanguage } from '../i18n/uiText';
import type { SourceType } from '../api/knowledgeBase';
import type { KnowledgeChunkHit } from '../api/knowledgeBase';

type ValidationStatus = KnowledgeChunkHit['validation_status'];

export const KNOWLEDGE_SOURCE_TYPE_LABELS: Record<UiLanguage, Record<SourceType, string>> = {
  zh: { text: '纯文本', markdown: 'Markdown', pdf: 'PDF', url: '网页' },
  en: { text: 'Text', markdown: 'Markdown', pdf: 'PDF', url: 'Web page' },
};

export const KNOWLEDGE_VALIDATION_STATUS_LABELS: Record<UiLanguage, Record<ValidationStatus, string>> = {
  zh: { VERIFIED: '已验证', CONFLICT: '存在冲突', USER_ONLY: '用户上传', PENDING: '待验证' },
  en: { VERIFIED: 'Verified', CONFLICT: 'Conflict', USER_ONLY: 'User uploaded', PENDING: 'Pending' },
};

export const KNOWLEDGE_TEXT = {
  zh: {
    title: '知识库',
    searching: '搜索中…',
    emptyQueryTitle: '输入关键词搜索知识库',
    emptyQueryHint: '支持股票代码、行业、主题等关键词',
    emptyResultsTitle: '未找到相关文档',
    emptyResultsHint: '尝试其他关键词，或上传相关文档',
    unavailableTitle: '搜索暂不可用',
    unavailableFallback: '服务暂时不可用，请稍后重试',
    resultsHeading: '搜索结果',
    resultsCount: '{count} 个结果',
    similarity: '相似度 {percent}%',
    copyContent: '复制内容',
    openSourceLink: '打开原文链接',
  },
  en: {
    title: 'Knowledge Base',
    searching: 'Searching…',
    emptyQueryTitle: 'Enter keywords to search the knowledge base',
    emptyQueryHint: 'Supports stock codes, sectors, themes and more',
    emptyResultsTitle: 'No matching documents',
    emptyResultsHint: 'Try other keywords or upload a related document',
    unavailableTitle: 'Search unavailable',
    unavailableFallback: 'Service is temporarily unavailable. Please try again later.',
    resultsHeading: 'Search results',
    resultsCount: '{count} results',
    similarity: 'Similarity {percent}%',
    copyContent: 'Copy content',
    openSourceLink: 'Open source link',
  },
} as const;

export const KNOWLEDGE_DOCUMENT_LIST_TEXT = {
  zh: {
    loading: '正在加载…',
    emptyTitle: '暂无文档',
    emptyHint: '上传文件或粘贴文本创建文档',
    chunksCount: '{count} 个内容片段',
    deleteAria: '删除文档：{title}',
    tagOverflow: '其余 {count} 个',
    unknownSourceType: '其他来源',
  },
  en: {
    loading: 'Loading…',
    emptyTitle: 'No documents',
    emptyHint: 'Upload a file or paste text to create a document',
    chunksCount: '{count} chunks',
    deleteAria: 'Delete document: {title}',
    tagOverflow: '+{count} more',
    unknownSourceType: 'Other source',
  },
} as const;

export const KNOWLEDGE_RUN_FALLBACK_TEXT = {
  zh: { eventTypeFallback: '其他事件' },
  en: { eventTypeFallback: 'Other event' },
} as const;

export function formatKnowledgeText(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (_match, key: string) => {
    const value = values[key];
    return value === undefined || value === null ? '' : String(value);
  });
}
