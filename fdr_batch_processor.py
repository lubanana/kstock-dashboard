#!/usr/bin/env python3
"""
FinanceDataReader Batch Processor
FDR 기반 다중 종목 병렬 처리

Features:
- concurrent.futures로 병렬 처리
- ThreadPoolExecutor로 I/O 병목 해결
- 50개씩 배치 처리 + 진행률 표시
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import time

import FinanceDataReader as fdr


class FDRBatchProcessor:
    """FDR 병렬 배치 프로세서"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.results = []
        self.errors = []
        
    def fetch_single_stock(self, stock_info: Dict) -> Optional[Dict]:
        """
        단일 종목 데이터 수집
        
        Args:
            stock_info: {'code': '005930', 'name': '삼성전자', 'market': 'KOSPI'}
        
        Returns:
            분석 결과 또는 None
        """
        code = stock_info['code']
        name = stock_info['name']
        market = stock_info.get('market', 'KRX')
        
        try:
            # FDR로 데이터 수집 (120일)
            end = datetime.now()
            start = end - timedelta(days=120)
            
            df = fdr.DataReader(
                code,
                start.strftime('%Y-%m-%d'),
                end.strftime('%Y-%m-%d')
            )
            
            if df is None or len(df) < 30:
                return None
            
            # 기술적 분석
            result = self._analyze(df)
            
            return {
                'code': code,
                'name': name,
                'market': market,
                'price': float(df['Close'].iloc[-1]),
                'change': float(df['Change'].iloc[-1]) if 'Change' in df.columns else 0.0,
                **result
            }
            
        except Exception as e:
            self.errors.append({'code': code, 'error': str(e)})
            return None
    
    def _analyze(self, df: pd.DataFrame) -> Dict:
        """기술적 분석"""
        close = df['Close']
        
        # 이동평균 (float로 변환)
        ma5 = float(close.rolling(5).mean().iloc[-1])
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60 = float(close.rolling(60).mean().iloc[-1])
        latest = float(close.iloc[-1])
        
        # RSI (float로 변환)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float(100 - (100 / (1 + rs)).iloc[-1])
        
        # MACD (float로 변환)
        exp1 = close.ewm(span=12).mean()
        exp2 = close.ewm(span=26).mean()
        macd = float((exp1 - exp2).iloc[-1])
        
        # 점수 계산 (float로 변환)
        score = 50.0
        
        # 이동평균 (30점)
        if latest > ma5: score += 10
        if latest > ma20: score += 10
        if ma5 > ma20: score += 10
        
        # RSI (20점)
        if 30 <= rsi <= 70: score += 20
        elif rsi < 30: score += 15
        
        # MACD (20점)
        if macd > 0: score += 20
        
        # 추세 (10점)
        if close.iloc[-1] > close.iloc[-5]: score += 10
        
        # 추천
        if score >= 70:
            rec = 'BUY'
        elif score >= 40:
            rec = 'HOLD'
        else:
            rec = 'SELL'
        
        return {
            'avg_score': float(score),
            'consensus': rec,
            'indicators': {
                'ma5': ma5,
                'ma20': ma20,
                'ma60': ma60,
                'rsi': rsi,
                'macd': macd
            }
        }
    
    def process_batch(self, stocks: List[Dict], batch_size: int = 50) -> List[Dict]:
        """
        배치 처리
        
        Args:
            stocks: 종목 리스트
            batch_size: 한 번에 처리할 종목 수
        
        Returns:
            결과 리스트
        """
        total = len(stocks)
        results = []
        
        print(f"\n🚀 FDR Batch Processing: {total} stocks")
        print(f"   Workers: {self.max_workers} | Batch size: {batch_size}")
        print("=" * 60)
        
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = stocks[batch_start:batch_end]
            
            print(f"\n📦 Batch {batch_start//batch_size + 1}/{(total-1)//batch_size + 1}")
            print(f"   Processing: {batch_start+1} ~ {batch_end} / {total}")
            
            # 병렬 처리
            batch_results = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self.fetch_single_stock, s): s for s in batch}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        batch_results.append(result)
                        print(f"   ✅ {result['name']}: {result['avg_score']}pts")
                    else:
                        stock = futures[future]
                        print(f"   ❌ {stock['name']}: Failed")
            
            results.extend(batch_results)
            
            # 진행률
            progress = len(results) / total * 100
            print(f"   Progress: {len(results)}/{total} ({progress:.1f}%)")
            
            # Rate limiting
            time.sleep(1)
        
        self.results = results
        print(f"\n{'=' * 60}")
        print(f"✅ Complete: {len(results)}/{total} stocks")
        print(f"❌ Failed: {len(self.errors)}")
        
        return results
    
    def save_results(self, filepath: str):
        """결과 저장"""
        output = {
            'date': datetime.now().isoformat(),
            'total': len(self.results),
            'data_source': 'fdr_batch',
            'results': self.results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved: {filepath}")


def test_batch():
    """배치 테스트"""
    # 테스트 종목 (50개)
    test_stocks = [
        {'code': '005930', 'name': '삼성전자', 'market': 'KOSPI'},
        {'code': '000660', 'name': 'SK하이닉스', 'market': 'KOSPI'},
        {'code': '035420', 'name': 'NAVER', 'market': 'KOSPI'},
        {'code': '051910', 'name': 'LG화학', 'market': 'KOSPI'},
        {'code': '005380', 'name': '현대차', 'market': 'KOSPI'},
        {'code': '207940', 'name': '삼성바이오로직스', 'market': 'KOSPI'},
        {'code': '068270', 'name': '셀트리온', 'market': 'KOSPI'},
        {'code': '000270', 'name': '기아', 'market': 'KOSPI'},
        {'code': '028260', 'name': '삼성물산', 'market': 'KOSPI'},
        {'code': '035720', 'name': '카카오', 'market': 'KOSPI'},
        {'code': '005490', 'name': 'POSCO홀딩스', 'market': 'KOSPI'},
        {'code': '105560', 'name': 'KB금융', 'market': 'KOSPI'},
        {'code': '012330', 'name': '현대모비스', 'market': 'KOSPI'},
        {'code': '055550', 'name': '신한지주', 'market': 'KOSPI'},
        {'code': '003550', 'name': 'LG', 'market': 'KOSPI'},
        {'code': '086790', 'name': '하나금융지주', 'market': 'KOSPI'},
        {'code': '032830', 'name': '삼성생명', 'market': 'KOSPI'},
        {'code': '009150', 'name': '삼성전기', 'market': 'KOSPI'},
        {'code': '033780', 'name': 'KT&G', 'market': 'KOSPI'},
        {'code': '010130', 'name': '고려아연', 'market': 'KOSPI'},
    ]
    
    processor = FDRBatchProcessor(max_workers=10)
    results = processor.process_batch(test_stocks, batch_size=10)
    
    # 상위 10개
    print("\n🏆 Top 10:")
    for r in sorted(results, key=lambda x: x['avg_score'], reverse=True)[:10]:
        print(f"   {r['name']}: {r['avg_score']}pts - {r['consensus']}")
    
    # 저장
    processor.save_results('data/fdr_batch_test.json')


if __name__ == '__main__':
    test_batch()
