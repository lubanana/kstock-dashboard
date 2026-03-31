#!/usr/bin/env python3
"""
실시간 DART Quality Oversold 스캐너
오늘(2026-03-31) 기준 과매도 + 재무우수 종목 발굴
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sqlite3
import sys
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

class DARTRealtimeScanner:
    """실시간 스캐너"""
    
    def __init__(self):
        self.price_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
        self.dart_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/dart_financial.db')
        self.fundamental_cache = {}
        self.load_fundamentals()
        
    def load_fundamentals(self):
        """재무 데이터 로드"""
        cursor = self.dart_conn.cursor()
        results = cursor.execute('''
            SELECT stock_code, year, revenue, operating_profit, net_income, 
                   total_assets, total_liabilities, total_equity
            FROM financial_data WHERE reprt_code = '11011'
            ORDER BY stock_code, year DESC
        ''').fetchall()
        
        for row in results:
            code = row[0]
            if code not in self.fundamental_cache:
                self.fundamental_cache[code] = []
            self.fundamental_cache[code].append(row[1:])
    
    def get_fundamental_score(self, symbol):
        """최신 재무 점수 계산"""
        if symbol not in self.fundamental_cache:
            return None
        
        data = self.fundamental_cache[symbol]
        if not data:
            return None
        
        latest = data[0]
        prev = data[1] if len(data) > 1 else None
        
        revenue, op_profit, net_income, assets, liabilities, equity = latest[1:]
        
        if equity <= 0 or revenue <= 0:
            return None
        
        roe = (net_income / equity) * 100
        debt_ratio = (liabilities / equity) * 100
        op_margin = (op_profit / revenue) * 100
        
        # 성장성
        revenue_growth = 0
        profit_growth = 0
        if prev and prev[1] > 0 and prev[3] > 0:
            revenue_growth = ((latest[1] - prev[1]) / prev[1]) * 100
            profit_growth = ((latest[3] - prev[3]) / prev[3]) * 100
        
        # 퀄리티 점수
        score = 0
        if roe >= 20: score += 30
        elif roe >= 15: score += 25
        elif roe >= 10: score += 20
        elif roe >= 5: score += 10
        
        if debt_ratio <= 50: score += 25
        elif debt_ratio <= 100: score += 20
        elif debt_ratio <= 200: score += 15
        elif debt_ratio <= 300: score += 10
        
        if op_margin >= 20: score += 25
        elif op_margin >= 15: score += 20
        elif op_margin >= 10: score += 15
        elif op_margin >= 5: score += 10
        
        if revenue_growth >= 20: score += 10
        elif revenue_growth >= 10: score += 7
        elif revenue_growth >= 0: score += 5
        
        if profit_growth >= 30: score += 10
        elif profit_growth >= 10: score += 7
        elif profit_growth >= 0: score += 5
        
        return {
            'quality_score': score, 'roe': roe, 'debt_ratio': debt_ratio,
            'op_margin': op_margin, 'revenue_growth': revenue_growth,
            'profit_growth': profit_growth, 'year': latest[0]
        }
    
    def scan_stock(self, symbol):
        """개별 종목 스캔"""
        try:
            # 재무 데이터
            fund = self.get_fundamental_score(symbol)
            if not fund or fund['quality_score'] < 60:
                return None
            
            # 가격 데이터 (최근 400일)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400)
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 100:
                return None
            
            latest = df.iloc[-1]
            if latest['Close'] < 1000:
                return None
            
            # RSI 계산
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1]
            
            if rsi_val > 40:
                return None
            
            # 52주 고점 대비
            high_52w = df['High'].tail(252).max()
            vs_high = (latest['Close'] - high_52w) / high_52w * 100
            
            if vs_high > -10:
                return None
            
            # 종목명 조회
            name = self.price_conn.execute(
                'SELECT name FROM stock_info WHERE symbol = ?', (symbol,)
            ).fetchone()
            name = name[0] if name else 'Unknown'
            
            return {
                'symbol': symbol,
                'name': name,
                'price': latest['Close'],
                'rsi': rsi_val,
                'vs_52w_high': vs_high,
                'quality_score': fund['quality_score'],
                'roe': fund['roe'],
                'debt_ratio': fund['debt_ratio'],
                'op_margin': fund['op_margin'],
                'year': fund['year']
            }
            
        except Exception as e:
            return None
    
    def run(self):
        """전체 종목 스캔"""
        print("="*70)
        print(f"📊 실시간 DART Quality Oversold 스캐너")
        print(f"기준일: 2026-03-31")
        print("="*70)
        print("\n선정 기준:")
        print("  • 재무점수 60점+")
        print("  • RSI 40 이하")
        print("  • 52주 고점 대비 -10%+")
        print("  • 주가 1,000원 이상")
        print()
        
        # 전체 종목 로드
        symbols = [r[0] for r in self.price_conn.execute('SELECT symbol FROM stock_info').fetchall()]
        print(f"대상: {len(symbols)}개 종목\n")
        
        results = []
        for i, symbol in enumerate(symbols, 1):
            if i % 200 == 0:
                print(f"  [{i}/{len(symbols)}] 스캔 중...", end='\r')
            
            result = self.scan_stock(symbol)
            if result:
                results.append(result)
                print(f"  ✓ {symbol} ({result['name']}) - 재무:{result['quality_score']:.0f} RSI:{result['rsi']:.1f}")
        
        print(f"\n\n✅ 선정 완료: {len(results)}개 종목")
        return sorted(results, key=lambda x: x['quality_score'], reverse=True)


def main():
    scanner = DARTRealtimeScanner()
    results = scanner.run()
    
    if results:
        print("\n" + "="*70)
        print("📈 오늘의 선정 종목")
        print("="*70)
        print(f"{'순위':<4} {'종목':<8} {'이름':<12} {'현재가':<10} {'RSI':<6} {'52주대비':<10} {'재무점수':<8}")
        print("-"*70)
        
        for i, r in enumerate(results[:20], 1):
            name_short = r['name'][:10] if len(r['name']) > 10 else r['name']
            print(f"{i:<4} {r['symbol']:<8} {name_short:<12} {r['price']:>8,.0f} {r['rsi']:>5.1f} {r['vs_52w_high']:>8.1f}% {r['quality_score']:>7.0f}")
        
        # 상세 정보
        print("\n" + "="*70)
        print("📊 상세 재무 정보")
        print("="*70)
        for i, r in enumerate(results[:10], 1):
            print(f"\n{i}. {r['symbol']} {r['name']} ({r['year']}년 기준)")
            print(f"   현재가: {r['price']:,.0f}원 | RSI: {r['rsi']:.1f} | 52주대비: {r['vs_52w_high']:.1f}%")
            print(f"   재무점수: {r['quality_score']:.0f}/100")
            print(f"   ROE: {r['roe']:.1f}% | 부채비율: {r['debt_ratio']:.1f}% | 영업익률: {r['op_margin']:.1f}%")
    
    # 저장
    date_str = datetime.now().strftime('%Y%m%d')
    output = f'/root/.openclaw/workspace/strg/docs/dart_realtime_scan_{date_str}.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 결과 저장: {output}")


if __name__ == '__main__':
    main()
