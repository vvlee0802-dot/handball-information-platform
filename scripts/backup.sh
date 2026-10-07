#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
BACKUP_ROOT="${BACKUP_ROOT:-backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${BACKUP_ROOT}/${STAMP}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file not found: ${ENV_FILE}" >&2
  exit 2
fi

set -a
source "${ENV_FILE}"
export APP_ENV_FILE="${ENV_FILE}"
set +a

mkdir -p "${BACKUP_DIR}"

docker compose --env-file "${ENV_FILE}" exec -T postgres \
  pg_dump --username="${POSTGRES_USER:-handball}" \
  --dbname="${POSTGRES_DB:-handball}" \
  --format=custom --no-owner --no-privileges \
  >"${BACKUP_DIR}/database.dump"

docker compose --env-file "${ENV_FILE}" exec -T backend \
  tar -C /data -czf - . >"${BACKUP_DIR}/media.tar.gz"

(
  cd "${BACKUP_DIR}"
  shasum -a 256 database.dump media.tar.gz >SHA256SUMS
)

printf 'created_at_utc=%s\ndatabase=%s\nmedia=%s\n' \
  "${STAMP}" "${POSTGRES_DB:-handball}" "handball_media_data" \
  >"${BACKUP_DIR}/manifest.txt"

echo "Backup completed: ${BACKUP_DIR}"
