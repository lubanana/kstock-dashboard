#!/usr/bin/env python3
"""
리스크 관리 계산기 - 목표가/손절가
피본acci 확장 + ATR 기반
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
from fdr_wrapper import get_price
from datetime import datetime, timedelta


class RiskCalculator:
    """피본acci + ATR 기반 리스크 관리"""
    
    # 피본acci 확장 레벨
    FIB_LEVELS = {
        'conservative': 1.272,  # 보수적
        'moderate': 1.618,      # 중립
        'aggressive': 2.618     # 공격적
    }
    
    # ATR 배수 (손절가)
    ATR_MULTIPLIER = 1.5
    
    @staticmethod
    def calculate_atr(df, period=14):
        """ATR 계산"""
        if df is None or len(df) < period:
            return None
        
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        atr = true_range.rolling(period).mean()
        return atr.iloc[-1]
    
    @staticmethod
    def find_swing_points(df, lookback=20):
        """스윙 고점/저점 찾기"""
        if df is None or len(df) < lookback:
            return None, None
        
        recent = df.tail(lookback)
        
        # 최근 고점/저점
        swing_high = recent['High'].max()
        swing_low = recent['Low'].min()
        
        return swing_high, swing_low
    
    @classmethod
    def calculate_targets(cls, symbol, entry_price=None):
        """목표가 계산"""
        try:
            # 데이터 로드
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 20:
                return None
            
            current_price = entry_price or df['Close'].iloc[-1]
            
            # ATR 계산
            atr = cls.calculate_atr(df)
            if atr is None:
                return None
            
            # 스윙 포인트 찾기
            swing_high, swing_low = cls.find_swing_points(df)
            if swing_high is None:
                return None
            
            # 변동폭 (Range)
            price_range = swing_high - swing_low
            
            # 피본acci 확장 목표가
            targets = {}
            for level_name, multiplier in cls.FIB_LEVELS.items():
                target = current_price + (price_range * (multiplier - 1))
                targets[level_name] = round(target, 0)
            
            # ATR 기반 손절가 (최대 -10% 제한)
            max_stop_distance = current_price * 0.10  # 최대 10% 하띡
            atr_stop = min(atr * cls.ATR_MULTIPLIER, max_stop_distance)
            stop_loss = current_price - atr_stop
            stop_loss_pct = ((stop_loss - current_price) / current_price) * 100
            
            # 리스크/리워드 계산
            risk = current_price - stop_loss
            rewards = {}
            for level_name, target in targets.items():
                reward = target - current_price
                r_ratio = reward / risk if risk > 0 else 0
                rewards[level_name] = {
                    'target': target,
                    'reward_pct': ((target - current_price) / current_price) * 100,
                    'r_ratio': round(r_ratio, 2)
                }
            
            return {
                'current_price': current_price,
                'atr': round(atr, 2),
                'swing_high': swing_high,
                'swing_low': swing_low,
                'stop_loss': round(stop_loss, 0),
                'stop_loss_pct': round(stop_loss_pct, 1),
                'targets': rewards
            }
            
        except Exception as e:
            print(f"   ⚠️ {symbol} 계산 오류: {e}")
            return None
    
    @classmethod
    def get_trading_plan(cls, symbol, name, score):
        """매매 계획 생성"""
        risk_data = cls.calculate_targets(symbol)
        
        if risk_data is None:
            return None
        
        # 최적 목표가 선택 (R:R 2:1 이상)
        recommended = None
        for level in ['conservative', 'moderate', 'aggressive']:
            if level in risk_data['targets']:
                t = risk_data['targets'][level]
                if t['r_ratio'] >= 2.0:
                    recommended = {
                        'level': level,
                        'target': t['target'],
                        'reward_pct': t['reward_pct'],
                        'r_ratio': t['r_ratio']
                    }
                    break
        
        # 2:1 미만이면 보수적 선택
        if recommended is None and 'conservative' in risk_data['targets']:
            t = risk_data['targets']['conservative']
            recommended = {
                'level': 'conservative',
                'target': t['target'],
                'reward_pct': t['reward_pct'],
                'r_ratio': t['r_ratio']
            }
        
        return {
            'symbol': symbol,
            'name': name,
            'score': score,
            'entry': risk_data['current_price'],
            'stop_loss': risk_data['stop_loss'],
            'stop_loss_pct': risk_data['stop_loss_pct'],
            'target': recommended['target'] if recommended else None,
            'target_pct': recommended['reward_pct'] if recommended else None,
            'r_ratio': recommended['r_ratio'] if recommended else None,
            'atr': risk_data['atr'],
            'all_targets': risk_data['targets']
        }


if __name__ == '__main__':
    # 테스트
    test_stocks = [
        ('0015N0', '한국알콜', 95),
        ('008110', '대동전자', 75),
    ]
    
    print('='*70)
    print('📊 피본acci + ATR 기반 매매 계획')
    print('='*70)
    
    for symbol, name, score in test_stocks:
        print(f'\n🔥 {name} ({symbol}) - {score}점')
        print('-'*70)
        
        plan = RiskCalculator.get_trading_plan(symbol, name, score)
        
        if plan:
            print(f"📍 진입가: {plan['entry']:,.0f}원")
            print(f"🛑 손절가: {plan['stop_loss']:,.0f}원 ({plan['stop_loss_pct']:+.1f}%)")
            print(f"   ATR(14): {plan['atr']:,.0f}원 (×{RiskCalculator.ATR_MULTIPLIER})")
            print(f"\n🎯 목표가:")
            for level, data in plan['all_targets'].items():
                marker = " 👈 추천" if plan['target'] == data['target'] else ""
                print(f"   • {level}: {data['target']:,.0f}원 (+{data['reward_pct']:.1f}%) R:R {data['r_ratio']}:1{marker}")
        else:
            print("   ⚠️ 계산 불가")
    
    print('\n' + '='*70)
