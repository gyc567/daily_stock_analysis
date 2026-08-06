# Loop Engineering 用户指南

> 让迭代开发更高效：如何与 AI 协作使用 Loop Engineering

## 目录

- [1. 快速开始](#1-快速开始)
- [2. 核心文件速查](#2-核心文件速查)
- [3. 日常使用场景](#3-日常使用场景)
- [4. AI 协作模板](#4-ai-协作模板)
- [5. 命令速查](#5-命令速查)
- [6. 故障排查](#6-故障排查)
- [7. 最佳实践](#7-最佳实践)

---

## 1. 快速开始

### 1.1 首次使用前

```bash
# 1. 查看当前 Loop 状态
cat LOOP.md

# 2. 运行完整审计
./scripts/loop/loop-audit.sh

# 3. 查看 Token 预算
cat LOOP_BUDGET.md

# 4. 阅读约束规则
cat LOOP_CONSTRAINTS.md
```

### 1.2 每次任务开始前

告诉 AI：
```
请先阅读以下文件了解当前状态：
- LOOP.md
- STATE.md
- LOOP_CONSTRAINTS.md
- gate.yaml

然后告诉我：
1. 当前 Loop 状态
2. 你的约束边界
3. 是否有任何需要注意的点
```

### 1.3 每次任务结束后

告诉 AI：
```
任务完成，请执行：
1. 更新 STATE.md（记录本次改动）
2. 记录到 loop-run-log.md（包含时间、动作、结果）
3. 确认是否触发了任何 escalation 条件
```

---

## 2. 核心文件速查

| 文件 | 作用 | 查看频率 |
|------|------|----------|
| `LOOP.md` | 运营总览，当前 Loop 列表 | 开始工作前 |
| `STATE.md` | 活跃任务、观察列表 | 每日检查 |
| `LOOP_BUDGET.md` | Token 预算限制 | 计划任务时 |
| `LOOP_CONSTRAINTS.md` | 行为约束规则 | **任何操作前必读** |
| `gate.yaml` | 路径安全配置 | PR review 前 |
| `loop-run-log.md` | 运行历史记录 | 排查问题时 |

### 2.1 LOOP_CONSTRAINTS.md 关键规则速记

```
✅ 可以做：
- 推送前必须告知人类
- 必须先创建 Draft PR
- 修复前必须运行测试
- 单项最多 3 次尝试

❌ 禁止做：
- 自动合并到 main（除依赖补丁外）
- 修改 .env、secrets、credentials 相关
- 禁用测试或跳过 lint
- 关闭 Issue/PR 或添加/删除 labels
- 修改 data_provider、src/reports、bot 配置
- 修改 main.py 核心逻辑

⚠️ 注意事项：
- Token 消耗达 80% 日限额时切换报告模式
- loop-pause-all 激活时立即退出
```

### 2.2 gate.yaml 关键配置

```yaml
paths:
  deny:                    # 禁止 AI 修改
    - .env
    - .env.*
    - **/secrets/**
    - **/credentials/**
    - auth/**
    - bot/**
    - data_provider/**
    - src/config/
  
  require_review:          # 需要人类审核
    - .github/workflows/
    - docker/
    - scripts/ci_gate.sh
    - src/reports/
    - src/analyzer/
    - main.py
  
  auto_merge:             # 可自动合并（需 CI 通过）
    - docs/
    - tests/
    - .claude/

constraints:
  max_files_per_change: 10
  max_lines_per_file: 500
```

---

## 3. 日常使用场景

### 场景 A: 让 AI 分析 Issue

**你告诉 AI:**
```
请使用 loop-triage skill 分析这个问题：

Issue: [粘贴内容或链接]

分析要求：
1. 分类：bug / feature / question / docs / infra
2. 评估优先级：P0 / P1 / P2 / P3
3. 评估复杂度：L1(简单) / L2(中等) / L3(复杂)
4. 判断是否需要 Loop 介入

约束：遵循 LOOP_CONSTRAINTS.md，不修改任何代码。

完成后更新 STATE.md 和 loop-run-log.md。
```

---

### 场景 B: 让 AI 做 Code Review

**你告诉 AI:**
```
请使用 loop-verify skill 对 PR 进行审查：

PR: [编号或链接]
分支: [分支名]
主要改动: [简要描述]

审查要求：
1. 路径检查：对比 gate.yaml，确认没有越界
2. 约束检查：确认符合 LOOP_CONSTRAINTS.md
3. 测试覆盖：是否包含测试
4. 文档更新：是否需要更新文档

验证步骤（必须实际执行）：
1. python -m py_compile <file>
2. ./scripts/ci_gate.sh deterministic
3. pytest tests/ -v

完成后更新 STATE.md。
```

---

### 场景 C: 让 AI 规划功能开发

**你告诉 AI:**
```
请使用 loop-plan skill 为这个功能制定实施计划：

目标：[描述功能]

约束：
- 遵循 LOOP_CONSTRAINTS.md
- 符合 gate.yaml 路径限制
- Token 预算不超过 LOOP_BUDGET.md 限制
- 单次修改不超过 10 个文件

分解要求：
1. 分成 N 个阶段（每个阶段可独立验证）
2. 每个阶段有明确的验收标准
3. 包含测试和文档要求

输出：
- 更新 LOOP.md
- 更新 STATE.md
- 记录到 loop-run-log.md
```

---

### 场景 D: 让 AI 修复 Bug

**你告诉 AI:**
```
请修复以下 bug：

问题描述：[描述问题]
复现步骤：[步骤]
预期行为：[期望]
实际行为：[实际]

约束：
1. 先阅读 LOOP_CONSTRAINTS.md 和 gate.yaml
2. 只修改必要的文件
3. 必须添加/更新测试
4. 最多尝试 3 次，超出后创建 Issue escalation

验证要求：
1. 运行 pytest tests/
2. 运行 ./scripts/ci_gate.sh
3. 确保没有引入新问题

完成后：
1. 创建 Draft PR
2. 更新 STATE.md
3. 记录到 loop-run-log.md
```

---

### 场景 E: 紧急停止所有 Loop

**你告诉 AI:**
```
紧急：停止所有 Loop 操作。

执行：
1. 在 STATE.md 添加暂停标记
2. 不要创建任何新的 PR 或分支
3. 记录到 loop-run-log.md
4. 确认没有正在运行的 workflow

不执行任何代码修改。
```

---

### 场景 F: 恢复 Loop 操作

**你告诉 AI:**
```
恢复 Loop 操作。

执行：
1. 删除 STATE.md 中的暂停标记
2. 运行 ./scripts/loop/loop-audit.sh 确认状态
3. 检查 loop-run-log.md 是否有待处理项
4. 记录恢复原因到 loop-run-log.md
```

---

### 场景 G: 让 AI 生成 Changelog

**你告诉 AI:**
```
请生成 CHANGELOG.md 的草稿：

基于最近合并的 PR：[PR 列表或链接]

要求：
1. 遵循 CHANGELOG.md 的扁平格式
2. 按类型分类：feat/fix/docs/refactor/test/ci/chore
3. 每个条目一行，格式：- [类型] 描述

完成后更新 loop-run-log.md。
```

---

## 4. AI 协作模板

### 4.1 标准 Loop 指令模板

```markdown
## 任务
[简要描述你要做什么]

## 约束
- 遵循 LOOP_CONSTRAINTS.md
- 检查 gate.yaml 的路径限制
- Token 预算不超过 LOOP_BUDGET.md 限制
- 单次修改不超过 10 个文件

## 操作要求
1. [具体步骤 1]
2. [具体步骤 2]
3. [具体步骤 3]

## 输出
- 更新 STATE.md（高优先级/观察列表）
- 记录到 loop-run-log.md（时间、动作、结果）
- [其他输出要求]
```

### 4.2 Issue 分析模板

```markdown
## Issue 分析请求

请使用 loop-triage skill 分析以下 Issue：

### Issue 内容
[粘贴 Issue 内容]

### 分析要求
1. **分类 Type**: bug / feature / question / docs / infra
2. **评估优先级**: 
   - P0: 安全漏洞、生产崩溃、数据丢失
   - P1: 功能缺失、严重影响使用、CI 持续失败
   - P2: 优化、改进建议、bug（不影响主流程）
   - P3: 低优先级、nice to have
3. **评估复杂度**:
   - L1: 简单，单文件修改
   - L2: 中等，涉及多个文件
   - L3: 复杂，涉及架构或多个子系统
4. **判断处理方式**:
   - auto-fix: 可自动修复（L2 Loop）
   - needs-review: 需要人类 review
   - blocked: 等待其他 Issue/PR
   - wontfix: 建议关闭

### 约束
- 不修改任何代码
- 不关闭任何 Issue/PR
- 不添加/删除 labels

### 输出
- 更新 STATE.md 的观察列表或高优先级列表
- 记录到 loop-run-log.md
```

### 4.3 PR Review 模板

```markdown
## PR Review 请求

请使用 loop-verify skill 对 PR 进行审查：

### PR 信息
- PR 编号/链接：[链接]
- 分支：[分支名]
- 主要改动：[简要描述]
- 涉及文件：[文件列表]

### 审查重点
1. **路径限制**：检查 gate.yaml
   - [ ] 确认没有修改 deny 列表中的路径
   - [ ] 确认 require_review 路径有 human approval
2. **约束检查**：检查 LOOP_CONSTRAINTS.md
   - [ ] 没有自动合并到 main
   - [ ] 没有禁用测试
   - [ ] 没有跳过 lint
3. **测试覆盖**：
   - [ ] 是否包含测试
   - [ ] 测试是否通过
4. **文档更新**：是否需要更新文档

### 验证步骤（必须实际执行）
```bash
# 语法检查
python -m py_compile <file>

# 确定性检查
./scripts/ci_gate.sh deterministic

# 离线测试
./scripts/ci_gate.sh offline-tests

# 运行测试
pytest tests/ -v
```

### 决策
- [ ] 可以合并（CI 通过 + human approval）
- [ ] 需要修改（列出具体问题）
- [ ] 需要人工 review（标注原因）

### 输出
- 更新 STATE.md
- 记录到 loop-run-log.md
```

### 4.4 任务规划模板

```markdown
## 任务规划请求

请使用 loop-plan skill 制定计划：

### 目标
[描述你想要实现的目标]

### 当前状态
[已知信息，如有]

### 约束
- 最大 Token 预算：[数字]k
- 单次修改不超过 10 个文件
- 单文件最多修改 500 行
- 必须包含测试

### 分解要求
1. 分成 N 个阶段（每个阶段可独立验证）
2. 每个阶段有明确的验收标准
3. 包含测试和文档要求

### 输出
- 更新 LOOP.md（添加新 Loop 条目）
- 更新 STATE.md（添加到观察列表）
- 记录到 loop-run-log.md
```

---

## 5. 命令速查

### 5.1 状态检查

```bash
# 查看 Loop 就绪度（完整审计）
./scripts/loop/loop-audit.sh

# 检查 Kill Switch
gh label list | grep loop-pause-all

# 查看最近运行日志
tail -20 loop-run-log.md

# 查看 GitHub Actions
gh run list --workflow=loop- --limit 10

# 查看高优先级事项
grep -A 10 "高优先级" STATE.md

# 查看观察列表
grep -A 10 "观察列表" STATE.md
```

### 5.2 手动触发 Workflow

```bash
# 手动触发 Triage（Issue/PR 分流）
gh workflow run loop-triage.yml

# 手动触发 CI Sweeper
gh workflow run loop-ci-sweeper.yml

# 手动触发 Dep Sweeper
gh workflow run loop-dep-sweeper.yml --field dry_run=false

# 查看 workflow 状态
gh run list --workflow=loop-triage --limit 5
```

### 5.3 安全检查

```bash
# Gate 检查（验证路径是否允许）
./scripts/loop/loop-gate.sh check --action auto-merge --paths "src/a.py,docs/b.md"

# Token 预算检查
./scripts/loop/loop-budget.sh status

# 完整审计
./scripts/loop/loop-audit.sh
```

### 5.4 紧急操作

```bash
# 紧急停止所有 Loop
gh label create loop-pause-all --color ff0000

# 验证已停止
gh run list --workflow=loop-triage --limit 3

# 恢复 Loop
gh label delete loop-pause-all
# 并删除 STATE.md 中的暂停标记
```

---

## 6. 故障排查

### 问题 1: AI 修改了不该改的文件

**症状**: 发现有文件被意外修改

**排查步骤**:
```bash
# 1. 查看最近改动
git diff HEAD~1 --name-only

# 2. 检查是否在 deny 列表
cat gate.yaml | grep -A 20 "deny"

# 3. 确认是否有人工 approval
gh pr view $PR_NUMBER --json reviewDecision,reviews
```

**解决方法**:
```bash
# 回退改动
git checkout -- <file>

# 创建 Issue 记录问题
gh issue create --title "Loop 越界：修改了禁止路径" --body "..."
```

---

### 问题 2: Loop 没有运行

**症状**: 期望的 workflow 没有触发

**排查步骤**:
```bash
# 1. 检查 workflow 是否启用
gh workflow view loop-triage

# 2. 检查 schedule 是否正确
gh run list --workflow=loop-triage --limit 1

# 3. 检查 Kill Switch
gh label list | grep loop-pause-all
```

**解决方法**:
```bash
# 手动触发测试
gh workflow run loop-triage.yml --field dry_run=true

# 检查 GitHub Actions 日志
gh run view $RUN_ID --log
```

---

### 问题 3: Token 消耗超支

**症状**: 月度账单暴涨

**排查步骤**:
```bash
# 1. 检查预算状态
./scripts/loop/loop-budget.sh status

# 2. 查看运行历史
grep "Token" loop-run-log.md | tail -20
```

**解决方法**:
```bash
# 1. 停止所有 Loop
gh label create loop-pause-all --color ff0000

# 2. 分析消耗原因
# 编辑 LOOP_BUDGET.md，调整限额

# 3. 恢复时删除 label
gh label delete loop-pause-all
```

---

### 问题 4: STATE.md 状态腐化

**症状**: STATE.md 引用已关闭的 Issue/PR

**排查步骤**:
```bash
# 1. 导出开放 Issue 列表
gh issue list --state open --limit 100 > /tmp/open_issues.txt

# 2. 导出 STATE.md 中的 Issue
grep -E "^#|^-.*#" STATE.md > /tmp/state_issues.txt

# 3. 对比
diff /tmp/open_issues.txt /tmp/state_issues.txt
```

**解决方法**:
```bash
# 手动清理 STATE.md
# 删除已关闭的 Issue 条目
# 更新 Last run 时间戳
```

---

### 问题 5: CI 持续失败

**症状**: 同一个 CI job 失败多次

**排查步骤**:
```bash
# 1. 查看最近 CI 失败
gh run list --workflow=CI --limit 5

# 2. 查看失败日志
gh run view $RUN_ID --log-failed | head -100

# 3. 检查是否由 Loop 修复导致
grep "CI Sweeper" loop-run-log.md | tail -10
```

---

## 7. 最佳实践

### 7.1 与 AI 协作的黄金法则

1. **每次任务前让 AI 读取约束文件**
   ```
   请先阅读 LOOP_CONSTRAINTS.md 和 gate.yaml，然后告诉我你的约束边界。
   ```

2. **明确指定输出格式**
   ```
   更新 STATE.md 的高优先级列表，格式为：
   | Issue/PR | 状态 | 最后更新 | 备注 |
   ```

3. **设置明确的验收标准**
   ```
   成功标准：
   1. pytest tests/ 全部通过
   2. ./scripts/ci_gate.sh 全部通过
   3. 没有修改 gate.yaml deny 列表中的路径
   ```

4. **记录所有操作**
   ```
   完成后：
   1. 更新 STATE.md
   2. 记录到 loop-run-log.md（包含时间、动作、结果）
   ```

### 7.2 安全优先

- **始终检查 gate.yaml**：确保 AI 不会修改禁止路径
- **使用 Draft PR**：AI 创建的 PR 默认为 Draft，需要人类审核
- **保留人工门禁**：关键路径（main.py、workflows）必须人工审核
- **监控 Token 消耗**：避免账单超支

### 7.3 迭代改进

1. **定期审计**
   ```bash
   ./scripts/loop/loop-audit.sh
   ```
   每月至少运行一次，确保持续符合 Loop Ready 标准。

2. **回顾失败模式**
   ```bash
   # 查看 loop-run-log.md 中的失败记录
grep -i "fail\|error\|issue" loop-run-log.md | tail -20
   ```

3. **更新文档**
   发现新问题后，更新 `docs/loop-failure-modes.md`。

### 7.4 快速参考卡片

```
┌─────────────────────────────────────────────────────────────┐
│  Loop Engineering 快速参考                                   │
├─────────────────────────────────────────────────────────────┤
│  📊 状态检查                                                │
│     ./scripts/loop/loop-audit.sh                           │
│                                                             │
│  🚫 紧急停止                                                │
│     gh label create loop-pause-all --color ff0000           │
│                                                             │
│  ▶️ 手动触发                                                │
│     gh workflow run loop-triage.yml                         │
│                                                             │
│  🔒 安全检查                                                │
│     ./scripts/loop/loop-gate.sh check --paths "src/a.py"  │
│                                                             │
│  💰 预算检查                                                │
│     ./scripts/loop/loop-budget.sh status                  │
│                                                             │
│  📝 每次任务前让 AI 读取                                    │
│     LOOP.md, STATE.md, LOOP_CONSTRAINTS.md, gate.yaml       │
│                                                             │
│  ✅ 每次任务后                                              │
│     更新 STATE.md + 记录到 loop-run-log.md                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 相关文档

- [Loop Engineering 集成方案](./loop-engineering-integration.md) - 完整的集成文档
- [Loop Engineering 设计指南](./loop-design-guide.md) - 创建新 Loop 的指南
- [Loop Engineering 运营手册](./loop-operating.md) - 日常运营指南
- [Loop Engineering 失败模式](./loop-failure-modes.md) - 失败模式与应对

---

*本文档与 LOOP_CONSTRAINTS.md、gate.yaml、LOOP.md、STATE.md 保持同步更新。*
