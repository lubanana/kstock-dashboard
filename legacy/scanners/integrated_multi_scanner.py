#!/usr/bin/env python3
"""
Integrated Multi-Strategy Scanner
V-Strategy + B01 + NPS 통합 스캐너
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import json
from pathlib import Path
import sys
sys.path.insert(0, '.')
from fdr_wrapper import get_price


class IntegratedMultiStrategyScanner:
    """
    4가지 전략 통합 스캐너:
    1. V-Strategy (Value + Fibonacci + ATR)
    2. B01 (Buffett Value)
    3. NPS (Net Purchase Strength)
    4. Multi-Strategy (Composite Score)
    """
    
    def __init__(self, symbols: List[str] = None):
        # 전체 코스피/코스닥 대형주
        self.symbols = symbols or self._load_all_symbols()
        self.results = {
            'V': [],
            'B01': [],
            'NPS': [],
            'Multi': []
        }
    
    def _load_all_symbols(self) -> List[str]:
        """DB에서 전체 종목 리스트 로드"""
        import sqlite3
        conn = sqlite3.connect('data/pivot_strategy.db')
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT symbol FROM stock_prices WHERE date = ?', ('2026-03-20',))
        symbols = [row[0] for row in cursor.fetchall()]
        conn.close()
        print(f"DB에서 {len(symbols)}개 종목 로드 완료")
        return symbols
    
    def fetch_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """종목 데이터 조회"""
        try:
            end_date = datetime(2026, 3, 20)
            start_date = end_date - timedelta(days=days)
            
            df = get_price(
                symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            if df.empty or len(df) < 20:
                return pd.DataFrame()
            
            df.columns = [c.lower() for c in df.columns]
            return df
            
        except Exception as e:
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """공통 기술적 지표 계산"""
        # 이동평균
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema60'] = df['close'].ewm(span=60, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df
    
    def calculate_v_score(self, df: pd.DataFrame) -> Dict:
        """V-Strategy 점수 계산 - 세부 점수 포함"""
        latest = df.iloc[-1]
        
        # 가치 점수 (Fibonacci 기반)
        fib_high = df['high'].rolling(20).max().iloc[-1]
        fib_low = df['low'].rolling(20).min().iloc[-1]
        current = latest['close']
        
        # 38.2% ~ 50% retracement zone이 진입 영역
        fib_382 = fib_high - 0.382 * (fib_high - fib_low)
        fib_50 = fib_high - 0.5 * (fib_high - fib_low)
        
        fib_score = 0
        if fib_50 <= current <= fib_382:
            fib_score = 70 + (fib_382 - current) / (fib_382 - fib_50) * 15 if (fib_382 - fib_50) > 0 else 70
        elif current < fib_50:
            fib_score = 50 + (current - fib_low) / (fib_50 - fib_low) * 20 if (fib_50 - fib_low) > 0 else 50
        else:
            fib_score = 40 + (fib_high - current) / (fib_high - fib_382) * 30 if (fib_high - fib_382) > 0 else 40
        
        # Trend 점수 (추세 확인)
        trend_score = 0
        if latest['close'] > latest['ema20']:
            trend_score += 15
        if latest['ema20'] > df['ema60'].iloc[-1]:
            trend_score += 15
        
        total_score = min(100, max(0, (fib_score + trend_score) / 2 + 15))
        
        return {
            'score': total_score,
            'fib_score': min(100, max(0, fib_score)),
            'trend_score': trend_score,
            'fib_level': 'fib_50' if current < fib_50 else 'fib_382',
            'fib_high': fib_high,
            'fib_low': fib_low,
            'atr': latest['atr']
        }
    
    def calculate_b01_score(self, df: pd.DataFrame) -> Dict:
        """B01 Buffett 점수 계산"""
        # 장기 추세 먼저 계산
        df['ma60'] = df['close'].rolling(60).mean()
        df['ma120'] = df['close'].rolling(120).mean()
        
        latest = df.iloc[-1]
        
        score = 0
        trend_score = 0
        if latest['close'] > latest['ma60']:
            score += 30
            trend_score += 30
        if latest['close'] > df['ma120'].iloc[-1]:
            score += 20
            trend_score += 20
        
        # 변동성
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100
        volatility_score = 0
        if volatility < 30:
            score += 25
            volatility_score = 25
        elif volatility < 40:
            score += 15
            volatility_score = 15
        
        # 수익성
        return_score = 0
        if len(df) >= 60:
            yoy = (latest['close'] - df['close'].iloc[-60]) / df['close'].iloc[-60] * 100
            if yoy > 10:
                score += 25
                return_score = 25
            elif yoy > 0:
                score += 15
                return_score = 15
        
        return {
            'score': score,
            'trend_score': trend_score,
            'volatility_score': volatility_score,
            'return_score': return_score,
            'volatility': volatility,
            'yoy_return': yoy if len(df) >= 60 else 0,
            'atr': latest['atr']
        }
    
    def calculate_nps_score(self, df: pd.DataFrame) -> Dict:
        """NPS 점수 계산 - 세부 점수 포함"""
        latest = df.iloc[-1]
        
        score = 0
        
        # 추세 점수 (최대 40점)
        trend_score = 0
        if latest['close'] > latest['ema20']:
            score += 25
            trend_score += 25
        if latest['ema20'] > df['ema60'].iloc[-1]:
            score += 15
            trend_score += 15
        
        # 모멘텀 점수 (RSI, 최대 35점)
        momentum_score = 0
        if 50 <= latest['rsi'] <= 60:
            score += 35
            momentum_score = 35
        elif 45 <= latest['rsi'] < 50:
            score += 30
            momentum_score = 30
        elif 40 <= latest['rsi'] < 45:
            score += 20
            momentum_score = 20
        elif 35 <= latest['rsi'] < 40:
            score += 10
            momentum_score = 10
        
        # 거래량 점수 (최대 25점)
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        volume_score = 0
        if avg_vol > 0:
            vol_ratio = latest['volume'] / avg_vol
            if vol_ratio > 1.5:
                score += 25
                volume_score = 25
            elif vol_ratio > 1.2:
                score += 20
                volume_score = 20
            elif vol_ratio > 1.0:
                score += 15
                volume_score = 15
            elif vol_ratio > 0.8:
                score += 10
                volume_score = 10
        
        return {
            'score': score,
            'trend_score': trend_score,
            'momentum_score': momentum_score,
            'volume_score': volume_score,
            'rsi': latest['rsi'],
            'volume_ratio': latest['volume'] / avg_vol if avg_vol > 0 else 0,
            'atr': latest['atr']
        }
    
    def calculate_atr_targets(self, current_price: float, atr: float, rr: float = 2.0) -> Dict:
        """ATR 기반 목표가/손절가 계산 - 실제 손익비 반환"""
        sl_multiplier = 1.5
        tp_multiplier = sl_multiplier * rr
        
        stop_loss = current_price - (atr * sl_multiplier)
        target_price = current_price + (atr * tp_multiplier)
        
        # 실제 손익비 계산
        potential_gain = target_price - current_price
        potential_loss = current_price - stop_loss
        actual_rr = potential_gain / potential_loss if potential_loss > 0 else rr
        
        return {
            'entry': round(current_price, 0),
            'stop_loss': round(stop_loss, 0),
            'target': round(target_price, 0),
            'rr_ratio': round(actual_rr, 2),
            'atr': round(atr, 2)
        }
    
    def scan(self) -> Dict:
        """전체 스캔 실행"""
        print("=" * 70)
        print("🔍 통합 멀티 전략 스캐너")
        print("=" * 70)
        print(f"대상 종목: {len(self.symbols)}개")
        print("-" * 70)
        
        for i, symbol in enumerate(self.symbols, 1):
            if i % 10 == 0:
                print(f"   진행: {i}/{len(self.symbols)}")
            
            df = self.fetch_data(symbol)
            if df.empty:
                continue
            
            df = self.calculate_indicators(df)
            latest = df.iloc[-1]
            current_price = latest['close']
            
            # V-Strategy - 점수 기준 70점 이상, 상위 10개만
            v_result = self.calculate_v_score(df)
            if v_result['score'] >= 70:
                targets = self.calculate_atr_targets(current_price, v_result['atr'])
                self.results['V'].append({
                    'symbol': symbol,
                    'name': self._get_name(symbol),
                    'score': v_result['score'],
                    'fib_score': v_result.get('fib_score', 0),
                    'trend_score': v_result.get('trend_score', 0),
                    'current_price': current_price,
                    'target_price': targets['target'],
                    'stop_loss': targets['stop_loss'],
                    'rr_ratio': targets['rr_ratio'],
                    'atr': v_result['atr'],
                    'fib_level': v_result['fib_level'],
                    'strategy': 'V-Strategy'
                })
            
            # B01 - 점수 기준 65점 이상
            b01_result = self.calculate_b01_score(df)
            if b01_result['score'] >= 65:
                targets = self.calculate_atr_targets(current_price, b01_result['atr'])
                self.results['B01'].append({
                    'symbol': symbol,
                    'name': self._get_name(symbol),
                    'score': b01_result['score'],
                    'trend_score': b01_result.get('trend_score', 0),
                    'volatility_score': b01_result.get('volatility_score', 0),
                    'return_score': b01_result.get('return_score', 0),
                    'current_price': current_price,
                    'target_price': targets['target'],
                    'stop_loss': targets['stop_loss'],
                    'rr_ratio': targets['rr_ratio'],
                    'atr': b01_result['atr'],
                    'volatility': b01_result['volatility'],
                    'strategy': 'B01'
                })
            
            # NPS - 점수 기준 70점 이상
            nps_result = self.calculate_nps_score(df)
            if nps_result['score'] >= 70:
                targets = self.calculate_atr_targets(current_price, nps_result['atr'])
                self.results['NPS'].append({
                    'symbol': symbol,
                    'name': self._get_name(symbol),
                    'score': nps_result['score'],
                    'trend_score': nps_result.get('trend_score', 0),
                    'momentum_score': nps_result.get('momentum_score', 0),
                    'volume_score': nps_result.get('volume_score', 0),
                    'current_price': current_price,
                    'target_price': targets['target'],
                    'stop_loss': targets['stop_loss'],
                    'rr_ratio': targets['rr_ratio'],
                    'atr': nps_result['atr'],
                    'rsi': nps_result['rsi'],
                    'strategy': 'NPS'
                })
            
            # Multi-Strategy - 평균 65점 이상
            multi_score = (v_result['score'] + b01_result['score'] + nps_result['score']) / 3
            if multi_score >= 65:
                targets = self.calculate_atr_targets(current_price, latest['atr'])
                self.results['Multi'].append({
                    'symbol': symbol,
                    'name': self._get_name(symbol),
                    'score': multi_score,
                    'v_score': v_result['score'],
                    'b01_score': b01_result['score'],
                    'nps_score': nps_result['score'],
                    'current_price': current_price,
                    'target_price': targets['target'],
                    'stop_loss': targets['stop_loss'],
                    'rr_ratio': targets['rr_ratio'],
                    'atr': latest['atr'],
                    'strategy': 'Multi'
                })
        
        # 정렬 (동점 시 세부 점수로 구분)
        for key in self.results:
            if key == 'V':
                # V: 총점 → Fib 점수 → Trend 점수
                self.results[key].sort(key=lambda x: (x['score'], x.get('fib_score', 0), x.get('trend_score', 0)), reverse=True)
            elif key == 'B01':
                # B01: 총점 → 변동성 점수 → 수익률 점수
                self.results[key].sort(key=lambda x: (x['score'], x.get('volatility_score', 0), x.get('return_score', 0)), reverse=True)
            elif key == 'NPS':
                # NPS: 총점 → 모멘텀 점수 → 거래량 점수
                self.results[key].sort(key=lambda x: (x['score'], x.get('momentum_score', 0), x.get('volume_score', 0)), reverse=True)
            elif key == 'Multi':
                # Multi: 총점 → V 점수 → NPS 점수
                self.results[key].sort(key=lambda x: (x['score'], x['v_score'], x['nps_score']), reverse=True)
            
            # 상위 10개만 선택
            self.results[key] = self.results[key][:10]
        
        return self.results
    
    def _get_name(self, symbol: str) -> str:
        """종목명 조회 - 확장된 매핑"""
        names = {
            # 코스피 대형주
            '005930': '삼성전자', '000660': 'SK하이닉스', '051910': 'LG화학',
            '005380': '현대차', '035720': '카카오', '068270': '셀트리온',
            '207940': '삼성바이오로직스', '006400': '삼성SDI', '000270': '기아',
            '012330': '현대모비스', '005490': 'POSCO홀딩스', '028260': '삼성물산',
            '105560': 'KB금융', '018260': '삼성에스디에스', '032830': '삼성생명',
            '034730': 'SK', '000150': '두산', '016360': '삼성증권',
            '009830': '한화솔루션', '003490': '대한항공', '004170': '신세계',
            '000100': '유한양행', '011200': 'HMM', '030200': 'KT',
            '010950': 'S-Oil', '034220': 'LG디스플레이', '086790': '하나금융지주',
            '055550': '신한지주', '047050': '포스코DX', '032640': 'LG유플러스',
            '009540': '삼성전기', '030000': '제일제당', '018880': '한온시스템',
            '000810': '삼성화재', '024110': '기업은행', '005940': 'NH투자증권',
            '010140': '삼성중공업', '001040': 'CJ', '003550': 'LG',
            '008770': '호텔신라', '007310': '오뚜기', '006800': '미래에셋증권',
            '000120': 'CJ대한통운', '001120': 'LG이노텍', '010130': '고려아연',
            '002790': '아모레퍼시픽', '001800': '오리온', '003000': '포스코인터내셔널',
            '005420': '코스모화학',
            # 코스닥 대형주
            '247540': '에코프로', '086520': '에코프로비엠', '091990': '셀트리온헬스케어',
            '035900': 'JYP Ent.', '293490': '카카오게임즈', '263750': '펄어비스',
            '151860': '바이로메드', '196170': '알테오젠', '214150': '큐라클',
            '221840': '크래프톤', '183490': '아미코젠', '095340': 'ISC',
            '100090': '삼강엠앤티', '137310': '에스디바이오센서', '058470': '리노공업',
            '048260': '오스템임플란트', '042000': '카페24', '041140': '넥슨게임즈',
            '025980': '아난티', '014990': '인디에프', '039030': '오션브릿지',
            # 추가 종목
            '000020': '동화약품', '000040': 'KR모터스', '000050': '경방',
            '000070': '삼양홀딩스', '000080': '하이트진로', '000140': '하이트진로홀딩스',
            '000180': '성창기업지주', '000210': 'DL', '000240': '한국테크놀로지',
            '000250': '삼천당제약', '000300': '대유플러스', '000320': '노서아',
            '000370': '한화손핳보험', '000400': '롯데손핳보험', '000430': '대원강업',
            '000480': '조선내화', '000490': '대동공업', '000500': '가온전선',
            '000520': '삼일제약', '000540': '흥국화재', '000590': 'CS홀딩스',
            '000640': '동아쏘시오홀딩스', '000650': '천일고속', '000670': '영풍',
            '000680': '유수홀딩스', '000700': '유수홀딩스우', '000720': '현대건설',
            '000725': '현대건설우', '000760': '삼성증권우', '000810': '삼성화재',
            '000815': '삼성화재우', '000850': '화천기공', '000860': '강남제비스코',
            '000880': '한화', '000885': '한화우', '000890': '보해양조',
            '000910': '유니온', '000950': '전방', '000970': '한국주철관',
            '000990': 'DB하이텍', '001020': '페이퍼코리아', '001040': 'CJ',
            '001060': 'JW중외제약', '001065': 'JW중외제약우', '001070': '대한방직',
            '001130': '대한제당', '001200': '유진투자증권', '001210': '우리은행',
            '001230': '동국제강', '001250': 'GS글로벌', '001260': '남광토건',
            '001270': '부국증권', '001280': '대창', '001290': '상상인증권',
            '001330': '삼성공조', '001340': '백광소재', '001360': '삼성제약',
            '001380': 'SG세계물산', '001390': 'KB캐피탈', '001430': '세아베스틸',
            '001440': '대한전선', '001450': '현대해상', '001460': 'BYC',
            '001465': 'BYC우', '001470': '삼부토건', '001500': '현대차증권',
            '001510': 'SK증권', '001520': '동양', '001550': '조비',
            '001560': '제일연마', '001570': '금양', '001620': '케이비아이동국증권',
            # 추가 종목 (결과에 나타난 종목들)
            '049720': '고려신용정보', '139480': '이마트', '154030': '아이윈',
            '001750': '한양증권', '002870': '신풍', '003300': '한일홀딩스',
            '049770': '대우증권', '049800': '우진플라임', '002600': '조흥',
            '001515': 'SK증권우', '002210': '동성제약', '002220': '한일철관',
            '002240': '고려제강', '002270': '기신정기', '002600': '조흥',
        }
        return names.get(symbol, symbol)
    
    def save_results(self):
        """결과 저장"""
        output_dir = Path('./reports/multi_strategy')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for strategy, stocks in self.results.items():
            output_file = output_dir / f'{strategy.lower()}_scan_20260320.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'scan_date': '2026-03-20',
                    'strategy': strategy,
                    'selected_count': len(stocks),
                    'stocks': stocks
                }, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n💾 결과 저장 완료")
        print(f"   V-Strategy: {len(self.results['V'])}개")
        print(f"   B01: {len(self.results['B01'])}개")
        print(f"   NPS: {len(self.results['NPS'])}개")
        print(f"   Multi: {len(self.results['Multi'])}개")


def main():
    scanner = IntegratedMultiStrategyScanner()
    results = scanner.scan()
    scanner.save_results()
    
    print("\n" + "=" * 70)
    print("📊 스캔 완료 요약")
    print("=" * 70)
    for strategy, stocks in results.items():
        print(f"   {strategy}: {len(stocks)}개 종목")
        if stocks:
            print(f"      TOP: {stocks[0]['name']} ({stocks[0]['score']:.1f}점)")


if __name__ == '__main__':
    main()
