#!/usr/bin/env bash
set -euo pipefail

DEPLOYED_BASE_URL="${DEPLOYED_BASE_URL:-https://y-finance-api.onrender.com}"
DEPLOYED_API_KEY="${DEPLOYED_API_KEY:-}"
DEPLOYED_EXPECT_DASHBOARD="${DEPLOYED_EXPECT_DASHBOARD:-0}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

export DEPLOYED_BASE_URL
export DEPLOYED_API_KEY
export DEPLOYED_EXPECT_DASHBOARD

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
  echo "[deployed-smoke] expect_dashboard=${DEPLOYED_EXPECT_DASHBOARD}"

  "$PYTHON_BIN" -m pytest -q -m deployed tests/test_deployed_smoke.py
} | tee "$REPORT_PATH"

cp "$REPORT_PATH" reports/latest_deployed_smoke.txt

echo "[deployed-smoke] report=${REPORT_PATH}"
