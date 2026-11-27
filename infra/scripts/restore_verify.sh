#!/usr/bin/env bash
set -euo pipefail

# MaanCamera Isolated Backup Restore Verification Drill
# Verifies checksum integrity, restores custom pg_dump archive into an ephemeral database,
# and validates critical schema tables & row counts.
# Usage: ./infra/scripts/restore_verify.sh /path/to/maancamera_db_20261127.dump

DUMP_FILE="${1:?Usage: restore_verify.sh <dump-file>}"
VERIFY_HOST="${PG_VERIFY_HOST:-127.0.0.1}"
VERIFY_PORT="${PG_VERIFY_PORT:-5432}"
VERIFY_USER="${POSTGRES_USER:-maancamera}"
VERIFY_DB="maancamera_restore_verify_$(date +%s)"

if [ ! -f "${DUMP_FILE}" ]; then
  echo "[restore-verify] ERROR: Dump file not found: ${DUMP_FILE}" >&2
  exit 1
fi

if [ -f "${DUMP_FILE}.sha256" ]; then
  echo "[restore-verify] Verifying SHA-256 checksum..."
  sha256sum -c "${DUMP_FILE}.sha256"
fi

cleanup() {
  echo "[restore-verify] Dropping ephemeral database ${VERIFY_DB}..."
  psql --host="${VERIFY_HOST}" --port="${VERIFY_PORT}" --username="${VERIFY_USER}" -d postgres \
    -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[restore-verify] Using $(pg_restore --version)"
echo "[restore-verify] Creating ephemeral verification database ${VERIFY_DB}..."
psql --host="${VERIFY_HOST}" --port="${VERIFY_PORT}" --username="${VERIFY_USER}" -d postgres \
  -c "CREATE DATABASE ${VERIFY_DB};"
psql --host="${VERIFY_HOST}" --port="${VERIFY_PORT}" --username="${VERIFY_USER}" -d "${VERIFY_DB}" \
  -c "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;"

echo "[restore-verify] Restoring dump into ${VERIFY_DB}..."
pg_restore \
  --host="${VERIFY_HOST}" \
  --port="${VERIFY_PORT}" \
  --username="${VERIFY_USER}" \
  --dbname="${VERIFY_DB}" \
  --no-owner \
  --no-acl \
  --no-comments \
  --exit-on-error \
  "${DUMP_FILE}"

echo "[restore-verify] Checking critical row counts & Alembic version..."
psql --host="${VERIFY_HOST}" --port="${VERIFY_PORT}" --username="${VERIFY_USER}" -d "${VERIFY_DB}" -c "
SELECT 'alembic_version' AS table_name, count(*) AS rows FROM alembic_version
UNION ALL SELECT 'users', count(*) FROM users
UNION ALL SELECT 'professional_profiles', count(*) FROM professional_profiles
UNION ALL SELECT 'bookings', count(*) FROM bookings
UNION ALL SELECT 'payments', count(*) FROM payments
UNION ALL SELECT 'payment_ledger_entries', count(*) FROM payment_ledger_entries;
"
echo "[restore-verify] Restore verification completed successfully."
