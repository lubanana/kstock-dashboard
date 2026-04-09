#!/bin/bash
# Daily Scanner - 매일 오전 8시 실행

WORK_DIR="/root/.openclaw/workspace/strg"
cd $WORK_DIR

# 오늘 날짜
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)

echo "=========================================="
echo "📅 Daily Scanner - $TODAY"
echo "=========================================="

# 1. 어제 데이터 확인 및 구축 (장마감 데이터)
echo "🔄 어제($YESTERDAY) 데이터 확인/구축 중..."
python3 unified_daily_updater.py --date $YESTERDAY --workers 8

# 2. 스캐너 실행 (어제 데이터 기준)
echo "🔍 스캐너 실행 중..."
python3 scanner_2604_v7_hybrid.py --date $YESTERDAY

# 3. GitHub에 푸시
echo "📤 GitHub에 푸시 중..."
git add -A
git commit -m "Daily scan $YESTERDAY - Automated" || echo "변경사항 없음"
git push || echo "푸시 실패"

echo "=========================================="
echo "✅ 완료: $YESTERDAY"
echo "=========================================="
