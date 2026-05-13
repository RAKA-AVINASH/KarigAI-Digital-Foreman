#!/bin/bash

# KarigAI Database Restore Script
# Restores database from backup file

set -e

# Configuration
BACKUP_DIR="/backups"

# Database connection details from environment
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB}"
DB_USER="${POSTGRES_USER}"
PGPASSWORD="${POSTGRES_PASSWORD}"

export PGPASSWORD

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh "${BACKUP_DIR}"/karigai_backup_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_DIR}/${BACKUP_FILE}"
    exit 1
fi

echo "WARNING: This will restore the database from backup."
echo "Database: ${DB_NAME}"
echo "Backup file: ${BACKUP_FILE}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "Starting restore at $(date)"

# Decompress backup if it's gzipped
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    echo "Decompressing backup..."
    DECOMPRESSED_FILE="${BACKUP_FILE%.gz}"
    gunzip -c "${BACKUP_DIR}/${BACKUP_FILE}" > "${BACKUP_DIR}/${DECOMPRESSED_FILE}"
    RESTORE_FILE="${DECOMPRESSED_FILE}"
else
    RESTORE_FILE="${BACKUP_FILE}"
fi

# Drop existing connections
echo "Terminating existing database connections..."
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();"

# Drop and recreate database
echo "Dropping and recreating database..."
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"

# Restore database
echo "Restoring database from backup..."
pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --verbose \
    --no-owner \
    --no-acl \
    "${BACKUP_DIR}/${RESTORE_FILE}"

# Clean up decompressed file
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    rm -f "${BACKUP_DIR}/${RESTORE_FILE}"
fi

echo "Database restore completed successfully at $(date)"

# Verify restore
echo "Verifying restore..."
TABLE_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

echo "Restored database contains ${TABLE_COUNT} tables"

# Send notification (optional)
if [ -n "${BACKUP_WEBHOOK_URL}" ]; then
    curl -X POST "${BACKUP_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"KarigAI database restored from: ${BACKUP_FILE}\"}"
fi

exit 0
