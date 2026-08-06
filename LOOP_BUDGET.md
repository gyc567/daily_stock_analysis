# LOOP_BUDGET.md — Loop Budget

> 本文件定义 Loop 的 Token 消耗预算，防止意外超支。
> **预算调整需要 PR approval，禁止 Agent 自动修改。**

## 每日限制

| Loop | 最大运行/日 | 最大 Token/日 | 最大子代理/次 | 当前消耗 |
|------|------------|--------------|--------------|---------|
| Daily Triage (L1) | 1 | 50k | 0 | <!-- -- |
| CI Sweeper (L2) | 5 | 100k | 2 | <!-- -- |
| Dependency Sweeper (L2) | 1 | 80k | 1 | <!-- -- |
| Changelog Drafter (L1) | 10 | 30k | 1 | <!-- -- |

## 累计限制

| 周期 | 最大 Token | 备注 |
|------|-----------|------|
| 每周 | 500k | 约 $0.5-2 (取决于模型) |
| 每月 | 2M | 约 $2-8 (取决于模型) |

## 超预算处理流程

1. **80% 警告**: 切换到报告模式，暂停子代理
2. **100% 暂停**: 
   - 暂停调度
   - 追加事件到 `loop-run-log.md`
   - 打开维护者 Issue
3. **人工恢复**: 审核后调整预算或关闭 Loop

## Kill Switch

- **Label**: `loop-pause-all`
- **立即生效**: 停止所有 Loop 运行

## 估算工具

```bash
./scripts/loop/loop-budget.sh estimate --loop daily-triage
```

## 模型成本参考

| 模型 | Input $/1M | Output $/1M |
|------|------------|------------|
| GPT-4o | $2.5 | $10 |
| Claude 3.5 | $3 | $15 |
| Gemini 1.5 | $0.125 | $0.5 |

## 消耗记录

<!-- 由 workflow 自动追加 -->
