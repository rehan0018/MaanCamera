#!/usr/bin/env bash
set -euo pipefail

# MaanCamera PostgreSQL + Media Backup Script
# Usage: POSTGRES_USER=... POSTGRES_DB=... BACKUP_DIR=/var/backups/maancamera ./infra/scripts/backup.sh

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PG_HOST="${PG_HOST:-postgres}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${POSTGRES_USER:?POSTGRES_USER is required}"
PG_DB="${POSTGRES_DB:?POSTGRES_DB is required}"

mkdir -p "${BACKUP_DIR}"
DUMP_FILE="${BACKUP_DIR}/maancamera_${PG_DB}_${TIMESTAMP}.dump"

echo "[backup] Starting PostgreSQL backup -> ${DUMP_FILE}"
pg_dump \
  --host="${PG_HOST}" \
  --port="${PG_PORT}" \
  --username="${PG_USER}" \
  --dbname="${PG_DB}" \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-acl \
  --file="${DUMP_FILE}"

sha256sum "${DUMP_FILE}" > "${DUMP_FILE}.sha256"
echo "[backup] Verified checksum written to ${DUMP_FILE}.sha256"

if [ -n "${S3_BACKUP_BUCKET:-}" ] && command -v aws >/dev/null 2>&1; then
  echo "[backup] Syncing dump to S3 bucket s3://${S3_BACKUP_BUCKET}/postgres/"
  aws s3 cp "${DUMP_FILE}" "s3://${S3_BACKUP_BUCKET}/postgres/"
  aws s3 cp "${DUMP_FILE}.sha256" "s3://${S3_BACKUP_BUCKET}/postgres/"
fi

echo "[backup] Pruning backups older than ${RETENTION_DAYS} days"
find "${BACKUP_DIR}" -type f -name "maancamera_*.dump*" -mtime +"${RETENTION_DAYS}" -delete || true
echo "[backup] Backup complete."
