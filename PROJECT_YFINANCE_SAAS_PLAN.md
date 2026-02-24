# PROJECT_YFINANCE_SAAS_PLAN

## 1) Current state snapshot
- API MVP is live in repo scope: quote, history, batch quotes, fundamentals, auth, billing endpoints, OpenAPI docs.
- Test baseline is healthy: `30 passed` (latest report: `reports/test_report_2026-02-24_13-29-33.txt`).
- Container/release hygiene exists: Dockerfile, compose healthchecks, CI smoke runbook, deployment smoke script.
- Docs are present (README + API guide), but customer onboarding and conversion flow are still lightweight.
- Billing webhook is acknowledged but production-grade subscription state persistence/ops controls are not fully closed.

## 2) Shipping priorities (match CRON_BRIEF order)
1. **API correctness + stability**
   - Tighten response/error contract consistency; expand edge-case regression coverage per endpoint.
2. **Auth/billing safety**
   - Harden auth/billing guardrails, webhook handling expectations, and failure-mode behavior.
3. **Customer docs quality**
   - Improve quickstart, endpoint examples, no-code recipes, and error-handling playbooks.
   - Add interactive API explorer UX (API key authorize + prebuilt try-it requests) as a planned docs milestone.
4. **Deployment + reliability**
   - Standardize smoke/deploy checks, runbooks, and alerting signals.
5. **Conversion improvements (landing + customer journey)**
   - Clarify value prop, CTA flow, pricing/plan copy, and trial-to-paid path.
6. **Internal dashboard + API key self-serve portal**
   - Define MVP scope and sequence after core reliability/docs are stable.

## 3) 2-week milestone plan (concrete deliverables)
### Week 1 — Reliability + safety foundation
- **Builder**: close top correctness gaps from test/backlog review; normalize error payload behavior across all public endpoints.
- **QA**: add targeted regression matrix for invalid symbol/period/interval, auth failures, and provider transient failures.
- **Docs**: publish "first 15 minutes" onboarding path + status-code troubleshooting guide.
- **Ops**: enforce container health smoke in CI + validate manual deploy smoke checklist against current env.
- **Deliverables**:
  - Updated test suite + green CI
  - Error contract checklist (implemented + validated)
  - Onboarding/troubleshooting docs merged
  - Smoke runbook verified and current

### Week 2 — Customer readiness + go-to-market baseline
- **Builder**: implement highest-impact non-breaking improvements for billing/auth safety and operational observability hooks.
- **QA**: execute end-to-end happy path + failure-path validation (API + billing endpoints).
- **Docs**: refresh landing/customer journey copy to reduce setup friction and make CTA path explicit.
- **Ops**: define deployment rollback criteria and alert thresholds for health/test regressions.
- **Deliverables**:
  - Billing/auth hardening checklist completed
  - E2E validation report published
  - Updated landing + customer flow copy shipped
  - Rollback + alert criteria documented

## 4) Definition of done per lane
- **Builder DoD**
  - Changes are scoped to assigned feature/fix, backward-compatible for documented API behavior.
  - Tests added/updated for new or changed behavior.
  - No deployment/process/docs-only tasks mixed into builder PRs.
- **QA DoD**
  - Test plan includes happy path + edge/failure cases for touched area.
  - Regressions reproducible with clear pass/fail evidence and report artifact.
  - No net drop in coverage of critical endpoints.
- **Docs DoD**
  - Steps are runnable by a new user without implicit context.
  - Examples validated against current API behavior and status codes.
  - Copy is concise, consistent, and mapped to target user journey.
- **Ops DoD**
  - Smoke checks/runbooks execute as documented.
  - Deploy/rollback criteria are explicit and testable.
  - Alerting/operational signals are actionable (clear owner + threshold).

## 5) Risk register + mitigations
- **Upstream market-data instability** → Mitigation: defensive error mapping, retries only where safe, clear 502 handling docs.
- **Billing/webhook misconfiguration in production** → Mitigation: preflight config checklist, webhook signature validation tests, staged verification before release.
- **Spec drift between docs and API behavior** → Mitigation: docs validation against live/local test calls each cycle.
- **Silent deploy regressions** → Mitigation: mandatory smoke gate + rollback trigger rules.
- **Scope sprawl across lanes** → Mitigation: strict role boundaries and main-coordinator re-assignment when cross-lane work appears.

## 6) Next cron-cycle task queue (small, actionable)
1. Build a short endpoint-by-endpoint error-contract checklist and mark current pass/fail.
2. Add/verify regression tests for auth missing/invalid key + malformed market-data query params.
3. Update docs with a single "new user quickstart" flow (env setup → first successful call → common errors).
4. Run and record container smoke check result in latest cycle notes.
5. Create a billing safety checklist (required env vars, webhook signature, expected failure responses).
6. Propose minimal metrics/alerts table for `/v1/health` and test-status regression visibility.
7. Implement docs explorer upgrade plan (Swagger/Scalar-style key authorize + curated example requests).
