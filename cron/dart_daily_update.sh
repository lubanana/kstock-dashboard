#!/bin/bash
# DART 공시정보 일일 업데이트 크론 스크립트
# 실행: 매일 18:00 (장 마감 후)

cd /root/.openclaw/workspace/strg

# 로그 파일
LOG_FILE="logs/dart_update_$(date +%Y%m%d).log"
mkdir -p logs

echo "=== DART 공시 업데이트 시작: $(date) ===" >> $LOG_FILE

# Python 환경 설정
export PYTHONPATH=/root/.openclaw/workspace/strg:$PYTHONPATH

# 최근 3일 공시 업데이트
python3 fast_dart_update.py --days 3 >> $LOG_FILE 2>&1

echo "=== 업데이트 완료: $(date) ===" >> $LOG_FILE
echo "" >> $LOG_FILE

# 30일 이상 된 로그 삭제
find logs -name "dart_update_*.log" -mtime +30 -delete
