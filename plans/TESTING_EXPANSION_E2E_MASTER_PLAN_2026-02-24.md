# YF API SaaS — Testing Expansion Master Plan

Date: 2026-02-24
Owner: Alfred
Status: Active

## Goal
Build a professional, production-grade testing program that progresses from strong API regression coverage to full end-to-end confidence across local, CI, and deployed environments.

## Success criteria (definition of "full E2E coverage")
1. Critical user journeys are validated end-to-end in deployed environment(s), not only mocks.
2. Billing/checkout/webhook flows are validated with realistic staging setup and failure-path checks.
3. Auth, API key lifecycle, and dashboard flows are validated via browser E2E tests.
4. Smoke + health + contract checks run automatically post-deploy.
5. 09:00 daily gate is strict: any regression causes RED alert with actionable failure details.
6. Test evidence is versioned (reports, artifacts, traces, screenshots) and easy to audit.

## Current baseline
- Strong pytest API regression suite exists for auth, market endpoints, billing contracts, and dashboard shell/API behavior.
- Current suite is mostly app-level test client + mocked dependencies.
- True full deployed E2E is still incomplete.

## Workstreams

### A) Test architecture hardening
- Create a test pyramid with explicit layers:
  - Unit tests (pure logic)
  - Service/API integration tests
  - Browser E2E tests (dashboard + customer journeys)
  - Deployed smoke & canary checks
- Standardize markers/tags: `unit`, `integration`, `e2e`, `deployed`, `billing`, `critical`.
- Enforce deterministic fixtures, seeded data, and stable test IDs.

### B) API contract + negative-path expansion
- Extend endpoint-by-endpoint contract tests for:
  - error codes
  - response schemas
  - auth boundary behavior
  - upstream failure and timeout mapping
- Add fuzz/property-style checks for malformed params and edge symbols.

### C) Billing and subscription E2E
- Add staging Stripe scenario tests:
  - checkout session creation
  - success/cancel redirects
  - webhook signature verification
  - subscription state transitions
  - idempotency/replay protection tests
- Add failure-path tests for misconfig and partial outages.

### D) Dashboard browser E2E
- Implement browser E2E suite (Playwright) for:
  - login/auth gate flow
  - API key create/rotate/revoke/activate UX
  - metrics page load and core widget assertions
  - unauthorized access redirects
- Enable artifact capture (screenshots/video/trace) for failures.

### E) Deployed environment verification
- Add deploy-target test pack:
  - `/v1/health` and core endpoint canaries
  - auth checks against deployed host
  - dashboard availability and critical UX path
  - billing webhook probe path (safe non-production mode)
- Add environment matrix (staging required; production read-only smoke).

### F) 09:00 quality gate (must be perfect)
- Daily 09:00 run executes:
  1) full regression suite
  2) browser E2E critical flows
  3) deployed smoke pack
  4) summary with PASS/FAIL + exact failing area
- If any critical test fails: immediate RED alert with triage notes and suspected owner lane.

## Hourly execution strategy
Each hourly run should ship one concrete increment from this backlog:
1. Add/upgrade tests
2. Improve harness/fixtures/stability
3. Wire CI/reporting/artifacts
4. Update docs/checklists
5. Re-run and validate

Each run must output:
- What changed
- Evidence (test command/results)
- Remaining gap to full E2E definition

## Prioritized backlog (next 10 milestones)
1. Add test markers + test run matrix script.
2. Add contract coverage map by endpoint and status-code class.
3. Add Playwright scaffold with one passing critical dashboard flow.
4. Add deployed smoke test package and env config contract.
5. Add Stripe staging webhook signature + replay tests.
6. Add API key lifecycle E2E in browser.
7. Add CI artifact upload for traces/screenshots/reports.
8. Add flaky test quarantine policy + retry classification.
9. Add 09:00 gate summary template (PASS/FAIL with risk score).
10. Add "full E2E readiness" dashboard report.

## Reporting standard
- Green: concise one-liner + milestone
- Red: failing suite, failing test IDs, likely root cause, unblock plan
- Weekly: % of critical flows covered by true deployed E2E

## Guardrails
- No silent failures.
- No "green" without evidence artifacts.
- Prefer realism over over-mocking for E2E layers.
- Keep tests maintainable and deterministic.
