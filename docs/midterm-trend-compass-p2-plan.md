# 中期趋势罗盘 P2 实施计划

> 设计文档：`docs/midterm-trend-compass-plan.md`（v2 架构总览）
> P1 状态：✅ PR #41 已合入 main（commit `0de1246`），含 schema / engine / i18n / fetcher / render / CLI / 50 测试
> P2 入口：本文档
> 依赖：plan v2 §13 待确认项（8 条）需要 maintainer 显式确认或调整后才能动 rewriter

---

## 0. P2 范围一句话

把 P1 的"只算不算"升级成"会改写 buy/sell"，并按 `phase_decision_guardrail` → `daily_market_context_guardrail` → **`compass_rewriter`** 的顺序挂入 `daily_market_context_guardrail` 之后的处理链，最后把结果注入 `AnalysisContextPack.blocks["midtrend_compass"]`。

P2 **不动**：60 分钟分批、流动性硬过滤、回测胜率、4 小时执行层、跨市场。这些都是 P3-P5。

---

## 1. P2 模块结构

```
src/services/compass/
├── __init__.py
├── engine.py            ← 不动
├── fetcher.py           ← 替换为独立周线 fetcher（不再 resample）
├── i18n.py              ← 不动
├── render.py            ← 增强 vs_previous 渲染
├── rewriter.py          ★ P2 新增
├── action_mapper.py     ★ P2 新增（CompassAction → DecisionAction 8 档 / InvestmentConclusion 6 档）
└── snapshot.py          ★ P2 新增（收盘快照 / 较昨日 / history 写）

src/schemas/compass.py   ← 增加 vs_previous 序列化字段；不破坏 v1.0（升级到 1.1）
strategies/midterm_compass.yaml  ★ P2 新增（Skill 描述 / default_active 由 §13.4 决定）
```

---

## 2. P2 子任务拆分（按独立 PR / commit）

### PR-B1：ActionMapper（独立模块，零侵入）
| 项 | 内容 |
|---|---|
| 文件 | `src/services/compass/action_mapper.py` |
| 输入 | `MidtrendCompass` + 现有 `AnalysisResult` |
| 输出 | `DecisionAction`（8 档）、`InvestmentConclusion.action`（6 档）|
| 风险 | 改写 `InvestmentConclusion.action` 字段；需 reviewer 关注对老报告的兼容性 |
| 独立 | 完全独立；不需要 §13 |
| commit | `feat(compass): add action mapper (8-state DecisionAction + 6-state InvestmentConclusion)` |

### PR-B2：Rewriter（依赖 §13 items 1/2）
| 项 | 内容 |
|---|---|
| 文件 | `src/services/compass/rewriter.py` |
| 输入 | 初稿 action（来自 LLM 或 strategy skill）+ `MidtrendCompass` |
| 输出 | `final_action ∈ {buy, watch, sell}` + `action_reason: list[ActionReasonCode]` |
| 核心逻辑 | 严格按 plan §4.5.2 14 条改写表 |
| 依赖 | **§13 items 1/2**（两条默认必须 confirm）；§13 item 3（是否复用同一引擎） |
| commit | `feat(compass): add action rewriter (plan §4.5.2)` |

### PR-B3：Weekly Fetcher（替换 resample 兜底）
| 项 | 内容 |
|---|---|
| 文件 | `src/services/compass/fetcher.py`（替换 resample 段）|
| 输入 | code, lookback |
| 输出 | weekly_close Series |
| 实现 | 评估 baostock / akshare / iFinD 现有 fetcher 的周线能力，选最稳定一个扩；评估 `data_provider/` denylist 风险，必要时 `gate.yaml` 加 allowlist |
| 依赖 | `data_provider/` 在 denylist；需 maintainer 显式 override |
| commit | `feat(compass): add weekly fetcher via <data_source>` |

### PR-B4：Pipeline 接入（PR-B1/B2/B3 完成后）
| 项 | 内容 |
|---|---|
| 文件 | `src/core/pipeline.py` + `src/analyzer.py`（都在 require-review 路径）|
| 接入点 | 在 `phase_decision_guardrail.apply_phase_decision_guardrails(...)` 与 `daily_market_context_guardrail.apply_daily_market_context_guardrail(...)` 之间调用 `compass.rewriter.rewrite()`，然后用 `compass.action_mapper.map()` 写回 `result.decision_type` / `result.action` / `result.operation_advice`。 |
| 入口 | Web/API 手动分析同流程；crons（main.py --schedule）同流程 |
| 写入 | `analysis_history.context_snapshot.midtrend_compass`（已在 plan §9 v2 锁）|
| 风险 | 写盘（P3 之前不写 history；P2 也不写，由 P4 决定）|
| 依赖 | PR-B1 + PR-B2 + §13 全部 confirm；PR-B3（可降级到 resample） |
| commit | `feat(compass): wire rewriter + action_mapper into pipeline guardrail chain` |

### PR-B5：Strategy Skill YAML（依赖 §13 item 4）
| 项 | 内容 |
|---|---|
| 文件 | `strategies/midterm_compass.yaml` |
| 内容 | skill 描述、`default_active` 由 §13 item 4 决定（默认 `false`）、`market_regimes`、`required_tools` |
| 接入 | 现有 `src/agent/skills/base.py` 自动加载新 yaml |
| commit | `feat(strategies): add midterm_compass skill yaml` |

---

## 3. P2 与现有 Guardrail 的串联顺序（plan §4.5.1）

```
phase_decision_guardrail  → daily_market_context_guardrail
                              ↓
                       compass_rewriter.rewrite(initial_draft, compass_state)
                              ↓
                       action_mapper.map(compass_state.final_action)
                              ↓
                       final AnalysisResult.decision_type / .operation_advice
```

- **critical**：三者最保守结果生效（plan §4.5.1）；compass rewriter 只在 compass_state  可用时介入
- **降级路径**：compass_state 不可用（fetch 失败）→ rewriter 透传，不改写
- **监控**：每次改写必须输出 `action_reason_codes[]` 落 `analysis_history.context_snapshot.midtrend_compass`，便于回溯

---

## 4. P2 状态机

```
initial_draft  →  [compass_rewriter]  →  final_action
   ↓                  ↓                     ↓
   来源（LLM         plan §4.5.2           buy/watch/sell
   或 strategy       14 条硬约束
   skill）
```

`final_action` 通过 `action_mapper` 映射：
| final_action | DecisionAction | InvestmentConclusion.action |
|---|---|---|
| `buy` | `buy` | `建仓` |
| `watch` | `watch` | `观察` |
| `sell` | `sell` | `止损` |

---

## 5. P2 测试矩阵

| 测试 | 类型 | 来源 |
|---|---|---|
| `test_action_mapper_compass_to_decision` | 单测 | PR-B1 |
| `test_action_mapper_compass_to_investment` | 单测 | PR-B1 |
| `test_rewriter_buy_to_watch_weekly_bear` | 单测 | PR-B2 |
| `test_rewriter_sell_blocked_by_resting` | 单测 | PR-B2 |
| `test_rewriter_l1_l2_bear_default_sell` | 单测 | PR-B2 |
| `test_rewriter_l3_exhausted_downgrades_sell_to_watch` | 单测 | PR-B2 |
| `test_rewriter_intraday_unconfirmed_blocks_buy` | 单测 | PR-B2 |
| `test_rewriter_data_missing_defaults_watch` | 单测 | PR-B2 |
| `test_weekly_fetcher_*` | 集成 / mock | PR-B3 |
| `test_pipeline_rewriter_runs_in_chain` | 端到端 | PR-B4 |
| `test_history_snapshot_persists_midtrend_compass` | 集成 | PR-B4 |
| `test_strategy_yaml_default_active_false` | 配置 | PR-B5 |
| `test_strategy_yaml_loads_via_skill_manager` | 配置 | PR-B5 |

预期 P2 测试增量：约 40-50 个新用例（rewrite + mapper + pipeline + strategy YAML）。

---

## 6. P2 与 plan v2 §13 待确认项的依赖

PR-B2 / PR-B4 启动前，§13 必须先 confirm。建议 maintainer 在 PR #41 review 时一次性答复：

- **§13.1** 周线 bear 时个股最高观望 / 仅风险提示 / 仅 L0=weekly_bear 时禁用 buy
- **§13.2** L1+L2 bear 默认 sell；L3 exhausted 降级为 watch
- **§13.3** 大盘复盘是否复用同一引擎
- **§13.4** 罗盘默认启用策略（`default_active`）
- **§13.5** 新配置项命名（`COMPASS_ENABLED` 等）
- **§13.6** i18n 语种范围（zh / en / 繁中）
- **§13.7** Web 手动分析是否写 history
- **§13.8** Backtest 接入时间点

确认后开 PR-B1（不依赖 §13）和 PR-B2（依赖 §13.1/§13.2）并行。

---

## 7. P2 风险登记

| 风险 | 触发 | 缓解 |
|---|---|---|
| `InvestmentConclusion.action` 字段被改写 → 老历史报告兼容性 | PR-B1 | `action_mapper` 是纯函数映射，老 action 是 `观察`/`加仓` 等，PR-B1 不动 Analyzer；PR-B4 接入后才生效；写入 context_snapshot 不覆盖已有字段 |
| rewriter 与 LLM 输出不一致 → 用户看到"模型说 buy / 系统说 watch" | PR-B4 | 报告里同时输出 LLM 原始建议 + rewriter 最终 action + reason codes（plan §3.2） |
| 周线 fetcher 引入新数据源 → denylist 风险 | PR-B3 | 维护者需显式 override；不引入新 fetcher 则维持 resample 兜底 |
| `gate.yaml` max-files: 10 → P2 一次 5 commit / 多文件可能再次超限 | 所有 | 同 P1：申请 waiver 或拆子目录 |
| phase / action 在中文 / 英文 label 漂移 | PR-B1 | i18n 单测（已存在）+ CI 中加 en 等价检查 |

---

## 8. P2 验收标准（对应 plan §11）

P2 完成后必须满足：
- §11.1 #1-10 全部在 P1 + P2 范围内已覆盖
- §11.2 防御层验收：mypy --strict 跨 compass 全部 0 错误；pyright 跨 compass 全部 0 错误
- §11.3 集成验收：
  - phase + market_context + compass rewriter 三者最保守结果生效
  - rewriter 输出落 `analysis_history.context_snapshot.midtrend_compass`
  - crons / Web / API 三入口路径一致
- §11.4 文档与变更：`docs/CHANGELOG.md` `[Unreleased]` 同步、`docs/*.md` 同步、`README.md` 不变
- 复测 PR #41 验收矩阵 + P2 新增 40+ 用例全过

---

## 9. 时间线（待 §13 答复后调整）

```
[维护者答复 §13]  →  PR-B1 + PR-B2 + PR-B3 并行   →  PR-B4 串联   →  PR-B5   →  Draft PR #42
       ↓                       ↓                       ↓            ↓
  预计 1 天           预计 3-5 天              预计 2 天       预计 1 天   预计 1 天
```

总计：依赖 §13 答复后约 1-2 周内可合入。
