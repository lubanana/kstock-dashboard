#!/bin/bash
# KStock Analyzer Launcher
# 사용법: kstock [종목코드]

cd /home/programs/kstock_analyzer
source venv/bin/activate 2>/dev/null || python3 -m venv venv

if [ $# -eq 0 ]; then
    python3 kstock.py
else
    python3 kstock.py "$1"
fi
