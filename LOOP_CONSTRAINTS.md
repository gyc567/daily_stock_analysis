# LOOP_CONSTRAINTS.md — Loop Constraints

> **Agent 必须遵守的约束文件**。每次 Loop 运行前必须读取并遵守。
> 此文件是 [AGENTS.md](./AGENTS.md) 的 Loop-specific 补充。

## 推送与合并

- ✅ 推送前必须告知人类
- ✅ 必须先创建 Draft PR，人类审核后才能标记 ready
- ❌ **禁止自动合并到 main**（除依赖补丁外，且需要 CI 通过 + 人类 approval）
- ❌ 禁止在未告知的情况下推送代码

## 路径保护 (Denylist)

以下路径 **禁止** Loop 自动修改：

```
.env
.env.*
**/secrets/**
**/credentials/**
**/*_key*
**/*_secret*
auth/**
bot/**
data_provider/**
src/config/**
src/services/notification/**
src/services/bot/**
```

以下路径 **需要人类审核**：

```
.github/workflows/
docker/
scripts/ci_gate.sh
src/reports/
src/analyzer/
main.py
```

## 代码质量

- ✅ 修复前必须运行测试: `pytest tests/` 或 `./scripts/ci_gate.sh`
- ❌ **禁止禁用测试** 以通过 CI
- ❌ **禁止跳过 lint** 以通过 CI
- ✅ 每次修复 **不超过一个功能模块**
- ✅ 单项最多 **3 次尝试**，超出后 escalation

## 股票分析特定约束

- ❌ 禁止修改 `data_provider/` 中的数据源 fallback 优先级
- ❌ 禁止修改 `src/reports/` 中的报告模板结构
- ❌ 禁止修改通知渠道配置（bot 配置、webhook 等）
- ❌ 禁止修改 `main.py` 的核心调度逻辑

## 通信与交接

- ✅ 执行前必须说明计划
- ✅ 完成后必须报告结果
- ❌ **禁止关闭 Issue 或 PR**（需人类确认）
- ❌ **禁止添加/删除 labels**（需人类确认）

## 预算与资源

- ⚠️ Token 消耗达 **80% 日限额** 时，切换到报告模式
- ⚠️ `loop-pause-all` 激活时 **立即退出**

## 错误处理

- ✅ 记录错误到 `loop-run-log.md`
- ✅ 创建 Issue 标记需要人工处理的问题
- ❌ **禁止静默失败**

---

*违反约束将触发 gate 检查失败，禁止继续执行*

## 极简主义约束（Ponytail）

- ❌ **禁止添加冗余工具函数库**（`utils.py`, `helpers.py` 等）
- ❌ **禁止添加无用的抽象层**（只有 1 个实现者的抽象类/接口）
- ❌ **禁止包装标准库**（如 `import json; def my_json_loads(...)`）
- ✅ **必须删除未使用的导入**
- ✅ **必须删除死代码**（未调用的函数、未使用的变量）
- ✅ **必须删除调试代码**（print、console.log、注释掉的代码）
- ❌ **不可删除三层防御代码**：
  - Pydantic models（`class X(BaseModel):`）
  - 类型注解（`def f() -> X:`）
  - icontract 装饰器（`@require(...)`）
  - 测试代码（`tests/`）
- ❌ **不可删除 Loop 安全相关文件**：
  - `gate.yaml`
  - `LOOP_*.md`
  - `.claude/skills/loop-*/`

### 快速检查

```bash
# 提交前自检
./scripts/ponytail-check.sh review
```
