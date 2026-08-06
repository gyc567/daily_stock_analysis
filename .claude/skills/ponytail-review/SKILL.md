# Ponytail Review Skill

使用 Ponytail 极简主义规则审查 diff。

## 触发条件

- PR 创建/更新
- CI Sweeper 修复后
- 手动 `/ponytail-review`

## 核心规则

### 永远不要添加

- ❌ 工具函数库（utils.py, helpers.js）
- ❌ 抽象基类（只有 1 个实现者）
- ❌ 设计模式（无实际使用）
- ❌ 包装器（包装标准库）
- ❌ 单独的常量文件（直接内联）
- ❌ 类型别名（除非被多处使用）
- ❌ 空模块或空文件（`__init__.py` 除外）

### 永远要删除

- ✅ 未使用的导入
- ✅ 死代码（未调用函数、未使用变量）
- ✅ 调试代码（console.log, print, 注释掉的旧代码）
- ✅ 冗余注释（代码本身已说明意图）
- ✅ 过时的 TODO（已不再是计划）

## 安全区（不删除）

| 类型 | 示例 | 原因 |
|------|------|------|
| Pydantic models | `class X(BaseModel):` | AGENTS.md §1.3 强制 |
| 类型注解 | `def f() -> List[str]:` | 三层防御 Layer 1 |
| icontract | `@require(...)` | 三层防御 Layer 2 |
| 测试代码 | `tests/*.py` | 质量底线 |
| CI 配置 | `.github/workflows/*.yml` | 部署安全 |
| 文档字符串 | `"""Docstring"""` | 保持可读性 |
| gate.yaml | `gate.yaml` | Loop 安全护栏 |
| denylist 文件 | `bot/**`, `data_provider/**` | 路径保护 |

## 检查清单

| 检查项 | 阈值 | 操作 |
|--------|------|------|
| 新增行数 / 删除行数 | > 3:0 | ⚠️ 警告 |
| 新增文件数 | > 3 | ⚠️ 警告 |
| 新增依赖 | ≥ 1 | ❌ 需明确理由 |
| utils.py 膨胀 | > 5 函数 | ❌ 建议删除 |
| 包装器代码 | 包装标准库 | ❌ 建议删除 |

## 快速检测命令

```bash
# 检测工具函数
find . -name "utils.py" -o -name "helpers.py" -o -name "common.py" | head -10

# 检测未使用导入
python -c "import ast; import sys; ..."

# 检测死代码
grep -r "def unused_" --include="*.py" .

# 检测注释掉的代码
grep -r "# " --include="*.py" | grep -v "^\s*# "

# 检测 TODO
grep -rn "TODO" --include="*.py" .
```

## 输出格式

```markdown
## Ponytail Review

### 🔴 删除建议
| 文件 | 行数 | 原因 | 建议操作 |
|------|------|------|----------|
| src/utils.py | 45 | 工具函数，可内联 | 删除或合并到调用处 |
| src/base.py | 30 | 无具体实现 | 删除 |

### 🟡 需人工判断
| 文件 | 描述 | 理由 |
|------|------|------|
| src/wrapper.py | 包装了标准库 json | 可能已有 json 够用 |

### 🟢 通过
- diff 比例合理（新增/删除 < 3:1）
- 无新增冗余文件
- 无工具函数膨胀
- 防御层完整

### 📊 统计
- 新增行数: X
- 删除行数: Y
- 净变化: +Z / -Z
- 估算 Token 节省: ~T%
```

## 约束

- 只建议，不强制删除
- 保留所有防御层代码
- 遵循 `LOOP_CONSTRAINTS.md` 和 `gate.yaml`
- 不删除 denylist 中的文件
- 不建议删除测试代码