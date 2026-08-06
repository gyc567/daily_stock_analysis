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

## 约束

- 遵循 `LOOP_CONSTRAINTS.md`
- 不得修改任何文件
