# Loop Engineering 运营手册

> 日常运营 Loop 的指南和最佳实践。

## 目录

- [日常操作](#日常操作)
- [监控与日志](#监控与日志)
- [问题处理](#问题处理)
- [成本管理](#成本管理)
- [安全运营](#安全运营)

---

## 日常操作

### 启动 Loop

```bash
# 查看 Loop 状态
./scripts/loop/loop-audit.sh

# 检查 Kill Switch
gh label list | grep loop-pause-all

# 手动触发 Triage
gh workflow run loop-triage.yml
```

### 停止 Loop

```bash
# 方法 1: 添加 Kill Switch label
gh label create loop-pause-all --color ff0000
gh issue comment $ISSUE --body "Adding loop-pause-all to stop all Loops"

# 方法 2: 在 STATE.md 中添加暂停标记
# 在 STATE.md 中添加:
# ## 暂停原因
# - 临时暂停进行维护
```

### 恢复 Loop

```bash
# 移除 Kill Switch
gh label delete loop-pause-all

# 清理 STATE.md 中的暂停标记
# 从 STATE.md 中删除 "暂停原因" section
```

---

## 监控与日志

### 查看运行日志

```bash
# 查看最近运行
tail -50 loop-run-log.md

# 查看特定 Loop
grep "Daily Triage" loop-run-log.md | tail -10

# 查看失败
grep "failure" loop-run-log.md | tail -10
```

### 查看 GitHub Actions

```bash
# 查看最近 workflow runs
gh run list --workflow=loop-triage --limit 10

# 查看特定 run 日志
gh run view $RUN_ID --log

# 查看失败 run
gh run view $RUN_ID --log-failed
```

### 查看 STATE.md

```bash
# 高优先级项
grep -A 10 "高优先级" STATE.md

# 观察列表
grep -A 10 "观察列表" STATE.md

# 最后更新时间
grep "Last run" STATE.md
```

---

## 问题处理

### CI 失败

```bash
# 1. 检查失败原因
gh run view $RUN_ID --log-failed | head -100

# 2. 检查 CI Sweeper 是否已分析
grep "CI Sweeper" loop-run-log.md | tail -5

# 3. 如果 CI Sweeper 产生了 PR
gh pr list --author=app/github-actions --state=open

# 4. 审查 PR 并决定是否合并
gh pr view $PR_NUMBER
```

### 预算超支

```bash
# 1. 检查当前消耗
./scripts/loop/loop-budget.sh status

# 2. 估算 Token 消耗
./scripts/loop/loop-budget.sh estimate --loop daily-triage

# 3. 如果超支，暂停 Loop
gh label create loop-pause-all --color ff0000
```

### 状态腐化

```bash
# 1. 检查 STATE.md 中的项目是否仍然存在
gh issue list --state open --limit 100 > /tmp/open_issues.txt
grep -E "#[[:digit:]]+" STATE.md > /tmp/state_issues.txt
diff /tmp/open_issues.txt /tmp/state_issues.txt

# 2. 清理过时条目
# 编辑 STATE.md，移除已关闭的 Issue/PR
```

### 通知疲劳

```bash
# 检查通知频率
gh run list --workflow=loop-triage --limit 30

# 如果太频繁，调整 cron 表达式
# 编辑 .github/workflows/loop-triage.yml
# 频率: 0 8 * * 1-5 (工作日 8:00 UTC)
```

---

## 成本管理

### 预算配置

编辑 `LOOP_BUDGET.md`:

```markdown
| Loop | 最大运行/日 | 最大 Token/日 |
|------|------------|--------------|
| Daily Triage | 1 | 50k |
| CI Sweeper | 5 | 100k |
```

### 成本估算

```bash
# 估算日消耗
./scripts/loop/loop-budget.sh estimate --loop daily-triage

# 模型成本参考
# GPT-4o: $2.5/1M input, $10/1M output
# Gemini 1.5: $0.125/1M input, $0.5/1M output
```

### 成本优化

1. **使用便宜的模型**: Gemini 1.5 比 GPT-4o 便宜 20 倍
2. **减少调用频率**: 不要分钟级调度
3. **限制子代理**: L1 Loop 不应该有子代理
4. **早退**: 没有可操作项时停止运行

---

## 安全运营

### Kill Switch

```bash
# 紧急停止
gh label create loop-pause-all --color ff0000

# 验证停止
gh run list --workflow=loop-triage --limit 5
# 应该有 "This run was cancelled" 或停止触发
```

### Gate 检查

```bash
# 检查路径是否允许
./scripts/loop/loop-gate.sh check --action auto-merge --paths "src/a.py,docs/b.md"

# 检查多个路径
./scripts/loop/loop-gate.sh check --action auto-merge --paths "src/a.py,src/b.py,tests/c.py"
```

### 审计

```bash
# 定期运行审计
./scripts/loop/loop-audit.sh

# 检查安全配置
cat gate.yaml
cat LOOP_CONSTRAINTS.md
```

### 审查自动 PR

```bash
# 查看所有 Loop 创建的 PR
gh pr list --author=app/github-actions --state=open

# 查看 Draft PR
gh pr list --draft --state=open

# 审查并决定是否合并
gh pr review $PR_NUMBER --approve
gh pr merge $PR_NUMBER --squash
```

---

## 故障排查

### Loop 没有运行

```bash
# 1. 检查 workflow 是否启用
gh workflow view loop-triage

# 2. 检查 schedule
gh run list --workflow=loop-triage --limit 1

# 3. 手动触发测试
gh workflow run loop-triage.yml --field dry_run=true
```

### 状态文件锁定

```bash
# 检查是否有 git 冲突
git status

# 如果有，解决冲突
git add .
git commit -m "chore: resolve state file conflict"
```

### Token 限制

```bash
# 检查 API 限制
# 如果看到 rate limit 错误，暂时降低频率

# 调整调度
# 编辑 .github/workflows/loop-*.yml
# cron: '0 8 * * 1-5' # 改为更少频率
```

---

## 最佳实践

1. **定期检查**: 每天至少检查一次 `loop-run-log.md`
2. **及时清理**: 每周清理一次 `STATE.md`
3. **记录问题**: 发现问题时记录到 `loop-run-log.md`
4. **更新文档**: 失败处理后更新本文档
5. **保持审计**: 每月运行一次完整审计

---

*本文档是 [loop-engineering-integration.md](./loop-engineering-integration.md) 的补充。*
