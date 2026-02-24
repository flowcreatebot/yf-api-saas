# Y Finance API — Cron Work Brief

## Purpose
Execute concrete shipping work on Y Finance API every run.

## Execution mode
- Main executes work directly in this repo for cron runs.
- First read `PROJECT_YFINANCE_SAAS_PLAN.md` for big-picture direction.
- **Do not spawn subagents during cron work-cycles** (temporary stability rule while announce-delivery bug is unresolved).
- Keep scope tight: one concrete milestone per run.
- If a task truly requires role split (builder/qa/docs/ops), defer that split to a manual non-cron run.

## Thinking policy (explicit)
Main should run at `medium` thinking for this work-cycle.
Prefer execution over long analysis loops.

## Shipping priority
1. API correctness + stability
2. Auth/billing safety
3. Customer docs quality
4. Deployment + reliability
5. Conversion improvements on landing/customer journey
6. Internal dashboard + API key self-serve portal

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
