# Y Finance API — Cron Work Brief

## Purpose
Execute concrete shipping work on Y Finance API every run.

## Execution mode
- Main acts as coordinator and may use subagents for larger scoped work.
- First read `PROJECT_YFINANCE_SAAS_PLAN.md` for big-picture direction.
- Stability limits for cron runs:
  - Spawn **max 1 subagent per cycle**.
  - Run subagent work **sequentially** (never fan out multiple subagents in one cycle).
  - Use subagents only for tasks likely to exceed 10 minutes if done directly.
- For the immediate dashboard focus, prefer a single `builder` subagent to deliver one vertical slice per cycle.
- Keep scope tight: one concrete milestone per run.

## Thinking policy (explicit)
Main should run at `medium` thinking for this work-cycle.
If spawning a subagent, set explicit thinking based on task:
- implementation/refactor: `medium`
- test/validation: `high`
- docs/copy: `low`
- ops/deploy: `medium`
Prefer execution over long analysis loops.

## Shipping priority
1. **Immediate focus (until first milestone lands): Internal dashboard v0 scaffold**
   - create dashboard app skeleton under `web/`
   - add auth gate placeholder/login shell
   - add API key management page shell
   - add usage/metrics page shell
2. API correctness + stability
3. Auth/billing safety
4. Customer docs quality
5. Deployment + reliability
6. Conversion improvements on landing/customer journey

## Operating rules
- Make real progress each run (code/docs/tests/deploy steps), not just reporting.
- Escalate only real blockers/decisions that need Boss input.
- Keep comms concise; no routine spam.
- No destructive actions without explicit approval.
- Never leak secrets.
- Target a runtime budget of <15 minutes; if work will exceed that, checkpoint and continue next cycle.

## Update policy
Post an update only when:
- a milestone is completed,
- a blocker needs input, or
- a risky decision needs approval.
