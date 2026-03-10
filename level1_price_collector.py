#!/usr/bin/env python3
"""
Level 1 Price Data Collector - Full Market
레벨1 전체 종목 가격 데이터 수집기

Features:
- FinanceDataReader (FDR) 기반
- 병렬 처리 (ThreadPoolExecutor)
- 3,286개 종목 전체 처리
- SQLite 저장 + JSON 백업
- 진행률 표시 + 오류 복구
"""

import json
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import time
import os

import FinanceDataReader as fdr


class Level1PriceCollector:
    """Level 1 가격 데이터 수집기"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db', max_workers: int = 15):
        self.db_path = db_path
        self.max_workers = max_workers
        self.results = []
        self.errors = []
        self.init_db()
        
    def init_db(self):
        """SQLite DB 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_data (
                code TEXT PRIMARY KEY,
                name TEXT,
                market TEXT,
                date TEXT,
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def load_stock_list(self) -> List[Dict]:
        """종목 리스트 로드 (JSON 파일)"""
        stocks = []
        
        # KOSPI
        try:
            with open('data/kospi_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({
                        'code': s['code'],
                        'name': s['name'],
                        'market': 'KOSPI'
                    })
        except Exception as e:
            print(f"   ⚠️  KOSPI load error: {e}")
        
        # KOSDAQ
        try:
            with open('data/kosdaq_stocks.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for s in data.get('stocks', []):
                    stocks.append({
                        'code': s['code'],
                        'name': s['name'],
                        'market': 'KOSDAQ'
                    })
        except Exception as e:
            print(f"   ⚠️  KOSDAQ load error: {e}")
        
        print(f"📋 Loaded {len(stocks)} stocks (KOSPI + KOSDAQ)")
        return stocks
    
    def fetch_and_analyze(self, stock: Dict, days: int = 60) -> Optional[Dict]:
        """
        단일 종목 데이터 수집 및 분석
        
        Returns:
            분석 결과 딕셔너리
        """
        code = stock['code']
        name = stock['name']
        market = stock['market']
        
        try:
            # FDR로 가격 데이터 수집
            end = datetime.now()
            start = end - timedelta(days=days)
            
            df = fdr.DataReader(
                code,
                start.strftime('%Y-%m-%d'),
                end.strftime('%Y-%m-%d')
            )
            
            if df is None or len(df) < 20:
                return {
                    'code': code,
                    'name': name,
                    'market': market,
                    'status': 'insufficient_data'
                }
            
            # 기본 가격 정보
            latest = df.iloc[-1]
            close = float(latest['Close'])
            open_price = float(latest['Open'])
            high = float(latest['High'])
            low = float(latest['Low'])
            volume = int(latest['Volume'])
            change_pct = float(latest['Change']) if 'Change' in df.columns else 0.0
            
            # 기술적 지표 계산
            prices = df['Close']
            
            # 이동평균
            ma5 = float(prices.rolling(5).mean().iloc[-1])
            ma20 = float(prices.rolling(20).mean().iloc[-1])
            ma60 = float(prices.rolling(60).mean().iloc[-1]) if len(prices) >= 60 else ma20
            
            # RSI
            delta = prices.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float(100 - (100 / (1 + rs)).iloc[-1])
            if pd.isna(rsi):
                rsi = 50.0
            
            # MACD
            exp1 = prices.ewm(span=12).mean()
            exp2 = prices.ewm(span=26).mean()
            macd = float((exp1 - exp2).iloc[-1])
            
            # 점수 계산 (0-100)
            score = 50.0
            
            # 이동평균 점수 (30점)
            if close > ma5: score += 10
            if close > ma20: score += 10
            if ma5 > ma20: score += 10
            
            # RSI 점수 (20점)
            if 30 <= rsi <= 70: score += 20
            elif rsi < 30: score += 15  # 과매도
            
            # MACD 점수 (20점)
            if macd > 0: score += 20
            
            # 추세 점수 (10점)
            if change_pct > 0: score += 10
            
            # 추천
            if score >= 70:
                recommendation = 'BUY'
            elif score >= 40:
                recommendation = 'HOLD'
            else:
                recommendation = 'SELL'
            
            return {
                'code': code,
                'name': name,
                'market': market,
                'date': end.strftime('%Y-%m-%d'),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'change_pct': change_pct,
                'ma5': ma5,
                'ma20': ma20,
                'ma60': ma60,
                'rsi': rsi,
                'macd': macd,
                'score': score,
                'recommendation': recommendation,
                'status': 'success'
            }
            
        except Exception as e:
            self.errors.append({'code': code, 'name': name, 'error': str(e)})
            return {
                'code': code,
                'name': name,
                'market': market,
                'status': 'error',
                'error': str(e)
            }
    
    def save_to_db(self, result: Dict):
        """결과를 SQLite에 저장"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO price_data
            (code, name, market, date, open, high, low, close, volume, change_pct,
             ma5, ma20, ma60, rsi, macd, score, recommendation, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.get('code'),
            result.get('name'),
            result.get('market'),
            result.get('date'),
            result.get('open'),
            result.get('high'),
            result.get('low'),
            result.get('close'),
            result.get('volume'),
            result.get('change_pct'),
            result.get('ma5'),
            result.get('ma20'),
            result.get('ma60'),
            result.get('rsi'),
            result.get('macd'),
            result.get('score'),
            result.get('recommendation'),
            result.get('status')
        ))
        
        conn.commit()
        conn.close()
    
    def process_all(self, batch_size: int = 100) -> Dict:
        """
        전체 종목 처리
        
        Returns:
            처리 결과 통계
        """
        # 종목 리스트 로드
        stocks = self.load_stock_list()
        total = len(stocks)
        
        print(f"\n{'=' * 70}")
        print(f"🚀 Level 1 Price Data Collection")
        print(f"   Total: {total} stocks | Workers: {self.max_workers} | Batch: {batch_size}")
        print(f"{'=' * 70}\n")
        
        success_count = 0
        error_count = 0
        start_time = time.time()
        
        # 배치 처리
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = stocks[batch_start:batch_end]
            batch_num = batch_start // batch_size + 1
            total_batches = (total - 1) // batch_size + 1
            
            print(f"📦 Batch {batch_num}/{total_batches} ({batch_start+1}-{batch_end}/{total})")
            
            # 병렬 처리
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.fetch_and_analyze, s): s 
                    for s in batch
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    
                    if result:
                        self.results.append(result)
                        self.save_to_db(result)
                        
                        if result.get('status') == 'success':
                            success_count += 1
                            print(f"   ✅ {result['name']}: {result['score']:.0f}pts ({result['recommendation']})")
                        else:
                            error_count += 1
                            print(f"   ⚠️  {result['name']}: {result['status']}")
            
            # 진행률
            elapsed = time.time() - start_time
            progress = (batch_end / total) * 100
            rate = batch_end / elapsed if elapsed > 0 else 0
            eta = (total - batch_end) / rate if rate > 0 else 0
            
            print(f"   📊 Progress: {batch_end}/{total} ({progress:.1f}%) | "
                  f"Rate: {rate:.1f} stocks/sec | ETA: {eta/60:.1f}min\n")
            
            # Rate limiting
            time.sleep(0.5)
        
        # 최종 통계
        total_time = time.time() - start_time
        
        print(f"{'=' * 70}")
        print(f"✅ Complete!")
        print(f"   Success: {success_count}/{total}")
        print(f"   Errors: {error_count}")
        print(f"   Time: {total_time/60:.1f} minutes")
        print(f"   DB: {self.db_path}")
        print(f"{'=' * 70}\n")
        
        return {
            'total': total,
            'success': success_count,
            'errors': error_count,
            'time_seconds': total_time,
            'db_path': self.db_path
        }
    
    def export_to_json(self, filepath: str = 'data/level1_price_results.json'):
        """JSON으로 낳출"""
        output = {
            'date': datetime.now().isoformat(),
            'total': len(self.results),
            'data_source': 'fdr_level1',
            'results': [r for r in self.results if r.get('status') == 'success']
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Exported to: {filepath}")


def main():
    """메인 실행"""
    collector = Level1PriceCollector(max_workers=15)
    stats = collector.process_all(batch_size=100)
    collector.export_to_json()
    
    # 상위 10개 출력
    print("\n🏆 Top 10 by Score:")
    top = sorted(
        [r for r in collector.results if r.get('status') == 'success'],
        key=lambda x: x.get('score', 0),
        reverse=True
    )[:10]
    
    for i, r in enumerate(top, 1):
        print(f"   {i}. {r['name']} ({r['code']}): {r['score']:.0f}pts - {r['recommendation']}")


if __name__ == '__main__':
    main()
