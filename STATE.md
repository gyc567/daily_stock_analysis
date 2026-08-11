# Loop State — daily_stock_analysis

- [waiting on user] 确认工作树变更是否进入 commit + PR（按下面分组）：
  - 仓库协作代码（7 个，**不含 review artifact**）：
    - `apps/dsa-web/src/components/dashboard/WatchlistPanel.tsx` (new)
    - `apps/dsa-web/src/components/dashboard/__tests__/WatchlistPanel.test.tsx` (new)
    - `apps/dsa-web/src/components/dashboard/index.ts`
    - `apps/dsa-web/src/pages/HomePage.tsx` (TDZ fix + sidebar wire)
    - `apps/dsa-web/src/i18n/uiText.ts` (5 keys × 2 langs)
    - `scripts/migrate_analysis_history_20260811.py` (new)
    - `docs/CHANGELOG.md` (Unreleased entry)
  - Loop 元数据（3 个，可选入）：
    - `loop-run-log.md` / `STATE.md` / `loop-budget.md`
  - **不入库**（已被 `.gitignore:89:.claude/*` 显式忽略，留本地供 agent context）：
    - `.claude/reviews/issue-watchlist-not-shown.md`
    - `.claude/reviews/post-run-2026-08-11-watchlist-and-3-bugfix.md`
  - 数据库 schema 升级：`data/stock_analysis.db`（+5 cols）不入 git，仅本地

## High Priority (loop is acting or waiting on human)
- [waiting on user] 确认 8 个工作树变更是否进入 commit + PR：
  - `apps/dsa-web/src/components/dashboard/WatchlistPanel.tsx` (new)
  - `apps/dsa-web/src/components/dashboard/__tests__/WatchlistPanel.test.tsx` (new)
  - `apps/dsa-web/src/components/dashboard/index.ts`
  - `apps/dsa-web/src/pages/HomePage.tsx` (TDZ fix + sidebar wire)
  - `apps/dsa-web/src/i18n/uiText.ts` (5 keys × 2 langs)
  - `scripts/migrate_analysis_history_20260811.py` (new)
  - `docs/CHANGELOG.md` (Unreleased entry)
  - `data/stock_analysis.db` (schema +5 cols)
  - `.claude/reviews/issue-watchlist-not-shown.md` (issue draft, repo issues disabled)
  - `.claude/reviews/post-run-2026-08-11-watchlist-and-3-bugfix.md` (post-mortem)
- [waiting on user] 是否在 GitHub issues 启用后把 `.claude/reviews/issue-watchlist-not-shown.md` 落到上游 issue tracker

## Watch List
- `src/storage.py` 仍是 schema-drift 高发区：下次有人加 `Mapped[...]` 列，必须同步 `scripts/migrate_*.py`（见 post-run review L3）
- 浏览器交互验证工具 `xd-open` / `browser` 在长 session 后段不稳：以后写新 UI 时默认 fallback 走「Vite-served bundle grep + vitest 行为契约」+ 报告里说清楚「缺一道浏览器实测」
- `WatchlistPanel` 的「分析全部」按钮暂未做：当前 `submitAnalysis` store 只支持单股；批量需要先升级 store action（见 review Adjustment #2）

## Recent Noise (ignored this run)
- Vite HMR 偶发 `Could not Fast Refresh ("useUiLanguage" export is incompatible)`：与本次无关，长期存在
- 后端 `akshare not installed` warning：本次未触及
- pydantic v1→v2 `'fields' has been removed` UserWarning：本次未触及

## Post-Run Critique (from last run)
- High-noise: 无
- False positives: 1（用户报的 `DashboardPanelHeader is not defined` 是 Vite HMR 缓存态而非代码 bug）
- Deprioritize: 无
- Friction:
  - `xd-open` / `browser` 工具在长 session 后段报 `Workspace not found` → fallback 到 Vite-served bundle 静态证据
  - Bash cell `cwd` 跨调用漂移 → 必须每条命令显式带 `cwd`
  - `edit` 工具对「`PUT N*:` 当成 hunk body 投递 import 行」的边界条件有静默成功语义 → 提交后必须再 `read` 一次确认
- Adjustment:
  - 写新组件前先看既有同类组件的 class token 表（避免 `home-surface-chip` 这种自造 class）
  - `useCallback` 链跨 `useMemo` 工厂时优先用 store action 叶子
  - 任何 ORM 加列必须同步迁移脚本

---
Run log: loop-run-log.md（2026-08-11 10:12 / 10:55）