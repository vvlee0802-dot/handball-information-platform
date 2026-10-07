#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.production}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Production environment file not found: ${ENV_FILE}" >&2
  exit 2
fi

set -a
source "${ENV_FILE}"
export APP_ENV_FILE="${ENV_FILE}"
set +a

if [[ -z "${APP_DOMAIN:-}" ]]; then
  echo "APP_DOMAIN must be set in ${ENV_FILE}." >&2
  exit 2
fi

docker compose --env-file "${ENV_FILE}" \
  -f docker-compose.yml -f docker-compose.prod.yml config --quiet
docker compose --env-file "${ENV_FILE}" \
  -f docker-compose.yml -f docker-compose.prod.yml up -d --build

APP_BASE_URL="https://${APP_DOMAIN}" ./scripts/smoke-test.sh
echo "Deployment passed smoke checks at https://${APP_DOMAIN}."
