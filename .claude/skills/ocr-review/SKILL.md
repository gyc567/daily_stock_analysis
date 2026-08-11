# ocr-review Skill

open-code-review (ocr) integration for Claude Code — local pre-review and delegated review.

详细教程见 `docs/ocr-guide.md`。

## 自动安装

若 `ocr --version` 失败，本 skill 自动触发安装流程（参见 `.claude/skills/ocr/SKILL.md`）：

```bash
npm install -g @alibaba-group/open-code-review
```

## Prerequisites

- `ocr` binary installed and configured
- `ocr --version` should show `open-code-review v1.9.x`
- Git repository with uncommitted or staged changes, or a branch range to review

## Commands

### `/ocr-review review`

Run ocr diff review on the current workspace (staged + unstaged changes).

```
ocr review --from main --to HEAD --repo . --format text --audience human
```

**When to use**: Before committing or opening a PR, to catch issues early.

### `/ocr-review scan --path <target>`

Run ocr full-file scan on specific file(s) or directory.

```
ocr scan --path src/pages/HomePage.tsx --no-summary
ocr scan --path apps/dsa-web/src/components --no-summary
```

**When to use**: Audit a specific component or directory without a diff.

### `/ocr-review delegate`

Output review spec (files + resolved rules) for host agent to execute.

```
ocr delegate preview --from main --to HEAD
ocr delegate rule <file1> <file2>
```

**When to use**: Let Claude Code perform the actual LLM review using ocr's file selection and rule engine.

### `/ocr-review check-config`

Verify ocr LLM connectivity and config.

```
ocr llm test
ocr config provider
```

**When to use**: After installing or changing ocr's provider/model config.

## Config

ocr reads config from `~/.opencodereview/config.json`. Set provider:

```bash
ocr config set provider anthropic
ocr config set providers.anthropic.api_key "$ANTHROPIC_API_KEY"
ocr config set model claude-opus-4-6
```

Or use a custom provider (e.g. local LiteLLM):

```bash
ocr config set custom_providers.local-gateway.url http://localhost:4000/v1
ocr config set custom_providers.local-gateway.protocol openai
ocr config set provider local-gateway
```

## Tips

- Use `--concurrency 4` in CI environments to limit parallel file reviews
- Set `OCR_NO_UPDATE=1` in CI to disable self-update check and avoid latency
- Use `--exclude "node_modules/**,*.log"` to skip noise files
- Session replay: `ocr session list` to see past reviews, `ocr viewer` for WebUI
