#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_DEPLOYED="${RUN_DEPLOYED:-0}"

mkdir -p reports
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
REPORT_PATH="reports/test_matrix_${STAMP}.txt"

run_lane() {
  local lane_name="$1"
  local marker_expr="$2"
  shift 2

  echo ""
  echo "[test-matrix] lane=${lane_name}"
  "$PYTHON_BIN" -m pytest -q -m "$marker_expr" "$@"
}

{
  echo "[test-matrix] started_at=$(date -Iseconds)"
  echo "[test-matrix] python_bin=${PYTHON_BIN}"
  echo "[test-matrix] run_deployed=${RUN_DEPLOYED}"

  run_lane "critical-integration" "integration and critical and not deployed"
  run_lane "billing-integration" "integration and billing and not deployed"

  if [[ "$RUN_DEPLOYED" == "1" ]]; then
    run_lane "critical-deployed" "deployed and critical" tests/test_deployed_smoke.py
  else
    echo ""
    echo "[test-matrix] lane=critical-deployed skipped (set RUN_DEPLOYED=1 to enable)"
  fi
} | tee "$REPORT_PATH"

cp "$REPORT_PATH" reports/latest_test_matrix.txt

echo "[test-matrix] report=${REPORT_PATH}"
