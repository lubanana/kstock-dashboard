#!/usr/bin/env python3
"""
Level 1 Daily Price Collector
매일 3회 가격 데이터 수집 (08:00, 12:00, 16:00)

Features:
- FDR 기반 실시간 가격 수집
- 기술적 지표 계산 (MA, RSI, MACD)
- SQLite 저장
- 70점 이상 종목 필터링
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

import FinanceDataReader as fdr


class DailyPriceCollector:
    """일일 가격 데이터 수집기"""
    
    def __init__(self, db_path: str = 'data/level1_daily.db'):
        self.db_path = db_path
        self.init_db()
        
    def init_db(self):
        """DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT,
                market TEXT,
                date TEXT,
                time_slot TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                change_pct REAL,
                ma5 REAL,
                ma20 REAL,
                ma60 REAL,
                rsi REAL,
                macd REAL,
                score REAL,
                recommendation TEXT,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, date, time_slot)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_stocks(self) -> List[Dict]:
        """종목 리스트 로드"""
        stocks = []
        try:
            with open('data/kospi_stocks.json', 'r') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSPI'})
        except: pass
        
        try:
            with open('data/kosdaq_stocks.json', 'r') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({'code': s['code'], 'name': s['name'], 'market': 'KOSDAQ'})
        except: pass
        
        return stocks
    
    def analyze_stock(self, code: str, name: str, market: str) -> Optional[Dict]:
        """단일 종목 분석"""
        try:
            # 60일 데이터 수집
            df = fdr.DataReader(code, (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'))
            if df is None or len(df) < 20:
                return None
            
            close = df['Close']
            latest = close.iloc[-1]
            
            # 이동평균
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else ma20
            
            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # MACD
            exp1 = close.ewm(span=12).mean()
            exp2 = close.ewm(span=26).mean()
            macd = (exp1 - exp2).iloc[-1]
            
            # 점수 계산
            score = 50.0
            if latest > ma5: score += 10
            if latest > ma20: score += 10
            if ma5 > ma20: score += 10
            if 30 <= rsi <= 70: score += 20
            elif rsi < 30: score += 15
            if macd > 0: score += 20
            
            latest_row = df.iloc[-1]
            return {
                'code': code,
                'name': name,
                'market': market,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'open': latest_row['Open'],
                'high': latest_row['High'],
                'low': latest_row['Low'],
                'close': latest,
                'volume': latest_row['Volume'],
                'change_pct': latest_row.get('Change', 0),
                'ma5': ma5,
                'ma20': ma20,
                'ma60': ma60,
                'rsi': rsi,
                'macd': macd,
                'score': score,
                'recommendation': 'BUY' if score >= 70 else 'HOLD' if score >= 40 else 'SELL',
                'status': 'success'
            }
        except:
            return None
    
    def collect(self, time_slot: str = 'morning'):
        """수집 실행"""
        stocks = self.load_stocks()
        results = []
        
        print(f"\n🚀 Daily Price Collection - {time_slot}")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"   Stocks: {len(stocks)}")
        
        for i, stock in enumerate(stocks, 1):
            result = self.analyze_stock(stock['code'], stock['name'], stock['market'])
            if result:
                result['time_slot'] = time_slot
                results.append(result)
                
                # DB 저장
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO price_analysis 
                    (code, name, market, date, time_slot, open, high, low, close, volume, 
                     change_pct, ma5, ma20, ma60, rsi, macd, score, recommendation, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', tuple(result.get(k) for k in ['code', 'name', 'market', 'date', 'time_slot', 
                    'open', 'high', 'low', 'close', 'volume', 'change_pct', 'ma5', 'ma20', 'ma60', 
                    'rsi', 'macd', 'score', 'recommendation', 'status']))
                conn.commit()
                conn.close()
            
            if i % 100 == 0:
                print(f"   Progress: {i}/{len(stocks)}")
            time.sleep(0.05)
        
        # 70점 이상 필터링
        high_scores = [r for r in results if r['score'] >= 70]
        
        print(f"\n✅ Complete!")
        print(f"   Total: {len(results)}")
        print(f"   High Score (≥70): {len(high_scores)}")
        
        return results, high_scores


if __name__ == '__main__':
    import sys
    slot = sys.argv[1] if len(sys.argv) > 1 else 'morning'
    collector = DailyPriceCollector()
    collector.collect(slot)
