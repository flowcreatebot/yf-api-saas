#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JSON="$ROOT/reports/latest_test_status.json"

if [[ ! -f "$JSON" ]]; then
  echo "No test status report found yet."
  exit 0
fi

STATUS=$(python3 - <<PY
import json
p="$JSON"
with open(p) as f:
    j=json.load(f)
print(j.get('status','unknown'))
PY
)

TS=$(python3 - <<PY
import json
p="$JSON"
with open(p) as f:
    j=json.load(f)
print(j.get('timestamp','unknown'))
PY
)

if [[ "$STATUS" == "green" ]]; then
  echo "Daily test suite: ALL GREEN ✅ (last run: $TS)"
else
  echo "Daily test suite: FAILING ❌ (last run: $TS) — needs attention."
fi
