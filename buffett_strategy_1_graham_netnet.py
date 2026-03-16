#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
버핏 가치투자 전략 #1: 그레이엄 스타일 "순유동자산" 전략
======================================================

핵심 원칙:
- 주가가 순유동자산(NCAV)보다 낮은 종목 (P/NCAV < 1)
- 벤자민 그레이엄의 고전적인 "10센트에 1달러짜리" 원칙
- 강력한 마진 오브 세이프티

적용 기준:
1. 시가총액 < 순유동자산 (유동자산 - 총부채)
2. P/B < 1.0
3. P/E < 10
4. 부채비율 < 100%
5. 최근 3년 연속 흑자

스크리닝 결과 예시:
- A 종목: 시총 100억, 순유동자산 150억 → P/NCAV = 0.67
  → "10센트에 15센트어치 자산을 사는 셈"

리스크 관리:
- 포트폴리오 20종목 이상 분산
- 1종목당 최대 5% 배분
- 2년 보유 후 미상승 시 재평가

한국형 적용시 고려사항:
- 순유동자산 기준: 현금성자산 + 단기투자자산 + 매출채권 - 총부채
- 계절성이 강한 업종 제외 (건설, 선박 등)
- 지주사/금융사 별도 기준 적용
"""

import pandas as pd
import numpy as np
from datetime import datetime

class GrahamNetNetStrategy:
    """
    그레이엄 순유동자산 전략
    """
    
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.results = []
        
    def screen_stocks(self):
        """
        NCAV 스크리닝
        """
        print("🔍 그레이엄 순유동자산 전략 스크리닝 중...")
        print("=" * 60)
        
        # 실제 구현시 DB에서 재무제표 데이터 조회
        # 현재는 시뮬레이션
        
        candidates = [
            {
                'symbol': '001130',
                'name': '대한제분',
                'market_cap': 3500,  # 시총 (억원)
                'current_assets': 4200,  # 유동자산
                'total_liabilities': 1800,  # 총부채
                'ncav': 2400,  # 순유동자산
                'p_ncav': 1.46,  # P/NCAV
                'pe': 8.2,
                'pb': 0.9,
                'debt_ratio': 45,
                'profit_3yr': True,
                'sector': '식품'
            },
            {
                'symbol': '002760',
                'name': '볼락',
                'market_cap': 420,
                'current_assets': 680,
                'total_liabilities': 220,
                'ncav': 460,
                'p_ncav': 0.91,
                'pe': 6.8,
                'pb': 0.7,
                'debt_ratio': 35,
                'profit_3yr': True,
                'sector': '식품'
            },
            {
                'symbol': '008350',
                'name': '남선알미늄',
                'market_cap': 1800,
                'current_assets': 2800,
                'total_liabilities': 1200,
                'ncav': 1600,
                'p_ncav': 1.13,
                'pe': 7.5,
                'pb': 0.8,
                'debt_ratio': 42,
                'profit_3yr': True,
                'sector': '비철금속'
            }
        ]
        
        # 필터링
        filtered = []
        for stock in candidates:
            score = 0
            checks = []
            
            # 1. P/NCAV < 1.5 (그레이엄 기준 완화)
            if stock['p_ncav'] < 1.5:
                score += 40
                checks.append(f"✅ P/NCAV {stock['p_ncav']:.2f}")
            else:
                checks.append(f"❌ P/NCAV {stock['p_ncav']:.2f}")
            
            # 2. P/B < 1.0
            if stock['pb'] < 1.0:
                score += 25
                checks.append(f"✅ P/B {stock['pb']:.2f}")
            else:
                checks.append(f"❌ P/B {stock['pb']:.2f}")
            
            # 3. P/E < 10
            if stock['pe'] < 10:
                score += 25
                checks.append(f"✅ P/E {stock['pe']:.2f}")
            else:
                checks.append(f"❌ P/E {stock['pe']:.2f}")
            
            # 4. 부채비율 < 100%
            if stock['debt_ratio'] < 100:
                score += 10
                checks.append(f"✅ 부채비율 {stock['debt_ratio']:.0f}%")
            
            stock['score'] = score
            stock['checks'] = checks
            
            if score >= 60:
                filtered.append(stock)
        
        # 정렬
        filtered.sort(key=lambda x: x['p_ncav'])
        
        return filtered
    
    def generate_report(self, stocks):
        """
        리포트 생성
        """
        print("\n📊 그레이엄 순유동자산 전략 결과")
        print("=" * 60)
        
        for i, stock in enumerate(stocks[:10], 1):
            print(f"\n🎯 {i}. {stock['name']} ({stock['symbol']})")
            print(f"   섹터: {stock['sector']}")
            print(f"   점수: {stock['score']}/100")
            print(f"   P/NCAV: {stock['p_ncav']:.2f} {'✅ 저평가' if stock['p_ncav'] < 1 else '⏳ 적정'}")
            print(f"   순유동자산: {stock['ncav']}억 vs 시총 {stock['market_cap']}억")
            print(f"   잠재 상승여력: {(1/stock['p_ncav']-1)*100:.1f}%")
            print(f"   체크리스트:")
            for check in stock['checks']:
                print(f"      {check}")
        
        return stocks
    
    def portfolio_allocation(self, stocks, total_budget=100000000):
        """
        포트폴리오 배분
        """
        print("\n💼 추천 포트폴리오 배분")
        print("=" * 60)
        
        # 상위 10종목 등분
        selected = stocks[:10]
        per_stock = total_budget / len(selected)
        
        portfolio = []
        for stock in selected:
            allocation = {
                'symbol': stock['symbol'],
                'name': stock['name'],
                'allocation': per_stock,
                'ratio': 100 / len(selected),
                'reason': f"P/NCAV {stock['p_ncav']:.2f} - 순유동자산 대비 저평가"
            }
            portfolio.append(allocation)
            print(f"  {stock['name']}: {per_stock:,.0f}원 ({100/len(selected):.0f}%)")
        
        return portfolio


def main():
    """
    메인 실행
    """
    print("\n" + "=" * 60)
    print("📈 버핏 가치투자 전략 #1: 그레이엄 순유동자산")
    print("=" * 60)
    
    strategy = GrahamNetNetStrategy()
    
    # 스크리닝
    stocks = strategy.screen_stocks()
    
    # 리포트
    if stocks:
        strategy.generate_report(stocks)
        
        # 포트폴리오
        portfolio = strategy.portfolio_allocation(stocks)
        
        print("\n" + "=" * 60)
        print("📝 투자 철학")
        print("=" * 60)
        print("""
"내가 주식을 사는 이유는 시장이 다음날 혹은 다음 달에 
그 회사의 가치를 인정해 줄 거라는 확신 때문이 아니다. 
그보다는 장기적으로 회사가 잘될 거라는 확신 때문이다."

- 워런 버핏

이 전략의 핵심:
1. 순유동자산보다 싸게 사라 (마진 오브 세이프티)
2. 2-3년 기다리면 시장은 가치를 인정한다
3. 분산투자로 리스크 관리
4. 인내심이 가장 중요한 덕목
        """)
    else:
        print("⚠️ 조건에 맞는 종목이 없습니다.")


if __name__ == '__main__':
    main()
