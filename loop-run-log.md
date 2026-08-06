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

---

<!-- 由 workflow 自动追加 -->

### 2026-08-06 Loop Ready 审计与修复

| 字段 | 值 |
|------|-----|
| Loop | Manual Audit |
| Level | - |
| Duration | ~20min |
| Tokens | - |
| Result | success |
| Trigger | manual |
| 备注 | 修复 LOOP.md Score、LOOP_CONSTRAINTS.md 路径、require-review 返回值 |
