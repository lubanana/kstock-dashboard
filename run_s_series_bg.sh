#!/bin/bash
# S-Series Scanner Background Runner
# Runs S1, S2, S3 sequential scans with progress logging

cd /root/.openclaw/workspace/strg

LOG_FILE="./logs/s_series_scan_$(date +%Y%m%d_%H%M).log"
mkdir -p ./logs

echo "🚀 S-Series 스캐너 백그라운드 실행 시작" | tee -a $LOG_FILE
echo "시작 시간: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a $LOG_FILE
echo "==================================================" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# Run S-Series scanner
python3 s_series_scanner.py 2>&1 | tee -a $LOG_FILE

# Completion message
echo "" | tee -a $LOG_FILE
echo "==================================================" | tee -a $LOG_FILE
echo "✅ S-Series 스캐너 실행 완료" | tee -a $LOG_FILE
echo "완료 시간: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a $LOG_FILE
echo "로그 파일: $LOG_FILE" | tee -a $LOG_FILE

# Send notification (if telegram CLI is available)
if command -v telegram-send &> /dev/null; then
    telegram-send "S-Series 스캐너 실행 완료! 결과 확인: $LOG_FILE"
fi
