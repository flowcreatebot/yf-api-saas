#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_DEPLOYED="${RUN_DEPLOYED:-0}"
RUN_DEPLOYED_STRIPE_MUTATION="${RUN_DEPLOYED_STRIPE_MUTATION:-0}"
RUN_DEPLOYED_STRIPE_CHECKOUT="${RUN_DEPLOYED_STRIPE_CHECKOUT:-0}"

mkdir -p reports
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
REPORT_PATH="reports/test_matrix_${STAMP}.txt"

run_lane() {
  local lane_name="$1"
  local marker_expr="$2"
  local smoke_profile="$3"
  shift 3

  echo ""
  echo "[test-matrix] lane=${lane_name}"
  if [[ -n "$smoke_profile" ]]; then
    DEPLOYED_SMOKE_PROFILE="$smoke_profile" "$PYTHON_BIN" -m pytest -q -m "$marker_expr" "$@"
  else
    "$PYTHON_BIN" -m pytest -q -m "$marker_expr" "$@"
  fi
}

{
  echo "[test-matrix] started_at=$(date -Iseconds)"
  echo "[test-matrix] python_bin=${PYTHON_BIN}"
  echo "[test-matrix] run_deployed=${RUN_DEPLOYED}"
  echo "[test-matrix] run_deployed_stripe_mutation=${RUN_DEPLOYED_STRIPE_MUTATION}"
  echo "[test-matrix] run_deployed_stripe_checkout=${RUN_DEPLOYED_STRIPE_CHECKOUT}"

  run_lane "critical-integration" "integration and critical and not deployed" ""
  run_lane "billing-integration" "integration and billing and not deployed" ""
  run_lane "critical-e2e" "e2e and critical and not deployed" ""

  if [[ "$RUN_DEPLOYED" == "1" ]]; then
    run_lane "critical-deployed" "deployed and critical" "staging" tests/test_deployed_smoke.py
  else
    echo ""
    echo "[test-matrix] lane=critical-deployed skipped (set RUN_DEPLOYED=1 to enable)"
  fi

  if [[ "$RUN_DEPLOYED_STRIPE_MUTATION" == "1" ]]; then
    run_lane "stripe-mutation-deployed" "deployed and billing and mutation and critical" "stripe-mutation" tests/test_deployed_smoke.py
  else
    echo ""
    echo "[test-matrix] lane=stripe-mutation-deployed skipped (set RUN_DEPLOYED_STRIPE_MUTATION=1 to enable)"
  fi

  if [[ "$RUN_DEPLOYED_STRIPE_CHECKOUT" == "1" ]]; then
    run_lane "stripe-checkout-deployed" "deployed and billing and mutation and critical and checkout" "stripe-checkout" tests/test_deployed_smoke.py
  else
    echo ""
    echo "[test-matrix] lane=stripe-checkout-deployed skipped (set RUN_DEPLOYED_STRIPE_CHECKOUT=1 to enable)"
  fi
} | tee "$REPORT_PATH"

cp "$REPORT_PATH" reports/latest_test_matrix.txt

echo "[test-matrix] report=${REPORT_PATH}"
