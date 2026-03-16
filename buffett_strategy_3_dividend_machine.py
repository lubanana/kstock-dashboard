#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
버핏 가치투자 전략 #3: "현금창출 머신" 배당성장 전략
========================================================

핵심 원칙:
- 버핏이 가장 좋아하는 "현금창출 머신" 기업 선별
- 꾸준한 배당 + 배당성장
- 재투자 필요 자본 적음 (High FCF Yield)
- 경기방어적 특성

선정 기준:
1. 배당수익률 ≥ 2.5%
2. 10년 연속 배당 지급
3. 5년간 배당 성장률 ≥ 5%
4. FCF Yield ≥ 5% (FCF / 시총)
5. 배당성향 30~70% (지속 가능한 수준)
6. 재투자율 < 40% (CAPEX가 적은 사업)

Buffett's Cash Machines:
- Coca-Cola: 60년+ 연속 배당
- See's Candies: 낮은 재투자, 높은 현금흐름
- Apple: 버핏의 최애 (배당 + 자사주 매입)

한국형 적용:
- 통신사: SKT, KT (안정적 배당)
- 유틸리티: 한전, 도시가스
- 제약/바이오: 유한양행, 한미약품
- 식품: 오뚜기, 농심

포트폴리오 구성:
- 핵심 배당주 (40%): 배당수익률 4%+
- 성장 배당주 (40%): 배당성장률 10%+
- 고배당 ETF (10%): 분산효과
- 현금 (10%): 리밸런싱용
"""

import pandas as pd
import numpy as np
from datetime import datetime

class BuffettDividendMachineStrategy:
    """
    버핏 스타일 현금창출 머신 배당전략
    """
    
    def __init__(self):
        self.results = []
        
    def screen_stocks(self):
        """
        배당 성장주 스크리닝
        """
        print("🔍 '현금창출 머신' 배당성장 전략 스크리닝 중...")
        print("=" * 60)
        
        # 시뮬레이션 데이터
        candidates = [
            {
                'symbol': '017670',
                'name': 'SK텔레콤',
                'dividend_yield': 5.2,  # 배당수익률 (%)
                'dividend_growth_5yr': 6.5,  # 5년 배당성장률
                'dividend_streak': 25,  # 연속 배당 년수
                'fcf_yield': 8.5,  # FCF 수익률
                'payout_ratio': 65,  # 배당성향
                'reinvestment_rate': 25,  # 재투자율
                'sector': '통신',
                'moat': '규모의 경제'
            },
            {
                'symbol': '030200',
                'name': 'KT',
                'dividend_yield': 4.8,
                'dividend_growth_5yr': 5.2,
                'dividend_streak': 20,
                'fcf_yield': 7.2,
                'payout_ratio': 58,
                'reinvestment_rate': 30,
                'sector': '통신',
                'moat': '인프라'
            },
            {
                'symbol': '000100',
                'name': '유한양행',
                'dividend_yield': 3.2,
                'dividend_growth_5yr': 8.5,
                'dividend_streak': 30,
                'fcf_yield': 6.8,
                'payout_ratio': 35,
                'reinvestment_rate': 35,
                'sector': '제약',
                'moat': '브랜드/특허'
            },
            {
                'symbol': '128940',
                'name': '한미약품',
                'dividend_yield': 2.8,
                'dividend_growth_5yr': 12.5,
                'dividend_streak': 15,
                'fcf_yield': 7.5,
                'payout_ratio': 28,
                'reinvestment_rate': 45,
                'sector': '제약',
                'moat': 'R&D'
            },
            {
                'symbol': '007310',
                'name': '오뚜기',
                'dividend_yield': 3.5,
                'dividend_growth_5yr': 5.8,
                'dividend_streak': 28,
                'fcf_yield': 6.2,
                'payout_ratio': 42,
                'reinvestment_rate': 22,
                'sector': '식품',
                'moat': '브랜드'
            },
            {
                'symbol': '004370',
                'name': '농심',
                'dividend_yield': 2.8,
                'dividend_growth_5yr': 4.5,
                'dividend_streak': 35,
                'fcf_yield': 5.5,
                'payout_ratio': 38,
                'reinvestment_rate': 28,
                'sector': '식품',
                'moat': '시장점유율'
            },
            {
                'symbol': '015760',
                'name': '한전기술',
                'dividend_yield': 4.2,
                'dividend_growth_5yr': 3.2,
                'dividend_streak': 18,
                'fcf_yield': 9.5,
                'payout_ratio': 55,
                'reinvestment_rate': 20,
                'sector': '에너지',
                'moat': '독점권'
            },
            {
                'symbol': '267250',
                'name': '현대중공업지주',
                'dividend_yield': 2.5,
                'dividend_growth_5yr': 15.2,
                'dividend_streak': 8,
                'fcf_yield': 6.8,
                'payout_ratio': 25,
                'reinvestment_rate': 48,
                'sector': '조선/에너지',
                'moat': '기술력'
            }
        ]
        
        filtered = []
        for stock in candidates:
            score = 0
            details = []
            category = ''
            
            # 1. 배당수익률 (20점)
            if stock['dividend_yield'] >= 4:
                score += 20
                details.append(f"✅ 배당 {stock['dividend_yield']:.1f}% (고배당)")
            elif stock['dividend_yield'] >= 2.5:
                score += 15
                details.append(f"⚡ 배당 {stock['dividend_yield']:.1f}% (준수)")
            else:
                details.append(f"❌ 배당 {stock['dividend_yield']:.1f}% (낮음)")
            
            # 2. 배당성장률 (25점)
            if stock['dividend_growth_5yr'] >= 10:
                score += 25
                details.append(f"✅ 성장 {stock['dividend_growth_5yr']:.1f}% (강력)")
                category = '성장배당'
            elif stock['dividend_growth_5yr'] >= 5:
                score += 18
                details.append(f"⚡ 성장 {stock['dividend_growth_5yr']:.1f}% (안정)")
                category = '안정배당'
            else:
                details.append(f"❌ 성장 {stock['dividend_growth_5yr']:.1f}% (정체)")
            
            # 3. 배당 연속성 (15점)
            if stock['dividend_streak'] >= 20:
                score += 15
                details.append(f"✅ {stock['dividend_streak']}년 연속")
            elif stock['dividend_streak'] >= 10:
                score += 10
                details.append(f"⚡ {stock['dividend_streak']}년 연속")
            else:
                details.append(f"❌ {stock['dividend_streak']}년")
            
            # 4. FCF Yield (20점)
            if stock['fcf_yield'] >= 8:
                score += 20
                details.append(f"✅ FCF {stock['fcf_yield']:.1f}% (우수)")
            elif stock['fcf_yield'] >= 5:
                score += 15
                details.append(f"⚡ FCF {stock['fcf_yield']:.1f}% (양호)")
            else:
                details.append(f"❌ FCF {stock['fcf_yield']:.1f}%")
            
            # 5. 배당성향 (10점)
            if 30 <= stock['payout_ratio'] <= 70:
                score += 10
                details.append(f"✅ 성향 {stock['payout_ratio']}% (적정)")
            else:
                details.append(f"⚡ 성향 {stock['payout_ratio']}%")
            
            # 6. 재투자율 (10점)
            if stock['reinvestment_rate'] < 30:
                score += 10
                details.append(f"✅ 재투자 {stock['reinvestment_rate']}% (효율)")
            elif stock['reinvestment_rate'] < 50:
                score += 5
                details.append(f"⚡ 재투자 {stock['reinvestment_rate']}%")
            
            stock['dividend_score'] = score
            stock['details'] = details
            stock['category'] = category if category else ('고배당' if stock['dividend_yield'] >= 4 else '일반')
            
            if score >= 60:
                filtered.append(stock)
        
        # 정렬
        filtered.sort(key=lambda x: (x['dividend_score'], x['dividend_yield']), reverse=True)
        
        return filtered
    
    def classify_by_type(self, stocks):
        """
        유형별 분류
        """
        types = {
            'high_yield': [],    # 고배당 (4%+)
            'dividend_growth': [],  # 배당성장 (10%+)
            'dividend_aristocrat': []  # 배당귀족 (20년+)
        }
        
        for stock in stocks:
            if stock['dividend_yield'] >= 4:
                types['high_yield'].append(stock)
            if stock['dividend_growth_5yr'] >= 8:
                types['dividend_growth'].append(stock)
            if stock['dividend_streak'] >= 20:
                types['dividend_aristocrat'].append(stock)
        
        return types
    
    def generate_report(self, stocks):
        """
        리포트 생성
        """
        types = self.classify_by_type(stocks)
        
        print("\n📊 '현금창출 머신' 배당성장 전략 결과")
        print("=" * 60)
        
        print("\n💰 고배당주 (4%+ 수익률)")
        print("-" * 60)
        for stock in types['high_yield']:
            print(f"\n💵 {stock['name']} ({stock['symbol']})")
            print(f"   배당: {stock['dividend_yield']:.1f}% | FCF: {stock['fcf_yield']:.1f}%")
            print(f"   Moat: {stock['moat']} | 섹터: {stock['sector']}")
            print(f"   추천 비중: 8-10%")
        
        print("\n📈 배당성장주 (연 8%+ 성장)")
        print("-" * 60)
        for stock in types['dividend_growth']:
            if stock not in types['high_yield']:
                print(f"\n🌱 {stock['name']} ({stock['symbol']})")
                print(f"   배당: {stock['dividend_yield']:.1f}% | 성장: {stock['dividend_growth_5yr']:.1f}%/년")
                print(f"   5년후 예상 배당: {stock['dividend_yield'] * (1 + stock['dividend_growth_5yr']/100)**5:.1f}%")
                print(f"   추천 비중: 6-8%")
        
        print("\n👑 배당귀족 (20년+ 연속)")
        print("-" * 60)
        for stock in types['dividend_aristocrat']:
            print(f"\n🏆 {stock['name']} - {stock['dividend_streak']}년 연속 배당")
        
        return types
    
    def income_projection(self, investment=100000000, years=10):
        """
        배당소득 프로젝션
        """
        print("\n💵 배당소득 예측 (10년)")
        print("=" * 60)
        print(f"초기 투자금: {investment:,.0f}원\n")
        
        # 포트폴리오 가정: 평균 3.5% 배당, 6% 성장
        avg_yield = 3.5
        avg_growth = 6.0
        
        for year in range(1, years + 1):
            annual_dividend = investment * (avg_yield / 100) * ((1 + avg_growth / 100) ** (year - 1))
            monthly_dividend = annual_dividend / 12
            
            if year in [1, 5, 10]:
                print(f"{year}년차: 연 {annual_dividend:,.0f}원 / 월 {monthly_dividend:,.0f}원")
        
        # 10년 누적 배당
        total_10yr = sum([
            investment * (avg_yield / 100) * ((1 + avg_growth / 100) ** (y - 1))
            for y in range(1, 11)
        ])
        
        print(f"\n📊 10년 누적 배당: {total_10yr:,.0f}원 (원금의 {total_10yr/investment*100:.0f}%)")
        print(f"📊 10년후 월 배당: {investment * (avg_yield / 100) * ((1 + avg_growth / 100) ** 9) / 12:,.0f}원")
    
    def allocation_strategy(self):
        """
        자산 배분 전략
        """
        print("\n💼 자산 배분 전략")
        print("=" * 60)
        
        allocation = {
            'high_yield': {'ratio': 40, 'desc': 'SKT, KT 등 통신/유틸리티'},
            'div_growth': {'ratio': 35, 'desc': '유한양행, 한미약품 등 성장주'},
            'defensive': {'ratio': 15, 'desc': '오뚜기, 농심 등 방어주'},
            'cash': {'ratio': 10, 'desc': '추가 매수/리밸런싱용'}
        }
        
        for key, value in allocation.items():
            emoji = {'high_yield': '💰', 'div_growth': '📈', 'defensive': '🛡️', 'cash': '💵'}[key]
            print(f"{emoji} {value['ratio']}% - {value['desc']}")
        
        return allocation


def main():
    """
    메인 실행
    """
    print("\n" + "=" * 60)
    print("📈 버핏 가치투자 전략 #3: 현금창출 머신 배당성장")
    print("=" * 60)
    
    strategy = BuffettDividendMachineStrategy()
    
    # 스크리닝
    stocks = strategy.screen_stocks()
    
    if stocks:
        # 리포트
        types = strategy.generate_report(stocks)
        
        # 배당소득 예측
        strategy.income_projection()
        
        # 배분
        allocation = strategy.allocation_strategy()
        
        print("\n" + "=" * 60)
        print("📝 투자 철학")
        print("=" * 60)
        print("""
"우리는 주식을 사면서 '오를 것'을 기대하지 않는다. 
그 대신 '내릴 것'을 기대하며 마진 오브 세이프티를 확보한다."

- 워런 버핏

이 전략의 핵심:
1. 배당은 현금흐름을 확인하는 증거
2. 배당성장은 회사의 자신감
3. FCF Yield 높은 회사가 진짜 현금창출 머신
4. 재투자가 적은 사업이 주주환원에 집중
5. 10년 후 월 100만원 배당이 목표

보유 기간: 영구 (버핏 스타일)
        """)
    else:
        print("⚠️ 조건에 맞는 종목이 없습니다.")


if __name__ == '__main__':
    main()
