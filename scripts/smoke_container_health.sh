#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAG="yf-api-smoke:local"
CONTAINER_NAME="yf-api-smoke"
PORT="18000"

if ! command -v docker >/dev/null 2>&1; then
  echo "[smoke] ERROR: docker is not installed or not on PATH"
  echo "[smoke] Run this script on a Docker-capable host/CI runner."
  exit 2
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "[smoke] ERROR: curl is required but not found on PATH"
  exit 2
fi

cleanup() {
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup

echo "[smoke] Building Docker image..."
docker build -t "$IMAGE_TAG" .

echo "[smoke] Starting container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -e API_MASTER_KEY="smoke-test-key" \
  -e PORT=10000 \
  -p "$PORT:10000" \
  "$IMAGE_TAG" >/dev/null

echo "[smoke] Waiting for /v1/health ..."
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/v1/health" >/dev/null; then
    echo "[smoke] OK: container responded at /v1/health"
    exit 0
  fi
  sleep 1
done

echo "[smoke] ERROR: container did not become healthy"
docker logs "$CONTAINER_NAME" || true
exit 1
