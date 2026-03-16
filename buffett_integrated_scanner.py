#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
버핏 3전략 통합 스캐너 + 백테스터
KOSPI/KOSDAQ 3,286종목 대상
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class BuffettIntegratedScanner:
    """
    3가지 버핏 전략 통합 스캐너
    """
    
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.results = {
            'strategy1': [],  # 그레이엄 순유동자산
            'strategy2': [],  # 퀄리티 적정가
            'strategy3': []   # 배당성장
        }
        self.conn = None
        
    def connect_db(self):
        """DB 연결"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
    def close_db(self):
        """DB 종료"""
        if self.conn:
            self.conn.close()
            
    def get_all_stocks(self) -> List[Dict]:
        """전체 종목 리스트 조회"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT symbol, name, market FROM stock_info ORDER BY market, symbol")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_price_data(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """주가 데이터 조회"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT date, open, high, low, close, volume 
            FROM stock_prices 
            WHERE symbol = ? 
            ORDER BY date DESC 
            LIMIT ?
        """, (symbol, days))
        
        rows = cursor.fetchall()
        if not rows or len(rows) < 60:  # 최소 60일 데이터 필요
            return None
            
        df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 기술적 지표 계산
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        df['ma120'] = df['close'].rolling(120).mean()
        
        return df
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        if len(prices) < period + 1:
            return 50
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    def calculate_macd(self, prices: pd.Series) -> Tuple[float, float, float]:
        """MACD 계산"""
        if len(prices) < 35:
            return 0, 0, 0
            
        exp1 = prices.ewm(span=12).mean()
        exp2 = prices.ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()
        hist = macd - signal
        
        return macd.iloc[-1], signal.iloc[-1], hist.iloc[-1]
    
    def screen_strategy1_graham(self, symbol: str, name: str, market: str, df: pd.DataFrame) -> Dict:
        """
        전략1: 그레이엄 순유동자산
        실제 재무 데이터 대신 기술적/가격 지표로 근사
        """
        if df is None or len(df) < 120:
            return None
            
        current_price = df['close'].iloc[-1]
        
        # 저평가 지표들 (NCAV 개념 근사)
        # 1. P/B 대용: 52주 최저가 대비 현재가
        low_52w = df['close'].tail(252).min() if len(df) >= 252 else df['close'].min()
        pb_proxy = current_price / low_52w if low_52w > 0 else 999
        
        # 2. 유동성 지표
        avg_volume = df['volume'].tail(20).mean()
        recent_volume = df['volume'].tail(5).mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # 3. 모멘텀
        returns_1m = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100 if len(df) >= 20 else 0
        returns_3m = (df['close'].iloc[-1] / df['close'].iloc[-60] - 1) * 100 if len(df) >= 60 else 0
        
        # 4. RSI
        rsi = self.calculate_rsi(df['close'])
        
        # 5. 이평선 정배열 (추세 확인)
        ma_aligned = (df['close'].iloc[-1] > df['ma20'].iloc[-1] > df['ma60'].iloc[-1]) if not pd.isna(df['ma60'].iloc[-1]) else False
        
        # 점수 계산
        score = 0
        checks = []
        
        # 저평가 (P/B proxy < 1.3)
        if pb_proxy < 1.3:
            score += 30
            checks.append(f"✅ 52주 저가 대비 {pb_proxy:.2f}")
        elif pb_proxy < 1.5:
            score += 20
            checks.append(f"⚡ 52주 저가 대비 {pb_proxy:.2f}")
        else:
            checks.append(f"❌ 52주 저가 대비 {pb_proxy:.2f}")
        
        # 거래량 증가
        if volume_ratio > 1.5:
            score += 20
            checks.append(f"✅ 거래량 {volume_ratio:.1f}배")
        elif volume_ratio > 1.0:
            score += 10
            checks.append(f"⚡ 거래량 {volume_ratio:.1f}배")
        
        # 긍정적 모멘텀
        if returns_3m > 0 and returns_1m > -5:
            score += 20
            checks.append(f"✅ 3M 수익 {returns_3m:.1f}%")
        elif returns_3m > -5:
            score += 10
            checks.append(f"⚡ 3M 수익 {returns_3m:.1f}%")
        else:
            checks.append(f"❌ 3M 수익 {returns_3m:.1f}%")
        
        # RSI 적정 (30-60)
        if 30 <= rsi <= 60:
            score += 15
            checks.append(f"✅ RSI {rsi:.1f}")
        elif rsi < 30:
            score += 10
            checks.append(f"⚡ RSI {rsi:.1f} (과매도)")
        else:
            checks.append(f"❌ RSI {rsi:.1f}")
        
        # 추세 확인
        if ma_aligned:
            score += 15
            checks.append("✅ 정배열")
        else:
            checks.append("❌ 역배열/혼조")
        
        if score >= 60:
            return {
                'symbol': symbol,
                'name': name,
                'market': market,
                'strategy': '그레이엄 순유동자산',
                'score': score,
                'price': current_price,
                'pb_proxy': round(pb_proxy, 2),
                'volume_ratio': round(volume_ratio, 2),
                'returns_3m': round(returns_3m, 2),
                'rsi': round(rsi, 1),
                'ma_aligned': ma_aligned,
                'checks': checks
            }
        return None
    
    def screen_strategy2_quality(self, symbol: str, name: str, market: str, df: pd.DataFrame) -> Dict:
        """
        전략2: 퀄리티 적정가
        ROE/수익성 대신 추세/모멘텀/거래량으로 근사
        """
        if df is None or len(df) < 120:
            return None
            
        current_price = df['close'].iloc[-1]
        
        # 1. 수익성 지표 (ROE 대용) - 추세의 일관성
        returns_1m = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100 if len(df) >= 20 else 0
        returns_3m = (df['close'].iloc[-1] / df['close'].iloc[-60] - 1) * 100 if len(df) >= 60 else 0
        returns_6m = (df['close'].iloc[-1] / df['close'].iloc[-120] - 1) * 100 if len(df) >= 120 else 0
        
        # 수익성 일관성 (ROE 안정성 대용)
        monthly_returns = []
        for i in range(1, min(7, len(df)//20)):
            if len(df) >= i*20:
                ret = (df['close'].iloc[-1] / df['close'].iloc[-i*20] - 1) * 100
                monthly_returns.append(ret)
        
        return_std = np.std(monthly_returns) if len(monthly_returns) > 1 else 10
        
        # 2. 해자 지표 - 상대강도
        market_return = returns_3m  # 시장 대비는 단순화
        
        # 3. 가치 지표
        high_52w = df['close'].tail(252).max() if len(df) >= 252 else df['close'].max()
        from_52w_high = (current_price / high_52w - 1) * 100 if high_52w > 0 else 0
        
        # 4. 모멘텀
        rsi = self.calculate_rsi(df['close'])
        macd, signal, hist = self.calculate_macd(df['close'])
        
        # 5. 거래량 (관심도)
        avg_volume = df['volume'].tail(60).mean()
        recent_volume = df['volume'].tail(10).mean()
        volume_trend = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # 점수 계산
        score = 0
        details = []
        
        # ROE 대용 (수익성)
        if returns_6m > 15:
            score += 25
            details.append(f"✅ 6M 수익 {returns_6m:.1f}%")
        elif returns_6m > 5:
            score += 18
            details.append(f"⚡ 6M 수익 {returns_6m:.1f}%")
        else:
            details.append(f"❌ 6M 수익 {returns_6m:.1f}%")
        
        # 안정성
        if return_std < 8:
            score += 15
            details.append(f"✅ 변동성 낮음 (σ={return_std:.1f})")
        elif return_std < 12:
            score += 10
            details.append(f"⚡ 변동성 보통 (σ={return_std:.1f})")
        else:
            details.append(f"❌ 변동성 높음 (σ={return_std:.1f})")
        
        # 52주 최고가 대비 (적정가)
        if -20 <= from_52w_high <= -5:
            score += 20
            details.append(f"✅ 52주 고점 대비 {from_52w_high:.1f}%")
        elif -30 <= from_52w_high < -20:
            score += 15
            details.append(f"⚡ 52주 고점 대비 {from_52w_high:.1f}%")
        else:
            details.append(f"❌ 52주 고점 대비 {from_52w_high:.1f}%")
        
        # 모멘텀
        if rsi > 50 and hist > 0:
            score += 20
            details.append(f"✅ 모멘텀 양호 (RSI {rsi:.1f}, MACD+)")
        elif rsi > 45:
            score += 12
            details.append(f"⚡ 모멘텀 보통 (RSI {rsi:.1f})")
        else:
            details.append(f"❌ 모멘텀 약함 (RSI {rsi:.1f})")
        
        # 거래량 증가 (관심도)
        if volume_trend > 1.3:
            score += 20
            details.append(f"✅ 관심 증가 (거래량 {volume_trend:.1f}배)")
        elif volume_trend > 1.0:
            score += 10
            details.append(f"⚡ 관심 보통 (거래량 {volume_trend:.1f}배)")
        
        if score >= 70:
            return {
                'symbol': symbol,
                'name': name,
                'market': market,
                'strategy': '퀄리티 적정가',
                'score': score,
                'price': current_price,
                'returns_6m': round(returns_6m, 2),
                'return_std': round(return_std, 2),
                'from_52w_high': round(from_52w_high, 2),
                'rsi': round(rsi, 1),
                'volume_trend': round(volume_trend, 2),
                'details': details
            }
        return None
    
    def screen_strategy3_dividend(self, symbol: str, name: str, market: str, df: pd.DataFrame) -> Dict:
        """
        전략3: 배당성장
        안정적 현금흐름을 가진 종목 (낮은 변동성 + 꾸준한 거래)
        """
        if df is None or len(df) < 120:
            return None
            
        current_price = df['close'].iloc[-1]
        
        # 1. 변동성 (안정성 지표)
        returns = df['close'].pct_change().dropna()
        volatility = returns.tail(60).std() * np.sqrt(252) * 100  # 연간화 변동성
        
        # 2. 추세 일관성
        returns_1m = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100 if len(df) >= 20 else 0
        returns_3m = (df['close'].iloc[-1] / df['close'].iloc[-60] - 1) * 100 if len(df) >= 60 else 0
        returns_6m = (df['close'].iloc[-1] / df['close'].iloc[-120] - 1) * 100 if len(df) >= 120 else 0
        
        # 꾸준한 성장 (배당성장 대용)
        consistent = (returns_6m > 0) and (returns_3m > -5) and (returns_1m > -10)
        
        # 3. 거래량 안정성 (FCF 대용)
        volume_std = df['volume'].tail(60).std() / df['volume'].tail(60).mean()
        
        # 4. 가격 안정성
        max_dd = ((df['close'] / df['close'].cummax()) - 1).min() * 100
        
        # 5. RSI 적정
        rsi = self.calculate_rsi(df['close'])
        
        # 점수 계산
        score = 0
        details = []
        
        # 변동성 낮음 (안정성)
        if volatility < 30:
            score += 25
            details.append(f"✅ 변동성 {volatility:.1f}% (매우 안정)")
        elif volatility < 40:
            score += 18
            details.append(f"⚡ 변동성 {volatility:.1f}% (안정)")
        else:
            details.append(f"❌ 변동성 {volatility:.1f}% (높음)")
        
        # 꾸준한 성장
        if consistent and returns_6m > 5:
            score += 25
            details.append(f"✅ 꾸준한 성장 (6M {returns_6m:.1f}%)")
        elif consistent:
            score += 15
            details.append(f"⚡ 안정적 (6M {returns_6m:.1f}%)")
        else:
            details.append(f"❌ 변동 큼 (6M {returns_6m:.1f}%)")
        
        # 거래량 안정성
        if volume_std < 0.5:
            score += 15
            details.append(f"✅ 거래 안정")
        elif volume_std < 0.8:
            score += 10
            details.append(f"⚡ 거래 보통")
        
        # 낮은 최대낙폭
        if max_dd > -20:
            score += 20
            details.append(f"✅ 낙폭 작음 ({max_dd:.1f}%)")
        elif max_dd > -30:
            score += 12
            details.append(f"⚡ 낙폭 보통 ({max_dd:.1f}%)")
        else:
            details.append(f"❌ 낙폭 큼 ({max_dd:.1f}%)")
        
        # RSI 적정
        if 40 <= rsi <= 60:
            score += 15
            details.append(f"✅ RSI 적정 ({rsi:.1f})")
        elif 35 <= rsi <= 65:
            score += 8
            details.append(f"⚡ RSI 보통 ({rsi:.1f})")
        
        if score >= 60:
            return {
                'symbol': symbol,
                'name': name,
                'market': market,
                'strategy': '배당성장',
                'score': score,
                'price': current_price,
                'volatility': round(volatility, 2),
                'returns_6m': round(returns_6m, 2),
                'max_dd': round(max_dd, 2),
                'rsi': round(rsi, 1),
                'details': details
            }
        return None
    
    def run_full_scan(self):
        """전체 스캔 실행"""
        print("🔍 버핏 3전략 통합 스캔 시작")
        print("=" * 60)
        
        self.connect_db()
        
        try:
            stocks = self.get_all_stocks()
            print(f"총 {len(stocks)}개 종목 스캔 대상")
            
            for i, stock in enumerate(stocks):
                if i % 500 == 0:
                    print(f"  진행: {i}/{len(stocks)} ({i/len(stocks)*100:.1f}%)")
                
                symbol = stock['symbol']
                name = stock['name']
                market = stock['market']
                
                # 주가 데이터 조회
                df = self.get_price_data(symbol)
                if df is None:
                    continue
                
                # 3전략 동시 스크리닝
                s1 = self.screen_strategy1_graham(symbol, name, market, df)
                s2 = self.screen_strategy2_quality(symbol, name, market, df)
                s3 = self.screen_strategy3_dividend(symbol, name, market, df)
                
                if s1:
                    self.results['strategy1'].append(s1)
                if s2:
                    self.results['strategy2'].append(s2)
                if s3:
                    self.results['strategy3'].append(s3)
            
            # 정렬
            self.results['strategy1'].sort(key=lambda x: x['score'], reverse=True)
            self.results['strategy2'].sort(key=lambda x: x['score'], reverse=True)
            self.results['strategy3'].sort(key=lambda x: x['score'], reverse=True)
            
            print(f"\n✅ 스캔 완료!")
            print(f"  전략1 (그레이엄): {len(self.results['strategy1'])}개")
            print(f"  전략2 (퀄리티): {len(self.results['strategy2'])}개")
            print(f"  전략3 (배당): {len(self.results['strategy3'])}개")
            
        finally:
            self.close_db()
        
        return self.results
    
    def save_results(self, timestamp: str = None):
        """결과 저장"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # numpy bool을 Python bool로 변환
        def convert_bools(obj):
            if isinstance(obj, dict):
                return {k: convert_bools(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_bools(item) for item in obj]
            elif isinstance(obj, (np.bool_, np.bool)):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            return obj
        
        results_clean = convert_bools(self.results)
        
        # JSON 저장
        json_path = f'./reports/buffett_scan_{timestamp}.json'
        os.makedirs('./reports', exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results_clean, f, ensure_ascii=False, indent=2)
        
        # CSV 저장
        for strategy_key, strategy_name in [
            ('strategy1', 'graham'), 
            ('strategy2', 'quality'), 
            ('strategy3', 'dividend')
        ]:
            if self.results[strategy_key]:
                df = pd.DataFrame(self.results[strategy_key])
                csv_path = f'./reports/buffett_{strategy_name}_{timestamp}.csv'
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 결과 저장 완료:")
        print(f"  JSON: {json_path}")
        print(f"  CSV: ./reports/buffett_*_{timestamp}.csv")
        
        return timestamp


def main():
    """메인 실행"""
    scanner = BuffettIntegratedScanner()
    results = scanner.run_full_scan()
    timestamp = scanner.save_results()
    
    # 상위 종목 출력
    print("\n" + "=" * 60)
    print("📊 상위 선정 종목")
    print("=" * 60)
    
    for strategy_name, stocks in [
        ("그레이엄 순유동자산", results['strategy1'][:5]),
        ("퀄리티 적정가", results['strategy2'][:5]),
        ("배당성장", results['strategy3'][:5])
    ]:
        print(f"\n🎯 {strategy_name} TOP 5")
        for i, stock in enumerate(stocks, 1):
            print(f"  {i}. {stock['name']} ({stock['symbol']}) - {stock['score']}점")
    
    return timestamp


if __name__ == '__main__':
    main()
