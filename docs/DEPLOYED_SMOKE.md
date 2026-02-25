# Deployed Smoke Test Pack

This pack validates critical flows against a real deployed host (not FastAPI test client mocks).

## What it covers

`tests/test_deployed_smoke.py` (`@pytest.mark.deployed`, `@pytest.mark.critical`):

1. `GET /v1/health` returns `200` + `{"ok": true}`
2. `GET /v1/billing/plans` returns `200` + plan contract keys
3. `GET /v1/quote/AAPL` without key returns `401 Missing API key`
4. `GET /v1/quote/AAPL` with invalid key returns `401 Invalid API key`
5. Optional authenticated quote check (`DEPLOYED_API_KEY`) returns `200` + quote payload contract
6. `GET /v1/history/AAPL?period=5d&interval=1d` without key returns `401 Missing API key`
7. `GET /v1/history/AAPL?period=5d&interval=1d` with invalid key returns `401 Invalid API key`
8. Optional authenticated history check (`DEPLOYED_API_KEY`) returns `200` + OHLCV series contract
9. `GET /v1/quotes?symbols=AAPL,MSFT` without key returns `401 Missing API key`
10. `GET /v1/quotes?symbols=AAPL,MSFT` with invalid key returns `401 Invalid API key`
11. Optional authenticated bulk quote check (`DEPLOYED_API_KEY`) returns `200` + multi-symbol payload contract
12. `GET /v1/fundamentals/AAPL` without key returns `401 Missing API key`
13. `GET /v1/fundamentals/AAPL` with invalid key returns `401 Invalid API key`
14. Optional authenticated fundamentals check (`DEPLOYED_API_KEY`) returns `200` + fundamentals payload contract
15. `POST /v1/billing/checkout/session` rejects insecure redirect URLs (`422 Validation failed`)
16. `POST /v1/billing/checkout/session` happy-path canary validates either a real checkout session contract (`200` with `id` + `url`) or expected `503` Stripe config guard (strict mode via env flag)
17. `POST /v1/billing/webhook/stripe` enforces signature guard (`400 Missing Stripe-Signature header`) when secret is enabled, otherwise confirms expected `503` config guard
18. `POST /v1/billing/webhook/stripe` rejects invalid signature (`400 Invalid webhook...`) when secret is enabled, otherwise confirms expected `503` config guard
19. (Optional, when `DEPLOYED_EXPECT_DASHBOARD=1`) `GET /internal` redirects to `/internal/dashboard/`
20. (Optional, when `DEPLOYED_EXPECT_DASHBOARD=1`) `GET /internal/dashboard/` returns dashboard shell (`Y Finance Dashboard`)
21. (Optional, when `DEPLOYED_EXPECT_DASHBOARD=1`) `GET /internal/api/overview?range=24h` returns dashboard overview contract keys

## Environment contract

Required:

- `DEPLOYED_BASE_URL` (example: `https://y-finance-api.onrender.com`)

Optional but recommended:

- `DEPLOYED_API_KEY` (valid API key for deeper authenticated canary)
- `DEPLOYED_EXPECT_DASHBOARD=1` to enforce deployed dashboard route canaries (staging-first rollout)
- `DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET=1` to require Stripe webhook secret behavior in deployed env (strict `400` signature failure canaries)
- `DEPLOYED_EXPECT_STRIPE_CHECKOUT=1` to require deployed Stripe checkout readiness (`200` happy path instead of allowing `503` config guard)

## Run locally

```bash
export DEPLOYED_BASE_URL="https://y-finance-api.onrender.com"
# optional
export DEPLOYED_API_KEY="..."
# optional: enable when dashboard routes are deployed on the target env
export DEPLOYED_EXPECT_DASHBOARD="1"
# optional: enforce strict deployed Stripe checks once configured
export DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET="1"
export DEPLOYED_EXPECT_STRIPE_CHECKOUT="1"

./scripts/run_deployed_smoke.sh
```

Outputs:

- timestamped report: `reports/deployed_smoke_YYYY-MM-DD_HH-MM-SS.txt`
- latest symlink/copy: `reports/latest_deployed_smoke.txt`

## CI wiring

`/.github/workflows/ci.yml` includes a `deployed-smoke` job that runs on:

- scheduled workflow
- manual `workflow_dispatch`

It uploads `reports/latest_deployed_smoke.txt` as a build artifact for auditability.
