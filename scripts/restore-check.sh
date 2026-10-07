#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-}"
ENV_FILE="${ENV_FILE:-.env}"
REPORT_DIR="${REPORT_DIR:-backups/restore-reports}"

if [[ -z "${BACKUP_FILE}" || ! -f "${BACKUP_FILE}" ]]; then
  echo "Usage: $0 backups/<timestamp>/database.dump" >&2
  exit 2
fi

set -a
source "${ENV_FILE}"
export APP_ENV_FILE="${ENV_FILE}"
set +a

PRIMARY_DB="${POSTGRES_DB:-handball}"
RESTORE_DB="${RESTORE_DB:-handball_restore_check}"

if [[ "${RESTORE_DB}" == "${PRIMARY_DB}" || "${RESTORE_DB}" == "postgres" ]]; then
  echo "RESTORE_DB must be an isolated verification database, not ${RESTORE_DB}." >&2
  exit 2
fi

mkdir -p "${REPORT_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_FILE="${REPORT_DIR}/${STAMP}.log"

docker compose --env-file "${ENV_FILE}" exec -T postgres \
  dropdb --if-exists --force --username="${POSTGRES_USER:-handball}" "${RESTORE_DB}"
docker compose --env-file "${ENV_FILE}" exec -T postgres \
  createdb --username="${POSTGRES_USER:-handball}" "${RESTORE_DB}"
docker compose --env-file "${ENV_FILE}" exec -T postgres \
  pg_restore --username="${POSTGRES_USER:-handball}" --dbname="${RESTORE_DB}" \
  --exit-on-error --no-owner --no-privileges <"${BACKUP_FILE}"

TABLE_COUNT="$(docker compose --env-file "${ENV_FILE}" exec -T postgres \
  psql --tuples-only --no-align --username="${POSTGRES_USER:-handball}" \
  --dbname="${RESTORE_DB}" \
  --command="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")"
MIGRATION_VERSION="$(docker compose --env-file "${ENV_FILE}" exec -T postgres \
  psql --tuples-only --no-align --username="${POSTGRES_USER:-handball}" \
  --dbname="${RESTORE_DB}" \
  --command="SELECT version_num FROM alembic_version LIMIT 1;")"

if [[ "${TABLE_COUNT}" -lt 10 || -z "${MIGRATION_VERSION}" ]]; then
  echo "Restore verification failed: tables=${TABLE_COUNT}, migration=${MIGRATION_VERSION}" >&2
  exit 1
fi

printf 'checked_at_utc=%s\nbackup=%s\nrestore_database=%s\ntable_count=%s\nalembic_version=%s\nresult=passed\n' \
  "${STAMP}" "${BACKUP_FILE}" "${RESTORE_DB}" "${TABLE_COUNT}" \
  "${MIGRATION_VERSION}" >"${REPORT_FILE}"

if [[ "${KEEP_RESTORE_DB:-0}" != "1" ]]; then
  docker compose --env-file "${ENV_FILE}" exec -T postgres \
    dropdb --if-exists --force --username="${POSTGRES_USER:-handball}" "${RESTORE_DB}"
fi

echo "Restore verification passed. Report: ${REPORT_FILE}"
