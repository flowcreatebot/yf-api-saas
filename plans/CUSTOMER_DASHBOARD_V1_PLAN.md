# Customer Dashboard v1 — Clean Plan

## Objective
Ship a customer-facing dashboard for paying users, with secure auth and tenant-scoped data.

## v1 Outcomes
- Customer can sign in securely.
- Customer can view and manage their own API keys.
- Customer can view their own usage/metrics and recent activity.
- Customer can never access another customer's data.

## Architecture decisions (v1)
1. Route model
   - Customer app route: `/dashboard` (target)
   - Existing `/internal/*` remains legacy/separate until cutover.
2. Auth/session
   - Use server-validated sessions/tokens (not local-only browser flags).
3. Tenant scoping
   - Every dashboard API request resolves tenant/user context before data read/write.
4. Data contracts
   - Keys, metrics, activity endpoints must be tenant-scoped by default.

## Implementation phases

### Phase A — Foundation
- Define customer auth/session contract.
- Define tenant/user data model and access rules.
- Add middleware/dependencies for authenticated tenant context.

### Phase B — Dashboard shell
- Establish customer dashboard shell and nav.
- Wire authenticated route guard and session handling.

### Phase C — API keys
- Implement scoped key inventory and lifecycle actions.
- Add confirmations, loading states, and clear error handling.

### Phase D — Usage + activity
- Implement scoped metrics and activity endpoints.
- Add filters/range controls and shareable deep links where useful.

### Phase E — Hardening
- Add tests for auth failures and cross-tenant access denial.
- Add docs for customer onboarding and dashboard usage.
- Run deploy smoke + acceptance checks.

## Acceptance criteria
- Auth required for all customer dashboard APIs.
- Cross-tenant access attempts return deny responses.
- Dashboard UX is production-usable (not placeholder-only).
- Tests cover core auth/scoping/security paths.

## Risks and mitigations
- Risk: scope creep into admin/internal tooling.
  - Mitigation: strict route/scope boundaries in this plan.
- Risk: security regressions in tenant access.
  - Mitigation: mandatory access-control tests each phase.
- Risk: deployment drift.
  - Mitigation: verify deployed routes and smoke reports every shipping cycle.
