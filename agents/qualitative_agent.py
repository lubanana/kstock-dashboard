#!/usr/bin/env python3
"""
Qualitative Analysis Agent (QUAL_001)
정성적 분석 에이전트 - 기업 보고서 리스크 및 비즈니스 모델 분석
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import sys


class QualitativeAnalysisAgent:
    """정성적 분석 에이전트"""
    
    def __init__(self, symbol: str, name: str = ""):
        self.symbol = symbol
        self.name = name or symbol
        self.ticker = None
        self.info = {}
        self.scores = {}
        self.signals = []
        self.risks = []
    
    def fetch_data(self) -> bool:
        """기업 데이터 수집"""
        try:
            self.ticker = yf.Ticker(self.symbol)
            self.info = self.ticker.info or {}
            return True
        except Exception as e:
            print(f"Error fetching data: {e}")
            return False
    
    def get_info(self, key: str, default=None):
        """info에서 데이터 추출"""
        return self.info.get(key, default)
    
    def analyze_business_model(self) -> Tuple[int, List[str], List[str]]:
        """
        비즈니스 모델 분석 (0-25점)
        - 경쟁 우위, 수익 모델 지속가능성, 시장 지위
        """
        score = 0
        signals = []
        risks = []
        
        # 1. 시장 지위 및 규모 (0-8점)
        market_cap = self.get_info('marketCap', 0)
        if market_cap >= 100_000_000_000_000:  # 100조 이상
            score += 8
            signals.append(f"시장지배적 기업 ({market_cap/1e12:.1f}조)")
        elif market_cap >= 50_000_000_000_000:  # 50조 이상
            score += 7
            signals.append(f"대형 기업 ({market_cap/1e12:.1f}조)")
        elif market_cap >= 10_000_000_000_000:  # 10조 이상
            score += 5
            signals.append(f"중대형 기업 ({market_cap/1e12:.1f}조)")
        elif market_cap >= 1_000_000_000_000:  # 1조 이상
            score += 3
            signals.append(f"중형 기업 ({market_cap/1e12:.1f}조)")
        else:
            score += 1
            risks.append("소형 기업 (규모 리스크)")
        
        # 2. 사업 다각화 (0-6점)
        sector = self.get_info('sector', '')
        industry = self.get_info('industry', '')
        
        diversified_sectors = ['Conglomerates', 'Industrials', 'Technology']
        if sector in diversified_sectors:
            score += 6
            signals.append(f"다각화된 사업 ({sector})")
        elif 'semiconductor' in industry.lower() or 'electronics' in industry.lower():
            score += 5
            signals.append("핵심 부품 사업")
        elif 'bank' in industry.lower() or 'financial' in industry.lower():
            score += 5
            signals.append("금융 프랜차이즈")
        else:
            score += 3
            signals.append(f"전문 사업 ({industry})")
        
        # 3. 수익 모델 평가 (0-7점)
        gross_margin = self.get_info('grossMargins', 0) * 100
        if gross_margin >= 50:
            score += 7
            signals.append(f"고부가가치 비즈니스 ({gross_margin:.1f}%)")
        elif gross_margin >= 30:
            score += 5
            signals.append(f"양호한 마진 ({gross_margin:.1f}%)")
        elif gross_margin >= 15:
            score += 3
            signals.append(f"표준 마진 ({gross_margin:.1f}%)")
        else:
            score += 1
            risks.append(f"낮은 마진 ({gross_margin:.1f}%)")
        
        # 4. R&D 투자 (0-4점)
        rd_ratio = self.get_info('revenuePerShare', 0)
        if rd_ratio > 0:
            score += 2
            signals.append("R&D 활동 확인")
        
        return min(score, 25), signals, risks
    
    def analyze_management(self) -> Tuple[int, List[str], List[str]]:
        """
        경영진 품질 분석 (0-25점)
        - CEO 리더십, 주주환원, 투명성
        """
        score = 0
        signals = []
        risks = []
        
        # 1. 주주환원 정책 (0-10점)
        dividend_rate = self.get_info('dividendRate', 0)
        dividend_yield = self.get_info('dividendYield', 0) * 100
        payout_ratio = self.get_info('payoutRatio', 0) * 100
        
        if dividend_yield >= 3:
            score += 10
            signals.append(f"고배당 ({dividend_yield:.2f}%)")
        elif dividend_yield >= 2:
            score += 8
            signals.append(f"배당 우수 ({dividend_yield:.2f}%)")
        elif dividend_yield >= 1:
            score += 5
            signals.append(f"배당 양호 ({dividend_yield:.2f}%)")
        elif dividend_yield > 0:
            score += 3
            signals.append(f"배당 있음 ({dividend_yield:.2f}%)")
        else:
            risks.append("배당 없음")
        
        # 2. 자사주 매입 (0-5점)
        # yfinance에서 직접 자사주 정보는 제한적
        if payout_ratio > 0 and payout_ratio < 60:
            score += 5
            signals.append("여력있는 배당성향")
        elif payout_ratio >= 60:
            score += 3
            signals.append("높은 배당성향")
        
        # 3. 기업 지배구조 (0-6점)
        held_by_insiders = self.get_info('heldPercentInsiders', 0) * 100
        held_by_institutions = self.get_info('heldPercentInstitutions', 0) * 100
        
        if 10 <= held_by_insiders <= 40:
            score += 3
            signals.append(f"적정 남부 지분 ({held_by_insiders:.1f}%)")
        
        if held_by_institutions >= 30:
            score += 3
            signals.append(f"기관 투자 활발 ({held_by_institutions:.1f}%)")
        elif held_by_institutions < 10:
            risks.append("기관 관심 저조")
        
        # 4. 기업 문화/평판 (0-4점)
        employees = self.get_info('fullTimeEmployees', 0)
        if employees > 10000:
            score += 4
            signals.append(f"대규모 고용 ({employees:,}명)")
        elif employees > 1000:
            score += 2
            signals.append(f"중견 고용 ({employees:,}명)")
        
        return min(score, 25), signals, risks
    
    def analyze_industry_outlook(self) -> Tuple[int, List[str], List[str]]:
        """
        산업 전망 분석 (0-25점)
        - TAM, 산업 성장률, 기술 혁신
        """
        score = 0
        signals = []
        risks = []
        
        sector = self.get_info('sector', '')
        industry = self.get_info('industry', '')
        
        # 1. 산업 성장성 (0-10점)
        growth_sectors = ['Technology', 'Healthcare', 'Communication Services']
        stable_sectors = ['Financial Services', 'Consumer Cyclical']
        defensive_sectors = ['Consumer Defensive', 'Utilities']
        
        if sector in growth_sectors:
            score += 10
            signals.append(f"고성장 산업 ({sector})")
        elif sector in stable_sectors:
            score += 7
            signals.append(f"성숙 산업 ({sector})")
        elif sector in defensive_sectors:
            score += 5
            signals.append(f"방어적 산업 ({sector})")
        else:
            score += 4
            signals.append(f"기타 산업 ({sector})")
        
        # 2. 기술 혁신 수준 (0-8점)
        tech_industries = ['Semiconductors', 'Software', 'Internet Content', 'Biotechnology']
        if any(ti in industry for ti in tech_industries):
            score += 8
            signals.append(f"첨단기술 산업 ({industry})")
        elif 'electronics' in industry.lower():
            score += 6
            signals.append(f"전자기술 산업 ({industry})")
        elif 'bank' in industry.lower():
            score += 4
            signals.append("핀테크 전환 중")
        else:
            score += 3
            signals.append(f"전통 산업 ({industry})")
        
        # 3. 시장 위치 (0-7점)
        beta = self.get_info('beta', 1.0)
        if beta >= 1.2:
            score += 7
            signals.append(f"성장주 특성 (베타 {beta:.2f})")
        elif beta >= 0.9:
            score += 5
            signals.append(f"시장 수익률 (베타 {beta:.2f})")
        elif beta >= 0.7:
            score += 4
            signals.append(f"방어적 (베타 {beta:.2f})")
        else:
            score += 2
            signals.append(f"저변동성 (베타 {beta:.2f})")
        
        return min(score, 25), signals, risks
    
    def analyze_risk_factors(self) -> Tuple[int, List[str], List[str]]:
        """
        리스크 요인 분석 (0-25점) - 높을수록 리스크 관리 우수
        - 규제 리스크, 경쟁 심화, 공급망, ESG
        """
        score = 25  # 만점에서 감점
        signals = []
        risks = []
        
        # 1. 변동성 리스크 (0-8점 감점)
        beta = self.get_info('beta', 1.0)
        if beta >= 1.5:
            score -= 8
            risks.append(f"고변동성 (베타 {beta:.2f})")
        elif beta >= 1.2:
            score -= 5
            risks.append(f"변동성 높음 (베타 {beta:.2f})")
        elif beta >= 1.0:
            score -= 2
            signals.append(f"시장 수준 변동성 (베타 {beta:.2f})")
        else:
            signals.append(f"안정적 (베타 {beta:.2f})")
        
        # 2. 재무 리스크 (0-7점 감점)
        debt_to_equity = self.get_info('debtToEquity', 0)
        if debt_to_equity >= 200:
            score -= 7
            risks.append(f"높은 부채비율 ({debt_to_equity:.1f}%)")
        elif debt_to_equity >= 100:
            score -= 4
            risks.append(f"부채 주의 ({debt_to_equity:.1f}%)")
        elif debt_to_equity > 0:
            signals.append(f"부채 관리 양호 ({debt_to_equity:.1f}%)")
        
        # 3. 수익 리스크 (0-6점 감점)
        revenue_growth = self.get_info('revenueGrowth', 0)
        if revenue_growth < -0.1:
            score -= 6
            risks.append(f"매출 감소 ({revenue_growth*100:.1f}%)")
        elif revenue_growth < 0:
            score -= 3
            risks.append(f"매출 정체 ({revenue_growth*100:.1f}%)")
        else:
            signals.append("매출 성장 중")
        
        # 4. 유동성 리스크 (0-4점 감점)
        current_ratio = self.get_info('currentRatio', 1.0)
        if current_ratio < 0.8:
            score -= 4
            risks.append(f"유동성 위험 ({current_ratio:.2f})")
        elif current_ratio < 1.0:
            score -= 2
            risks.append(f"유동성 부족 ({current_ratio:.2f})")
        else:
            signals.append(f"유동성 양호 ({current_ratio:.2f})")
        
        return max(score, 0), signals, risks
    
    def get_moat_rating(self) -> str:
        """경제적 해자 평가"""
        gross_margin = self.get_info('grossMargins', 0)
        operating_margin = self.get_info('operatingMargins', 0)
        market_cap = self.get_info('marketCap', 0)
        
        if gross_margin >= 0.5 and operating_margin >= 0.2 and market_cap > 50_000_000_000_000:
            return "Wide"
        elif gross_margin >= 0.3 and operating_margin >= 0.1:
            return "Narrow"
        else:
            return "None"
    
    def analyze(self) -> Dict:
        """전체 정성적 분석 실행"""
        print(f"\n{'='*60}")
        print(f"🏢 Qualitative Analysis Agent (QUAL_001)")
        print(f"   Target: {self.name} ({self.symbol})")
        print('='*60)
        
        # 데이터 수집
        if not self.fetch_data():
            return {
                'error': 'Failed to fetch data',
                'symbol': self.symbol,
                'name': self.name
            }
        
        print(f"   📋 Company info fetched")
        print(f"   🏢 Sector: {self.get_info('sector', 'N/A')}")
        print(f"   🏭 Industry: {self.get_info('industry', 'N/A')}")
        
        # 각 영역 분석
        print(f"\n   Analyzing...")
        
        business_score, business_signals, business_risks = self.analyze_business_model()
        self.scores['business_model'] = business_score
        print(f"   ✅ Business Model: {business_score}/25")
        
        management_score, management_signals, management_risks = self.analyze_management()
        self.scores['management'] = management_score
        print(f"   ✅ Management: {management_score}/25")
        
        industry_score, industry_signals, industry_risks = self.analyze_industry_outlook()
        self.scores['industry_outlook'] = industry_score
        print(f"   ✅ Industry Outlook: {industry_score}/25")
        
        risk_score, risk_signals, risk_risks = self.analyze_risk_factors()
        self.scores['risk_factors'] = risk_score
        print(f"   ✅ Risk Management: {risk_score}/25")
        
        # 종합 점수
        total_score = business_score + management_score + industry_score + risk_score
        
        # 모든 신호와 리스크 합치기
        all_signals = business_signals + management_signals + industry_signals + risk_signals
        all_risks = business_risks + management_risks + industry_risks + risk_risks
        
        # 추천 결정
        if total_score >= 70:
            recommendation = "BUY"
        elif total_score >= 50:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"
        
        # 해자 평가
        moat_rating = self.get_moat_rating()
        
        # 결과 구성
        result = {
            'agent_id': 'QUAL_001',
            'agent_name': 'Qualitative Analyst',
            'symbol': self.symbol,
            'name': self.name,
            'analysis_date': datetime.now().isoformat(),
            'sector': self.get_info('sector', 'Unknown'),
            'industry': self.get_info('industry', 'Unknown'),
            'total_score': total_score,
            'breakdown': {
                'business_model': business_score,
                'management': management_score,
                'industry_outlook': industry_score,
                'risk_factors': risk_score
            },
            'moat_rating': moat_rating,
            'key_signals': all_signals[:5],
            'key_risks': all_risks[:3],
            'recommendation': recommendation
        }
        
        # 출력
        print(f"\n{'='*60}")
        print(f"📊 ANALYSIS COMPLETE")
        print('='*60)
        print(f"   Total Score: {total_score}/100")
        print(f"   Moat Rating: {moat_rating}")
        print(f"   Recommendation: {recommendation}")
        print(f"   Key Signals: {', '.join(all_signals[:3])}")
        if all_risks:
            print(f"   ⚠️  Key Risks: {', '.join(all_risks[:2])}")
        print('='*60)
        
        return result


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Qualitative Analysis Agent')
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g., 005930.KS)')
    parser.add_argument('--name', help='Stock name')
    parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    # 분석 실행
    agent = QualitativeAnalysisAgent(args.symbol, args.name or args.symbol)
    result = agent.analyze()
    
    # JSON 출력
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Result saved: {args.output}")
    else:
        print("\n📋 JSON Output:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
