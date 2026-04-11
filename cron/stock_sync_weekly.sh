#!/bin/bash
# Stock Database Sync - Weekly Cron Job
# =======================================
# KRX 종목정보 주간 동기화 (매주 일요일 새벽 실행)

set -e

LOG_FILE="/root/.openclaw/workspace/logs/stock_sync_$(date +%Y%m%d).log"
SCRIPT_DIR="/root/.openclaw/workspace/strg"

echo "[$(date)] Stock Database Sync Started" >> "$LOG_FILE"

cd "$SCRIPT_DIR"

# Python 동기화 실행
if python3 stock_database_manager.py >> "$LOG_FILE" 2>&1; then
    echo "[$(date)] ✅ Sync completed successfully" >> "$LOG_FILE"
    
    # 통계 저장
    python3 stock_db_cli.py stats >> "$LOG_FILE" 2>&1
    
    # Git 커밋 (변경사항이 있는 경우)
    cd /root/.openclaw/workspace
    if git status --porcelain | grep -q "^"; then
        git add strg/data/
        git commit -m "Weekly stock database sync - $(date +%Y-%m-%d)" >> "$LOG_FILE" 2>&1 || true
        git push origin main >> "$LOG_FILE" 2>&1 || true
        echo "[$(date)] ✅ Changes committed to Git" >> "$LOG_FILE"
    fi
else
    echo "[$(date)] ❌ Sync failed" >> "$LOG_FILE"
    exit 1
fi

echo "[$(date)] Stock Database Sync Finished" >> "$LOG_FILE"
