# Loop Engineering 设计指南

> 创建新 Loop 的设计原则和检查清单。

## 设计原则

### 1. 从 L1 开始

**总是从报告模式开始**，而不是无人值守：

1. **L1 (0% 自主)**: Loop 只报告，人类决定行动
2. **L2 (50% 自主)**: Loop 建议修复，人类审核后合并
3. **L3 (90% 自主)**: Loop 自动修复，人类只处理 escalation

**原则**: 在升级到 L2/L3 之前，先在 L1 模式下运行足够长时间，确保理解问题和失败模式。

### 2. 单一职责

**每个 Loop 只做一件事**：

| ✅ 好 | ❌ 差 |
|------|------|
| Daily Triage | 包含 CI 修复 |
| CI Sweeper | 包含依赖更新 |
| Dep Sweeper | 包含代码重构 |

**原因**: 单一职责的 Loop 更易理解、测试和调试。

### 3. 明确边界

**定义 Loop 的输入和输出**：

```markdown
## 输入
- Issue 列表
- PR 列表
- Commit 历史

## 输出
- 更新后的 STATE.md
- 生成的报告
- 创建的 Draft PR
```

### 4. 人类门禁

**每个 Loop 必须有至少一个人类门禁**：

```yaml
# 门禁位置
L1: 人类决定是否执行建议
L2: 人类审核 Draft PR 后合并
L3: 人类处理 escalation
```

### 5. 可观测性

**Loop 必须能追踪和调试**：

- 记录运行到 `loop-run-log.md`
- 更新 `STATE.md` 的相关 section
- 失败时创建可追踪的 Issue

---

## 设计检查清单

在创建新 Loop 之前，完成以下检查：

### 问题定义

- [ ] 解决了什么问题？
- [ ] 当前人工处理需要多少时间？
- [ ] Loop 能节省多少时间？
- [ ] 失败的成本是什么？

### 范围定义

- [ ] 输入是什么？（Issue、PR、API、文件）
- [ ] 输出是什么？（报告、PR、Issue、状态更新）
- [ ] 边界在哪里？（什么不做）
- [ ] 依赖哪些其他系统？

### 安全设计

- [ ] 识别 denylist 路径
- [ ] 定义 require-review 路径
- [ ] 设置 max-files 限制
- [ ] 定义 auto-merge 条件

### 成本估算

- [ ] 估算 Token 消耗/次
- [ ] 估算运行频率
- [ ] 月度成本上限
- [ ] 超预算处理策略

### 失败处理

- [ ] 定义失败条件
- [ ] 定义 escalation 条件
- [ ] 定义重试策略
- [ ] 定义 kill switch

### 验证策略

- [ ] 定义验证步骤
- [ ] 定义验证命令
- [ ] 定义 maker/checker 分离
- [ ] 定义人工审核点

---

## Loop 模板

### 新 Loop 目录结构

```
.github/workflows/
└── loop-{name}.yml    # Workflow

.claude/skills/
└── loop-{name}/
    └── SKILL.md       # Skill 定义

STATE.md               # 状态更新
loop-run-log.md        # 运行日志
```

### SKILL.md 模板

```markdown
# Loop {Name} Skill

## 描述
描述 Loop 做什么。

## 触发条件
- 自动触发（schedule）
- 手动触发（workflow_dispatch）

## 输入
- 列表输入
- API 数据

## 处理流程
1. 步骤 1
2. 步骤 2
3. 步骤 3

## 输出
- 更新后的状态
- 生成的内容

## 约束
- 遵循 LOOP_CONSTRAINTS.md
- 不修改禁止路径
- 最多 N 次尝试

## 错误处理
- 错误 1 → 处理方式
- 错误 2 → 处理方式
```

### Workflow 模板

```yaml
name: Loop {Name}

on:
  schedule:
    - cron: '0 8 * * 1-5'  # 调整频率
  workflow_dispatch:

jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Context Check
        run: |
          # 检查 Kill Switch
          # 检查预算

      - name: Run Loop
        run: |
          # 执行 Loop 逻辑

      - name: Update State
        run: |
          # 更新 STATE.md

      - name: Log Run
        run: |
          # 记录到 loop-run-log.md
```

---

## 升级路径

### L1 → L2

**条件**:
- L1 模式运行超过 2 周
- 理解并记录了所有失败模式
- 有清晰的可自动修复场景
- 验证步骤可靠

**步骤**:
1. 在 `LOOP.md` 中标记为 L2
2. 添加 Draft PR 创建逻辑
3. 添加人类审核步骤
4. 更新 SKILL.md

### L2 → L3

**条件**:
- L2 模式运行超过 1 个月
- 自动修复成功率 > 95%
- 没有严重失败记录
- 有可靠的 escalation 机制

**步骤**:
1. 在 `LOOP.md` 中标记为 L3
2. 移除 Draft PR 步骤
3. 添加自动合并逻辑
4. 更新 SKILL.md
5. 添加监控告警

---

## 反模式

### ❌ 过度自动化

**问题**: 太快升级到 L3，没有理解失败模式。

**后果**: 错误合并、状态损坏、安全问题。

**解决方案**: 慢慢升级，在每级充分验证。

### ❌ 范围蔓延

**问题**: Loop 不断添加功能，变得复杂。

**后果**: 难以维护、难以调试、难以升级。

**解决方案**: 保持单一职责，创建新 Loop 而不是扩展。

### ❌ 缺乏监控

**问题**: Loop 无人看管，失败也不知道。

**后果**: 问题积累、状态腐化、预算超支。

**解决方案**: 始终监控运行日志和 Token 消耗。

### ❌ 绕过门禁

**问题**: 为了速度跳过人类审核。

**后果**: 错误代码合并、安全问题。

**解决方案**: 保持人类门禁，即使慢也要安全。

---

## 案例研究

### 成功案例

**Daily Triage Loop (L1 → L2)**

1. **初始状态**: 手动处理 Issue，每天花费 30 分钟
2. **L1 实施**: 自动分类和报告，人类决定行动
3. **运行 2 周**: 理解了 Issue 类型分布
4. **L2 升级**: 自动创建 Draft PR，人类审核
5. **结果**: 节省 80% 人工时间，Issue 响应从 2 天缩短到 4 小时

### 失败案例

**CI Sweeper Loop (L3 太早)**

1. **初始状态**: CI 失败频繁，人工排查
2. **直接实施 L3**: 自动修复并合并
3. **结果**: 错误代码被合并，导致生产问题
4. **教训**: 必须从 L1 开始，充分理解后再升级

---

*本文档是 [loop-engineering-integration.md](./loop-engineering-integration.md) 的补充。*
