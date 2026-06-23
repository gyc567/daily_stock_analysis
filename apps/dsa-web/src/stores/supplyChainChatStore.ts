import { createAgentChatStore } from './agentChatStore';
import { supplyChainApi } from '../api/supplyChainChat';

/**
 * 供应链分析聊天 store（第 3 个独立实例）。
 *
 * 与问股 `useAgentChatStore`、郑希 `useZhengxiChatStore` 隔离：独立 messages /
 * sessions / sessionId，独立 localStorage key（`dsa_supply_chain_session_id`），
 * 独立的完成 badge 路由判断（`/supply-chain`）。复用同一套 store 逻辑。
 */
export const useSupplyChainChatStore = createAgentChatStore({
  api: supplyChainApi,
  storageKey: 'dsa_supply_chain_session_id',
  routePath: '/supply-chain',
});

export type { Message, ProgressStep } from './agentChatStore';
