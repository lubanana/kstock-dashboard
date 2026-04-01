#!/bin/bash
# Paper Trading Notification Script
# Runs at 8 AM and 5 PM daily

WORKSPACE="/root/.openclaw/workspace/strg"
cd "$WORKSPACE"

export PYTHONPATH="$WORKSPACE:$PYTHONPATH"
export PYTHONIOENCODING=utf-8

echo "=== Paper Trading Monitor ($(date)) ===" >> /tmp/paper_trading.log

# 모니터링 실행
python3 paper_trading_monitor.py --check all --summary >> /tmp/paper_trading.log 2>&1

echo "" >> /tmp/paper_trading.log
