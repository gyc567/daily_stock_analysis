# Ponytail Audit Skill

审计整个仓库的过度工程化和技术债务。

## 触发条件

- 手动 `/ponytail-audit`
- 定期（建议每月）
- loop-triage 标记后

## 审计范围

### 1. 工具函数库检测

```bash
# 查找工具函数文件
find . -name "utils.py" -o -name "helpers.py" -o -name "common.py" -o -name "tools.py" 2>/dev/null | grep -v node_modules | grep -v __pycache__

# 分析每个文件
for f in $(find . -name "utils.py" -o -name "helpers.py" 2>/dev/null | grep -v node_modules); do
    echo "=== $f ==="
    wc -l "$f"
    grep "def " "$f" | wc -l
done
```

### 2. 死代码检测

```bash
# Python: 查找未使用函数（简单版）
grep -rn "def " --include="*.py" . | grep -v test | grep -v __pycache__
grep -rn "class " --include="*.py" . | grep -v test | grep -v __pycache__

# 检测从未被调用的函数（需要 vulture）
pip install vulture --quiet 2>/dev/null
vulture --min-confidence 80 . 2>/dev/null || echo "vulture not available"
```

### 3. 冗余代码检测

```bash
# 检测重复代码块（简单版）
grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.py" . | grep -v test

# 检测过长的函数（> 50 行）
awk '/^def / {func=$0; n=0} /^[^ \t]/? /^def / {print n, func; func=$0; n=0} {n++} END {print n, func}' -- --include="*.py" . | sort -rn | head -10
```

### 4. 包装器检测

```bash
# 检测包装标准库的代码
grep -rn "import json" --include="*.py" . | head -5
grep -rn "from json import" --include="*.py" . | head -5
grep -rn "import requests" --include="*.py" . | head -5
```

### 5. ponytail: 标记收集

```bash
# 收集标记的延迟任务
grep -rn "ponytail:" --include="*.py" --include="*.js" . 2>/dev/null || echo "No ponytail markers found"
```

### 6. 依赖膨胀检测

```bash
# 检查 requirements.txt 或 package.json 变化
if [ -f "requirements.txt" ]; then
    echo "=== Python 依赖 ==="
    wc -l requirements.txt
    head -20 requirements.txt
fi

if [ -f "package.json" ]; then
    echo "=== Node 依赖 ==="
    grep '"dependencies"' -A 20 package.json | head -25
fi
```

## 输出格式

```markdown
## Ponytail Audit Report

**审计时间**: YYYY-MM-DD
**仓库**: <当前目录>

### 🔴 高优先级（建议修复）

| 类型 | 文件 | 行数 | 原因 |
|------|------|------|------|
| 工具函数 | src/utils.py | 45 | 可内联到调用处 |
| 死代码 | src/old.py | 30 | 函数未被调用 |
| 过度抽象 | src/base.py | 20 | 无具体实现 |

### 🟡 中优先级

| 类型 | 数量 | 估算减少 |
|------|------|----------|
| 未使用导入 | 12 | ~50 LOC |
| 冗余注释 | 8 | ~30 LOC |
| 调试代码 | 5 | ~20 LOC |

### 📊 仓库统计

| 指标 | 数值 |
|------|------|
| 总文件数 | X |
| 总代码行数 | Y |
| 估算可减少 | Z% (~W LOC) |
| 预估 Token 节省 | ~T% |

### 📋 建议创建的 Issue

\`\`\`markdown
Title: [Tech Debt] 清理过度工程化代码

## 摘要
- 工具函数库: N 个文件
- 死代码: ~X LOC
- 冗余导入: Y 个

## 影响
- 代码可维护性提升
- 编译/解析速度提升
- Token 消耗减少

## 标签
- ponytail-debt
- tech-debt
- good-first-issue (部分)

## 建议
分批次清理，每批不超过 5 个文件
\`\`\`

### 📌 ponytail: 标记的任务

| 文件 | 行号 | 描述 |
|------|------|------|
| - | - | 无延迟任务 |
```

## 约束

- 只报告，不修改任何代码
- 提供可操作的建议
- 按影响优先级排序
- 遵循 `gate.yaml` 路径保护
- 不审计 denylist 路径