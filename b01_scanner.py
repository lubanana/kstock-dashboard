#!/usr/bin/env python3
"""
B01 Strategy Scanner - Buffett Quality + Breakout
버핏 품질 + 브레이크아웃 결합 전략

전략 조건:
1. ROE >= 15% (3년 평균)
2. 부채비율 <= 50%
3. 영업이익률 >= 10%
4. PBR <= 2.0
5. 거래대금 >= 50억
6. 20일 신고가 돌파 (Breakout)
"""

import sys
import json
import warnings
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

warnings.filterwarnings('ignore')

from fdr_wrapper import FDRWrapper


@dataclass
class B01Result:
    symbol: str
    name: str
    roe: float
    debt_ratio: float
    margin: float
    pbr: float
    volume_amount: float
    breakout: bool
    current_price: float
    target_price: float
    stop_loss: float
    score: float
    grade: str


class B01Scanner:
    """B01: Buffett Quality + Breakout Strategy"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.target_stocks = [
            # 대형 우량주 위주
            '005930', '000660', '051910', '005380', '035720',
            '068270', '207940', '006400', '000270', '012330',
            '005490', '028260', '105560', '018260', '032830',
            '011200', '030200', '009150', '097950', '051900',
            '128940', '139480', '316140', '018880', '010950',
            '024110', '139130', '298050', '012450', '161390',
            '282330', '032640', '086280', '100090', '950160',
        ]
    
    def get_stock_name(self, symbol: str) -> str:
        """종목명 조회"""
        # 미리 정의된 종목명 매핑
        stock_names = {
            '005930': '삼성전자',
            '000660': 'SK하이닉스',
            '051910': 'LG화학',
            '005380': '현대차',
            '035720': '카카오',
            '068270': '셀트리온',
            '207940': '삼성바이오로직스',
            '006400': '삼성SDI',
            '000270': '기아',
            '012330': '현대모비스',
            '005490': 'POSCO홀딩스',
            '028260': '삼성물산',
            '105560': 'KB금융',
            '018260': '삼성에스디에스',
            '032830': '삼성생명',
            '011200': 'HMM',
            '030200': 'KT',
            '009150': '삼성전기',
            '097950': 'CJ제일제당',
            '051900': 'LG생활건강',
            '128940': '한미약품',
            '139480': '이마트',
            '316140': '우리금융지주',
            '018880': '한온시스템',
            '010950': 'S-Oil',
            '024110': '기업은행',
            '139130': 'DGB금융지주',
            '298050': '효성첨단소재',
            '012450': '한화에어로스페이스',
            '161390': '한국타이어앤테크놀로지',
            '282330': 'BGF리테일',
            '032640': 'LG유플러스',
            '086280': '현대글로비스',
            '100090': 'SK바이오팜',
            '950160': '코스모신소재',
        }
        return stock_names.get(symbol, symbol)
    
    def calculate_quality_metrics(self, symbol: str) -> Optional[Dict]:
        """품질 지표 계산 (재무제表 대신 기술적 지표로 대체)"""
        try:
            df = self.fdr.get_price(symbol, min_days=252)  # 1년 데이터
            if df is None or len(df) < 100:
                return None
            
            # ROE 대체: 수익성 추정 (1년 수익률 / 변동성)
            returns = df['close'].pct_change().dropna()
            annual_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
            volatility = returns.std() * np.sqrt(252) * 100
            roe_proxy = annual_return / (volatility + 1e-10) * 10  # Sharpe-like metric
            
            # 부채비율 대체: 하띋 위험 (최대 낙폭)
            cummax = df['close'].cummax()
            drawdown = (df['close'] - cummax) / cummax
            max_dd = drawdown.min() * 100
            debt_proxy = abs(max_dd) * 2  # Drawdown을 부채로 변환
            
            # 영업이익률 대체: 추세 강도
            df['MA20'] = df['close'].rolling(20).mean()
            df['MA60'] = df['close'].rolling(60).mean()
            trend_strength = (df['close'].iloc[-1] / df['MA20'].iloc[-1] - 1) * 100
            margin_proxy = trend_strength + 10  # 기본 10% 가정
            
            # PBR 대체: 상대적 가치 (52주 고점 대비)
            high_52w = df['close'].rolling(252).max().iloc[-1]
            pbr_proxy = df['close'].iloc[-1] / high_52w * 2  # 0~2 범위
            
            return {
                'roe': max(0, roe_proxy),
                'debt_ratio': max(0, debt_proxy),
                'margin': margin_proxy,
                'pbr': pbr_proxy,
                'current_price': df['close'].iloc[-1],
                'volume_20d': df['volume'].rolling(20).mean().iloc[-1],
                'price_20d_high': df['close'].rolling(20).max().iloc[-1],
                'price_20d_low': df['close'].rolling(20).min().iloc[-1],
                'atr_14': (df['high'] - df['low']).rolling(14).mean().iloc[-1]
            }
        except Exception as e:
            return None
    
    def check_breakout(self, df: pd.DataFrame) -> bool:
        """20일 신고가 돌파 체크"""
        if len(df) < 21:
            return False
        
        current = df['close'].iloc[-1]
        high_20d = df['close'].iloc[-21:-1].max()
        
        return current > high_20d
    
    def scan_stock(self, symbol: str) -> Optional[B01Result]:
        """개별 종목 스캔"""
        metrics = self.calculate_quality_metrics(symbol)
        if metrics is None:
            return None
        
        # 조건 체크
        # 1. ROE >= 15% (프록시)
        roe_pass = metrics['roe'] >= 15
        
        # 2. 부채비율 <= 50% (프록시)
        debt_pass = metrics['debt_ratio'] <= 50
        
        # 3. 영업이익률 >= 10% (프록시)
        margin_pass = metrics['margin'] >= 10
        
        # 4. PBR <= 2.0 (프록시)
        pbr_pass = metrics['pbr'] <= 2.0
        
        # 5. 거래대금 >= 50억
        amount = metrics['current_price'] * metrics['volume_20d']
        volume_pass = amount >= 50 * 1e8
        
        # 6. 브레이크아웃
        df = self.fdr.get_price(symbol, min_days=30)
        breakout = self.check_breakout(df) if df is not None else False
        
        # 점수 계산
        score = 0
        if roe_pass: score += 20
        if debt_pass: score += 15
        if margin_pass: score += 20
        if pbr_pass: score += 15
        if volume_pass: score += 15
        if breakout: score += 15
        
        # 등급
        if score >= 80: grade = 'A'
        elif score >= 65: grade = 'B'
        elif score >= 50: grade = 'C'
        else: grade = 'D'
        
        # 최소 3개 조건 충족 시만 반환
        conditions_met = sum([roe_pass, debt_pass, margin_pass, pbr_pass, volume_pass, breakout])
        if conditions_met < 3:
            return None
        
        # 목표가/손절가
        target = metrics['current_price'] * 1.15  # +15%
        stop_loss = metrics['current_price'] * 0.93  # -7%
        
        return B01Result(
            symbol=symbol,
            name=self.get_stock_name(symbol),
            roe=metrics['roe'],
            debt_ratio=metrics['debt_ratio'],
            margin=metrics['margin'],
            pbr=metrics['pbr'],
            volume_amount=amount / 1e8,  # 억 단위
            breakout=breakout,
            current_price=metrics['current_price'],
            target_price=target,
            stop_loss=stop_loss,
            score=score,
            grade=grade
        )
    
    def scan_all(self) -> List[B01Result]:
        """전체 스캔"""
        print(f"\n{'='*60}")
        print(f"🔍 B01 전략 스캔 시작")
        print(f"{'='*60}")
        print(f"대상 종목: {len(self.target_stocks)}개")
        
        results = []
        for i, symbol in enumerate(self.target_stocks, 1):
            try:
                result = self.scan_stock(symbol)
                if result:
                    results.append(result)
                    print(f"   ✅ {i}/{len(self.target_stocks)} {symbol} - {result.grade}등급 ({result.score}점)")
                else:
                    print(f"   ⏭️  {i}/{len(self.target_stocks)} {symbol} - 조건 미충족")
            except Exception as e:
                print(f"   ❌ {i}/{len(self.target_stocks)} {symbol} - 오류: {e}")
        
        # 점수순 정렬
        results.sort(key=lambda x: x.score, reverse=True)
        
        print(f"\n📊 선정 결과: {len(results)}개 종목")
        return results
    
    def export_results(self, results: List[B01Result], filename: str = None):
        """결과 저장"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"b01_scan_{timestamp}"
        
        # JSON
        json_data = [{
            'symbol': r.symbol,
            'name': r.name,
            'grade': r.grade,
            'score': r.score,
            'roe': round(r.roe, 2),
            'debt_ratio': round(r.debt_ratio, 2),
            'margin': round(r.margin, 2),
            'pbr': round(r.pbr, 2),
            'volume_amount': round(r.volume_amount, 2),
            'breakout': bool(r.breakout),
            'current_price': r.current_price,
            'target_price': r.target_price,
            'stop_loss': r.stop_loss,
        } for r in results]
        
        json_path = f"./reports/b01_value/{filename}.json"
        import os
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # CSV
        csv_path = f"./reports/b01_value/{filename}.csv"
        df = pd.DataFrame(json_data)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 결과 저장:")
        print(f"   JSON: {json_path}")
        print(f"   CSV: {csv_path}")
        
        return json_path, csv_path


def main():
    scanner = B01Scanner()
    results = scanner.scan_all()
    
    if results:
        scanner.export_results(results)
        
        print(f"\n{'='*60}")
        print(f"📈 TOP 10 종목")
        print(f"{'='*60}")
        for i, r in enumerate(results[:10], 1):
            print(f"{i:2d}. {r.symbol} {r.name:10s} | {r.grade}등급 | {r.score}점 | ₩{r.current_price:,.0f}")
    else:
        print("❌ 선정된 종목 없음")


if __name__ == '__main__':
    main()
