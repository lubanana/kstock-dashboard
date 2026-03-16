#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
버핏 가치투자 전략 #2: "좋은 회사를 적정가에" (Quality at Fair Price)
==================================================================

핵심 원칙:
- 버핏의 " moat (해자)" 보유 기업 선호
- 지속 가능한 경쟁 우위
- 일관된 높은 ROE (15% 이상, 5년 이상)
- 합리적인 가격 (PEG < 1, P/E < 업종 평균)

선정 기준:
1. ROE ≥ 15% (5년 평균)
2. ROE 변동성 작음 (표준편차 < 5%)
3. 부채비율 < 50%
4. 영업이익률 ≥ 10%
5. PEG < 1.0 (주가수익성장비율)
6. 배당성향 20~60%

Buffett's Criteria:
- "I look for businesses I can understand"
- "With favorable long-term prospects"
- "Operated by honest and competent people"
- "Available at attractive prices"

한국형 적용:
- 삼성전자, SK하이닉스 등 글로벌 리더
- 숨은 champions (중견기업 중 수출 비중 높은 기업)
- 2차전지 소재, 바이오, 반도체 장비

포트폴리오 구성:
- 핵심 5종목 (60%): 확실한 moat 기업
- 보조 5종목 (30%): 성장성 있는 중견기업
- 현금 (10%): 기회 대비
"""

import pandas as pd
import numpy as np
from datetime import datetime

class BuffettQualityStrategy:
    """
    버핏 스타일 좋은 회사 적정가 전략
    """
    
    def __init__(self):
        self.results = []
        
    def screen_stocks(self):
        """
        퀄리티 스톡 스크리닝
        """
        print("🔍 '좋은 회사 적정가' 전략 스크리닝 중...")
        print("=" * 60)
        
        # 시뮬레이션 데이터 (실제로는 DB에서 재무 데이터 조회)
        candidates = [
            {
                'symbol': '005930',
                'name': '삼성전자',
                'roe_5yr': 16.8,  # 5년 평균 ROE
                'roe_std': 3.2,   # ROE 표준편차
                'debt_ratio': 35,
                'op_margin': 15.2,  # 영업이익률
                'pe': 12.5,
                'peg': 0.85,  # PEG ratio
                'dividend_yield': 2.1,
                'payout_ratio': 25,
                'moat_score': 95,  # 해자 점수 (브랜드, 기술, 규모)
                'sector': '반도체',
                'growth_5yr': 14.5  # 5년 매출 성장률
            },
            {
                'symbol': '000660',
                'name': 'SK하이닉스',
                'roe_5yr': 18.2,
                'roe_std': 4.5,
                'debt_ratio': 42,
                'op_margin': 28.5,
                'pe': 8.8,
                'peg': 0.55,
                'dividend_yield': 1.8,
                'payout_ratio': 15,
                'moat_score': 88,
                'sector': '반도체',
                'growth_5yr': 22.3
            },
            {
                'symbol': '035420',
                'name': 'NAVER',
                'roe_5yr': 14.5,
                'roe_std': 2.8,
                'debt_ratio': 28,
                'op_margin': 18.5,
                'pe': 22.5,
                'peg': 1.45,
                'dividend_yield': 0.8,
                'payout_ratio': 18,
                'moat_score': 90,
                'sector': 'IT/플랫폼',
                'growth_5yr': 18.2
            },
            {
                'symbol': '051910',
                'name': 'LG화학',
                'roe_5yr': 12.8,
                'roe_std': 5.5,
                'debt_ratio': 48,
                'op_margin': 8.5,
                'pe': 15.2,
                'peg': 1.15,
                'dividend_yield': 2.5,
                'payout_ratio': 35,
                'moat_score': 75,
                'sector': '화학/2차전지',
                'growth_5yr': 16.8
            },
            {
                'symbol': '068270',
                'name': '셀트리온',
                'roe_5yr': 15.5,
                'roe_std': 4.2,
                'debt_ratio': 25,
                'op_margin': 35.2,
                'pe': 18.5,
                'peg': 0.95,
                'dividend_yield': 0,
                'payout_ratio': 0,
                'moat_score': 85,
                'sector': '바이오',
                'growth_5yr': 28.5
            },
            {
                'symbol': '006110',
                'name': '삼아알미늄',
                'roe_5yr': 13.2,
                'roe_std': 3.5,
                'debt_ratio': 38,
                'op_margin': 6.8,
                'pe': 9.5,
                'peg': 0.75,
                'dividend_yield': 3.2,
                'payout_ratio': 32,
                'moat_score': 68,
                'sector': '비철금속',
                'growth_5yr': 12.5
            }
        ]
        
        filtered = []
        for stock in candidates:
            score = 0
            details = []
            
            # 1. ROE ≥ 15% (25점)
            if stock['roe_5yr'] >= 15:
                score += 25
                details.append(f"✅ ROE {stock['roe_5yr']:.1f}% (5년)")
            elif stock['roe_5yr'] >= 12:
                score += 15
                details.append(f"⚡ ROE {stock['roe_5yr']:.1f}% (양호)")
            else:
                details.append(f"❌ ROE {stock['roe_5yr']:.1f}% (부족)")
            
            # 2. ROE 안정성 (15점)
            if stock['roe_std'] < 3:
                score += 15
                details.append(f"✅ ROE 안정성 우수 (σ={stock['roe_std']:.1f}%)")
            elif stock['roe_std'] < 5:
                score += 10
                details.append(f"⚡ ROE 안정성 양호 (σ={stock['roe_std']:.1f}%)")
            else:
                details.append(f"❌ ROE 변동성 큼 (σ={stock['roe_std']:.1f}%)")
            
            # 3. 부채비율 (10점)
            if stock['debt_ratio'] < 40:
                score += 10
                details.append(f"✅ 부채비율 {stock['debt_ratio']}%")
            elif stock['debt_ratio'] < 60:
                score += 5
                details.append(f"⚡ 부채비율 {stock['debt_ratio']}%")
            else:
                details.append(f"❌ 부채비율 {stock['debt_ratio']}%")
            
            # 4. PEG < 1 (20점)
            if stock['peg'] < 1:
                score += 20
                details.append(f"✅ PEG {stock['peg']:.2f} (저평가)")
            elif stock['peg'] < 1.5:
                score += 10
                details.append(f"⚡ PEG {stock['peg']:.2f} (적정)")
            else:
                details.append(f"❌ PEG {stock['peg']:.2f} (고평가)")
            
            # 5. Moat 점수 (20점)
            if stock['moat_score'] >= 85:
                score += 20
                details.append(f"✅ Moat {stock['moat_score']} (강력)")
            elif stock['moat_score'] >= 70:
                score += 12
                details.append(f"⚡ Moat {stock['moat_score']} (보통)")
            else:
                details.append(f"❌ Moat {stock['moat_score']} (약함)")
            
            # 6. 배당 (10점, 가산점)
            if 20 <= stock['payout_ratio'] <= 60:
                score += 10
                details.append(f"✅ 배당성향 {stock['payout_ratio']}% (적정)")
            
            stock['quality_score'] = score
            stock['details'] = details
            
            # 70점 이상만 선정
            if score >= 70:
                filtered.append(stock)
        
        # 정렬
        filtered.sort(key=lambda x: x['quality_score'], reverse=True)
        
        return filtered
    
    def classify_tier(self, stocks):
        """
        티어 분류
        """
        tiers = {
            'core': [],    # 핵심 (80점+)
            'quality': [], # 퀄리티 (70-79점)
            'watch': []    # 관망
        }
        
        for stock in stocks:
            if stock['quality_score'] >= 80:
                tiers['core'].append(stock)
            elif stock['quality_score'] >= 70:
                tiers['quality'].append(stock)
            else:
                tiers['watch'].append(stock)
        
        return tiers
    
    def generate_report(self, stocks):
        """
        리포트 생성
        """
        tiers = self.classify_tier(stocks)
        
        print("\n📊 '좋은 회사 적정가' 전략 결과")
        print("=" * 60)
        
        print("\n🥇 핵심 포트폴리오 (Core - 80점+)")
        print("-" * 60)
        for stock in tiers['core']:
            print(f"\n⭐ {stock['name']} ({stock['symbol']})")
            print(f"   섹터: {stock['sector']} | 점수: {stock['quality_score']}/100")
            print(f"   ROE: {stock['roe_5yr']:.1f}% (5년) | PEG: {stock['peg']:.2f}")
            print(f"   Moat: {stock['moat_score']}/100 | P/E: {stock['pe']:.1f}")
            print(f"   추천 비중: 10-15%")
        
        print("\n🥈 퀄리티 포트폴리오 (70-79점)")
        print("-" * 60)
        for stock in tiers['quality']:
            print(f"\n• {stock['name']} ({stock['symbol']}) - {stock['quality_score']}점")
            print(f"  ROE: {stock['roe_5yr']:.1f}% | PEG: {stock['peg']:.2f} | Moat: {stock['moat_score']}")
            print(f"  추천 비중: 5-8%")
        
        return tiers
    
    def allocation_strategy(self, total_budget=100000000):
        """
        자산 배분 전략
        """
        print("\n💼 자산 배분 전략")
        print("=" * 60)
        
        allocation = {
            'core': {
                'ratio': 60,
                'amount': total_budget * 0.6,
                'stocks': 4,
                'per_stock': total_budget * 0.6 / 4
            },
            'quality': {
                'ratio': 30,
                'amount': total_budget * 0.3,
                'stocks': 5,
                'per_stock': total_budget * 0.3 / 5
            },
            'cash': {
                'ratio': 10,
                'amount': total_budget * 0.1,
                'reason': '추가 매수 기회 대비'
            }
        }
        
        print(f"\n🥇 핵심 종목 (60%): {allocation['core']['amount']:,.0f}원")
        print(f"   종목당 {allocation['core']['per_stock']:,.0f}원 × 4종목")
        
        print(f"\n🥈 퀄리티 종목 (30%): {allocation['quality']['amount']:,.0f}원")
        print(f"   종목당 {allocation['quality']['per_stock']:,.0f}원 × 5종목")
        
        print(f"\n💵 현금 (10%): {allocation['cash']['amount']:,.0f}원")
        print(f"   목적: {allocation['cash']['reason']}")
        
        return allocation


def main():
    """
    메인 실행
    """
    print("\n" + "=" * 60)
    print("📈 버핏 가치투자 전략 #2: 좋은 회사를 적정가에")
    print("=" * 60)
    
    strategy = BuffettQualityStrategy()
    
    # 스크리닝
    stocks = strategy.screen_stocks()
    
    if stocks:
        # 리포트
        tiers = strategy.generate_report(stocks)
        
        # 배분
        allocation = strategy.allocation_strategy()
        
        print("\n" + "=" * 60)
        print("📝 투자 철학")
        print("=" * 60)
        print("""
"훌륭한 경제적 특성을 가진 회사를 합리적인 가격에 사라."

- 워런 버핏

이 전략의 핵심:
1. ROE 15% 이상 유지하는 능력이 해자의 증거
2. PEG 1 미만이면 성장성 대비 저평가
3. 안정적 ROE > 변동성 큰 고ROE
4. 장기 보유 시 복리의 힘
5. 좋은 회사는 시간이 지날수록 더 좋아진다

보유 기간: 최소 3-5년 (버핏은 평균 10년+)
        """)
    else:
        print("⚠️ 조건에 맞는 종목이 없습니다.")


if __name__ == '__main__':
    main()
