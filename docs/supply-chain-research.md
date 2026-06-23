# 供应链分析（Serenity 方法）

「供应链分析」是一个独立的对话框功能（侧栏入口 `/supply-chain`），用 **Serenity「供应链卡点猎手」9 步深度调研方法**做投研：主题扫描、单公司挑战、候选对比、瓶颈打分。所有结论**标注证据强度、不编造数据、不给买卖指令**。

## 功能定位

用户提问 → 系统按 9 步 pipeline 深度调研 → 返回白话排序 + 卡点层 + 证据 + 证伪条件。

方法论来源：开源 skill [serenity-skill](https://github.com/gyc567/serenity-skill)（MIT，复刻公开投研方法），落盘在 `data/supply_chain_skill/`。

## 9 步 pipeline（核心方法论）

```
市场故事 → 系统变化 → 需要的零部件 → 产业链层级 → 稀缺约束（卡点）
       → 上市公司 → 证据 → 市场可能忽略了什么 → 什么会证伪
```

- 先排**价值链层级**（8 层 checklist：终端/集成/模块/芯片/工艺/设备/材料/基础设施），再排公司
- **稀缺层识别**：客户无它无法扩产、供应商少、验证周期长、扩产需特种设备/许可
- 候选池 ≥20 家（含"需降级的热门股"），证据 ≥25 源（条件性，工具/时间不允许则声明"初步筛选"）
- 证据分级：`primary`（交易所文件/年报/电话会/官方订单）/ `media` / `analysis` / `social` / `rumor`，无源标"待核验"

## 能力

| 能力 | 触发问法 | 工具 |
|---|---|---|
| 主题扫描 | "分析 A 股 AI 半导体供应链" | 复用问股工具（行情/新闻/基本面）+ 9 步 pipeline |
| 单公司挑战 | "挑战中际旭创是不是 CPO 核心" | 复用问股工具查数据 + 卡点核查 |
| 候选对比 | "比较几家光通信设备商" | 复用问股工具 + 横向排序 |
| 瓶颈打分 | "给 XX 打供应链瓶颈分" | `score_supply_chain_bottleneck`（8 因子 + 8 惩罚，满分 100） |
| 研究/学习对话 | "带我学这套方法" | serenity-dialogue-protocol（每轮一问） |

## 合规红线（必须遵守）

1. **禁止直接买卖指令**。强制措辞："我会按优先研究价值排序。买卖动作由你自己决定。"
2. **禁止炒作小票/社交驱动标的**；遇到先拉回证据、流动性、稀释、估值。
3. **禁止编造**价格/文件/客户/订单/合同/市值。数字必须有源，无源标"待核验"。
4. 输出先结论（纯文本，非券商报告腔）→ 层级排序 → 紧凑表格（标的|卡住的环节|为什么排这里|关键证据|主要风险）→ 证伪条件 + 下一步。

## 技术架构

- **executor**：`src/agent/supply_chain_executor.py` 的 `SupplyChainExecutor`，复用 `run_agent_loop` / `LLMToolAdapter` / `conversation_manager` / SSE 包装。
- **工具集**：**复用问股 `get_tool_registry()` 的 18 个工具**（行情/基本面/新闻/技术）+ 1 个供应链打分工具，装入独立 ToolRegistry 实例（复制问股工具，不污染全局单例）。
- **打分**：`src/services/supply_chain/scorecard.py` 通过 importlib 加载 `data/supply_chain_skill/scripts/serenity_scorecard.py`（纯函数，无需 subprocess）。
- **system prompt**：运行时组装 SKILL.md + 核心 5 references（deep-research-workflow / evidence-ladder / market-source-playbook / serenity-dialogue-protocol / output-style-and-language）+ 合规红线 + **工具结果摘要约束**。
- **API**：`api/v1/endpoints/supply_chain.py`，`POST /api/v1/supply-chain/chat/stream`（SSE）+ 会话 CRUD。
- **会话隔离**：`supply_chain:` 前缀，复用 `session_prefix` 过滤，与问股/郑希 3 路不串台。
- **前端**：`pages/SupplyChainChatPage.tsx`，独立路由 + `useSupplyChainChatStore`（第 3 个工厂实例）。

## 长任务特性（与问股/郑希的关键差异）

供应链是**深度调研**，不是快速问答：

- `max_steps=40`（问股/郑希 10），9 步 pipeline 多次工具调用
- `wall_clock=1200s`（20 分钟上限），单次问答通常 5–15 分钟
- SSE event 间隔 timeout **1200s**（问股/郑希 300s）
- 前端空态/副标题提示"深度调研模式，预计 5–10 分钟"
- SSE 进度事件（thinking/tool_start/tool_done）实时显示调研过程，是天然进度条
- `max_steps` 硬编码在 `build_supply_chain_executor`（方案 A），**不碰 `config.agent_max_steps`**，问股/郑希零影响

## 成本预期

单次深度调研 = 40 步 LLM 往返 + 几十次工具调用 ≈ **50–200K tokens**（约为问股/郑希的 10–20 倍）。成本计入系统 `llm_usage`（`/api/v1/usage` 可查）。当前版本无配额限速，后续可加每会话深度调研次数限制。

## 数据局限（诚实处理）

Serenity 要求 ≥25 源含公告/招投标/环评/专利等深度源；项目 `data_provider` 只有行情/新闻/基本面。pipeline 会完整跑，但深度源靠：
- 复用问股工具（`search_comprehensive_intel` 间接搜公告/财报线索）
- LLM 自身知识
- evidence-ladder 的"待核验"标注

二期接公告/招投标专用源可提升证据精度。

## 部署提示（nginx / 反向代理超时分层）

**分层原则：外层（nginx/proxy）超时必须 ≥ 内层（app）超时**，否则代理会在 app 仍在合法处理时先掐断连接。app 侧上限 = SSE event 间隔 timeout `1200s` = executor `wall_clock=1200s`，因此 nginx `proxy_read_timeout` 必须 **≥ 1200s**（建议留余量 `1300s`）。

项目自带链路（FastAPI + uvicorn）**不会截断** 1200s 长任务。但若部署在 nginx/反向代理后，默认 `proxy_read_timeout 60s` **会截断** SSE 流，必须按上面的分层原则配置：

```nginx
location /api/ {
    proxy_read_timeout 1200s;     # ≥ app SSE/executor 上限 1200s（建议 1300s 留余量）
    proxy_send_timeout 1200s;
    proxy_buffering off;          # 或依赖响应头 X-Accel-Buffering: no（后端已设）
}
```

> `proxy_read_timeout` 在 nginx **每收到一个 SSE event 就重置**，所以只要调研过程中事件间隔远小于此值（通常每几秒一条 thinking/tool 事件），连接就不会被掐；该上限只在"长时间无任何事件"的极端静默（如单次 LLM 调用 >1200s）时触发。

**客户端断连的孤儿线程成本（已知边界）**：SSE 端点把 executor 跑在线程池里，Python 线程无法强制取消。若客户端中途断开或代理提前掐断，后端 executor 仍会跑到自身 `wall_clock=1200s` 上限才结束——最坏情况会多消耗约一次深度调研的 token（50–200K）。当前不做协同取消（避免改动共享 `run_agent_loop`，保持问股/郑希零影响）；二期可给 `run_agent_loop` 加可选取消信号。

## 验证

```bash
python scripts/check_supply_chain_data.py        # 数据完整性
python -m pytest tests/test_supply_chain_services.py   # scorecard + 工具
```

## 配置

复用现有 Agent 配置（`AGENT_MODE` / LLM 渠道），无新增环境变量。Agent 未启用时供应链端点返回 400。`max_steps=40` / `wall_clock=1200s` 在 `build_supply_chain_executor` 硬编码（后续可抽到 config）。

## 后续版本（未实现）

- **token budget 熔断**：当前靠 max_steps + wall_clock + prompt 摘要约束；二期给 `run_agent_loop` 加可选 `token_budget` 参数（默认 None 不影响问股/郑希）。
- **公告/招投标/环评专用工具**：提升证据精度（当前靠搜索间接）。
- **每会话深度调研配额**：控制成本。
- **深度调研长任务 UI**：更明显的进度/取消/后台化。
