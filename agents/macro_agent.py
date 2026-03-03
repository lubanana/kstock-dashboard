#!/usr/bin/env python3
"""
Macro Analysis Agent (MACRO_001)
매크로 분석 에이전트 - 금리, 환율, VIX 등 거시경제 분석
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
import yfinance as yf

BASE_PATH = '/home/programs/kstock_analyzer'


class MacroAnalysisAgent:
    """매크로 분석 에이전트"""
    
    def __init__(self):
        self.macro_data = {}
        self.market_indicators = {}
        self.adjustment = 0
    
    def fetch_us_treasury_yield(self) -> Dict:
        """미국 10년물 국채 금리 조회"""
        try:
            # ^TNX = 10-Year Treasury Note Yield
            tnx = yf.Ticker("^TNX")
            hist = tnx.history(period="5d")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                change = current - prev
                
                return {
                    'name': 'US 10Y Treasury',
                    'symbol': '^TNX',
                    'current': round(current, 2),
                    'change': round(change, 2),
                    'trend': 'Rising' if change > 0 else 'Falling' if change < 0 else 'Stable'
                }
        except Exception as e:
            print(f"   ⚠️  Error fetching Treasury yield: {e}")
        
        return {'name': 'US 10Y Treasury', 'current': 4.2, 'change': 0, 'trend': 'Unknown'}
    
    def fetch_korea_rate(self) -> Dict:
        """한국 기준금리 (고정값 - 실시간 API 제한)"""
        # 실제로는 한국은행 API 사용
        return {
            'name': 'Korea Base Rate',
            'current': 3.0,
            'change': 0,
            'trend': 'Stable',
            'note': 'Fixed reference value'
        }
    
    def fetch_usd_krw(self) -> Dict:
        """원/달러 환율 조회"""
        try:
            # KRW=X = USD/KRW
            krw = yf.Ticker("KRW=X")
            hist = krw.history(period="5d")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                change_pct = (current / prev - 1) * 100 if prev > 0 else 0
                
                return {
                    'name': 'USD/KRW',
                    'symbol': 'KRW=X',
                    'current': round(current, 2),
                    'change_pct': round(change_pct, 2),
                    'trend': 'Weakening' if change_pct > 0 else 'Strengthening' if change_pct < 0 else 'Stable'
                }
        except Exception as e:
            print(f"   ⚠️  Error fetching USD/KRW: {e}")
        
        return {'name': 'USD/KRW', 'current': 1330, 'change_pct': 0, 'trend': 'Unknown'}
    
    def fetch_vix(self) -> Dict:
        """VIX 변동성 지수 조회"""
        try:
            # ^VIX = CBOE Volatility Index
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="5d")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                change = current - prev
                
                # VIX 해석
                if current >= 30:
                    sentiment = 'High Fear'
                elif current >= 20:
                    sentiment = 'Elevated'
                elif current >= 15:
                    sentiment = 'Normal'
                else:
                    sentiment = 'Low Fear/Complacent'
                
                return {
                    'name': 'VIX',
                    'symbol': '^VIX',
                    'current': round(current, 2),
                    'change': round(change, 2),
                    'sentiment': sentiment,
                    'trend': 'Rising' if change > 0 else 'Falling' if change < 0 else 'Stable'
                }
        except Exception as e:
            print(f"   ⚠️  Error fetching VIX: {e}")
        
        return {'name': 'VIX', 'current': 18, 'change': 0, 'sentiment': 'Normal', 'trend': 'Unknown'}
    
    def fetch_kospi(self) -> Dict:
        """KOSPI 지수 조회"""
        try:
            kospi = yf.Ticker("^KS11")
            hist = kospi.history(period="20d")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                ma20 = hist['Close'].rolling(20).mean().iloc[-1]
                
                # 추세 판정
                if current > ma20 * 1.02:
                    trend = 'Strong Uptrend'
                elif current > ma20:
                    trend = 'Uptrend'
                elif current > ma20 * 0.98:
                    trend = 'Sideways'
                else:
                    trend = 'Downtrend'
                
                # 변동성
                returns = hist['Close'].pct_change().dropna()
                volatility = returns.std() * 100 * (252 ** 0.5)  # 연율화
                
                return {
                    'name': 'KOSPI',
                    'symbol': '^KS11',
                    'current': round(current, 2),
                    'ma20': round(ma20, 2),
                    'trend': trend,
                    'volatility_annual': round(volatility, 2)
                }
        except Exception as e:
            print(f"   ⚠️  Error fetching KOSPI: {e}")
        
        return {'name': 'KOSPI', 'current': 2600, 'trend': 'Unknown', 'volatility_annual': 15}
    
    def calculate_macro_adjustment(self) -> Tuple[int, str]:
        """매크로 환경 기반 조정 계산"""
        adjustment = 0
        reasons = []
        
        # 1. 금리 환경 (US 10Y)
        treasury = self.macro_data.get('us_treasury', {})
        if treasury.get('current', 4) > 4.5:
            adjustment -= 5
            reasons.append("고금리 환경 (10Y > 4.5%)")
        elif treasury.get('current', 4) < 3.5:
            adjustment += 5
            reasons.append("저금리 환경 (10Y < 3.5%)")
        
        # 2. 환율 (원/달러)
        usdkrw = self.macro_data.get('usd_krw', {})
        if usdkrw.get('current', 1300) > 1400:
            adjustment -= 5
            reasons.append("고환율 (원화 약세)")
        elif usdkrw.get('current', 1300) < 1250:
            adjustment += 3
            reasons.append("저환율 (원화 강세)")
        
        # 3. VIX (변동성)
        vix = self.macro_data.get('vix', {})
        vix_val = vix.get('current', 18)
        if vix_val >= 30:
            adjustment -= 10
            reasons.append("고변동성 (VIX >= 30)")
        elif vix_val >= 25:
            adjustment -= 5
            reasons.append("상승 변동성 (VIX 25-30)")
        elif vix_val <= 15:
            adjustment += 3
            reasons.append("낮은 변동성 (VIX <= 15)")
        
        # 4. KOSPI 추세
        kospi = self.macro_data.get('kospi', {})
        trend = kospi.get('trend', 'Sideways')
        if trend == 'Strong Uptrend':
            adjustment += 10
            reasons.append("KOSPI 강한 상승추세")
        elif trend == 'Uptrend':
            adjustment += 5
            reasons.append("KOSPI 상승추세")
        elif trend == 'Downtrend':
            adjustment -= 10
            reasons.append("KOSPI 하락추세")
        
        # 5. 변동성
        vol = kospi.get('volatility_annual', 15)
        if vol > 25:
            adjustment -= 5
            reasons.append("KOSPI 고변동성")
        elif vol < 15:
            adjustment += 3
            reasons.append("KOSPI 저변동성")
        
        # 조정 범위 제한 (-20% ~ +20%)
        adjustment = max(-20, min(20, adjustment))
        
        reason_str = "; ".join(reasons) if reasons else "중립적 매크로 환경"
        
        return adjustment, reason_str
    
    def analyze(self) -> Dict:
        """매크로 분석 실행"""
        print("=" * 70)
        print("🌍 Macro Analysis Agent (MACRO_001)")
        print("=" * 70)
        
        # 데이터 수집
        print("\n📊 Fetching macro data...")
        
        print("   📈 US 10Y Treasury Yield...")
        self.macro_data['us_treasury'] = self.fetch_us_treasury_yield()
        
        print("   🏦 Korea Base Rate...")
        self.macro_data['korea_rate'] = self.fetch_korea_rate()
        
        print("   💱 USD/KRW Exchange Rate...")
        self.macro_data['usd_krw'] = self.fetch_usd_krw()
        
        print("   📉 VIX Volatility Index...")
        self.macro_data['vix'] = self.fetch_vix()
        
        print("   📊 KOSPI Index...")
        self.macro_data['kospi'] = self.fetch_kospi()
        
        # 조정 계수 계산
        print("\n🔍 Calculating macro adjustment...")
        self.adjustment, reason = self.calculate_macro_adjustment()
        
        # 출력
        print("\n" + "=" * 70)
        print("📋 MACRO INDICATORS")
        print("=" * 70)
        
        print(f"\n1️⃣  Interest Rates:")
        t = self.macro_data['us_treasury']
        print(f"    US 10Y Treasury: {t['current']}% ({t['trend']})")
        k = self.macro_data['korea_rate']
        print(f"    Korea Base Rate: {k['current']}%")
        
        print(f"\n2️⃣  Currency:")
        u = self.macro_data['usd_krw']
        print(f"    USD/KRW: {u['current']} ({u['change_pct']:+.2f}%) - {u['trend']}")
        
        print(f"\n3️⃣  Volatility:")
        v = self.macro_data['vix']
        print(f"    VIX: {v['current']} ({v['sentiment']}) - {v['trend']}")
        
        print(f"\n4️⃣  Market Trend:")
        ko = self.macro_data['kospi']
        print(f"    KOSPI: {ko['current']} (MA20: {ko['ma20']})")
        print(f"    Trend: {ko['trend']}")
        print(f"    Volatility (Annual): {ko['volatility_annual']}%")
        
        print("\n" + "=" * 70)
        print("📊 MACRO ADJUSTMENT")
        print("=" * 70)
        print(f"\n   Adjustment: {self.adjustment:+.0f}%")
        print(f"   Reason: {reason}")
        
        # 시장 상황 판정
        if self.adjustment >= 10:
            market_condition = "BULLISH"
        elif self.adjustment >= 5:
            market_condition = "MODERATELY BULLISH"
        elif self.adjustment > -5:
            market_condition = "NEUTRAL"
        elif self.adjustment > -10:
            market_condition = "MODERATELY BEARISH"
        else:
            market_condition = "BEARISH"
        
        print(f"   Market Condition: {market_condition}")
        
        # 결과 구성
        result = {
            'agent_id': 'MACRO_001',
            'agent_name': 'Macro Analyst',
            'analysis_date': datetime.now().isoformat(),
            'macro_indicators': self.macro_data,
            'adjustment': {
                'pct': self.adjustment,
                'reason': reason,
                'market_condition': market_condition
            },
            'recommendations': {
                'equity_exposure': 'Overweight' if self.adjustment >= 5 else 'Neutral' if self.adjustment > -5 else 'Underweight',
                'defensive_sectors': self.adjustment < -5,
                'risk_on_off': 'Risk-On' if self.adjustment > 5 else 'Risk-Off' if self.adjustment < -5 else 'Neutral'
            }
        }
        
        print("\n" + "=" * 70)
        print("✅ MACRO ANALYSIS COMPLETE")
        print("=" * 70)
        
        return result
    
    def save_result(self, result: Dict):
        """결과 저장"""
        output_path = f'{BASE_PATH}/data/level2_daily'
        os.makedirs(output_path, exist_ok=True)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        output_file = f'{output_path}/macro_analysis_{date_str}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Result saved: {output_file}")
        return output_file


def main():
    """메인 함수"""
    agent = MacroAnalysisAgent()
    result = agent.analyze()
    
    if result:
        agent.save_result(result)
        
        print("\n📋 JSON Output:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
