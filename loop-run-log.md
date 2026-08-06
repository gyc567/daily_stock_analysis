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
