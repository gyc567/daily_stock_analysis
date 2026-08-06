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
- 遵循 `LOOP_CONSTRAINTS.md`
