import { createAgentChatStore } from './agentChatStore';
import { zhengxiApi } from '../api/zhengxiChat';

// 复用问股 store 的消息类型（郑希与问股消息结构一致）
export type { Message, ProgressStep } from './agentChatStore';

/**
 * 郑希投研分析聊天 store（独立实例）。
 *
 * 与问股 `useAgentChatStore` 隔离：独立的 messages / sessions / sessionId，
 * 独立的 localStorage key（`dsa_zhengxi_session_id`），独立的完成 badge
 * 路由判断（`/zhengxi`）。复用同一套 store 逻辑（`createAgentChatStore`）。
 */
export const useZhengxiChatStore = createAgentChatStore({
  api: zhengxiApi,
  storageKey: 'dsa_zhengxi_session_id',
  routePath: '/zhengxi',
});
