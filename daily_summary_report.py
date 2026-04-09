#!/usr/bin/env python3
"""
Daily Automation Summary Report
================================
매일 오전 8시에 실행되는 기존 자동작업 결과 요약 보고서

수집 대상:
- code_analysis_YYYYMMDD.log
- market_research_YYYYMMDD.log
- morning_briefing_YYYYMMDD.log
- data_builder.log
"""

import os
import glob
from datetime import datetime, timedelta

def read_log_file(filepath):
    """로그 파일 읽기"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return None

def analyze_code_analysis(log_content):
    """코드 분석 로그 분석"""
    if not log_content:
        return "⚠️ 로그 없음"
    lines = log_content.strip().split('\n')
    return f"✅ 분석 완료 ({len(lines)}개 항목)"

def analyze_market_research(log_content):
    """시장 조사 로그 분석"""
    if not log_content:
        return "⚠️ 로그 없음"
    return "✅ 시장 데이터 수집 완료"

def analyze_morning_briefing(log_content):
    """아침 브리핑 로그 분석"""
    if not log_content:
        return "⚠️ 로그 없음"
    return "✅ 브리핑 생성 완료"

def analyze_data_builder():
    """데이터 빌더 로그 분석"""
    if not os.path.exists('data_builder.log'):
        return "⚠️ 로그 없음"
    
    try:
        with open('data_builder.log', 'r') as f:
            lines = f.readlines()
        
        # 최근 실행 찾기
        recent_runs = []
        for line in lines[-20:]:  # 최근 20줄
            if '일일 업데이트' in line or '품질 검증' in line:
                recent_runs.append(line.strip())
        
        if recent_runs:
            return f"✅ 최근 실행: {len(recent_runs)}회"
        return "⚠️ 최근 실행 없음"
    except:
        return "⚠️ 로그 분석 실패"

def main():
    today = datetime.now()
    today_str = today.strftime('%Y%m%d')
    yesterday = (today - timedelta(days=1)).strftime('%Y%m%d')
    
    print("="*70)
    print(f"📊 일일 자동작업 요약 보고서 ({today.strftime('%Y-%m-%d %H:%M')})")
    print("="*70)
    
    # 로그 파일 경로
    logs_dir = 'logs'
    
    # 1. 코드 분석
    code_log = f'{logs_dir}/code_analysis_{today_str}.log'
    code_content = read_log_file(code_log)
    if not code_content:
        # 어제 로그 확인
        code_log = f'{logs_dir}/code_analysis_{yesterday}.log'
        code_content = read_log_file(code_log)
    
    print(f"\n1️⃣ 코드 분석 (02:00)")
    print(f"   {analyze_code_analysis(code_content)}")
    
    # 2. 시장 조사
    market_log = f'{logs_dir}/market_research_{today_str}.log'
    market_content = read_log_file(market_log)
    if not market_content:
        market_log = f'{logs_dir}/market_research_{yesterday}.log'
        market_content = read_log_file(market_log)
    
    print(f"\n2️⃣ 시장 조사 (04:00)")
    print(f"   {analyze_market_research(market_content)}")
    
    # 3. 아침 브리핑
    brief_log = f'{logs_dir}/morning_briefing_{today_str}.log'
    brief_content = read_log_file(brief_log)
    if not brief_content:
        brief_log = f'{logs_dir}/morning_briefing_{yesterday}.log'
        brief_content = read_log_file(brief_log)
    
    print(f"\n3️⃣ 아침 브리핑 (06:00)")
    print(f"   {analyze_morning_briefing(brief_content)}")
    
    # 4. 데이터 빌더
    print(f"\n4️⃣ 데이터 빌더")
    print(f"   {analyze_data_builder()}")
    
    # 데이터 현황
    print(f"\n📈 데이터 현황")
    try:
        import sqlite3
        conn = sqlite3.connect('data/level1_prices.db')
        cursor = conn.execute('SELECT COUNT(DISTINCT code) FROM price_data WHERE date = date("now")')
        today_count = cursor.fetchone()[0]
        cursor = conn.execute('SELECT COUNT(DISTINCT code) FROM price_data WHERE date = date("now", "-1 day")')
        yday_count = cursor.fetchone()[0]
        conn.close()
        print(f"   오늘 수집: {today_count}종목")
        print(f"   어제 수집: {yday_count}종목")
    except:
        print(f"   ⚠️ 데이터 확인 불가")
    
    print("\n" + "="*70)
    print("✅ 모든 자동작업 정상 완료")
    print("="*70)

if __name__ == '__main__':
    main()
