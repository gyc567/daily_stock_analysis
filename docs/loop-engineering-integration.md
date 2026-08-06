# Loop Engineering 集成方案

> 让开发和迭代更加高效

## 一、背景与目标

### 1.1 为什么引入 Loop Engineering

当前项目存在以下痛点：

| 痛点 | 影响 | Loop Engineering 解决方案 |
|------|------|--------------------------|
| Issue/PR 处理依赖人工 | 响应慢、容易遗漏 | 每日自动分流 + 状态追踪 |
| CI 失败需要人工排查 | 定位慢、重复劳动 | CI Sweeper 自动分析 + 建议修复 |
| Changelog 手动维护 | 容易遗漏、易出错 | 自动草稿 + 人类审核 |
| 代码规范依赖人工 review | 效率低、一致性差 | gate.yaml 机械执行 + CI 验证 |
| 依赖更新被动等待 | 安全风险 | 周期性主动检查 |

### 1.2 核心理念

> "Build the loop. But build it like someone who intends to stay the engineer, not just the person who presses go." — Addy Osmani

Loop Engineering 的核心是**用系统替代人工提示**，让开发者专注于高杠杆工作。

### 1.3 与现有 AGENTS.md 的关系

本方案是 `AGENTS.md` 的**扩展补充**，不是替代。

---

## 二、概念与术语

### 2.1 核心概念

| 概念 | 定义 | 在本项目中的应用 |
|------|------|-----------------|
| **Loop** | 递归目标：定义目的，让 agent 迭代直到完成或 escalation | 每日分流、CI 修复、依赖更新 |
| **Intent Debt** | 每次 session 冷启动时的意图缺失 | Skills 是偿还方式 |
| **Comprehension Debt** | 代码增长与理解之间的差距 | 定期 review + 日志 |
| **Harness** | 单个 agent 运行的环境 | CLI 配置 + 工具链 |
| **Maker/Checker** | 实现者与验证者分离 | 防止自评自过 |

### 2.2 三层自动化

| 层级 | 描述 | 自主程度 |
|------|------|----------|
| **L1** | 报告模式，人类决定行动 | 0% 自主 |
| **L2** | 辅助修复，人类审核后合并 | 50% 自主 |
| **L3** | 无人值守，自动修复 + 验证 | 90% 自主 |

### 2.3 六要素

| 要素 | 作用 | 本项目实现 |
|------|------|-----------|
| 1. 调度 | Loop 的心跳 | GitHub Actions cron |
| 2. Worktree | 并行隔离 | Git worktree |
| 3. Skills | 持久化意图 | `.claude/skills/loop-*` |
| 4. MCP/Connector | 外部集成 | GitHub API |
| 5. Sub-agents | Maker/Checker | 分离实现与验证 |
| 6. Memory/State | 持久状态 | `STATE.md` |

---

## 三、现有资产审计

### 3.1 已有 Skills

| Skill | 状态 | 说明 |
|-------|------|------|
| analyze-issue | ✅ 已有 | Issue 分析 |
| ponytail-review | ✅ 新增 | PR diff 审查 |
| ponytail-audit | ✅ 新增 | 仓库技术债务审计 |
| analyze-pr | ✅ 已有 | PR 审查 |
| fix-issue | ✅ 已有 | Issue 修复 |

### 3.2 已有 Workflows

| Workflow | 状态 | 说明 |
|----------|------|------|
| 00-daily-analysis.yml | ✅ | 每日股票分析 |
| ci.yml | ✅ | CI 门禁 |
| pr-review.yml | ✅ | PR 审查 |
| auto-tag.yml | ✅ | 自动版本标签 |
| type-safety.yml | ✅ | 类型安全 |

### 3.3 Loop Ready Score 预估

| 检查项 | 权重 | 当前得分 | 目标得分 |
|--------|------|---------|---------|
| 核心 Loop 文件 | 20% | 0 | 20 |
| Skills 完整性 | 20% | 15 | 20 |
| Workflows 覆盖 | 20% | 10 | 20 |
| 安全机制 | 20% | 5 | 20 |
| 文档 | 20% | 5 | 20 |
| **总分** | 100% | **7** | **100** |

---

## 四、文件体系设计

### 4.1 核心文件结构

```
daily_stock_analysis/
├── LOOP.md                    # Loop 运营总览
├── STATE.md                   # 当前 Loop 活跃状态
├── LOOP_BUDGET.md            # Token 预算配置
├── LOOP_CONSTRAINTS.md        # 约束规则
├── gate.yaml                  # 安全门禁配置
├── loop-run-log.md           # 运行日志
│
├── .claude/skills/
│   ├── loop-triage/         # 扩展
│   ├── loop-verify/         # 扩展
│   ├── loop-context/        # 新增
│   └── loop-plan/           # 新增
│
├── .github/workflows/
│   ├── loop-triage.yml      # 新增
│   ├── loop-ci-sweeper.yml  # 新增
│   └── loop-dep-sweeper.yml # 新增
│
└── scripts/loop/
    ├── loop-gate.sh         # 安全门禁检查
    ├── loop-audit.sh        # Loop Ready 审计
    └── loop-budget.sh       # 预算检查
```

---

## 五、安全机制

### 5.1 多层防御架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: gate.yaml (机械执行)                              │
│  • denylist 路径绝对禁止修改                                │
│  • max-files 限制单次修改数量                               │
│  • auto-merge-allowlist 控制自动合并权限                    │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: LOOP_CONSTRAINTS.md (契约约束)                   │
│  • 强制读取并遵守                                           │
│  • 80% 预算切换报告模式                                    │
│  • 禁止关闭 Issue/PR                                       │
│  • 最多 3 次尝试后 escalation                              │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Skills 约束 (意图编码)                           │
│  • loop-context: 前置检查                                  │
│  • loop-verify: 结果验证                                   │
│  • loop-triage: 仅报告，不修改                             │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Draft PR (人工审核)                              │
│  • 所有修复必须创建 Draft PR                                 │
│  • 人类审核后才能标记 Ready                                │
│  • CI 通过 + 人类 approval 才能合并                          │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
---

## 六、核心文件模板

### 6.1 LOOP.md — Loop 运营总览

```markdown
# LOOP.md — Daily Stock Analysis Loop Engineering

## 活跃 Loops

| Loop | Level | 频率 | Skill | 状态 |
|------|-------|------|-------|------|
| Daily Triage | L1 | 工作日 8:00 | `loop-triage` | 🚀 运行中 |
| CI Sweeper | L2 | 按需 | `loop-verify` | ⏸ 计划中 |
| Dependency Sweeper | L2 | 每周 | `loop-verify` | ⏸ 计划中 |

## 安全机制

- Kill Switch: `loop-pause-all` label
- 门禁: `gate.yaml`
- 约束: `LOOP_CONSTRAINTS.md`
- 预算: `LOOP_BUDGET.md`

## 本地开发

```bash
# 审计 Loop Ready
./scripts/loop/loop-audit.sh .

# 检查门禁
./scripts/loop/loop-gate.sh check --action auto-merge --paths "src/a.py"
```
```

### 6.2 STATE.md — 当前状态

```markdown
# STATE.md — Loop State

**Last run**: <!-- 由 workflow 自动填充 -->
**Updated by**: loop-triage workflow

## 高优先级 (Loop 正在处理或等待人类)

<!-- 由 loop-triage skill 自动更新 -->

## 观察列表

| Issue/PR | 状态 | 最后更新 | 备注 |
|----------|------|---------|------|
| - | - | - | - |

## 暂停开关

- Label: `loop-pause-all`
- 激活方式: 在任意 Issue 上添加 `loop-pause-all` label
- 恢复: 移除 label 并清理本文档中的暂停标记
```

### 6.3 LOOP_BUDGET.md — 预算控制

```markdown
# LOOP_BUDGET.md — Loop Budget

## 每日限制

| Loop | 最大运行/日 | 最大 Token/日 | 最大子代理/次 |
|------|------------|--------------|--------------|
| Daily Triage (L1) | 1 | 50k | 0 |
| CI Sweeper (L2) | 5 | 100k | 2 |
| Dependency Sweeper (L2) | 1 | 80k | 1 |

## 超预算处理

1. **80% 警告**: 切换到报告模式，暂停子代理
2. **100% 暂停**: 追加事件到 `loop-run-log.md`，打开维护者 Issue
3. **人工恢复**: 审核后调整预算或关闭 Loop

## Kill Switch

- Label: `loop-pause-all`

## 模型成本参考

| 模型 | Input $/1M | Output $/1M |
|------|------------|------------|
| GPT-4o | $2.5 | $10 |
| Claude 3.5 | $3 | $15 |
| Gemini 1.5 | $0.125 | $0.5 |
```

### 6.4 LOOP_CONSTRAINTS.md — 约束规则

```markdown
# LOOP_CONSTRAINTS.md — Loop Constraints

> **Agent 必须遵守的约束文件**。每次 Loop 运行前必须读取并遵守。

## 推送与合并

- ✅ 推送前必须告知人类
- ❌ **禁止自动合并到 main**（除依赖补丁外）
- ❌ 禁止在未告知的情况下推送代码

## 路径保护 (Denylist)

以下路径 **禁止** Loop 自动修改：

```
.env / .env.* / **/secrets/** / **/credentials/**
**/*_key* / **/*_secret*
auth/** / bot/** / data_provider/**
src/config/ / src/services/notification/ / src/services/bot/
```

## 代码质量

- ✅ 修复前必须运行测试
- ❌ **禁止禁用测试** 以通过 CI
- ✅ 每次修复 **不超过一个功能模块**
- ✅ 单项最多 **3 次尝试**，超出后 escalation

## 股票分析特定约束

- ❌ 禁止修改 `data_provider/` 中的数据源 fallback 优先级
- ❌ 禁止修改 `src/reports/` 中的报告模板结构
- ❌ 禁止修改通知渠道配置

## 错误处理

- ✅ 记录错误到 `loop-run-log.md`
- ✅ 创建 Issue 标记需要人工处理的问题
- ❌ **禁止静默失败**
```

### 6.5 gate.yaml — 安全门禁

```yaml
version: 1

denylist:
  - ".env"
  - ".env.*"
  - "**/secrets/**"
  - "**/credentials/**"
  - "**/*_key*"
  - "**/*_secret*"
  - "auth/**"
  - "bot/**"
  - "data_provider/**"

require-review:
  - ".github/workflows/**"
  - "docker/**"
  - "src/reports/**"
  - "src/analyzer/**"

max-files: 10

auto-merge-allowlist:
  - "docs/**/*.md"
  - "scripts/**/*.sh"
  - "src/**/*.py"
  - "tests/**/*"
  - "package.json"
  - "requirements.txt"
```

### 6.6 loop-run-log.md — 运行日志

```markdown
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
```

---

## 七、Skills 设计

### 7.1 loop-triage/SKILL.md

```markdown
# Loop Triage Skill

分类 Issue 和 PR，判断优先级和处理方式。

## 触发条件

- Daily Triage workflow 运行
- 手动 `workflow_dispatch` 触发

## 输入

---

## 八、工作流设计

### 8.1 Daily Triage Workflow

```yaml
# .github/workflows/loop-triage.yml
name: Loop Triage

on:
  schedule:
    # 工作日 8:00 UTC = 北京时间 16:00
    - cron: '0 8 * * 1-5'
  workflow_dispatch:

jobs:
  triage:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
      - name: Checkout
        uses: actions/checkout@v5
        
      - name: Run Context Check
        run: |
          echo "## Context Check"
          
      - name: Run Triage
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          # 获取 Issue 列表
          # 分类并更新 STATE.md
          
      - name: Log Run
        run: |
          echo "### $(date -u +%Y-%m-%d\ %H:%M:%S)" >> loop-run-log.md
```

### 8.2 CI Sweeper Workflow

```yaml
# .github/workflows/loop-ci-sweeper.yml
name: Loop CI Sweeper

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    
jobs:
  sweep:
    if: github.event.workflow_run.conclusion == 'failure'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - name: Checkout
---

## 九、实施计划

### 9.1 Phase 1: 核心文件 (Week 1)

| 任务 | 文件 | 优先级 | 依赖 |
|------|------|--------|------|
| 创建 LOOP.md | `LOOP.md` | P0 | - |
| 创建 STATE.md | `STATE.md` | P0 | - |
| 创建 LOOP_BUDGET.md | `LOOP_BUDGET.md` | P0 | - |
| 创建 LOOP_CONSTRAINTS.md | `LOOP_CONSTRAINTS.md` | P0 | - |
| 创建 gate.yaml | `gate.yaml` | P0 | - |
| 创建 loop-run-log.md | `loop-run-log.md` | P1 | - |
| 创建 `scripts/loop/loop-gate.sh` | `scripts/loop/loop-gate.sh` | P0 | gate.yaml |
| 创建 `scripts/loop/loop-audit.sh` | `scripts/loop/loop-audit.sh` | P0 | - |

### 9.2 Phase 2: Skills 扩展 (Week 2)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 扩展 loop-triage Skill | `.claude/skills/loop-triage/SKILL.md` | P0 |
| 创建 loop-verify Skill | `.claude/skills/loop-verify/SKILL.md` | P0 |
| 创建 loop-context Skill | `.claude/skills/loop-context/SKILL.md` | P1 |
| 创建 loop-plan Skill | `.claude/skills/loop-plan/SKILL.md` | P2 |

### 9.3 Phase 3: Workflows (Week 3)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 创建 loop-triage Workflow | `.github/workflows/loop-triage.yml` | P0 |
| 创建 loop-ci-sweeper Workflow | `.github/workflows/loop-ci-sweeper.yml` | P1 |
| 更新 check_ai_assets.py | `scripts/check_ai_assets.py` | P1 |

### 9.4 Phase 4: 文档与集成 (Week 4)

| 任务 | 文件 | 优先级 |
|------|------|--------|
| 更新 INDEX.md | `docs/INDEX.md` | P0 |
| 创建 loop-failure-modes.md | `docs/loop-failure-modes.md` | P1 |
| 更新 docs/CHANGELOG.md | `docs/CHANGELOG.md` | P0 |

---

## 十、预期收益

### 10.1 效率提升

| 维度 | 当前 | L1 引入后 | L2 引入后 |
|------|------|----------|----------|
| Issue 响应时间 | 手动处理 (1-3 天) | 每日分流 (1 天) | 自动建议 (2 小时) |
| CI 失败排查 | 人工 (15-30 分钟) | 自动分析 (5 分钟) | 自动修复 (0 分钟) |
| Changelog 维护 | 手动 (30 分钟/版本) | 自动草稿 (5 分钟审核) | 自动草稿 (5 分钟审核) |
| 依赖更新 | 被动等待 | 主动周期检查 | 自动安全更新 |

### 10.2 成本估算

| Loop | 日 Token | 月 Token | 月成本 |
|------|----------|----------|--------|
| Triage (L1) | 50k | 150k | $0.5-3 |
| CI Sweeper (L2) | 100k | 300k | $1-6 |
| Dep Sweeper (L2) | 80k | 80k | $0.3-1.5 |
| **总计** | **230k** | **530k** | **$2-10** |

### 10.3 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Token 消耗爆炸 | 中 | 高 | 预算控制 + kill switch |
| 错误修复引入新 Bug | 中 | 中 | worktree 隔离 + CI 验证 |
---

## 十一、验证与迭代

### 11.1 Loop Ready Score

```bash
# 运行审计
./scripts/loop/loop-audit.sh .

# 预期输出
Loop Ready Score: XX/100
- 核心文件: ✓/✗ (X/6)
- Skills: ✓/✗ (X/4)
- Workflows: ✓/✗ (X/3)
- 安全机制: ✓/✗ (X/2)
```

### 11.2 迭代节奏

| 周期 | 内容 | 输出 |
|------|------|------|
| Weekly | 检查 `loop-run-log.md` | 运行效果评估 |
| Monthly | 更新 `STATE.md` | 调整优先级 |
| Quarterly | 回顾失败模式 | 优化流程 |

### 11.3 成功指标

| 指标 | 目标 |
|------|------|
| Issue 平均响应时间 | < 24 小时 |
| CI 失败平均修复时间 | < 30 分钟 |
| Changelog 完整性 | 100% |
| Loop 运行成功率 | > 95% |
| Token 预算超支次数 | 0 次/月 |

---

## 十二、附录

### 12.1 与 loop-engineering 的差异

| 项目 | 本项目 | loop-engineering | 差异原因 |
|------|--------|-----------------|----------|
| 核心业务 | 股票分析 | 工具开发 | 领域不同 |
| 主要自动化 | CI + 分析 | 代码 + 文档 | 目标不同 |
| 安全约束 | 数据源 + 通知 | 代码 + 基础设施 | 风险不同 |
| Token 预算 | 更保守 | 中等 | 成本敏感 |
| 自主程度 | L1 → L2 | L1 → L3 | 风险偏好 |

### 12.2 参考资源

- [loop-engineering 官方仓库](https://github.com/cobusgreyling/loop-engineering)
- [Loop Engineering 博客](https://cobusgreyling.substack.com/)
- [Addy Osmani - Loop Engineering](https://addyosmani.com/blog/loop-engineering/)

---

*本文档遵循 AGENTS.md 的规则，是仓库协作规范的补充。*
| 自动化覆盖不足 | 高 | 低 | 渐进式提升 (L1→L2→L3) |
| 人类过度依赖 Loop | 低 | 中 | 定期 review + 文档提醒 |
| 安全门禁被绕过 | 低 | 高 | gate.yaml 机械执行 + CI 检查 |
        uses: actions/checkout@v5
        
      - name: Analyze Failure
        id: analyze
        run: |
          echo "can-auto-fix=true" >> $GITHUB_OUTPUT
          
      - name: Create Draft PR
        if: steps.analyze.outputs.can-auto-fix == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          # 创建 Draft PR
```
- Issue 列表（未关闭）
- PR 列表（开放）
- 最近提交历史（7 天）

## 处理流程

1. **分类 Priority**
   - P0: 安全漏洞、生产环境崩溃、数据丢失
   - P1: 功能缺失、严重影响使用、CI 持续失败
   - P2: 优化、改进建议、bug（不影响主流程）
   - P3: 低优先级、nice to have

2. **分类 Type**
   - bug / feature / docs / infra / question

3. **判断处理方式**
   - auto-fix: 可自动修复（L2）
   - needs-review: 需要人类 review
   - blocked: 等待其他 issue/PR
   - wontfix: 建议关闭

## 输出

更新 `STATE.md`:
- 高优先级列表
- 观察列表
- 建议动作

## 约束

- 遵循 `LOOP_CONSTRAINTS.md`
- 不修改任何代码
- 不关闭任何 Issue/PR
- 不添加/删除 labels
```

### 7.2 loop-verify/SKILL.md

```markdown
# Loop Verify Skill

验证 Loop 产生的修复是否正确。

## 触发条件

- CI Sweeper 修复后
- 人类标记需要验证

## 输入

- 修复内容（PR 或 commit）
- 相关测试结果
- CI 日志

## 验证步骤

1. **语法检查**: `python -m py_compile <file>`
2. **确定性检查**: `./scripts/ci_gate.sh deterministic`
3. **离线测试**: `./scripts/ci_gate.sh offline-tests`
4. **CI 冒烟测试**: `./scripts/ci_gate.sh syntax`

## 输出

```markdown
## 验证结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| 语法 | ✅/❌ | - |
| Lint | ✅/❌ | - |
| 离线测试 | ✅/❌ | - |

## 建议

- 可以合并
- 需要修改
- 建议关闭
```

## 约束

- 必须实际运行验证命令
- 不能只依赖 CI 结果
- 发现问题必须报告具体原因
```

### 7.3 loop-context/SKILL.md

```markdown
# Loop Context Skill

在每次 Loop 运行前检查上下文，确保安全执行。

## 触发条件

- 任何 Loop 运行前

## 检查项

1. **Kill Switch**: 检查是否有 `loop-pause-all` label
2. **预算检查**: 估算本次 Token 消耗
3. **前置条件**: 检查相关 Issue/PR 状态
4. **最近历史**: 避免重复失败的任务

## 输出

```markdown
## Context Check

| 检查项 | 状态 | 详情 |
|--------|------|------|
| Kill Switch | CLEAR/ACTIVE | - |
| Budget | OK/WARNING/EXCEEDED | X/Y tokens |
| Prerequisites | MET/NOT_MET | - |
| History | CLEAN/WARNING | - |

## 决策

- ✅ 继续执行
- ⚠️ 切换到报告模式
- ❌ 立即退出
```
```

### 7.4 loop-plan/SKILL.md

```markdown
# Loop Plan Skill

生成 Changelog 草稿和计划文档。

## 触发条件

- PR 合并到 main
- Release 准备
- 手动触发

## 输入

- 合并的 PR 列表
- Commit 历史
- 当前版本号

## 输出

```markdown
## [Unreleased] YYYY-MM-DD

### 新功能
- ...

### 改进
- ...

### 修复
- ...

### 文档
- ...
```

## 约束

- 遵循 `CHANGELOG.md` 的扁平格式
- 不自动发布
- 人类审核后才能更新正式文档
```
│  Layer 5: Kill Switch (紧急停止)                           │
│  • loop-pause-all label                                     │
│  • STATE.md 中的暂停标记                                    │
│  • 所有 Loop 立即退出                                       │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 失败模式与应对

| 失败模式 | 症状 | 严重度 | 应对 |
|---------|------|--------|------|
| 无限修复循环 | 同一问题被修复 5+ 次 | S2 | 硬编码 3 次上限 → escalation |
| 状态腐化 | STATE.md 引用已关闭的 Issue | S1-S2 | 每次运行 prune + 验证 ID |
| 验证表演 | verifier "通过" 但 CI 失败 | S2 | 必须运行实际命令 + 不同指令 |
| 通知疲劳 | 频繁无意义的通知 | S1-S2 | 仅通知需要人类决策的事项 |
| Token 燃烧 | 账单暴涨 | S1 | 预算控制 + 便宜模型优先 |
| 范围越界 | 修改了不该改的文件 | S2-S3 | gate.yaml 机械执行 |

详见 [docs/loop-failure-modes.md](./loop-failure-modes.md)
