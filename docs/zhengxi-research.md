# 郑希投研分析

「郑希投研分析」是一个独立的对话框功能（侧栏入口 `/zhengxi`），用自然语言回答关于易方达基金经理**郑希**的投研问题：他的投资观点、管理的基金数据、以及用他的框架给基金打分。所有回答**可溯源、不杜撰**。

## 功能定位

用户提问 → 系统基于三类可溯源材料作答：

1. **郑希公开观点语料**：76 篇季报/中报/年报、基金经理手记、媒体专访（2012–2026），段落级检索。
2. **投资方法框架**：从语料蒸馏的 `method.md`，每条配原话佐证。
3. **真实基金数据**：郑希管理过的 8 只基金（4 在任 + 4 曾任）的季度持仓、净值、规模、任职回报。

数据迁移自开源知识库 [zhengxi-views](https://github.com/gyc567/zhengxi-views)（MIT License，公开内容），落盘在 `data/fund_manager_views/zhengxi/`。

## 能力（MVP 三件）

| 能力 | 触发问法 | 后端工具 |
|---|---|---|
| **溯源问答** | 「郑希怎么看光通信」 | `search_zhengxi_views`（语料段落检索，带出处） |
| **业绩/持仓查询** | 「001513 最近持仓」「信息产业今年涨多少」 | `get_zhengxi_fund_data`（最新持仓+集中度+换手+收益+回撤+规模） |
| **框架评分** | 「用郑希框架给 001513 打分」 | `score_fund_zhengxi`（六维证据档案+评分指引，满分 100） |

## 诚实红线（回答必须遵守）

1. **三种话分开**：【郑希原话】（忠引 + 自然出处）/【按其方法的推演】（首句声明非本人观点）/【需核实的事实】（标注，不编造）。
2. **不报内部记号**：回答里不出现文件路径、`method.md`、章节号、工具字段名等。
3. **数据必标日期**：持仓/业绩带季度，只来自工具返回，静态快照非实时。
4. **评分守定位**：六维评的是「与郑希风格的契合度」，不是基金优劣；防御型/红利/纯债天然低分是正常的。

> 红线在当前版本由 system prompt 落实（method + scorecard + 红线全文注入），工具返回值带 `source`/`quote` 字段引导引用。

## 技术架构

- **后端 executor**：`src/agent/zhengxi_executor.py` 的 `ZhengxiExecutor`，独立于问股的 `AgentExecutor`（不耦合股票 scope/决策仪表盘），但复用 `run_agent_loop` / `LLMToolAdapter` / `conversation_manager` / SSE 包装。
- **工具**：`src/agent/tools/zhengxi_tools.py`（3 个 `ToolDefinition`），注册到**独立** `ToolRegistry` 实例，不进入问股的全局工具集。
- **数据层**：`src/services/zhengxi/`（`corpus.py` 检索、`fund_data.py` 基金摘要、`scoring.py` 机械指标、`synonyms.py` 同义词扩展）。
- **API**：`api/v1/endpoints/zhengxi.py`，`POST /api/v1/zhengxi/chat/stream`（SSE）+ 会话 CRUD，事件类型与问股一致。
- **会话隔离**：`session_id` 统一 `zhengxi:` 前缀，列表查询固定按 `zhengxi` 前缀过滤，复用 `src.storage.get_chat_sessions(session_prefix=...)`，**后端零 schema 改动**，与问股会话天然隔离。
- **前端**：`apps/dsa-web/src/pages/ZhengxiChatPage.tsx`，独立路由 + `useZhengxiChatStore`（store 工厂化实例，独立 localStorage key `dsa_zhengxi_session_id`）。复用问股的 `.chat-*` CSS 与通用组件。

## 数据时效

基金数据为**静态快照**（来源：天天基金/易方达官网公开数据），最新到 2026 年 Q1。数据会随时间过期，回答中已标注「静态快照、非实时」。刷新方式：重新运行 zhengxi-views 的 `fetch_fund_data.py` 更新 `data/fund_manager_views/zhengxi/fund_data/`（本项目 MVP 未集成实时抓取）。

## 配置

复用现有 Agent 配置（`AGENT_*` 环境变量与 LLM 渠道），无新增配置项。Agent 未启用时郑希端点返回 400（与问股一致）。

## 验证

```bash
# 数据完整性校验
python scripts/check_zhengxi_data.py

# 检索召回验证（15 条溯源黄金集 + 同义词扩展）
python scripts/check_zhengxi_retrieval.py
```

评测黄金集：`data/fund_manager_views/zhengxi/golden_questions.json`（20 条，覆盖溯源/查询/评分/前瞻/红线）。

## 后续版本（未实现）

- **实时全市场任意基金对比**：MVP 仅支持郑希管理过的 8 只基金；二期评估在 `data_provider/` 新建 `FundFetcher` 子体系（akshare 公募基金接口，独立抽象，不走股票 OHLCV 主链路）。
- **向量 RAG**：当前为关键词检索 + 同义词扩展；语料进一步增长或召回质量要求提升时，升级为向量检索。
- **诚实红线代码层强制**：当前靠 prompt；二期可在工具返回与 runner 增加出处追踪与原话/推演区分标注。
