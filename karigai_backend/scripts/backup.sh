#!/bin/bash

# KarigAI Database Backup Script
# Performs automated backups with retention policy

set -e

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="karigai_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=30

# Database connection details from environment
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${POSTGRES_DB}"
DB_USER="${POSTGRES_USER}"
PGPASSWORD="${POSTGRES_PASSWORD}"

export PGPASSWORD

echo "Starting backup at $(date)"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Perform database backup
echo "Backing up database ${DB_NAME}..."
pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --format=custom \
    --file="${BACKUP_DIR}/${BACKUP_FILE}"

# Compress backup
echo "Compressing backup..."
gzip "${BACKUP_DIR}/${BACKUP_FILE}"

# Calculate backup size
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
echo "Backup completed: ${BACKUP_FILE}.gz (${BACKUP_SIZE})"

# Remove old backups (older than RETENTION_DAYS)
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -name "karigai_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# List current backups
echo "Current backups:"
ls -lh "${BACKUP_DIR}"/karigai_backup_*.sql.gz 2>/dev/null || echo "No backups found"

# Verify backup integrity
echo "Verifying backup integrity..."
if gzip -t "${BACKUP_DIR}/${BACKUP_FILE}.gz"; then
    echo "Backup verification successful"
else
    echo "ERROR: Backup verification failed!"
    exit 1
fi

# Optional: Upload to cloud storage (S3, GCS, etc.)
if [ -n "${BACKUP_S3_BUCKET}" ]; then
    echo "Uploading backup to S3..."
    # aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}.gz" "s3://${BACKUP_S3_BUCKET}/backups/"
    echo "S3 upload would happen here (commented out for safety)"
fi

echo "Backup process completed successfully at $(date)"

# Send notification (optional)
if [ -n "${BACKUP_WEBHOOK_URL}" ]; then
    curl -X POST "${BACKUP_WEBHOOK_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"KarigAI backup completed: ${BACKUP_FILE}.gz (${BACKUP_SIZE})\"}"
fi

exit 0
