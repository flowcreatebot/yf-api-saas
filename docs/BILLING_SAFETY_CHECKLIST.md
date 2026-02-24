# Billing Safety Checklist (MVP)

Last validated: 2026-02-24
Scope: `GET /v1/billing/plans`, `POST /v1/billing/checkout/session`, `POST /v1/billing/webhook/stripe`

## 1) Required environment configuration

Minimum required for safe billing flow:

- `STRIPE_SECRET_KEY` (server-side secret key used to create checkout sessions)
- `STRIPE_PRICE_ID_MONTHLY` (price id for subscription line item)
- `STRIPE_WEBHOOK_SECRET` (used to verify Stripe webhook signatures)

Optional but strongly recommended:

- `BILLING_ALLOWED_REDIRECT_HOSTS` (comma-separated host allowlist for checkout redirect URLs)
  - Example: `app.example.com,staging.example.com`

## 2) Redirect safety rules (checkout input validation)

For `POST /v1/billing/checkout/session` request body:

- `email` must be a valid email
- `success_url` and `cancel_url` must be valid URLs
- URLs must be `https://` unless host is `localhost` or `127.0.0.1` (dev only)
- If `BILLING_ALLOWED_REDIRECT_HOSTS` is set, host must be in the allowlist

Expected failures:

- Invalid payload/URL/email/host policy violation → `422` (`detail: "Validation failed"`, plus `errors[]`)

## 3) Stripe config gate behavior

Expected endpoint behavior when Stripe vars are missing:

- Missing `STRIPE_SECRET_KEY` on checkout call → `503` with detail `"Stripe secret key not configured"`
- Missing `STRIPE_PRICE_ID_MONTHLY` on checkout call → `503` with detail `"Stripe monthly price id not configured"`
- Missing `STRIPE_WEBHOOK_SECRET` on webhook call → `503` with detail `"Stripe webhook secret not configured"`

## 4) Webhook signature verification behavior

For `POST /v1/billing/webhook/stripe`:

- Missing `Stripe-Signature` header → `400` (`"Missing Stripe-Signature header"`)
- Invalid signature / malformed payload → `400` (`"Invalid webhook: ..."`)
- Valid signature → `200` with payload:
  - `received: true`
  - `type: <event_type>`
  - `handled: <bool>` (`true` for `customer.subscription.*` and `invoice.payment_*`)

## 5) Preflight runbook (before deploy)

1. Confirm env vars are present in deploy target (not just local `.env`)
2. Verify `BILLING_ALLOWED_REDIRECT_HOSTS` matches production/staging domains
3. Send one negative checkout request (bad URL host) and confirm `422`
4. Send one positive checkout request and confirm response has `id` + `url`
5. Send webhook without signature and confirm `400`
6. Send webhook with valid test signature from Stripe CLI/dashboard and confirm `200`

## 6) Expected status code map (billing lane)

- `200` success (`plans`, valid webhook)
- `400` webhook request invalid (missing/invalid signature)
- `422` request validation failed (checkout payload)
- `502` Stripe API call failed during checkout
- `503` Stripe environment configuration missing

## 7) Current limitation (known, non-blocking)

- Webhook handler currently acknowledges and classifies events but does not persist subscription state yet. Add durable event processing + idempotency storage before production-scale rollout.
