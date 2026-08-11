# loop-run-log.md — Loop Run Log

> 记录所有 Loop 运行历史，用于分析和优化。

## 日志格式

```markdown
### YYYY-MM-DD HH:MM:SS

| 字段 | 值 |
|------|-----|
| Loop | <name> |
| Level | <L1|L2|L3> |
| Duration | <seconds>s |
| Tokens | <input>/<output> |
| Result | <success|failure|skipped|paused> |
| Trigger | <scheduled|manual|ci-failure> |
```

---

<!-- 由 workflow 自动追加 -->

### 2026-08-06 Loop Ready 审计与修复

| 字段 | 值 |
|------|-----|
| Loop | Manual Audit |
| Level | - |
| Duration | ~20min |
| Tokens | - |
| Result | success |
| Trigger | manual |
| 备注 | 修复 LOOP.md Score、LOOP_CONSTRAINTS.md 路径、require-review 返回值 |

### 2026-08-11 10:12 前后端本地启动 + 验证

| 字段 | 值 |
|------|-----|
| Loop | Manual — Dev Bootstrap |
| Level | L1 |
| Duration | ~4 min |
| Tokens | 估算 ~25k（命令与探针为主） |
| Result | success |
| Trigger | manual |
| Sub-agents | 0 |
| 备注 | `scripts/start-dev.sh` 一键拉起后端 (uvicorn PID 11500, :8000) + 前端 (vite PID 11518, :5173)。健康检查全绿：`/health` 200、`/api/health` 200、`/docs` 200、`/api/v1/agent/skills` 200 返回 skills 列表。日志路径：`logs/backend.log`、`logs/frontend.log`。风险：启动时一条 pydantic v1→v2 `'fields' removed` 的 UserWarning 遗留（与本次无关）。 |

### 2026-08-11 10:12→10:55 Watchlist 渲染缺失（feature + 3-bug 修复）

| 字段 | 值 |
|------|-----|
| Loop | Manual — Bug Fix + Feature |
| Level | L2 |
| Duration | ~45 min |
| Tokens | 估算 ~75k（多次 grep / read / 浏览器探测 / 编辑 / 测试） |
| Result | success |
| Trigger | manual (user report) |
| Sub-agents | 0 |
| Iteration 1 | 复现：浏览器 DOM 证据 + `curl /api/v1/stocks/watchlist` 200 返回 11 只但首页 body 只有「开始分析」empty state。根因：`useWatchlist` 仅用于单股 toggle，无任何组件渲染 `watchlistCodes` 列表。修复：新增 `WatchlistPanel`（含 Badge chip / 加载 / 空态 / 折叠溢出） + i18n 5 键 × 2 语言 + HomePage 侧边栏顶部接入 + `handleWatchlistSelect` 复用 `submitAnalysis` 触发单股分析。Issue 落档到 `.claude/reviews/issue-watchlist-not-shown.md`（仓库 GitHub issues 已禁用，无法 `gh issue create`）。验证：`npm run lint` 0 warning、`npm run build` 4.95s、`npm run test -- WatchlistPanel` 5/5、dev bundle 含 `<WatchlistPanel codes={watchlistState.watchlistCodes} ...>`。未做：「分析全部」按钮（Ponytail 原则下不绕过 store）；commit/PR（AGENTS.md 硬规则待 user 确认）。 |
| Iteration 2 | 用户报告 `ReferenceError: Cannot access 'handleSubmitAnalysis' before initialization`（HomePage 整体崩溃）+ `DashboardPanelHeader is not defined`（WatchlistPanel）+ 大量 `:5173/api/v1/history/stocks?start_date=...&end_date=...` 500。根因 1：iteration 1 把 `handleWatchlistSelect` 放在 `handleSubmitAnalysis` 之后，但 `useMemo(sidebarContent)` 工厂首次渲染就闭包引用它，触发 TDZ。修复：把 `handleWatchlistSelect` 提到 `useWatchlist()` 之后，body 改用 `submitAnalysis` store action 直接调用。根因 2：截图时刻的 Vite HMR 缓存态（`?t=1786414982692`），实际文件 `import { DashboardPanelHeader }` 已正确，硬刷新即可；不需改代码。根因 3：`AnalysisHistory` ORM 模型新增 5 列（`research_framework` / `bayesian_framework` / `supply_chain` / `value_scenarios` / `investment_conclusion`）但旧迁移 `migrate_analysis_history_20250625.py` 早于这 5 列，DB schema 漂移 → `no such column` 500。修复：新建 `scripts/migrate_analysis_history_20260811.py` 幂等 ALTER TABLE 5 列 + backend 重启拾取新 schema。验证：5 列添加成功（DB 22 列）、`/api/v1/history/stocks?limit=5` 200、用户原始 URL 200、`/health` 200、`npm run lint` 0 warning、`npm run build` 4.96s、WatchlistPanel 测试 5/5、Vite HMR 最后一行 10:54:31 clean、backend log 无 traceback。 |
| Friction | (a) `xd-open` / `browser` 工具在多轮 session 中后段报 `Workspace not found`，浏览器交互验证降级为 Vite-served bundle 静态证据 + vitest 行为契约；(b) Bash cell 的 `cwd` 跨 cell 漂移，必须每条命令显式带 `cwd`；(c) `state.is` 一开始对 `State Block` 渲染调试时把 import 行错当成 hunk body 投递，edit 静默未报但 `home-surface-chip` 是凭空 class 名 → 后续切换 `Badge` 才稳。 |
| Adjustment | (1) 写新组件时严格走「先看既有 dashboard 组件的 class token 表」+ 「先建一个空组件 + 测试 + lint 再加 prop」可减少自造 class 名；(2) `useCallback` 引用链跨 useMemo 时优先用 store action 叶子，不要再多包一层；(3) 任何 ORM 模型加列后必须同步 `scripts/migrate_*.py`，并在 PR 描述里写明「需先跑迁移再启后端」。 |
