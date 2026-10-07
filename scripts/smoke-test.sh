#!/usr/bin/env bash
set -euo pipefail

APP_BASE_URL="${APP_BASE_URL:-http://127.0.0.1:${APP_PORT:-8080}}"

curl --fail --silent --show-error "${APP_BASE_URL}/healthz" >/dev/null
READY_JSON="$(curl --fail --silent --show-error "${APP_BASE_URL}/api/health/ready")"

if [[ "${READY_JSON}" != *'"status":"ok"'* && "${READY_JSON}" != *'"status": "ok"'* ]]; then
  echo "Readiness check did not return an ok status: ${READY_JSON}" >&2
  exit 1
fi

docker compose exec -T worker python -m app.tasks.worker_health

for service in postgres redis backend worker frontend; do
  if ! docker compose ps --status running --services | grep -qx "${service}"; then
    echo "Required service is not running: ${service}" >&2
    exit 1
  fi
done

echo "Smoke test passed for ${APP_BASE_URL}."
