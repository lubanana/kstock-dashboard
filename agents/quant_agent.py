#!/usr/bin/env python3
"""
Quant Analysis Agent (QUANT_001)
정량적 분석 에이전트 - 재무 지표 및 성장률 분석
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import sys


class QuantAnalysisAgent:
    """정량적 분석 에이전트"""
    
    def __init__(self, symbol: str, name: str = ""):
        self.symbol = symbol
        self.name = name or symbol
        self.ticker = None
        self.info = {}
        self.financials = None
        self.quarterly_financials = None
        self.balance_sheet = None
        self.cash_flow = None
        self.scores = {}
        self.metrics = {}
    
    def fetch_data(self) -> bool:
        """재무 데이터 수집"""
        try:
            self.ticker = yf.Ticker(self.symbol)
            self.info = self.ticker.info or {}
            
            # 재무제표
            self.financials = self.ticker.financials
            self.quarterly_financials = self.ticker.quarterly_financials
            self.balance_sheet = self.ticker.balance_sheet
            self.cash_flow = self.ticker.cashflow
            
            return True
        except Exception as e:
            print(f"Error fetching data: {e}")
            return False
    
    def get_metric(self, key: str, default: float = 0) -> float:
        """info에서 지표 추출"""
        value = self.info.get(key, default)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return default
        return float(value)
    
    def analyze_profitability(self) -> Tuple[int, List[str], List[str]]:
        """
        수익성 분석 (0-25점)
        - ROE, ROA, 영업이익률, 순이익률
        """
        score = 0
        signals = []
        risks = []
        
        # ROE (0-8점)
        roe = self.get_metric('returnOnEquity', 0) * 100
        if roe >= 20:
            score += 8
            signals.append(f"ROE 우수 ({roe:.1f}%)")
        elif roe >= 15:
            score += 6
            signals.append(f"ROE 양호 ({roe:.1f}%)")
        elif roe >= 10:
            score += 4
            signals.append(f"ROE 보통 ({roe:.1f}%)")
        elif roe > 0:
            score += 2
            signals.append(f"ROE 낮음 ({roe:.1f}%)")
        else:
            risks.append(f"ROE 부진 ({roe:.1f}%)")
        
        self.metrics['ROE'] = roe
        
        # ROA (0-5점)
        roa = self.get_metric('returnOnAssets', 0) * 100
        if roa >= 10:
            score += 5
            signals.append(f"ROA 우수 ({roa:.1f}%)")
        elif roa >= 5:
            score += 3
            signals.append(f"ROA 양호 ({roa:.1f}%)")
        elif roa > 0:
            score += 1
        else:
            risks.append(f"ROA 부진 ({roa:.1f}%)")
        
        self.metrics['ROA'] = roa
        
        # 영업이익률 (0-6점)
        op_margin = self.get_metric('operatingMargins', 0) * 100
        if op_margin >= 20:
            score += 6
            signals.append(f"영업이익률 우수 ({op_margin:.1f}%)")
        elif op_margin >= 10:
            score += 4
            signals.append(f"영업이익률 양호 ({op_margin:.1f}%)")
        elif op_margin >= 5:
            score += 2
            signals.append(f"영업이익률 보통 ({op_margin:.1f}%)")
        elif op_margin > 0:
            score += 1
        else:
            risks.append(f"영업이익률 부진 ({op_margin:.1f}%)")
        
        self.metrics['OperatingMargin'] = op_margin
        
        # 순이익률 (0-6점)
        net_margin = self.get_metric('profitMargins', 0) * 100
        if net_margin >= 15:
            score += 6
            signals.append(f"순이익률 우수 ({net_margin:.1f}%)")
        elif net_margin >= 8:
            score += 4
            signals.append(f"순이익률 양호 ({net_margin:.1f}%)")
        elif net_margin >= 3:
            score += 2
        elif net_margin > 0:
            score += 1
        else:
            risks.append(f"순이익률 적자 ({net_margin:.1f}%)")
        
        self.metrics['NetMargin'] = net_margin
        
        return min(score, 25), signals, risks
    
    def analyze_growth(self) -> Tuple[int, List[str], List[str]]:
        """
        성장성 분석 (0-25점)
        - 매출 성장률, 영업이익 성장률, EPS 성장률
        """
        score = 0
        signals = []
        risks = []
        
        # 매출 성장률 (0-10점)
        revenue_growth = self.get_metric('revenueGrowth', 0) * 100
        if revenue_growth >= 30:
            score += 10
            signals.append(f"매출 고성장 ({revenue_growth:.1f}%)")
        elif revenue_growth >= 15:
            score += 8
            signals.append(f"매출 성장 ({revenue_growth:.1f}%)")
        elif revenue_growth >= 5:
            score += 5
            signals.append(f"매출 안정적 ({revenue_growth:.1f}%)")
        elif revenue_growth > 0:
            score += 2
        else:
            risks.append(f"매출 감소 ({revenue_growth:.1f}%)")
        
        self.metrics['RevenueGrowth'] = revenue_growth
        
        # 영업이익 성장률 (0-8점)
        earnings_growth = self.get_metric('earningsGrowth', 0) * 100
        if earnings_growth >= 30:
            score += 8
            signals.append(f"이익 고성장 ({earnings_growth:.1f}%)")
        elif earnings_growth >= 15:
            score += 6
            signals.append(f"이익 성장 ({earnings_growth:.1f}%)")
        elif earnings_growth >= 5:
            score += 3
        elif earnings_growth > 0:
            score += 1
        else:
            risks.append(f"이익 감소 ({earnings_growth:.1f}%)")
        
        self.metrics['EarningsGrowth'] = earnings_growth
        
        # EPS 성장률 (0-7점)
        eps_growth = self.get_metric('earningsQuarterlyGrowth', 0) * 100
        if eps_growth >= 25:
            score += 7
            signals.append(f"EPS 고성장 ({eps_growth:.1f}%)")
        elif eps_growth >= 10:
            score += 5
            signals.append(f"EPS 성장 ({eps_growth:.1f}%)")
        elif eps_growth > 0:
            score += 2
        else:
            risks.append(f"EPS 감소 ({eps_growth:.1f}%)")
        
        self.metrics['EPSGrowth'] = eps_growth
        
        return min(score, 25), signals, risks
    
    def analyze_stability(self) -> Tuple[int, List[str], List[str]]:
        """
        안정성 분석 (0-25점)
        - 부채비율, 유동비율, 현금흐름
        """
        score = 0
        signals = []
        risks = []
        
        # 부채비율 (0-10점) - 낮을수록 좋음
        debt_to_equity = self.get_metric('debtToEquity', 100)
        if debt_to_equity <= 50:
            score += 10
            signals.append(f"부채비율 우수 ({debt_to_equity:.1f}%)")
        elif debt_to_equity <= 100:
            score += 7
            signals.append(f"부채비율 양호 ({debt_to_equity:.1f}%)")
        elif debt_to_equity <= 150:
            score += 4
            signals.append(f"부채비율 보통 ({debt_to_equity:.1f}%)")
        elif debt_to_equity <= 200:
            score += 2
            risks.append(f"부채비율 높음 ({debt_to_equity:.1f}%)")
        else:
            risks.append(f"부채비율 과다 ({debt_to_equity:.1f}%)")
        
        self.metrics['DebtToEquity'] = debt_to_equity
        
        # 유동비율 (0-8점)
        current_ratio = self.get_metric('currentRatio', 1.0)
        if current_ratio >= 2.0:
            score += 8
            signals.append(f"유동비율 우수 ({current_ratio:.2f})")
        elif current_ratio >= 1.5:
            score += 6
            signals.append(f"유동비율 양호 ({current_ratio:.2f})")
        elif current_ratio >= 1.0:
            score += 3
        else:
            risks.append(f"유동비율 부족 ({current_ratio:.2f})")
        
        self.metrics['CurrentRatio'] = current_ratio
        
        # 현금흐름 (0-7점)
        operating_cf = self.get_metric('operatingCashflow', 0)
        total_revenue = self.get_metric('totalRevenue', 1)
        cf_margin = (operating_cf / total_revenue) * 100 if total_revenue > 0 else 0
        
        if cf_margin >= 15:
            score += 7
            signals.append(f"현금창출 우수 ({cf_margin:.1f}%)")
        elif cf_margin >= 8:
            score += 5
            signals.append(f"현금창출 양호 ({cf_margin:.1f}%)")
        elif cf_margin > 0:
            score += 2
        else:
            risks.append(f"현금흐름 부진 ({cf_margin:.1f}%)")
        
        self.metrics['CFMargin'] = cf_margin
        
        return min(score, 25), signals, risks
    
    def analyze_valuation(self) -> Tuple[int, List[str], List[str]]:
        """
        밸류에이션 분석 (0-25점)
        - PER, PBR, PEG, EV/EBITDA
        """
        score = 0
        signals = []
        risks = []
        
        # PER (0-8점) - 적정 PER 기준
        pe_ratio = self.get_metric('trailingPE', 20)
        forward_pe = self.get_metric('forwardPE', pe_ratio)
        
        if 8 <= pe_ratio <= 15:
            score += 8
            signals.append(f"PER 매우매력 ({pe_ratio:.1f})")
        elif pe_ratio < 8:
            score += 6
            signals.append(f"PER 저평가 의심 ({pe_ratio:.1f})")
        elif pe_ratio <= 20:
            score += 5
            signals.append(f"PER 적정 ({pe_ratio:.1f})")
        elif pe_ratio <= 30:
            score += 2
            risks.append(f"PER 다소높음 ({pe_ratio:.1f})")
        else:
            risks.append(f"PER 과고평가 ({pe_ratio:.1f})")
        
        self.metrics['PER'] = pe_ratio
        self.metrics['ForwardPER'] = forward_pe
        
        # PBR (0-6점)
        pb_ratio = self.get_metric('priceToBook', 2)
        if pb_ratio <= 1:
            score += 6
            signals.append(f"PBR 저평가 ({pb_ratio:.2f})")
        elif pb_ratio <= 1.5:
            score += 5
            signals.append(f"PBR 매력 ({pb_ratio:.2f})")
        elif pb_ratio <= 2.5:
            score += 3
        elif pb_ratio <= 4:
            score += 1
            risks.append(f"PBR 높음 ({pb_ratio:.2f})")
        else:
            risks.append(f"PBR 과고 ({pb_ratio:.2f})")
        
        self.metrics['PBR'] = pb_ratio
        
        # PEG (0-6점)
        peg = self.get_metric('pegRatio', 2)
        if 0 < peg <= 1:
            score += 6
            signals.append(f"PEG 우수 ({peg:.2f})")
        elif peg <= 1.5:
            score += 4
            signals.append(f"PEG 양호 ({peg:.2f})")
        elif peg <= 2:
            score += 2
        else:
            risks.append(f"PEG 높음 ({peg:.2f})")
        
        self.metrics['PEG'] = peg
        
        # EV/EBITDA (0-5점)
        ev_ebitda = self.get_metric('enterpriseToEbitda', 12)
        if ev_ebitda <= 6:
            score += 5
            signals.append(f"EV/EBITDA 매력 ({ev_ebitda:.1f})")
        elif ev_ebitda <= 10:
            score += 4
            signals.append(f"EV/EBITDA 적정 ({ev_ebitda:.1f})")
        elif ev_ebitda <= 15:
            score += 2
        else:
            risks.append(f"EV/EBITDA 높음 ({ev_ebitda:.1f})")
        
        self.metrics['EVEBITDA'] = ev_ebitda
        
        return min(score, 25), signals, risks
    
    def get_peer_comparison(self) -> str:
        """동종업계 비교"""
        sector = self.info.get('sector', 'Unknown')
        industry = self.info.get('industry', 'Unknown')
        
        # 간단한 휴리스틱
        total_score = sum(self.scores.values()) if self.scores else 0
        
        if total_score >= 80:
            return "상위"
        elif total_score >= 60:
            return "중상위"
        elif total_score >= 40:
            return "중위"
        else:
            return "하위"
    
    def analyze(self) -> Dict:
        """전체 정량적 분석 실행"""
        print(f"\n{'='*60}")
        print(f"📊 Quant Analysis Agent (QUANT_001)")
        print(f"   Target: {self.name} ({self.symbol})")
        print('='*60)
        
        # 데이터 수집
        if not self.fetch_data():
            return {
                'error': 'Failed to fetch data',
                'symbol': self.symbol,
                'name': self.name
            }
        
        print(f"   📈 Financial data fetched")
        print(f"   🏢 Sector: {self.info.get('sector', 'N/A')}")
        print(f"   🏭 Industry: {self.info.get('industry', 'N/A')}")
        
        # 각 영역 분석
        print(f"\n   Analyzing...")
        
        profit_score, profit_signals, profit_risks = self.analyze_profitability()
        self.scores['profitability'] = profit_score
        print(f"   ✅ Profitability: {profit_score}/25")
        
        growth_score, growth_signals, growth_risks = self.analyze_growth()
        self.scores['growth'] = growth_score
        print(f"   ✅ Growth: {growth_score}/25")
        
        stability_score, stability_signals, stability_risks = self.analyze_stability()
        self.scores['stability'] = stability_score
        print(f"   ✅ Stability: {stability_score}/25")
        
        valuation_score, valuation_signals, valuation_risks = self.analyze_valuation()
        self.scores['valuation'] = valuation_score
        print(f"   ✅ Valuation: {valuation_score}/25")
        
        # 종합 점수
        total_score = profit_score + growth_score + stability_score + valuation_score
        
        # 모든 신호와 리스크 합치기
        all_signals = profit_signals + growth_signals + stability_signals + valuation_signals
        all_risks = profit_risks + growth_risks + stability_risks + valuation_risks
        
        # 추천 결정
        if total_score >= 70:
            recommendation = "BUY"
        elif total_score >= 50:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"
        
        # 동종업계 비교
        peer_comparison = self.get_peer_comparison()
        
        # 결과 구성
        result = {
            'agent_id': 'QUANT_001',
            'agent_name': 'Quant Analyst',
            'symbol': self.symbol,
            'name': self.name,
            'analysis_date': datetime.now().isoformat(),
            'sector': self.info.get('sector', 'Unknown'),
            'industry': self.info.get('industry', 'Unknown'),
            'total_score': total_score,
            'breakdown': {
                'profitability': profit_score,
                'growth': growth_score,
                'stability': stability_score,
                'valuation': valuation_score
            },
            'key_metrics': {
                'ROE': round(self.metrics.get('ROE', 0), 2),
                'ROA': round(self.metrics.get('ROA', 0), 2),
                'PER': round(self.metrics.get('PER', 0), 2),
                'PBR': round(self.metrics.get('PBR', 0), 2),
                'PEG': round(self.metrics.get('PEG', 0), 2),
                'RevenueGrowth': round(self.metrics.get('RevenueGrowth', 0), 2),
                'DebtToEquity': round(self.metrics.get('DebtToEquity', 0), 2)
            },
            'peer_comparison': peer_comparison,
            'key_signals': all_signals[:5],
            'risk_flags': all_risks[:3],
            'recommendation': recommendation
        }
        
        # 출력
        print(f"\n{'='*60}")
        print(f"📊 ANALYSIS COMPLETE")
        print('='*60)
        print(f"   Total Score: {total_score}/100")
        print(f"   Peer Ranking: {peer_comparison}")
        print(f"   Recommendation: {recommendation}")
        print(f"   Key Signals: {', '.join(all_signals[:3])}")
        if all_risks:
            print(f"   ⚠️  Risks: {', '.join(all_risks[:2])}")
        print('='*60)
        
        return result


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Quant Analysis Agent')
    parser.add_argument('--symbol', required=True, help='Stock symbol (e.g., 005930.KS)')
    parser.add_argument('--name', help='Stock name')
    parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    # 분석 실행
    agent = QuantAnalysisAgent(args.symbol, args.name or args.symbol)
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
