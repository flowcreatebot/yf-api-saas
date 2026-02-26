#!/usr/bin/env bash
set -euo pipefail

DEPLOYED_BASE_URL="${DEPLOYED_BASE_URL:-https://y-finance-api.onrender.com}"
DEPLOYED_API_KEY="${DEPLOYED_API_KEY:-}"
DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET="${DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET:-0}"
DEPLOYED_EXPECT_STRIPE_CHECKOUT="${DEPLOYED_EXPECT_STRIPE_CHECKOUT:-0}"
DEPLOYED_EXPECT_CUSTOMER_DASHBOARD="${DEPLOYED_EXPECT_CUSTOMER_DASHBOARD:-0}"
DEPLOYED_EXPECT_STRIPE_MUTATION_E2E="${DEPLOYED_EXPECT_STRIPE_MUTATION_E2E:-0}"
DEPLOYED_STRIPE_WEBHOOK_SECRET="${DEPLOYED_STRIPE_WEBHOOK_SECRET:-}"
DEPLOYED_SMOKE_PROFILE="${DEPLOYED_SMOKE_PROFILE:-staging}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

export DEPLOYED_BASE_URL
export DEPLOYED_API_KEY
export DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET
export DEPLOYED_EXPECT_STRIPE_CHECKOUT
export DEPLOYED_EXPECT_CUSTOMER_DASHBOARD
export DEPLOYED_EXPECT_STRIPE_MUTATION_E2E
export DEPLOYED_STRIPE_WEBHOOK_SECRET
export DEPLOYED_SMOKE_PROFILE

case "$DEPLOYED_SMOKE_PROFILE" in
  staging)
    PYTEST_MARK_EXPR="deployed"
    ;;
  production-readonly)
    PYTEST_MARK_EXPR="deployed and not mutation"
    ;;
  stripe-mutation)
    PYTEST_MARK_EXPR="deployed and billing and mutation and critical"
    ;;
  *)
    echo "[deployed-smoke] invalid DEPLOYED_SMOKE_PROFILE=${DEPLOYED_SMOKE_PROFILE} (expected: staging|production-readonly|stripe-mutation)" >&2
    exit 2
    ;;
esac

mkdir -p reports
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
REPORT_PATH="reports/deployed_smoke_${STAMP}.txt"

{
  echo "[deployed-smoke] started_at=$(date -Iseconds)"
  echo "[deployed-smoke] base_url=${DEPLOYED_BASE_URL}"
  if [[ -n "$DEPLOYED_API_KEY" ]]; then
    echo "[deployed-smoke] api_key=provided"
  else
    echo "[deployed-smoke] api_key=not_provided (authenticated quote check will be skipped)"
  fi
  # dashboard internal canary removed
  echo "[deployed-smoke] expect_webhook_secret=${DEPLOYED_EXPECT_STRIPE_WEBHOOK_SECRET}"
  echo "[deployed-smoke] expect_stripe_checkout=${DEPLOYED_EXPECT_STRIPE_CHECKOUT}"
  echo "[deployed-smoke] expect_customer_dashboard=${DEPLOYED_EXPECT_CUSTOMER_DASHBOARD}"
  echo "[deployed-smoke] expect_stripe_mutation_e2e=${DEPLOYED_EXPECT_STRIPE_MUTATION_E2E}"
  if [[ -n "$DEPLOYED_STRIPE_WEBHOOK_SECRET" ]]; then
    echo "[deployed-smoke] stripe_webhook_secret=provided"
  else
    echo "[deployed-smoke] stripe_webhook_secret=not_provided"
  fi
  echo "[deployed-smoke] profile=${DEPLOYED_SMOKE_PROFILE}"
  echo "[deployed-smoke] marker_expr=${PYTEST_MARK_EXPR}"

  "$PYTHON_BIN" -m pytest -q -m "$PYTEST_MARK_EXPR" tests/test_deployed_smoke.py
} | tee "$REPORT_PATH"

cp "$REPORT_PATH" reports/latest_deployed_smoke.txt

echo "[deployed-smoke] report=${REPORT_PATH}"
