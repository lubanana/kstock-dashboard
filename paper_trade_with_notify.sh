#!/bin/bash
# paper_trade_with_notify.sh - 페이퍼트레이딩 + 알림 통합 실행

echo "=========================================="
echo "🚀 페이퍼트레이딩 + 알림 시스템 시작"
echo "=========================================="
echo ""

# 1. 알림 모니터 백그라운드 실행
echo "📡 알림 모니터 시작..."
python3 paper_notifier.py --interval 30 &
NOTIFIER_PID=$!
echo "   PID: $NOTIFIER_PID"

# 2. 잠시 대기 (알림 모니터 준비)
sleep 2

# 3. 초기 스캔 실행
echo ""
echo "🔍 초기 스캔 실행..."
python3 paper_trading.py --mode scan --coins BTC,ETH,XRP,SOL --strategy mean_reversion

echo ""
echo "=========================================="
echo "✅ 시스템 실행 완료"
echo "=========================================="
echo "알림 모니터 PID: $NOTIFIER_PID"
echo ""
echo "명령어:"
echo "  - 종료: kill $NOTIFIER_PID"
echo "  - 상태: python paper_dashboard.py"
echo "  - 수동스캔: python paper_trading.py --mode scan"
echo "=========================================="

# 종료 시 알림 모니터도 종료
trap "echo ''; echo '🛑 시스템 종료...'; kill $NOTIFIER_PID 2>/dev/null; exit" INT TERM

# 포그라운드 유지
wait $NOTIFIER_PID
