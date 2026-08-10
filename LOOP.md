# Loop Configuration — Minimal Triage

## Active Loops

| Pattern | Cadence | Status | Command |
|---------|---------|--------|---------|
| Daily Triage | 1d | L1 report-only | See README |

## Human Gates

- No auto-fix until L2 checklist complete
- All high-risk paths: human review required

## Budget

- Max sub-agent spawns per run: 0 (L1) / 2 (L2)
- Max tokens/day: 100k (see `loop-budget.md`)
- Append each run to `loop-run-log.md`; use `loop-budget` skill at start/end
- Kill switch: `loop-pause-all` — pause schedulers and notify human
- Estimate: `npx @cobusgreyling/loop-cost --pattern daily-triage`

## MCP Usage

MCP not required for this pattern. This loop uses native Claude Code tools only.

## Worktree Isolation

For high-risk fixes (P0/P1), the loop should:
1. Create isolated worktree: `git worktree add .worktrees/<branch> <branch>`
2. Implement and verify fix in isolation
3. Merge via PR after human review
4. Remove worktree after merge

This prevents main branch pollution from experimental fixes.

## Links

- Pattern: [daily-triage](../../patterns/daily-triage.md)
- Checklist: [loop-design-checklist](../../docs/loop-design-checklist.md)