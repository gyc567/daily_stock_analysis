import apiClient from './index';
import { API_BASE_URL } from '../utils/constants';
import { createApiError, isApiRequestError, parseApiError } from './error';
import type { ChatSessionItem, ChatSessionMessage } from './agent';

export interface SupplyChainChatStreamOptions {
  signal?: AbortSignal;
}

export interface SupplyChainChatRequest {
  message: string;
  session_id?: string;
  context?: unknown;
}

/**
 * 供应链分析 API 客户端（Serenity 方法）。
 *
 * 与问股 `agentApi` / 郑希 `zhengxiApi` 结构对齐（满足 `ChatStoreApi` 接口），
 * 路径前缀 `/api/v1/supply-chain/...`，会话由后端按 `supply_chain:` 前缀隔离。
 */
export const supplyChainApi = {
  async getChatSessions(limit = 50): Promise<ChatSessionItem[]> {
    const response = await apiClient.get<{ sessions: ChatSessionItem[] }>(
      '/api/v1/supply-chain/chat/sessions',
      { params: { limit } },
    );
    return response.data.sessions;
  },

  async getChatSessionMessages(sessionId: string): Promise<ChatSessionMessage[]> {
    const response = await apiClient.get<{ messages: ChatSessionMessage[] }>(
      `/api/v1/supply-chain/chat/sessions/${sessionId}`,
    );
    return response.data.messages;
  },

  async deleteChatSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/api/v1/supply-chain/chat/sessions/${sessionId}`);
  },

  async chatStream(
    payload: SupplyChainChatRequest,
    options?: SupplyChainChatStreamOptions,
  ): Promise<Response> {
    const base = API_BASE_URL || '';
    const url = `${base}/api/v1/supply-chain/chat/stream`;
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
