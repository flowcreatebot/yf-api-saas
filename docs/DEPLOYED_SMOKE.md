# Deployed Smoke Test Pack

This pack validates critical flows against a real deployed host (not FastAPI test client mocks).

## What it covers

`tests/test_deployed_smoke.py` (`@pytest.mark.deployed`, `@pytest.mark.critical`):

1. `GET /v1/health` returns `200` + `{"ok": true}`
2. `GET /v1/billing/plans` returns `200` + plan contract keys
3. `GET /v1/quote/AAPL` without key returns `401 Missing API key`
4. `GET /v1/quote/AAPL` with invalid key returns `401 Invalid API key`
5. Optional authenticated quote check (`DEPLOYED_API_KEY`) returns `200` + quote payload
6. (Optional, when `DEPLOYED_EXPECT_DASHBOARD=1`) `GET /internal` redirects to `/internal/dashboard/`
7. (Optional, when `DEPLOYED_EXPECT_DASHBOARD=1`) `GET /internal/dashboard/` returns dashboard shell (`Y Finance Dashboard`)
8. (Optional, when `DEPLOYED_EXPECT_DASHBOARD=1`) `GET /internal/api/overview?range=24h` returns dashboard overview contract keys

## Environment contract

Required:

- `DEPLOYED_BASE_URL` (example: `https://y-finance-api.onrender.com`)

Optional but recommended:

- `DEPLOYED_API_KEY` (valid API key for deeper authenticated canary)
- `DEPLOYED_EXPECT_DASHBOARD=1` to enforce deployed dashboard route canaries (staging-first rollout)

## Run locally

```bash
export DEPLOYED_BASE_URL="https://y-finance-api.onrender.com"
# optional
export DEPLOYED_API_KEY="..."
# optional: enable when dashboard routes are deployed on the target env
export DEPLOYED_EXPECT_DASHBOARD="1"

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
