# YF API SaaS — Phased Build Plan

## Product

Yahoo Finance API for no-code users (Zapier, Make). Customers pay $4.99/mo, get an API key, use it in their automations. They need: a way to sign up and pay, a dashboard to manage their keys and see usage, good API docs, and a sales page that explains the product.

## Rules

- Phases are strictly ordered. Complete one before starting the next.
- "Done" means working code with passing tests, not docs or plans.
- Each phase's "done when" criteria must all be met before moving on.

---

## Phase 1: Database foundation

**Status: COMPLETE**

### Work

- Wire SQLAlchemy to Postgres (connection already provisioned via `DATABASE_URL` on Render)
- Create models:
  - `User` — email, hashed_password, stripe_customer_id, created_at
  - `APIKey` — key_hash, user_id, name, status, created_at, last_used_at
  - `Subscription` — user_id, stripe_subscription_id, status, plan, current_period_end
  - `UsageLog` — api_key_id, endpoint, status_code, response_ms, created_at
- Alembic for migrations
- Replace the in-memory API key check in `auth.py` to validate against the DB

### Done when

- [ ] `pytest` passes
- [ ] App connects to Postgres on startup
- [ ] API key auth validates against the DB (not in-memory dict)
- [ ] Migrations run clean (`alembic upgrade head` succeeds)

---

## Phase 2: Real user auth

**Status: COMPLETE**

### Work

- Registration endpoint: email + password → bcrypt hash → store User → return session token
- Login endpoint: email + password → verify hash → return session token
- Sessions stored in DB (or Redis if available), not in-memory dict
- Password reset flow (stretch — can defer if it blocks progress)
- Update dashboard frontend `api.js` to store and send session token on every request

### Done when

- [x] Can register a new user via API
- [x] Can log in and receive a session token
- [x] Session token grants access to dashboard endpoints
- [x] Frontend login flow works end-to-end in browser (no 401s on authenticated pages)

---

## Phase 3: Billing completion (Stripe end-to-end)

**Status: IN PROGRESS**

### Work

- Webhook handler processes `checkout.session.completed` → creates Subscription record + provisions first API key
- Webhook handles `customer.subscription.updated` and `customer.subscription.deleted` → updates Subscription status
- Checkout endpoint links to authenticated user (attaches `stripe_customer_id`)
- API key auth checks subscription status (active subscription required)
- Plans endpoint reads from config, not hardcoded dict

### Done when

- [ ] Full flow works: register → checkout → Stripe test payment → webhook fires → Subscription created → API key provisioned
- [ ] User can call market endpoints with their provisioned key
- [ ] Subscription cancellation (via webhook) revokes API access

---

## Phase 4: Dashboard goes real

**Status: NOT STARTED**

### Work

- Replace all mock data in `dashboard_data.py` with real DB queries
- Overview: real key count, real usage stats from UsageLog
- API keys page: real CRUD against APIKey table
- Activity: real usage logs
- Metrics: real request counts and latency from UsageLog

### Done when

- [ ] Dashboard shows real data from the database (no hardcoded mock dicts)
- [ ] Creating a key in the dashboard creates a real APIKey record
- [ ] Revoking a key in the dashboard changes its status in the DB
- [ ] Usage numbers change when the API is actually called

---

## Phase 5: Sales page + API docs

**Status: NOT STARTED**

### Work

- Mount landing page at `/` (currently redirects to /docs)
- Clean up `web/landing.html` — real CTA pointing to registration/checkout
- Replace default Swagger UI with Scalar (or similar) for interactive API docs at `/docs`
- Add "try it" examples with API key authorize flow
- Add no-code quickstart (Zapier webhook URL, Make HTTP module setup)

### Done when

- [ ] Visiting root URL `/` shows a sales page with signup CTA
- [ ] `/docs` shows interactive API explorer
- [ ] User can authorize with their API key in the docs UI and make real calls

---

## Phase 6: Rate limiting + usage tracking

**Status: NOT STARTED**

### Work

- Wire `slowapi` (already in requirements) to rate limit per API key
- Log every API call to UsageLog table
- Dashboard metrics pull from real usage data

### Done when

- [ ] Hitting rate limit returns 429
- [ ] Every API call creates a UsageLog record
- [ ] Usage shows up in dashboard within reasonable delay

---

## Phase 7: E2E testing

**Status: NOT STARTED**

### Work

- Tests cover the real flows: register → pay → get key → call API → see usage in dashboard
- Deployed smoke tests validate actual deployed behavior
- Remove or replace tests that only test mock data

### Done when

- [ ] `pytest` covers the critical user journey end-to-end
- [ ] Smoke tests run against deployed env and validate real flows
- [ ] No tests exist that only validate mock/hardcoded data
