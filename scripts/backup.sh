#!/bin/bash
#
# FactoryOps Database Backup Script
# 
# This script performs automated backups of MySQL and InfluxDB databases.
# Backups are compressed and uploaded to MinIO S3-compatible storage.
# Retention: Keep last 30 days, delete older backups.
#
# Usage:
#   ./scripts/backup.sh
#
# Cron setup (daily at 2 AM):
#   0 2 * * * /path/to/factoryops/scripts/backup.sh >> /var/log/factoryops-backup.log 2>&1
#

set -euo pipefail

# Configuration
BACKUP_DIR="/tmp/factoryops-backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

#
# 1. MySQL Backup
#
log "Starting MySQL backup..."

MYSQL_BACKUP_FILE="$BACKUP_DIR/mysql_${TIMESTAMP}.sql.gz"

if docker compose exec -T mysql mysqldump \
    -u "${MYSQL_USER:-factoryops}" \
    -p"${MYSQL_PASSWORD:-factoryops_dev}" \
    "${MYSQL_DATABASE:-factoryops}" \
    --single-transaction \
    --quick \
    --lock-tables=false \
    --routines \
    --triggers \
    --events \
    | gzip > "$MYSQL_BACKUP_FILE"; then
    
    MYSQL_SIZE=$(du -h "$MYSQL_BACKUP_FILE" | cut -f1)
    log "MySQL backup completed: $MYSQL_BACKUP_FILE ($MYSQL_SIZE)"
else
    error "MySQL backup failed"
    exit 1
fi

#
# 2. InfluxDB Backup
#
log "Starting InfluxDB backup..."

INFLUXDB_BACKUP_DIR="$BACKUP_DIR/influxdb_${TIMESTAMP}"
INFLUXDB_BACKUP_FILE="${INFLUXDB_BACKUP_DIR}.tar.gz"

# Create backup using InfluxDB backup command
if docker compose exec -T influxdb influx backup \
    --host http://localhost:8086 \
    --token "${INFLUXDB_TOKEN:-dev_token_12345}" \
    "/tmp/backup_${TIMESTAMP}"; then
    
    # Copy backup from container
    docker compose cp influxdb:/tmp/backup_${TIMESTAMP} "$INFLUXDB_BACKUP_DIR"
    
    # Compress backup
    tar -czf "$INFLUXDB_BACKUP_FILE" -C "$BACKUP_DIR" "influxdb_${TIMESTAMP}"
    rm -rf "$INFLUXDB_BACKUP_DIR"
    
    INFLUX_SIZE=$(du -h "$INFLUXDB_BACKUP_FILE" | cut -f1)
    log "InfluxDB backup completed: $INFLUXDB_BACKUP_FILE ($INFLUX_SIZE)"
    
    # Cleanup container backup
    docker compose exec -T influxdb rm -rf "/tmp/backup_${TIMESTAMP}"
else
    warn "InfluxDB backup failed (continuing with MySQL backup)"
fi

#
# 3. Upload to MinIO
#
log "Uploading backups to MinIO..."

MINIO_BACKUP_BUCKET="${MINIO_BACKUP_BUCKET:-factoryops-backups}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"

# Install MinIO client if not present
if ! command -v mc &> /dev/null; then
    warn "MinIO client (mc) not found. Installing..."
    wget -q https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc
    chmod +x /usr/local/bin/mc
fi

# Configure MinIO client
mc alias set factoryops-minio "http://${MINIO_ENDPOINT}" \
    "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" --api S3v4 > /dev/null 2>&1

# Create bucket if it doesn't exist
if ! mc ls factoryops-minio/"$MINIO_BACKUP_BUCKET" > /dev/null 2>&1; then
    log "Creating backup bucket: $MINIO_BACKUP_BUCKET"
    mc mb factoryops-minio/"$MINIO_BACKUP_BUCKET"
fi

# Upload MySQL backup
if mc cp "$MYSQL_BACKUP_FILE" \
    "factoryops-minio/${MINIO_BACKUP_BUCKET}/mysql/mysql_${TIMESTAMP}.sql.gz"; then
    log "MySQL backup uploaded to MinIO"
else
    error "Failed to upload MySQL backup to MinIO"
    exit 1
fi

# Upload InfluxDB backup if exists
if [ -f "$INFLUXDB_BACKUP_FILE" ]; then
    if mc cp "$INFLUXDB_BACKUP_FILE" \
        "factoryops-minio/${MINIO_BACKUP_BUCKET}/influxdb/influxdb_${TIMESTAMP}.tar.gz"; then
        log "InfluxDB backup uploaded to MinIO"
    else
        warn "Failed to upload InfluxDB backup to MinIO"
    fi
fi

#
# 4. Cleanup old backups (keep last 30 days)
#
log "Cleaning up old backups (retention: $RETENTION_DAYS days)..."

# Cleanup local backups
find "$BACKUP_DIR" -name "mysql_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "influxdb_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Cleanup MinIO backups
CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)

# MySQL backups
mc ls factoryops-minio/"$MINIO_BACKUP_BUCKET"/mysql/ | while read -r line; do
    FILE_DATE=$(echo "$line" | grep -oP 'mysql_\K[0-9]{8}' || true)
    if [ -n "$FILE_DATE" ] && [ "$FILE_DATE" -lt "$CUTOFF_DATE" ]; then
        FILENAME=$(echo "$line" | awk '{print $NF}')
        log "Deleting old backup: $FILENAME"
        mc rm "factoryops-minio/${MINIO_BACKUP_BUCKET}/mysql/$FILENAME"
    fi
done

# InfluxDB backups
mc ls factoryops-minio/"$MINIO_BACKUP_BUCKET"/influxdb/ | while read -r line; do
    FILE_DATE=$(echo "$line" | grep -oP 'influxdb_\K[0-9]{8}' || true)
    if [ -n "$FILE_DATE" ] && [ "$FILE_DATE" -lt "$CUTOFF_DATE" ]; then
        FILENAME=$(echo "$line" | awk '{print $NF}')
        log "Deleting old backup: $FILENAME"
        mc rm "factoryops-minio/${MINIO_BACKUP_BUCKET}/influxdb/$FILENAME"
    fi
done

#
# 5. Backup summary
#
log "Backup completed successfully!"
log "Summary:"
log "  - MySQL backup: $MYSQL_SIZE"
if [ -f "$INFLUXDB_BACKUP_FILE" ]; then
    log "  - InfluxDB backup: $INFLUX_SIZE"
fi
log "  - Uploaded to: s3://${MINIO_BACKUP_BUCKET}/"
log "  - Retention: $RETENTION_DAYS days"

# Optional: Send notification
# if [ -n "${NOTIFICATION_WEBHOOK:-}" ]; then
#     curl -X POST "$NOTIFICATION_WEBHOOK" \
#         -H "Content-Type: application/json" \
#         -d "{\"text\": \"FactoryOps backup completed: MySQL ($MYSQL_SIZE)\"}"
# fi

# Cleanup temp directory
rm -f "$MYSQL_BACKUP_FILE" "$INFLUXDB_BACKUP_FILE"

log "Backup process finished"
exit 0
