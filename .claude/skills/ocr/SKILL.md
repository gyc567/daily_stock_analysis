# ocr Skill

open-code-review (ocr) 安装状态检查 + 自动安装 + 配置引导。

## 自动安装流程

当 `ocr --version` 失败（command not found / exit != 0）时，本 skill 自动执行：

```bash
npm install -g @alibaba-group/open-code-review
```

安装完成后验证：

```bash
ocr --version
```

期望输出：`open-code-review v1.9.x ...`

## 配置引导

安装成功后，检查 `ocr llm test` 是否通过（至少能列出 provider）。

**若未配置 provider**（`ocr llm test` 失败或提示 `api_key missing`）：

1. 询问用户要使用哪个 provider（推荐 `anthropic`）
2. 引导用户提供 API key（通过凭据管理器，不接受硬编码）
3. 执行 `ocr config set provider <name>`
4. 执行 `ocr config set providers.<name>.api_key "$API_KEY"`
5. 执行 `ocr config set model <model>`（推荐 `claude-opus-4-6`）
6. 验证：`ocr llm test`

**快速配置（已知 API key）**

```bash
ocr config set provider anthropic
ocr config set providers.anthropic.api_key "$ANTHROPIC_API_KEY"
ocr config set model claude-opus-4-6
ocr llm test
```

## 使用方式

安装 + 配置完成后，直接使用 ocr：

```bash
# Diff review
ocr review --from main --to HEAD --repo . --format text --audience human

# Full scan
ocr scan --path src/pages/HomePage.tsx

# Delegate
ocr delegate preview --from main --to HEAD
```

详细用法见 `docs/ocr-guide.md`。
