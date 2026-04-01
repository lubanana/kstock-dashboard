#!/usr/bin/env python3
"""
KAGGRESSIVE 개선 전략 백테스트 (v1.2) - 필터 단계적 적용
기존 65점 종목에 필터 추가하여 성과 비교
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from fdr_wrapper import get_price


class ImprovedKaggBacktestV2:
    """개선된 KAGGRESSIVE 백테스트 - 필터 비교"""
    
    def __init__(self):
        self.conn = sqlite3.connect('data/pivot_strategy.db')
        
    def get_stock_data(self, symbol, date_str, days=60):
        """주가 데이터 로드"""
        end_date = datetime.strptime(date_str, '%Y-%m-%d')
        start_date = end_date - timedelta(days=days)
        
        df = get_price(symbol, start_date.strftime('%Y-%m-%d'), date_str)
        return df
    
    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calculate_sma(self, prices, period):
        """단순 이동평균"""
        if len(prices) < period:
            return None
        return np.mean(prices[-period:])
    
    def check_filters(self, symbol, date_str):
        """필터 확인 - 딕셔너리 반환"""
        df = self.get_stock_data(symbol, date_str)
        if df is None or len(df) < 30:
            return None
        
        closes = df['Close'].values
        volumes = df['Volume'].values
        
        result = {
            'has_data': True,
            'price': closes[-1],
            'rsi': None,
            'rsi_pass': False,
            'volume_ratio': None,
            'volume_pass': False,
            'sma5_pass': False,
            'filters_pass': False
        }
        
        # RSI (35~65)
        rsi = self.calculate_rsi(closes, 14)
        if rsi:
            result['rsi'] = round(rsi, 1)
            result['rsi_pass'] = 35 <= rsi <= 65
        
        # 거래량 (1.2배)
        if len(volumes) >= 20:
            vol_ma20 = np.mean(volumes[-20:])
            result['volume_ratio'] = round(volumes[-1] / vol_ma20, 2)
            result['volume_pass'] = volumes[-1] >= vol_ma20 * 1.2
        
        # 5일선
        sma5 = self.calculate_sma(closes, 5)
        if sma5:
            result['sma5_pass'] = closes[-1] > sma5
        
        # 종합 필터
        result['filters_pass'] = (
            result['rsi_pass'] and 
            result['volume_pass'] and 
            result['sma5_pass']
        )
        
        return result
    
    def simulate_trade(self, symbol, entry_date_str, entry_price, filters):
        """거래 시뮬레이션"""
        # R:R 1:3 설정
        stop_loss = entry_price * 0.93  # -7%
        target_price = entry_price * 1.21  # +21%
        
        entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d')
        hold_days = 7
        
        # 청산일 데이터 로드
        exit_start = entry_date + timedelta(days=hold_days - 2)
        exit_end = entry_date + timedelta(days=hold_days + 5)
        
        df = get_price(symbol, exit_start.strftime('%Y-%m-%d'), exit_end.strftime('%Y-%m-%d'))
        if df is None or df.empty:
            return None
        
        df = df.reset_index()
        date_col = 'Date' if 'Date' in df.columns else df.columns[0]
        df['Date'] = pd.to_datetime(df[date_col])
        
        # 7거래일 후 청산
        if len(df) < 2:
            return None
        
        exit_row = df.iloc[min(6, len(df)-1)]  # 7거래일
        exit_price = exit_row['Close']
        exit_date = exit_row['Date'].strftime('%Y-%m-%d')
        exit_reason = '보유만기'
        
        # 중간에 손절/목표 도달 체크
        for idx in range(min(7, len(df))):
            row = df.iloc[idx]
            if row['Low'] <= stop_loss:
                exit_price = stop_loss
                exit_date = row['Date'].strftime('%Y-%m-%d')
                exit_reason = '손절'
                break
            if row['High'] >= target_price:
                exit_price = target_price
                exit_date = row['Date'].strftime('%Y-%m-%d')
                exit_reason = '목표도달'
                break
        
        return_pct = ((exit_price - entry_price) / entry_price) * 100
        
        return {
            'entry_date': entry_date_str,
            'exit_date': exit_date,
            'entry_price': round(entry_price, 0),
            'exit_price': round(exit_price, 0),
            'return_pct': round(return_pct, 2),
            'exit_reason': exit_reason,
            'filters': filters
        }
    
    def run_comparison_backtest(self):
        """필터 적용 전후 비교 백테스트"""
        print("=" * 70)
        print("🔥 KAGGRESSIVE 개선 전략 백테스트 (v1.2)")
        print("=" * 70)
        print("📊 기존 65점 종목 vs 필터 적용 종목 비교")
        print()
        
        # 테스트할 종목들 (이전 스캔 결과 기반)
        test_cases = [
            # (symbol, name, entry_date, entry_price, score)
            ('033100', '제룡전기', '2026-03-03', 51100, 65),
            ('140860', '파크시스템스', '2026-03-03', 279500, 65),
            ('348210', '넥스틴', '2026-03-03', 82000, 65),
            ('006730', '서부T&D', '2026-03-03', 15320, 65),
            ('009620', '삼보산업', '2026-03-03', 1642, 65),
            ('012210', '삼미금속', '2026-03-03', 15480, 65),
            ('025980', '아난티', '2026-03-03', 8210, 65),
            ('042700', '한미반도체', '2026-03-03', 282000, 65),
        ]
        
        baseline_trades = []
        filtered_trades = []
        
        print("🔍 개별 종목 분석 중...")
        print("-" * 70)
        
        for symbol, name, entry_date, entry_price, score in test_cases:
            print(f"\n📈 {name} ({symbol}) - {entry_date}")
            
            # 필터 확인
            filters = self.check_filters(symbol, entry_date)
            
            if not filters:
                print(f"   ❌ 데이터 없음")
                continue
            
            print(f"   기준가: {entry_price:,.0f}원")
            print(f"   RSI: {filters['rsi']} {'✅' if filters['rsi_pass'] else '❌'}")
            print(f"   거래량: {filters['volume_ratio']}x {'✅' if filters['volume_pass'] else '❌'}")
            print(f"   5일선: {'✅' if filters['sma5_pass'] else '❌'}")
            
            # 기존 전략 (필터 없이) - 시뮬레이션
            baseline_trade = self.simulate_trade(symbol, entry_date, entry_price, None)
            if baseline_trade:
                baseline_trade['symbol'] = symbol
                baseline_trade['name'] = name
                baseline_trade['score'] = score
                baseline_trades.append(baseline_trade)
                print(f"   기존전략: {baseline_trade['return_pct']:+.2f}%")
            
            # 개선 전략 (필터 적용)
            if filters['filters_pass']:
                filtered_trade = self.simulate_trade(symbol, entry_date, entry_price, filters)
                if filtered_trade:
                    filtered_trade['symbol'] = symbol
                    filtered_trade['name'] = name
                    filtered_trade['score'] = score
                    filtered_trades.append(filtered_trade)
                    print(f"   개선전략: {filtered_trade['return_pct']:+.2f}% ✅ 필터통과")
            else:
                print(f"   개선전략: 필터 탈락 ❌")
        
        # 결과 비교
        print("\n" + "=" * 70)
        print("📊 결과 비교")
        print("=" * 70)
        
        # 기존 전략 통계
        if baseline_trades:
            baseline_returns = [t['return_pct'] for t in baseline_trades]
            baseline_wins = len([r for r in baseline_returns if r > 0])
            
            print(f"\n[기존 전략 - 필터 없음]")
            print(f"   거래수: {len(baseline_trades)}")
            print(f"   승률: {baseline_wins/len(baseline_trades)*100:.1f}%")
            print(f"   평균수익: {np.mean(baseline_returns):+.2f}%")
            print(f"   총수익: {np.sum(baseline_returns):+.2f}%")
        
        # 개선 전략 통계
        if filtered_trades:
            filtered_returns = [t['return_pct'] for t in filtered_trades]
            filtered_wins = len([r for r in filtered_returns if r > 0])
            
            print(f"\n[개선 전략 - 필터 적용]")
            print(f"   거래수: {len(filtered_trades)}")
            print(f"   승률: {filtered_wins/len(filtered_trades)*100:.1f}%")
            print(f"   평균수익: {np.mean(filtered_returns):+.2f}%")
            print(f"   총수익: {np.sum(filtered_returns):+.2f}%")
        else:
            print(f"\n[개선 전략] 필터 통과 종목 없음")
        
        return {
            'baseline': baseline_trades,
            'filtered': filtered_trades
        }
    
    def save_report(self, report, filename='docs/improved_kagg_comparison.json'):
        """리포트 저장"""
        # numpy bool_ to python bool 변환
        import json
        def convert_to_serializable(obj):
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(i) for i in obj]
            elif isinstance(obj, (np.bool_, np.integer, np.floating)):
                return bool(obj) if isinstance(obj, np.bool_) else float(obj)
            return obj
        
        serializable_report = convert_to_serializable(report)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(serializable_report, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 리포트 저장: {filename}")


if __name__ == '__main__':
    import pandas as pd
    
    backtest = ImprovedKaggBacktestV2()
    report = backtest.run_comparison_backtest()
    backtest.save_report(report)
