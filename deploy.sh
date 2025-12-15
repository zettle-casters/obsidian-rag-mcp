#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

LOG_FILE="/var/log/deploy-dev.log"
LOCK_FILE="/tmp/deploy.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

if [ -f "$LOCK_FILE" ]; then
    log "ERROR: Deploy already in progress"
    exit 1
fi

touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "=== Deploy started in $(pwd) ==="

PREV_COMMIT=$(git rev-parse HEAD)
log "Previous commit: $PREV_COMMIT"

log "Fetching updates..."
git fetch || { log "ERROR: git fetch failed"; exit 1; }

log "Pulling changes..."
git pull --rebase || { log "ERROR: git pull failed"; exit 1; }

log "Updating submodules..."
git submodule update --init --recursive || { log "ERROR: submodule update failed"; exit 1; }

NEW_COMMIT=$(git rev-parse HEAD)
log "New commit: $NEW_COMMIT"

if git diff --name-only "$PREV_COMMIT" "$NEW_COMMIT" | grep -q "docker-compose\|Dockerfile"; then
    log "Docker files changed, rebuilding..."
    docker compose up -d --build || {
        log "ERROR: Docker build failed, attempting rollback..."
        git reset --hard "$PREV_COMMIT"
        docker compose up -d
        exit 1
    }
else
    log "No Docker changes, restarting containers..."
    docker compose up -d
fi

sleep 5
if docker compose ps | grep -q "Exit\|unhealthy"; then
    log "WARNING: Some containers are not healthy"
    docker compose ps
fi

log "=== Deploy completed successfully ==="