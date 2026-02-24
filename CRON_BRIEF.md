# Y Finance API — Cron Work Brief

## Purpose
Execute concrete shipping work on Y Finance API every run.

## Execution mode
- Main acts as coordinator.
- First read `PROJECT_YFINANCE_SAAS_PLAN.md` for big-picture direction.
- Then assign scoped tasks to subagents and enforce role boundaries:
  - `builder`: implementation/refactors only (no deployment changes, no pricing/copy decisions)
  - `qa`: tests/validation/regressions only (no feature authoring except minimal test fixes)
  - `docs`: customer docs/onboarding/positioning copy only (no backend code changes)
  - `ops`: deployment hardening/infra/runbooks only (no product feature changes)
- Subagents must stay in their lane; if a task crosses lanes, return to `main` for re-assignment.

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

## Update policy
Post an update only when:
- a milestone is completed,
- a blocker needs input, or
- a risky decision needs approval.
