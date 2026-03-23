#!/usr/bin/env python3
"""
Korea Value Stock Scanner - 저평가 종목 발굴 시스템
=====================================================
기존 전략 차용:
- V-Series: Value Score (PER, PBR 기반)
- B01: 버핏 가치투자 원칙 (안정성 + 수익성)
- Ultimate Screener: 기술적 모멘텀 + 유동성 필터
- NPS: 추세 확인 + 리스크 관리

점수 체계: 1000점 (가치평가 400점 + 재무건전성 300점 + 모멘텀 200점 + 리스크 100점)
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys
import os

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)


class ValueStockScanner:
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.stock_names = self._load_names()
        
        # 재무 데이터 캐시 (실제로는 DART API 또는 FnGuide에서 수집)
        self.fundamental_cache = self._load_fundamental_data()
    
    def _load_names(self):
        names = {}
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT symbol, name FROM stock_info')
            for row in cursor.fetchall():
                names[row[0]] = row[1]
        except:
            pass
        
        defaults = {
            '000440': '중앙에너비스', 'BYC': 'BYC', '000250': '삼천당제약',
            '000490': '대동공업', '003350': '기산텔레콤', '001750': '한양증권',
            '001515': 'SK증권우', '154030': '아이윈', '139480': '이마트',
            '049720': '고려신용정보', '002870': '신풍', '005930': '삼성전자',
            '051600': '한전KPS', '036190': '금화피에스시', '117700': '건설'
        }
        names.update(defaults)
        return names
    
    def _load_fundamental_data(self):
        """재무 데이터 로드 (캐시 또는 DB에서)"""
        # 실제 환경에서는 DART API 또는 기존 DB의 fundamental 테이블 사용
        fund_data = {}
        cursor = self.conn.cursor()
        
        try:
            # stock_info 테이블에서 기본 정보 로드 시도
            cursor.execute('''
                SELECT symbol, market_cap, per, pbr, eps, bps 
                FROM stock_info 
                WHERE per IS NOT NULL OR pbr IS NOT NULL
            ''')
            for row in cursor.fetchall():
                fund_data[row[0]] = {
                    'market_cap': row[1] or 0,
                    'per': row[2] or 99.9,
                    'pbr': row[3] or 9.9,
                    'eps': row[4] or 0,
                    'bps': row[5] or 0
                }
        except:
            pass
        
        return fund_data
    
    def get_price(self, symbol, days=252):
        """가격 데이터 로드 (1년)"""
        query = '''SELECT date, open, high, low, close, volume 
                   FROM stock_prices WHERE symbol = ? 
                   AND date >= date('now', '-{} days') ORDER BY date'''.format(days)
        df = pd.read_sql_query(query, self.conn, params=(symbol,))
        if df.empty or len(df) < 60:
            return None
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    
    def calc_technical_indicators(self, df):
        """기술적 지표 계산"""
        if len(df) < 60:
            return None
        
        # 추세 지표
        df['ema20'] = df['close'].ewm(span=20).mean()
        df['ema60'] = df['close'].ewm(span=60).mean()
        df['ema120'] = df['close'].ewm(span=120).mean()
        df['sma200'] = df['close'].rolling(200).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain / loss))
        
        # 변동성
        df['returns'] = df['close'].pct_change()
        df['volatility_20d'] = df['returns'].rolling(20).std() * np.sqrt(252) * 100
        df['volatility_60d'] = df['returns'].rolling(60).std() * np.sqrt(252) * 100
        
        # 거래량
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma20']
        
        # ATR
        df['tr'] = np.maximum(df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                      abs(df['low'] - df['close'].shift(1))))
        df['atr14'] = df['tr'].rolling(14).mean()
        
        return df
    
    def estimate_fundamentals(self, symbol, price, df):
        """재무 지표 추정 (가격 데이터 기반)"""
        fund = self.fundamental_cache.get(symbol, {})
        
        # 캐시에 없으면 기본값 사용 (향후 DART 연동 필요)
        if not fund:
            # 거래대금 기반 시가총액 추정 (rough estimate)
            avg_volume = df['volume'].tail(20).mean()
            est_market_cap = price * avg_volume * 252 / 1e8  # rough estimate
            
            return {
                'per': 15.0,  # 시장 평균 가정
                'pbr': 1.0,
                'roe': 10.0,
                'market_cap': est_market_cap,
                'debt_ratio': 100.0,
                'is_estimated': True
            }
        
        return {
            'per': fund.get('per', 15.0),
            'pbr': fund.get('pbr', 1.0),
            'roe': fund.get('roe', 10.0),
            'market_cap': fund.get('market_cap', 0),
            'debt_ratio': fund.get('debt_ratio', 100.0),
            'is_estimated': False
        }
    
    def score_value(self, fund, price, df):
        """가치평가 점수 (0-400점)"""
        score = 0
        details = {}
        
        # 1. PER 기반 점수 (0-150점) - 낮을수록 좋음
        per = fund.get('per', 99.9)
        if per < 0:  # 적자기업
            per_score = 0
        elif per < 5:
            per_score = 150
        elif per < 8:
            per_score = 120
        elif per < 10:
            per_score = 100
        elif per < 12:
            per_score = 80
        elif per < 15:
            per_score = 60
        elif per < 20:
            per_score = 40
        elif per < 30:
            per_score = 20
        else:
            per_score = 0
        score += per_score
        details['per'] = {'value': per, 'score': per_score}
        
        # 2. PBR 기반 점수 (0-100점) - 낮을수록 좋음
        pbr = fund.get('pbr', 9.9)
        if pbr < 0:
            pbr_score = 0
        elif pbr < 0.5:
            pbr_score = 100
        elif pbr < 0.8:
            pbr_score = 80
        elif pbr < 1.0:
            pbr_score = 60
        elif pbr < 1.5:
            pbr_score = 40
        elif pbr < 2.0:
            pbr_score = 20
        else:
            pbr_score = 0
        score += pbr_score
        details['pbr'] = {'value': pbr, 'score': pbr_score}
        
        # 3. ROE 기반 점수 (0-100점) - 높을수록 좋음
        roe = fund.get('roe', 0)
        if roe > 20:
            roe_score = 100
        elif roe > 15:
            roe_score = 80
        elif roe > 12:
            roe_score = 60
        elif roe > 8:
            roe_score = 40
        elif roe > 5:
            roe_score = 20
        else:
            roe_score = 0
        score += roe_score
        details['roe'] = {'value': roe, 'score': roe_score}
        
        # 4. 52주 변동성 대비 현재 위치 (0-50점)
        if len(df) >= 252:
            high_52w = df['high'].tail(252).max()
            low_52w = df['low'].tail(252).min()
            if high_52w > low_52w:
                position = (price - low_52w) / (high_52w - low_52w)
                if position < 0.3:  # 저점 대비 30% 이내
                    position_score = 50
                elif position < 0.5:
                    position_score = 30
                else:
                    position_score = 0
                score += position_score
                details['position_52w'] = {'value': position, 'score': position_score}
        
        return min(score, 400), details
    
    def score_financial_health(self, fund):
        """재무건전성 점수 (0-300점)"""
        score = 0
        details = {}
        
        # 1. 부채비율 (0-100점) - 낮을수록 좋음
        debt_ratio = fund.get('debt_ratio', 100)
        if debt_ratio < 50:
            debt_score = 100
        elif debt_ratio < 100:
            debt_score = 80
        elif debt_ratio < 150:
            debt_score = 60
        elif debt_ratio < 200:
            debt_score = 40
        elif debt_ratio < 300:
            debt_score = 20
        else:
            debt_score = 0
        score += debt_score
        details['debt_ratio'] = {'value': debt_ratio, 'score': debt_score}
        
        # 2. 시가총액 규모 (0-100점) - 중대형주 선호 (안정성)
        market_cap = fund.get('market_cap', 0)
        if market_cap > 10000:  # 1조 이상 (대형)
            cap_score = 100
        elif market_cap > 3000:  # 3천억 이상 (중대형)
            cap_score = 80
        elif market_cap > 1000:  # 1천억 이상 (중형)
            cap_score = 60
        elif market_cap > 500:   # 5백억 이상 (중소형)
            cap_score = 40
        elif market_cap > 100:   # 1백억 이상 (소형)
            cap_score = 20
        else:
            cap_score = 0
        score += cap_score
        details['market_cap'] = {'value': market_cap, 'score': cap_score}
        
        # 3. 이익안정성 (추정) (0-100점)
        # PER < 20 and PBR < 2 일때 가산점
        per = fund.get('per', 99)
        pbr = fund.get('pbr', 9)
        if per < 15 and pbr < 1.5:
            stability_score = 100
        elif per < 20 and pbr < 2:
            stability_score = 70
        elif per < 30 and pbr < 3:
            stability_score = 40
        else:
            stability_score = 0
        score += stability_score
        details['stability'] = {'score': stability_score}
        
        return min(score, 300), details
    
    def score_momentum(self, df):
        """기술적 모멘텀 점수 (0-200점)"""
        score = 0
        details = {}
        latest = df.iloc[-1]
        
        # 1. 추세 방향 (0-80점)
        trend_score = 0
        if latest['close'] > latest['ema20']:
            trend_score += 20
        if latest['ema20'] > latest['ema60']:
            trend_score += 20
        if latest['ema60'] > latest['ema120']:
            trend_score += 20
        if latest['close'] > latest['sma200']:
            trend_score += 20
        score += trend_score
        details['trend'] = {'score': trend_score}
        
        # 2. RSI (0-60점) - 과매도 구간 선호 (반등 가능성)
        rsi = latest['rsi']
        if rsi < 30:
            rsi_score = 60  # 과매도
        elif rsi < 40:
            rsi_score = 50
        elif rsi < 50:
            rsi_score = 40
        elif rsi < 60:
            rsi_score = 20
        else:
            rsi_score = 0
        score += rsi_score
        details['rsi'] = {'value': rsi, 'score': rsi_score}
        
        # 3. 최근 수익률 (0-60점) - 너무 안좋으면 패널티
        if len(df) >= 20:
            ret_20d = (latest['close'] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
            if ret_20d > 20:  # 급등주는 제외 (이미 올랐음)
                ret_score = 0
            elif ret_20d > 10:
                ret_score = 30
            elif ret_20d > 0:
                ret_score = 50
            elif ret_20d > -10:
                ret_score = 60  # 눌림목 선호
            elif ret_20d > -20:
                ret_score = 40
            else:
                ret_score = 10  # 너무 많이 빠진 경우
            score += ret_score
            details['return_20d'] = {'value': ret_20d, 'score': ret_score}
        
        return min(score, 200), details
    
    def score_risk(self, df, fund):
        """리스크 관리 점수 (0-100점)"""
        score = 100  # 만점에서 감점
        details = {}
        latest = df.iloc[-1]
        
        # 1. 변동성 패널티 (0-40점 감점)
        volatility = latest.get('volatility_60d', 30)
        if volatility > 50:
            vol_penalty = 40
        elif volatility > 40:
            vol_penalty = 30
        elif volatility > 30:
            vol_penalty = 15
        elif volatility > 20:
            vol_penalty = 5
        else:
            vol_penalty = 0
        score -= vol_penalty
        details['volatility'] = {'value': volatility, 'penalty': vol_penalty}
        
        # 2. 거래량 유동성 (0-30점 감점)
        vol_ratio = latest['vol_ratio']
        if vol_ratio < 0.3:
            liq_penalty = 30
        elif vol_ratio < 0.5:
            liq_penalty = 15
        else:
            liq_penalty = 0
        score -= liq_penalty
        details['liquidity'] = {'vol_ratio': vol_ratio, 'penalty': liq_penalty}
        
        # 3. 소형주 리스크 (0-30점 감점)
        market_cap = fund.get('market_cap', 0)
        if market_cap < 100:  # 100억 미만
            size_penalty = 30
        elif market_cap < 300:
            size_penalty = 15
        else:
            size_penalty = 0
        score -= size_penalty
        details['size'] = {'market_cap': market_cap, 'penalty': size_penalty}
        
        return max(score, 0), details
    
    def scan_stock(self, symbol):
        """개별 종목 분석"""
        # 가격 데이터 로드
        df = self.get_price(symbol)
        if df is None:
            return None
        
        # 기술적 지표 계산
        df = self.calc_technical_indicators(df)
        if df is None:
            return None
        
        latest = df.iloc[-1]
        price = latest['close']
        name = self.stock_names.get(symbol, symbol)
        
        # 재무 데이터 추정/로드
        fund = self.estimate_fundamentals(symbol, price, df)
        
        # 각 영역 점수 계산
        value_score, value_details = self.score_value(fund, price, df)
        health_score, health_details = self.score_financial_health(fund)
        momentum_score, momentum_details = self.score_momentum(df)
        risk_score, risk_details = self.score_risk(df, fund)
        
        # 총점
        total_score = value_score + health_score + momentum_score + risk_score
        
        # 최소 요건 체크
        if value_score < 100:  # 가치평가가 너무 낮으면 제외
            return None
        
        if risk_score < 50:  # 리스크가 너무 높으면 제외
            return None
        
        # 목표가/손절가 계산
        if latest['atr14'] > 0:
            target = price + latest['atr14'] * 3
            stop_loss = price - latest['atr14'] * 1.5
            rr = (target - price) / (price - stop_loss) if price > stop_loss else 0
        else:
            target = price * 1.12
            stop_loss = price * 0.95
            rr = 2.4
        
        return {
            'symbol': symbol,
            'name': name,
            'price': round(price, 0),
            'score': total_score,
            'scores': {
                'value': value_score,
                'health': health_score,
                'momentum': momentum_score,
                'risk': risk_score
            },
            'fundamentals': {
                'per': round(fund.get('per', 0), 2),
                'pbr': round(fund.get('pbr', 0), 2),
                'roe': round(fund.get('roe', 0), 2),
                'market_cap': round(fund.get('market_cap', 0), 0),
                'is_estimated': fund.get('is_estimated', True)
            },
            'technical': {
                'rsi': round(latest['rsi'], 1),
                'vol_ratio': round(latest['vol_ratio'], 2),
                'volatility': round(latest.get('volatility_60d', 0), 1)
            },
            'target': round(target, 0),
            'stop_loss': round(stop_loss, 0),
            'rr_ratio': round(rr, 2),
            'details': {
                'value': value_details,
                'health': health_details,
                'momentum': momentum_details,
                'risk': risk_details
            }
        }
    
    def scan_all(self):
        """전체 종목 스캔"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT symbol FROM stock_prices WHERE date >= "2025-01-01"')
        symbols = [row[0] for row in cursor.fetchall()]
        
        print(f"총 {len(symbols)}개 종목 분석 시작...")
        print("=" * 70)
        
        results = []
        start_time = datetime.now()
        
        for i, symbol in enumerate(symbols, 1):
            # 진행률 표시
            if i % 100 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                progress = i / len(symbols) * 100
                eta = (elapsed / i) * (len(symbols) - i) / 60
                print(f"  진행: {i}/{len(symbols)} ({progress:.1f}%) | 예상남은시간: {eta:.1f}분")
            
            result = self.scan_stock(symbol)
            if result and result['score'] >= 500:  # 500점 이상만
                results.append(result)
        
        # 점수 순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        
        total_time = (datetime.now() - start_time).total_seconds() / 60
        print(f"\n✅ 스캔 완료: {len(results)}개 종목 발굴 (총 {total_time:.1f}분)")
        
        return results


def main():
    print("=" * 70)
    print("📊 Korea Value Stock Scanner")
    print("=" * 70)
    print("저평가 종목 발굴 시스템 (1000점 체계)")
    print()
    print("점수 구성:")
    print("  • 가치평가 (400점): PER, PBR, ROE, 52주 위치")
    print("  • 재무건전성 (300점): 부채비율, 시총, 안정성")
    print("  • 기술적모멘텀 (200점): 추세, RSI, 수익률")
    print("  • 리스크관리 (100점): 변동성, 유동성, 규모")
    print()
    
    scanner = ValueStockScanner()
    results = scanner.scan_all()
    
    if results:
        print("\n" + "=" * 70)
        print("🏆 TOP 10 저평가 종목")
        print("=" * 70)
        
        for i, r in enumerate(results[:10], 1):
            est_flag = " (추정)" if r['fundamentals']['is_estimated'] else ""
            print(f"\n#{i} {r['name']} ({r['symbol']})")
            print(f"   현재가: {r['price']:,.0f}원 | 총점: {r['score']}/1000점")
            print(f"   PER: {r['fundamentals']['per']:.1f}x | PBR: {r['fundamentals']['pbr']:.1f}x{est_flag}")
            print(f"   세부점수: 가치{r['scores']['value']}+건전성{r['scores']['health']}+모멘텀{r['scores']['momentum']}+리스크{r['scores']['risk']}")
            print(f"   목표가: {r['target']:,.0f}원 | 손절가: {r['stop_loss']:,.0f}원 | 손익비: 1:{r['rr_ratio']:.2f}")
    
    scanner.conn.close()


if __name__ == '__main__':
    main()
