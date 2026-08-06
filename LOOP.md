# LOOP.md — Daily Stock Analysis Loop Engineering

> 本文件是 Loop Engineering 的入口文档，描述本仓库的活跃 Loops 和运营状态。
> 参考 [docs/loop-engineering-integration.md](./docs/loop-engineering-integration.md)

## 活跃 Loops

| Loop | Level | 频率 | Skill | 状态 |
|------|-------|------|-------|------|
| Daily Triage | L1 | 工作日 8:00 UTC | `loop-triage` | 🚀 已完成 |
| CI Sweeper | L2 | 按需 | `loop-verify` | 🚀 已完成 |
| Dependency Sweeper | L2 | 每周 | `loop-verify` | 🚀 已完成 |

## Loop Ready Score

当前分数: **80** / 110

详见 `scripts/loop/loop-audit.sh`

## 安全机制

| 机制 | 文件 | 说明 |
|------|------|------|
| Kill Switch | `loop-pause-all` label | 立即停止所有 Loop |
| 门禁 | `gate.yaml` | 路径保护与自动合并限制 |
| 约束 | `LOOP_CONSTRAINTS.md` | Agent 必须遵守的规则 |
| 预算 | `LOOP_BUDGET.md` | Token 消耗控制 |

## 本地开发

```bash
# 审计 Loop Ready
./scripts/loop/loop-audit.sh .

# 检查门禁
./scripts/loop/loop-gate.sh check --action auto-merge --paths "src/a.py"

# 检查预算
./scripts/loop/loop-budget.sh status
```

## 贡献 Loop

新增 Loop 需要：
1. 在 `STATE.md` 添加条目
2. 创建对应的 Skill
3. 创建对应的 Workflow
4. 更新本文档
5. 更新 `docs/INDEX.md` 的参考与开发部分

## 相关文件

- [Loop Engineering 集成方案](./docs/loop-engineering-integration.md)
- [Loop Engineering 失败模式](./docs/loop-failure-modes.md)
