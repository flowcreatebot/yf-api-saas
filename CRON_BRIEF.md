# Y Finance API — Cron Work Brief

## Purpose
Execute concrete shipping work on Y Finance API every run.

## Product target (authoritative)
This dashboard is for **logged-in paying customers** of the app.
Not an internal/admin-only dashboard.

## Execution mode
- Main acts as coordinator and may use subagents for larger scoped work.
- First read `PROJECT_YFINANCE_SAAS_PLAN.md` for big-picture direction.
- Stability limits for cron runs (parallel-safe mode):
  - Spawn **max 2 subagents in parallel** per cycle.
  - Allowed pair:
    - `builder` (implementation)
    - plus exactly one of `qa` (test hardening) or `docs` (customer docs)
  - Never spawn more than 2 subagents in the same cycle.
  - If a blocker appears, stop further spawns and report blocker.
- Every cycle must include one `builder` subagent delivering a customer-facing dashboard vertical slice.
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
1. **Immediate focus: customer dashboard v1 (authenticated product UX)**
   - customer login/session flow (no localStorage-only placeholder auth)
   - tenant/user-scoped data access for keys/usage/activity
   - dashboard routes/UX for real customers (`/dashboard` product experience)
   - migrate placeholder endpoints/contracts to customer-safe equivalents
   - keep backward compatibility only as temporary migration aid
2. API correctness + stability
3. Auth/billing safety
4. Customer docs quality
5. Deployment + reliability
6. Conversion improvements on landing/customer journey

## Guardrails
- Do not describe the dashboard as “internal” in user updates.
- Use “customer dashboard” terminology in code comments/docs where applicable.
- If a task requires product decision (auth provider/session model), surface concise options + recommendation.

## Operating rules
- Make real progress each run (code/docs/tests/deploy steps), not just reporting.
- Escalate only real blockers/decisions that need Boss input.
- Keep comms concise; no routine spam.
- No destructive actions without explicit approval.
- Never leak secrets.
- Target a runtime budget of <35 minutes even with parallel subagents; if work will exceed that, checkpoint and continue next cycle.
- Main must post a single consolidated milestone/blocker update (avoid noisy per-step chatter).

## Update policy
Post an update only when:
- a milestone is completed,
- a blocker needs input, or
- a risky decision needs approval.
