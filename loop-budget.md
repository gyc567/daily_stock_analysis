# Loop Budget — YOUR_PROJECT

> Primary loop: **Daily Triage** (scaffolded by loop-init)

## Daily limits

| Loop | Max runs/day | Max tokens/day | Max sub-agent spawns/run |
|------|--------------|----------------|--------------------------|
| Daily Triage | 2 | 100k | 0 (L1) / 2 (L2) |

## On budget exceed

1. Pause schedulers (`scheduler_delete` or disable automations)
2. Append event to `loop-run-log.md`
3. Notify human (Slack / issue / STATE.md High Priority)

## Kill switch

- Command or issue label: `loop-pause-all`
- Resume only after human clears the flag in STATE.md

## Estimate spend

```bash
npx @cobusgreyling/loop-cost --pattern daily-triage
```
## 2026-08-11 actual spend

| Iteration | Loop | Sub-agents | Tokens (est) | Trigger |
|-----------|------|------------|--------------|---------|
| Dev bootstrap | Manual L1 | 0 | ~25k | manual |
| Watchlist + 3-bug fix | Manual L2 | 0 | ~75k | manual (user report) |
| Commit + push + draft PR | Manual L1 | 0 | ~10k | manual (user instruction) |
| Merge PR #32 | Manual L1 | 0 | ~3k | manual (user instruction) |
| **Day total** | — | **0** | **~113k** | within cap |
| (2026-08-14) analyze-all + PR #33 | Manual L2 | 0 | ~35k | manual ("继续完成工作") |
| (2026-08-14) Merge PR #33 | Manual L1 | 0 | ~3k | manual ("合 PR") |
| **Cross-day total** | — | **0** | **~191k** | within cap |

Notes: 全程 in-process，未 spawn 任何 sub-agent。下次起手前 `loop-budget` skill 复算。
