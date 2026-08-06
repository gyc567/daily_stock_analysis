# Loop Engineering 安全机制

> 本文档是 gate.yaml 的摘要版本，用于快速参考。

## 禁止路径 (Denylist)

以下路径 **禁止** Loop 自动修改：

| 路径 | 说明 |
|------|------|
| `.env`, `.env.*` | 环境变量（可能包含密钥） |
| `**/secrets/**`, `**/credentials/**` | 密钥存储目录 |
| `**/*_key*`, `**/*_secret*` | 密钥相关文件 |
| `auth/**` | 认证模块 |
| `bot/**` | 机器人配置 |
| `data_provider/**` | 数据源适配器 |
| `src/config/**` | 配置模块 |
| `src/services/notification/**` | 通知服务 |
| `src/services/bot/**` | 机器人服务 |

## 需要人类审核的路径 (Require Review)

以下路径修改需要人类审核：

| 路径 | 说明 |
|------|------|
| `.github/workflows/**` | GitHub Actions 工作流 |
| `docker/**` | Docker 配置 |
| `scripts/ci_gate.sh` | CI 门禁脚本 |
| `src/reports/**` | 报告生成模块 |
| `src/analyzer/**` | 分析器模块 |
| `main.py` | 主入口文件 |

## 自动合并白名单 (Auto-Merge Allowlist)

只有以下路径可以自动合并：

| 路径 | 说明 |
|------|------|
| `docs/**/*.md` | 文档文件 |
| `scripts/**/*.sh` | Shell 脚本 |
| `src/**/*.py` | Python 源代码 |
| `tests/**/*` | 测试文件 |
| `package.json` | npm 包配置 |
| `requirements.txt` | Python 依赖 |

## 自动合并条件

1. CI 必须通过
2. 测试必须通过
3. 必须有人类审核批准
4. 不能触碰 denylist 路径
5. 修改文件数不超过 10 个

## Kill Switch

紧急情况下，可以使用 `loop-pause-all` label 立即停止所有 Loop：

```bash
gh label create loop-pause-all --color ff0000
gh issue label add <issue_number> --repo <owner/repo> loop-pause-all
```

## 约束规则

详见 [LOOP_CONSTRAINTS.md](../LOOP_CONSTRAINTS.md)

## 检查工具

```bash
# 检查路径是否合规
./scripts/loop/loop-gate.sh check --action auto-merge --paths "src/utils.py"

# 审计 Loop Ready 状态
./scripts/loop/loop-audit.sh

# 检查预算
./scripts/loop/loop-budget.sh status
```
