#!/usr/bin/env python3
"""
RSI + 볼린저밴드 단타 전략 - 시장 국멸별 분석
상승장(Bull) / 하락장(Bear) / 횡보장(Sideways) 분리
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
import json
import sys

sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

class MarketRegimeAnalyzer:
    """시장 국면 분류기"""
    
    @staticmethod
    def classify_regime(df, lookback=20):
        """
        시장 국면 분류:
        - Bull: 정배열 (Close > EMA20 > EMA60) + 상승 추세
        - Bear: 역배열 (Close < EMA20 < EMA60) + 하락 추세
        - Sideways: 혼합 또는 수렴 (EMA20와 EMA60 근접)
        """
        df = df.copy()
        
        # 이동평균
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA60'] = df['Close'].ewm(span=60).mean()
        
        # 추세 강도 (ADX-like)
        df['Trend_Strength'] = abs(df['EMA20'] - df['EMA60']) / df['EMA60'] * 100
        
        # 국면 분류
        conditions = [
            (df['Close'] > df['EMA20']) & (df['EMA20'] > df['EMA60']) & (df['Trend_Strength'] > 2),
            (df['Close'] < df['EMA20']) & (df['EMA20'] < df['EMA60']) & (df['Trend_Strength'] > 2),
        ]
        choices = ['BULL', 'BEAR']
        df['Regime'] = np.select(conditions, choices, default='SIDEWAYS')
        
        return df
    
    @staticmethod
    def get_regime_stats(df, window=20):
        """최근 국면 통계"""
        recent = df.tail(window)
        regime_counts = recent['Regime'].value_counts()
        dominant = regime_counts.index[0] if len(regime_counts) > 0 else 'UNKNOWN'
        dominance_pct = regime_counts.iloc[0] / len(recent) * 100 if len(recent) > 0 else 0
        return dominant, dominance_pct


class RSIBBRegimeBacktest:
    """시장 국멸별 RSI+BB 백테스트"""
    
    def __init__(self):
        self.fee_rate = 0.00015
        self.sl_rate = 0.02
        self.tp_rate = 0.03
        self.tp_rate_ext = 0.05
        self.max_hold_days = 3
        
        # 필터링
        self.min_trading_amount = 5
        self.min_atr_pct = 1.5
        
        # 기술적 지표
        self.bb_period = 20
        self.bb_std = 2
        self.rsi_period = 14
        self.rsi_lower = 25
        self.rsi_upper = 35
        self.volume_threshold = 1.3
        
        self.regime_analyzer = MarketRegimeAnalyzer()
    
    def get_stock_list(self):
        """종목 리스트"""
        conn = sqlite3.connect('data/pivot_strategy.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, name, market_cap, market 
            FROM stock_info 
            WHERE market IN ('KOSPI', 'KOSDAQ')
              AND name NOT LIKE '%관리%'
            ORDER BY COALESCE(market_cap, 0) DESC
        """)
        stocks = cursor.fetchall()
        conn.close()
        return [{'code': s[0], 'name': s[1], 'market_cap': s[2], 'market': s[3]} for s in stocks]
    
    def calculate_indicators(self, df):
        """기술적 지표 계산"""
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        df['RSI'] = 100 - (100 / (1 + gain / loss))
        
        # 볼린저밴드
        df['BB_Middle'] = df['Close'].rolling(window=self.bb_period).mean()
        df['BB_Std'] = df['Close'].rolling(window=self.bb_period).std()
        df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * self.bb_std)
        df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * self.bb_std)
        
        # 거래량
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # ATR
        df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
        
        return df
    
    def backtest_stock(self, stock, start_date, end_date):
        """단일 종목 백테스트 (국멸별 분리)"""
        ticker = stock['code']
        name = stock.get('name', '')
        
        try:
            df = get_price(ticker, start_date, end_date)
            if df is None or len(df) < 80:  # EMA60 계산 위해 80일 필요
                return [], "데이터 부족"
            
            # 필터링
            df['Amount'] = df['Close'] * df['Volume'] / 100000000
            avg_amount = df['Amount'].tail(20).mean()
            if avg_amount < self.min_trading_amount:
                return [], f"거래대금 부족 ({avg_amount:.1f}억)"
            
            atr_pct = (df['ATR'].iloc[-1] / df['Close'].iloc[-1]) * 100 if 'ATR' in df.columns else 0
            if atr_pct < self.min_atr_pct and atr_pct > 0:
                return [], f"ATR 부족 ({atr_pct:.1f}%)"
            
            # 지표 계산
            df = self.calculate_indicators(df)
            
            # 시장 국면 분류
            df = self.regime_analyzer.classify_regime(df)
            
            # 매수 신호
            df['Buy_Signal'] = (
                (df['RSI'] >= self.rsi_lower) & 
                (df['RSI'] <= self.rsi_upper) &
                (df['Close'] <= df['BB_Lower'] * 1.02) &
                (df['Volume_Ratio'] >= self.volume_threshold) &
                (df['Close'] > df['Open'])
            )
            
            # 백테스트 (국멸별 분리)
            trades = []
            position = None
            entry_price = entry_date = entry_regime = None
            
            for i in range(65, len(df)):  # 충분한 데이터 필요
                date = df.index[i]
                row = df.iloc[i]
                
                if position is None and row['Buy_Signal']:
                    position = 'LONG'
                    entry_price = row['Close']
                    entry_date = date
                    entry_regime = row['Regime']
                    entry_rsi = row['RSI']
                
                elif position == 'LONG':
                    current_price = row['Close']
                    holding_days = (date - entry_date).days
                    pnl_rate = (current_price - entry_price) / entry_price
                    
                    exit_reason = None
                    if pnl_rate <= -self.sl_rate:
                        exit_reason = 'STOP_LOSS'
                    elif pnl_rate >= self.tp_rate_ext:
                        exit_reason = 'TP_EXT'
                    elif pnl_rate >= self.tp_rate:
                        exit_reason = 'TAKE_PROFIT'
                    elif holding_days >= self.max_hold_days:
                        exit_reason = 'TIME_EXIT'
                    
                    if exit_reason:
                        net_pnl_rate = (pnl_rate - self.fee_rate * 2) * 100
                        trades.append({
                            'ticker': ticker, 'name': name,
                            'entry_date': entry_date.strftime('%Y-%m-%d'),
                            'exit_date': date.strftime('%Y-%m-%d'),
                            'regime': entry_regime,  # 진입 시 국면
                            'holding_days': holding_days,
                            'entry_price': round(entry_price, 0),
                            'exit_price': round(current_price, 0),
                            'entry_rsi': round(entry_rsi, 1),
                            'net_pnl_rate': round(net_pnl_rate, 2),
                            'result': 'WIN' if net_pnl_rate > 0 else 'LOSS',
                            'exit_reason': exit_reason
                        })
                        position = None
            
            return trades, f"✅ {len(trades)}거래"
            
        except Exception as e:
            return [], f"❌ {str(e)[:20]}"


def analyze_by_regime(all_trades):
    """국멸별 성과 분석"""
    if not all_trades:
        return {}
    
    df = pd.DataFrame(all_trades)
    
    results = {}
    for regime in ['BULL', 'BEAR', 'SIDEWAYS']:
        regime_df = df[df['regime'] == regime]
        if len(regime_df) == 0:
            continue
        
        total = len(regime_df)
        wins = len(regime_df[regime_df['result'] == 'WIN'])
        win_rate = wins / total * 100
        avg_pnl = regime_df['net_pnl_rate'].mean()
        total_ret = ((1 + regime_df['net_pnl_rate']/100).prod() - 1) * 100
        
        avg_win = regime_df[regime_df['result'] == 'WIN']['net_pnl_rate'].mean() if wins > 0 else 0
        avg_loss = regime_df[regime_df['result'] == 'LOSS']['net_pnl_rate'].mean() if (total - wins) > 0 else 0
        
        results[regime] = {
            'total_trades': total,
            'win_rate': win_rate,
            'wins': wins,
            'losses': total - wins,
            'avg_pnl': avg_pnl,
            'total_return': total_ret,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0
        }
    
    return results


def main():
    backtest = RSIBBRegimeBacktest()
    
    # 종목 리스트 (KOSPI 대형주 중심)
    stocks = backtest.get_stock_list()[:100]  # 상위 100개
    print(f"📊 시장 국멸별 백테스트")
    print(f"   대상: 상위 100개 종목")
    print(f"   기간: 2024-01-01 ~ 2025-03-30")
    print(f"   국면: 상승장(Bull) / 하락장(Bear) / 횡보장(Sideways)")
    print("="*70)
    
    all_trades = []
    
    for i, stock in enumerate(stocks, 1):
        print(f"[{i:3d}/{len(stocks)}] {stock['code']} ({stock['name'][:8]:8s})", end=' ')
        trades, msg = backtest.backtest_stock(stock, '2024-01-01', '2025-03-30')
        
        if trades:
            all_trades.extend(trades)
            regime_counts = {}
            for t in trades:
                regime_counts[t['regime']] = regime_counts.get(t['regime'], 0) + 1
            regimes_str = ', '.join([f"{k}:{v}" for k, v in regime_counts.items()])
            wins = sum(1 for t in trades if t['result'] == 'WIN')
            print(f"→ {len(trades)}거래 (승:{wins}) [{regimes_str}]")
        else:
            print(f"→ {msg}")
    
    # 국멸별 분석
    print("\n" + "="*70)
    print("📈 시장 국멸별 성과 분석")
    print("="*70)
    
    if not all_trades:
        print("⚠️ 거래 내역 없음")
        return
    
    # 전체 통계
    df_all = pd.DataFrame(all_trades)
    total = len(df_all)
    wins = len(df_all[df_all['result'] == 'WIN'])
    total_return = ((1 + df_all['net_pnl_rate']/100).prod() - 1) * 100
    
    print(f"\n📊 전체 통계")
    print(f"   총 거래: {total}회")
    print(f"   승률: {wins/total*100:.1f}%")
    print(f"   총 수익률: +{total_return:.2f}%")
    
    # 국멸별 분석
    regime_results = analyze_by_regime(all_trades)
    
    print("\n📊 국멸별 상세 성과")
    print("-"*70)
    print(f"{'국면':<12} {'거래수':>8} {'승률':>8} {'총수익':>10} {'평균':>8} {'손익비':>8}")
    print("-"*70)
    
    for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
        if regime in regime_results:
            r = regime_results[regime]
            print(f"{regime:<12} {r['total_trades']:>8} {r['win_rate']:>7.1f}% {r['total_return']:>+9.1f}% {r['avg_pnl']:>+7.2f}% {r['profit_factor']:>7.1f}")
    
    # 국멸별 최적 전략 제안
    print("\n💡 국멸별 전략 인사이트")
    print("-"*70)
    
    if 'BULL' in regime_results:
        bull = regime_results['BULL']
        print(f"🟢 상승장(BULL): 승률 {bull['win_rate']:.1f}%, 수익률 +{bull['total_return']:.1f}%")
        if bull['win_rate'] >= 60:
            print("   → RSI+BB 전략 적합, 추세 추종 병행 권장")
        else:
            print("   → 과매도 진입 시점이 적은 편, 정배열 유지 종목 선별")
    
    if 'BEAR' in regime_results:
        bear = regime_results['BEAR']
        print(f"🔴 하락장(BEAR): 승률 {bear['win_rate']:.1f}%, 수익률 {bear['total_return']:+.1f}%")
        if bear['win_rate'] >= 60:
            print("   → RSI+BB 전략 효과적, 반등 매매 적합")
        else:
            print("   → 추세 하락이 강할 경우 손절 확대 또는 관망")
    
    if 'SIDEWAYS' in regime_results:
        side = regime_results['SIDEWAYS']
        print(f"🟡 횡보장(SIDEWAYS): 승률 {side['win_rate']:.1f}%, 수익률 +{side['total_return']:.1f}%")
        if side['win_rate'] >= 60:
            print("   → RSI+BB 전략 최적, 밴드 내 매매 효과적")
        else:
            print("   → 변동성 축소 시 거래 피할 것")
    
    # 저장
    output_md = f'/root/.openclaw/workspace/strg/docs/rsi_bb_regime_analysis_{datetime.now().strftime("%Y%m%d")}.md'
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write("# RSI+BB 단타 전략 - 시장 국멸별 분석\n\n")
        f.write(f"**생성일:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("## 전체 통계\n\n")
        f.write(f"- 총 거래: {total}회\n")
        f.write(f"- 승률: {wins/total*100:.1f}%\n")
        f.write(f"- 총 수익률: +{total_return:.2f}%\n\n")
        
        f.write("## 국멸별 성과\n\n")
        f.write("| 국면 | 거래수 | 승률 | 총수익률 | 평균수익 | 손익비 |\n")
        f.write("|:---|---:|---:|---:|---:|---:|\n")
        for regime in ['BULL', 'SIDEWAYS', 'BEAR']:
            if regime in regime_results:
                r = regime_results[regime]
                f.write(f"| {regime} | {r['total_trades']} | {r['win_rate']:.1f}% | {r['total_return']:+.1f}% | {r['avg_pnl']:+.2f}% | {r['profit_factor']:.1f} |\n")
        
        f.write("\n## 상세 거래 내역\n\n")
        f.write("| 종목 | 진입일 | 국면 | 진입RSI | 수익률 | 결과 |\n")
        f.write("|:---|:---|:---|---:|---:|:---:|\n")
        for t in sorted(all_trades, key=lambda x: x['entry_date'], reverse=True)[:50]:
            f.write(f"| {t['ticker']} | {t['entry_date']} | {t['regime']} | {t['entry_rsi']} | {t['net_pnl_rate']:+.2f}% | {t['result']} |\n")
    
    output_json = output_md.replace('.md', '.json')
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': {'total': total, 'win_rate': wins/total*100, 'total_return': total_return},
            'regime_analysis': regime_results,
            'trades': all_trades
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 저장 완료:")
    print(f"   {output_md}")
    print(f"   {output_json}")


if __name__ == '__main__':
    main()
