#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v gh >/dev/null 2>&1; then
  echo "CI status: gh CLI not installed on this host."
  exit 0
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "CI status: gh CLI is not authenticated."
  exit 0
fi

if ! gh run list --workflow ci.yml --limit 1 --json status >/dev/null 2>&1; then
  echo "CI status: no ci.yml workflow runs found yet."
  exit 0
fi

gh run list \
  --workflow ci.yml \
  --limit 1 \
  --json status,conclusion,updatedAt,headSha,url \
  --jq '.[0] | "CI: " + (if .conclusion == "success" then "ALL GREEN ✅" elif .status != "completed" then "IN PROGRESS ⏳" else "FAILING ❌" end) + " | status=" + .status + " | conclusion=" + (.conclusion // "n/a") + " | sha=" + (.headSha[0:7]) + " | updated=" + .updatedAt + " | " + .url'
