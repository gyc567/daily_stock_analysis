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

---

## Ponytail 规则检查

### 必须通过的检查

| 检查项 | 通过条件 |
|--------|----------|
| 无新增工具函数库 | 不存在 utils.py, helpers.py 等 |
| 无新增包装器 | 不包装标准库 |
| 无新增冗余抽象 | 抽象层有 >= 2 个实现 |
| 无新增未使用导入 | 所有导入被使用 |
| 无新增死代码 | 所有函数被调用 |
| 无新增调试代码 | 无 print, console.log |

### 防御层完整性

| 类型 | 必须保留 |
|------|----------|
| Pydantic models | ✅ |
| 类型注解 | ✅ |
| icontract 装饰器 | ✅ |
| 测试代码 | ✅ |

### 检查命令

```bash
# 运行 Ponytail 检查
./scripts/ponytail-check.sh review
```
