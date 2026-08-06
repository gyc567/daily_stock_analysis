# Ponytail 整合文档

> 本文档描述 Ponytail 极简主义在仓库中的集成方式和最佳实践。

## 一、概述

Ponytail 是一个让 AI Agent 像"最懒的老程序员"一样思考的技能：
- 什么都不说
- 写一行代码
- 能工作

**核心原则**："The best code is the code you never wrote."

## 二、与现有系统的关系

### 2.1 与 AGENTS.md 的关系

Ponytail 是 AGENTS.md §1.2 的具体实现：

| AGENTS.md 规则 | Ponytail 实现 |
|----------------|---------------|
| 默认稳定性优先于顺手优化 | 不添加工具函数库 |
| 非必要重构克制 | 删除死代码、调试代码 |
| 优先复用 | 不包装标准库 |

### 2.2 与三层防御的关系

**三层防御 > Ponytail 极简主义**

当 Ponytail 建议删除某代码，但该代码属于三层防御时，以三层防御为准：

```
Pydantic models ──▶ 不可删除
类型注解 ─────────▶ 不可删除
icontract 装饰器 ──▶ 不可删除
测试代码 ─────────▶ 不可删除
```

### 2.3 与 Loop Engineering 的关系

Ponytail 作为 Loop 的辅助工具：

```
loop-triage ──▶ 识别过度工程化的 Issue
    │
    ▼
ponytail-audit ──▶ 审计技术债务
    │
    ▼
ponytail-review ──▶ 审查 PR diff
    │
    ▼
loop-verify ──▶ 验证修复正确性
```

## 三、核心规则

### 3.1 永远不要添加

- ❌ `utils.py`, `helpers.py`, `common.py`
- ❌ 只有 1 个实现者的抽象类/接口
- ❌ 包装标准库的函数（如 `def my_json_loads()`）
- ❌ 单独的类型别名文件
- ❌ 未使用的占位代码

### 3.2 永远要删除

- ✅ 未使用的导入
- ✅ 死代码（未调用的函数、未使用的变量）
- ✅ `print()` 语句
- ✅ 注释掉的旧代码
- ✅ 过时的 TODO/FIXME

### 3.3 安全区（不可删除）

| 类型 | 示例 | 原因 |
|------|------|------|
| Pydantic models | `class Config(BaseModel):` | 数据验证层 |
| 类型注解 | `def f() -> List[str]:` | 类型安全层 |
| icontract | `@require(x > 0)` | 业务契约层 |
| 测试代码 | `tests/test_*.py` | 质量保障 |
| CI 配置 | `.github/workflows/` | 部署安全 |

## 四、使用方式

### 4.1 本地检查

```bash
# 审查当前 diff
./scripts/ponytail-check.sh review

# 审计整个仓库
./scripts/ponytail-check.sh audit
```

### 4.2 Skill 集成

| Skill | 用途 | 触发条件 |
|-------|------|----------|
| `ponytail-review` | 审查 PR diff | PR 创建/更新 |
| `ponytail-audit` | 仓库技术债务 | 手动/定期 |

### 4.3 Loop 集成

Ponytail 已集成到以下 Loop：

- **loop-triage**: 识别过度工程化的 Issue
- **loop-verify**: 验证代码精简度

## 五、配置

### 5.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MIN_CONFIDENCE` | 80 | 死代码检测置信度 |

### 5.2 强度模式

Ponytail 支持强度模式（可选配置）：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `lite` | 轻度提醒 | 新团队、保守策略 |
| `full` | 标准执行 | 推荐（默认） |
| `ultra` | 激进删除 | 成熟团队、高信任 |

## 六、常见问题

### Q: Ponytail 和 Caveman 有什么区别？

| | Ponytail | Caveman |
|--|----------|---------|
| 作用对象 | 代码 | 对话/回复 |
| 效果 | 减少冗余代码 | 减少冗长回复 |
| 组合 | 推荐同时使用 | - |

### Q: 如何标记"不要删除"的代码？

使用注释标记：
```python
# ponytail:keep  # 这是必需的 Pydantic model
class Config(BaseModel):
    ...
```

### Q: Ponytail 删除了必要的代码怎么办？

1. 使用 `ponytail:keep` 标记
2. 在 PR review 中指出
3. 参考 failure mode #11

## 七、相关文件

| 文件 | 说明 |
|------|------|
| `AGENTS.md` §1.2 | 极简主义规则 |
| `LOOP_CONSTRAINTS.md` | Loop 约束（含 Ponytail 约束） |
| `.claude/skills/ponytail-review/` | Diff 审查 Skill |
| `.claude/skills/ponytail-audit/` | 仓库审计 Skill |
| `scripts/ponytail-check.sh` | 本地检查脚本 |
| `docs/loop-failure-modes.md` | #11-13 Ponytail 特有失败模式 |