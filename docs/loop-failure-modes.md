# Loop Engineering 失败模式

> 记录 Loop 运行中的常见失败模式、应对策略和经验教训。

## 分类说明

| 严重度 | 含义 |
|--------|------|
| **S1** | 烦人但无害（浪费时间和 Token） |
| **S2** | 有害（错误代码合并、通知疲劳） |
| **S3** | 严重（安全问题、数据丢失） |

---

## 1. 无限修复循环

**症状**: 同一个 PR 或 CI job 被自动化修复尝试 5+ 次，从不收敛。

**严重度**: S2

**原因**:
- Verifier 太弱或与实现者同处一个 session
- 根因误判（只修复症状）
- 把 flaky test 当作回归处理

**应对**:
- 硬编码尝试上限（如 3 次）→ escalation 到人类
- 使用不同的 verifier model 或更高的推理能力
- 在 triage 阶段将 flaky test 隔离，而不是改代码
- 在状态文件中记录尝试次数

**检测**:
```bash
# 检查 loop-run-log.md 中同一问题的重复尝试
grep "CI Sweeper" loop-run-log.md | tail -10
```

---

## 2. 状态腐化

**症状**: `STATE.md` 引用已合并的 PR、已关闭的 Issue 或过期的分支。

**严重度**: S1 → S2（Loop 基于幽灵行动）

**原因**:
- 运行结束时没有 prune 步骤
- 运行开始时没有读取状态文件
- 多个 Loop 写入同一文件但没有 schema

**应对**:
- 每次运行结束时 prune 已关闭/合并的项目
- `Last run` 时间戳 + 验证 ID 是否与 live API 一致
- 每个 Loop pattern 独立的状态文件，或清晰的 section 隔离

**检测**:
```bash
# 检查 STATE.md 中的 Issue/PR 是否仍然开放
gh issue list --state open --limit 100 | grep -f STATE.md
```

---

## 3. 验证表演

**症状**: Verifier "批准" 但 CI 失败或 review 发现明显 bug。

**严重度**: S2

**原因**:
- Verifier prompt 太模糊（"看起来不错"）
- Verifier 不运行测试
- 使用相同的 model 和 context

**应对**:
- Verifier 必须运行 test/lint 命令并报告输出
- 使用不同的指令："找出拒绝的理由"
- 对于无人值守 Loop 使用更强的 model

**检测**:
```bash
# 检查 CI 失败是否在 verifier "通过" 后发生
gh run list --workflow=CI --limit 5
```

---

## 4. 通知疲劳

**症状**: Slack/邮件 每 5 分钟 ping 一次；团队静音 bot。

**严重度**: S1 → S2（真正 escalation 被错过）

**原因**:
- 每次运行都通知，而不是每次*可操作*发现时通知
- Triage skill 中 "高优先级" 标准太低

**应对**:
- 只在需要人类决策时通知
- 对于纯报告 Loop 使用摘要模式
- 收紧 triage "高优先级" 规则

**检测**:
```bash
# 检查通知频率
gh run list --workflow=loop-triage --limit 20
```

---

## 5. Token 燃烧

**症状**: 账单暴涨；Loop 在空或嘈杂的 triage 上运行完整子代理链。

**严重度**: S1

**原因**:
- 分钟级频率 + 重子代理
- watchlist 为空时没有提前退出
- 瞬时 API 错误时重试整个 pipeline

**应对**:
- 先用便宜的 triage-only pass；只为可操作项 spawn 子代理
- watchlist 为空时 `scheduler_delete`
- 日 Token 预算 → 暂停 Loop
- 详见 [LOOP_BUDGET.md](../LOOP_BUDGET.md)

**检测**:
```bash
# 检查 Token 消耗
./scripts/loop/loop-budget.sh status
```

---

## 6. 范围越界

**症状**: Loop 重构无关模块、"修复" 设计问题或触碰 denylist 路径。

**严重度**: S2 → S3

**原因**:
- minimal-fix skill 太宽松
- 没有 path allowlist/denylist
- Triage 把架构工作放入 "高优先级"

**应对**:
- [safety.md](./safety.md) denylist 在 skills 中强制执行
- "最小可能 diff" + verifier 检查触碰的文件
- Triage skill: 只信号，不创造

**检测**:
```bash
# 检查是否有越界修改
./scripts/loop/loop-gate.sh check --action auto-merge --paths "src/**/*.py"
```

---

## 7. 理解债务螺旋

**症状**: 速度上升，但没人能解释最近的改动；review 成为橡皮图章。

**严重度**: S2（长期）

**原因**:
- 人类停止阅读 Loop 输出
- 允许列表持续扩大
- 没有每周人工综合 Loop 行动

**应对**:
- 非平凡 PR 强制人类 review
- Owner 每周必读 "loop digest"
- 允许自动合并的范围限制在真正平凡的路径

**检测**:
```bash
# 检查最近的合并
gh pr list --state=merged --limit 10
```

---

## 8. 认知投降

**症状**: "Loop 会处理" — 对正确性或设计没有意见。

**严重度**: S2（文化）

**原因**:
- Loop 成功指标 = volume，而不是质量
- 中等风险工作没有人类门禁

**应对**:
- 每个 pattern 明确人类门禁
- 成功指标: 节省时间 *同时* 保持质量
- 提醒: "Build it like someone who intends to stay the engineer"

**检测**:
```bash
# 检查是否有太多无人值守合并
gh pr list --state=merged --search "author:app/github-actions" --limit 10
```

---

## 9. 并行冲突

**症状**: 两个子代理编辑同一文件；合并冲突；状态损坏。

**严重度**: S2

**原因**:
- 没有 worktree 隔离
- 两个 Loop 同时作用于同一 PR

**应对**:
- 所有代码编辑子代理使用 `isolation: worktree`
- 在状态中加锁或队列: "PR #1234 — worktree 进行中"

**检测**:
```bash
# 检查工作树
git worktree list
```

---

## 10. Escalation 失败

**症状**: Loop 卡住重试；人类从未收到通知。

**严重度**: S2

**原因**:
- 没有实现最大尝试次数
- Escalation 只写入没人读的状态文件

**应对**:
- Escalation 时使用 connector ping（Slack、Linear comment）
- `STATE.md` 中 "高优先级（等待人类）" section
- 如果项目在该 section 超过 24 小时则报警

**检测**:
```bash
# 检查等待人类的项目
grep -A 5 "高优先级" STATE.md
```

---

## 贡献故事

如果你有失败故事，请通过 PR 添加到本文档或在 issue 中分享：

- Pattern 名称
- 症状
- 什么缓解了它（或者没有）

---

*本文档是 [loop-engineering-integration.md](./loop-engineering-integration.md) 的补充。*
