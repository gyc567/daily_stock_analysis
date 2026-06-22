import apiClient from './index';
import { API_BASE_URL } from '../utils/constants';
import { createApiError, isApiRequestError, parseApiError } from './error';
import type { ChatSessionItem, ChatSessionMessage } from './agent';

export interface ZhengxiChatStreamOptions {
  signal?: AbortSignal;
}

export interface ZhengxiChatRequest {
  message: string;
  session_id?: string;
  context?: unknown;
}

/**
 * 郑希投研分析 API 客户端。
 *
 * 与问股 `agentApi` 结构对齐（满足 `ChatStoreApi` 接口），但：
 * - 路径前缀 `/api/v1/zhengxi/...`（独立 endpoint，走郑希专属 executor）；
 * - 无 skills / sendChat（郑希无技能选择、无通知发送）；
 * - 会话由后端按 `zhengxi:` 前缀隔离，前端无需传 user_id。
 */
export const zhengxiApi = {
  async getChatSessions(limit = 50): Promise<ChatSessionItem[]> {
    const response = await apiClient.get<{ sessions: ChatSessionItem[] }>(
      '/api/v1/zhengxi/chat/sessions',
      { params: { limit } },
    );
    return response.data.sessions;
  },

  async getChatSessionMessages(sessionId: string): Promise<ChatSessionMessage[]> {
    const response = await apiClient.get<{ messages: ChatSessionMessage[] }>(
      `/api/v1/zhengxi/chat/sessions/${sessionId}`,
    );
    return response.data.messages;
  },

  async deleteChatSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/api/v1/zhengxi/chat/sessions/${sessionId}`);
  },

  async chatStream(
    payload: ZhengxiChatRequest,
    options?: ZhengxiChatStreamOptions,
  ): Promise<Response> {
    const base = API_BASE_URL || '';
    const url = `${base}/api/v1/zhengxi/chat/stream`;
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include',
        signal: options?.signal,
      });

      if (response.ok) {
        return response;
      }

      const contentType = response.headers.get('content-type') || '';
      let responseData: unknown = null;
      if (contentType.includes('application/json')) {
        responseData = await response.json().catch(() => null);
      } else {
        responseData = await response.text().catch(() => null);
      }

      const parsed = parseApiError({
        response: {
          status: response.status,
          statusText: response.statusText,
          data: responseData,
        },
      });
      throw createApiError(parsed, {
        response: {
          status: response.status,
          statusText: response.statusText,
          data: responseData,
        },
      });
    } catch (error: unknown) {
      if (isApiRequestError(error)) {
        throw error;
      }
      if (error instanceof Error && error.name === 'AbortError') {
        throw error;
      }

      const parsed = parseApiError(error);
      throw createApiError(parsed, { cause: error });
    }
  },
};
