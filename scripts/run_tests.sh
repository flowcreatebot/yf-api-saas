#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p reports
TS="$(date +%F_%H-%M-%S)"
REPORT="reports/test_report_${TS}.txt"
LATEST="reports/latest_test_report.txt"
JSON="reports/latest_test_status.json"

if python3 -m venv .venv >/dev/null 2>&1; then
  PY_BIN="$(pwd)/.venv/bin/python"
else
  PY_BIN="python3"
fi

"$PY_BIN" -m pip install -q -r requirements.txt

set +e
"$PY_BIN" -m pytest 2>&1 | tee "$REPORT"
CODE=${PIPESTATUS[0]}
set -e

cp "$REPORT" "$LATEST"

if [[ $CODE -eq 0 ]]; then
  STATUS="green"
else
  STATUS="red"
fi

cat > "$JSON" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "status": "$STATUS",
  "exit_code": $CODE,
  "report_file": "$REPORT"
}
EOF

exit $CODE
