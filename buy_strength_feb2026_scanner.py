#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Buy Strength Backtest - February 2026
===========================================
2026년 2월 매일 Buy Strength 스캔 실행 및 결과 저장

- 2026-02-01 ~ 2026-02-28 기간 매일 스캔
- 발굴 종목 추적
- 결과 CSV 저장
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import sqlite3

from buy_strength_scanner import BuyStrengthScanner


def get_date_range(year: int, month: int) -> list:
    """해당 연월의 모든 날짜 생성"""
    dates = []
    start_date = datetime(year, month, 1)
    
    # 다음 달 1일 전까지
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    current = start_date
    while current < end_date:
        # 주말 제외 (월=0, 금=4)
        if current.weekday() < 5:
            dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates


def scan_for_date(scan_date: str, db_path: str = './data/pivot_strategy.db') -> pd.DataFrame:
    """
    특정 날짜 기준으로 스캔 실행
    
    Args:
        scan_date: 스캔 기준일 (YYYY-MM-DD)
        db_path: DB 경로
    
    Returns:
        결과 DataFrame
    """
    print(f"\n📅 {scan_date} 기준 스캔 중...")
    
    # 스캐너 생성 (해당 날짜 기준)
    scanner = BuyStrengthScanner(
        db_path=db_path,
        min_amount=1e9,  # 10억
        min_price=1000
    )
    
    # 종목 리스트 로드
    with open('./data/stock_list.json', 'r') as f:
        stocks_data = json.load(f)
    stocks = pd.DataFrame(stocks_data['stocks'])
    
    results = []
    
    for idx, row in stocks.iterrows():
        if idx % 200 == 0:
            print(f"   진행: {idx}/{len(stocks)}")
        
        try:
            # 해당 날짜 기준 데이터 조회
            symbol = row['symbol']
            
            # DB에서 해당 날짜까지의 데이터 조회
            conn = sqlite3.connect(db_path)
            query = """
                SELECT * FROM stock_prices 
                WHERE symbol = ? AND date <= ?
                ORDER BY date
            """
            df = pd.read_sql_query(query, conn, params=(symbol, scan_date))
            conn.close()
            
            if len(df) < 60:
                continue
            
            # 분석 실행
            df.columns = [c.lower() for c in df.columns]
            
            current = df.iloc[-1]
            current_price = current['close']
            current_volume = current['volume']
            amount = current_price * current_volume
            
            # 하드 필터링
            if amount < 1e9 or current_price < 1000:
                continue
            
            # 점수 계산
            trend_score, trend_metrics = scanner.calculate_trend_score(df)
            momentum_score, momentum_metrics = scanner.calculate_momentum_score(df)
            volume_score, volume_metrics = scanner.calculate_volume_score(df)
            
            total_score = trend_score + momentum_score + volume_score
            
            if total_score >= 80:  # A등급만
                grade = 'A'
                results.append({
                    'scan_date': scan_date,
                    'symbol': symbol,
                    'name': row['name'],
                    'market': row['market'],
                    'price': current_price,
                    'amount': amount / 1e8,  # 억 단위
                    'total_score': total_score,
                    'trend_score': trend_score,
                    'momentum_score': momentum_score,
                    'volume_score': volume_score,
                    'rsi': momentum_metrics.get('rsi14', 0),
                    'volume_ratio': volume_metrics.get('volume_ratio', 0),
                    'grade': grade
                })
                print(f"   🎯 {symbol} ({row['name']}): {total_score}점")
                
        except Exception as e:
            continue
    
    if results:
        return pd.DataFrame(results)
    return pd.DataFrame()


def run_february_2026_scan():
    """2026년 2월 전체 스캔 실행"""
    print("🚀 2026년 2월 Buy Strength 백테스트")
    print("=" * 70)
    
    # 2월 영업일 목록
    dates = get_date_range(2026, 2)
    print(f"📅 총 {len(dates)}개 영업일 스캔 예정")
    print(f"   기간: {dates[0]} ~ {dates[-1]}")
    
    all_results = []
    
    for scan_date in dates:
        result_df = scan_for_date(scan_date)
        if not result_df.empty:
            all_results.append(result_df)
            print(f"   ✅ {scan_date}: {len(result_df)}개 종목 발굴")
        else:
            print(f"   ⚠️ {scan_date}: 발굴 종목 없음")
    
    # 전체 결과 합치기
    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        
        # 저장
        output_dir = Path('./reports/buy_strength_feb2026')
        output_dir.mkdir(exist_ok=True)
        
        final_df.to_csv(output_dir / 'daily_scan_results.csv', 
                       index=False, encoding='utf-8-sig')
        
        # 종목별 집계
        symbol_stats = final_df.groupby(['symbol', 'name', 'market']).agg({
            'scan_date': 'count',
            'total_score': 'mean',
            'price': 'last'
        }).reset_index()
        symbol_stats.columns = ['종목코드', '종목명', '시장', '발굴횟수', '평균점수', '최종가']
        symbol_stats = symbol_stats.sort_values('발굴횟수', ascending=False)
        
        symbol_stats.to_csv(output_dir / 'symbol_summary.csv',
                           index=False, encoding='utf-8-sig')
        
        print("\n" + "=" * 70)
        print("✅ 스캔 완료!")
        print(f"📊 총 {len(final_df)}건의 신호 발견")
        print(f"📊 {len(symbol_stats)}개 종목 발굴")
        print(f"\n📁 저장 위치: {output_dir}")
        print("\n📈 발굴 빈도 TOP 10:")
        print(symbol_stats.head(10).to_string(index=False))
        
        return final_df, symbol_stats
    else:
        print("\n⚠️ 발굴 결과 없음")
        return pd.DataFrame(), pd.DataFrame()


if __name__ == "__main__":
    run_february_2026_scan()
