#!/bin/bash

set -e

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="$HOME/backups/gamehosting"
PROJECT_DIR="$HOME/gamehosting"

mkdir -p "$BACKUP_DIR"

echo "Starting backup: $DATE"

docker exec gamehosting-db mysqldump -u root -prootpass123 gamehosting > "$BACKUP_DIR/db_$DATE.sql"

tar -czf "$BACKUP_DIR/stack_$DATE.tar.gz" "$PROJECT_DIR"

find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
