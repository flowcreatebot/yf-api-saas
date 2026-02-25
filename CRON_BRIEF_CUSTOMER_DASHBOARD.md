# Y Finance API — Customer Dashboard Work-Cycle Brief

## Mission
Build the **customer dashboard** for logged-in paying users.

This lane is product-facing. It is not an internal/admin dashboard lane.

## Scope
Deliver the customer dashboard under a customer route (`/dashboard` target architecture), including:
- authenticated customer sessions
- tenant-scoped API key management
- tenant-scoped usage/metrics views
- tenant-scoped activity/events
- customer-safe UX (no internal-only labels or assumptions)

## Explicit non-goals (for this lane)
- Internal/admin tooling
- Placeholder-only localStorage auth as a final solution
- Unscoped global data views shared across tenants

## Execution mode
- Main coordinates work and may spawn subagents.
- Max 2 subagents per run:
  - required: `builder`
  - optional second: `qa` or `docs`
- Keep each run to one concrete milestone.

## Shipping order
1. Auth/session foundation for customers
2. Tenant/user model + scoped data contracts
3. Customer dashboard route + shell + navigation
4. API keys customer lifecycle (create/rotate/revoke) with real scoped backend
5. Usage/metrics/customer activity from scoped endpoints
6. Docs + onboarding for customer dashboard

## Quality gates per run
- Code compiles and tests relevant to touched area pass.
- No regressions to existing public API routes.
- No leakage of another tenant's data in responses.

## Update policy
Report only:
- completed milestone,
- blocker requiring decision,
- risky decision requiring approval.

## Output style
- Say "customer dashboard" in updates.
- Keep updates focused on customer dashboard delivery.
