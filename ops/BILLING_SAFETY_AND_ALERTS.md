# Billing Safety Checklist + Minimal Reliability Alerts

Last updated: 2026-02-24 13:41:53 +07
Owner lane: Ops

## 1) Billing safety checklist (pre-deploy / post-rotate)

### Required environment variables

- `API_MASTER_KEY`
  - Required for protected API routes.
- `STRIPE_SECRET_KEY`
  - Required for `POST /v1/billing/checkout/session`.
  - Expected format: Stripe secret key (typically `sk_...`).
- `STRIPE_PRICE_ID_MONTHLY`
  - Required for `POST /v1/billing/checkout/session`.
  - Expected format: Stripe price ID (typically `price_...`).
- `STRIPE_WEBHOOK_SECRET`
  - Required for `POST /v1/billing/webhook/stripe` signature verification.
  - Expected format: Stripe webhook secret (typically `whsec_...`).
- `BILLING_ALLOWED_REDIRECT_HOSTS` (recommended hardening)
  - Comma-separated allowlist for checkout success/cancel redirect hosts.
  - If set, non-allowlisted hosts must be rejected.

### Webhook signature expectations

Endpoint: `POST /v1/billing/webhook/stripe`

Must-haves:
- Header `Stripe-Signature` present.
- Request payload signed by Stripe and verifiable by `stripe.Webhook.construct_event(...)` with `STRIPE_WEBHOOK_SECRET`.

Expected behavior:
- Valid signature + supported event prefix (`customer.subscription.*`, `invoice.payment_*`) → `200` with `{"received": true, "handled": true, ...}`.
- Valid signature + unknown event type → `200` with `handled: false` (accepted but not processed).
- Missing `Stripe-Signature` header → `400` (`Missing Stripe-Signature header`).
- Invalid signature/payload verification failure → `400` (`Invalid webhook: ...`).
- Missing `STRIPE_WEBHOOK_SECRET` → `503` (`Stripe webhook secret not configured`).

### Expected failure responses for billing endpoints

- `POST /v1/billing/checkout/session`
  - Missing `STRIPE_SECRET_KEY` → `503`.
  - Missing `STRIPE_PRICE_ID_MONTHLY` → `503`.
  - Invalid redirect URL / host not in allowlist / insecure URL (`http` non-localhost) → `422` validation error.
  - Stripe provider call failure → `502`.
- `POST /v1/billing/webhook/stripe`
  - Missing webhook secret → `503`.
  - Missing signature header or invalid signature → `400`.

## 2) Minimal metrics + alerts table

| Signal | Threshold / Trigger | Action owner |
|---|---|---|
| `/v1/health` uptime probe (1-min interval) | Alert if 2 consecutive failures OR success rate <99% over 15 min | Ops on-call |
| `/v1/health` p95 latency | Warn at >800ms for 15 min; critical at >1500ms for 10 min | Ops on-call |
| Container smoke check (`scripts/smoke_container_health.sh`) | Any failure on main branch CI `docker-smoke` job | Release manager + Ops |
| Regression visibility: `latest_test_status.json` status | `status != green` on latest scheduled/daily run | QA/Engineering owner |
| Regression visibility: CI `ci.yml` conclusion | Latest completed run conclusion != `success` | Engineering owner |

## 3) Operator quick checks

1. Confirm env var presence in runtime secret store (do not log secret values).
2. Send Stripe test webhook and verify `200` + expected `handled` flag.
3. Run smoke check on Docker-capable runner before release gate.
4. Confirm latest regression status remains green (`reports/latest_test_status.json` and `ci.yml`).
