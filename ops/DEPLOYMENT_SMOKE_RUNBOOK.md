# Deployment Smoke Runbook

Purpose: verify the production container can build and boot before deploy.

## Automated (CI)

GitHub Actions runs `docker-smoke` after tests:

1. Build Docker image from `Dockerfile`
2. Start container on local port `18000`
3. Probe `GET /v1/health`
4. Fail pipeline if container does not become healthy within 30s

Workflow file: `.github/workflows/ci.yml`
Script: `scripts/smoke_container_health.sh`

## Manual execution

From repo root:

```bash
./scripts/smoke_container_health.sh
```

Expected output ends with:

```text
[smoke] OK: container responded at /v1/health
```

## If smoke test fails

1. Inspect logs printed by the script (container startup errors).
2. Re-run locally with full output:
   - `docker build -t yf-api-smoke:local .`
   - `docker run --rm -e API_MASTER_KEY=smoke-test-key -e PORT=10000 -p 18000:10000 yf-api-smoke:local`
3. Verify env vars used at runtime (especially `PORT`, API keys, and optional Stripe vars).
4. Block deploy until smoke passes.

## Latest smoke result log

- **Timestamp:** 2026-02-24 16:53 +07
- **Command:** `./scripts/smoke_container_health.sh`
- **Outcome:** ❌ Preflight failed (expected in non-Docker environment)
- **Failure:** Docker not available on PATH (exit code `2`)
- **Report artifact:** `reports/smoke_report_2026-02-24_16-53-23.txt`

```text
[smoke] ERROR: docker is not installed or not on PATH
[smoke] Run this script on a Docker-capable host/CI runner.
```

Follow-up required: run smoke from a host/runner with Docker installed and re-log a passing result before deploy approval.
