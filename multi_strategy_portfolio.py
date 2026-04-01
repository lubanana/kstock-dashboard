#!/usr/bin/env python3
"""
다중 전략 포트폴리오 백테스트 (Multi-Strategy Portfolio Backtest)
- 매매횟수 적음 + 손익비 높음
- 추세 추종 + 짧은 보유
- 전략 조합 최적화
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
from fdr_wrapper import get_price
from trend_following_strategies import MovingAverageCross, ATRChannelBreakout, RSI2MeanReversion


@dataclass
class Trade:
    """거래 데이터 클래스"""
    strategy: str
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    return_pct: float
    exit_reason: str
    rr_ratio: float


@dataclass
class StrategyConfig:
    """전략 설정"""
    name: str
    weight: float
    min_score: int
    hold_days: int
    stop_loss_pct: float
    target_rr: float


class MultiStrategyPortfolio:
    """다중 전략 포트폴리오 백테스트"""
    
    def __init__(self, initial_capital: float = 100_000_000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions: List[Dict] = []
        self.trades: List[Trade] = []
        self.daily_values: List[Dict] = []
        
        # 전략 인스턴스
        self.strategies = {
            'MA_CROSS': MovingAverageCross(50, 200),
            'ATR_BREAK': ATRChannelBreakout(350, 14),
            'RSI2_MA200': RSI2MeanReversion(2, 200),
        }
        
        # 전략 설정 조합 (테스트할 조합들)
        self.strategy_configs = [
            # 조합 1: 보수적 (적은 거래, 높은 R:R)
            {
                'name': 'Conservative_High_RR',
                'description': '매매횟수 적음, 손익비 높음',
                'max_positions': 3,
                'position_size_pct': 0.15,  # 포지션당 15%
                'configs': [
                    StrategyConfig('MA_CROSS', 0.4, 70, 10, 0.05, 4.0),
                    StrategyConfig('ATR_BREAK', 0.4, 75, 15, 0.07, 4.0),
                    StrategyConfig('RSI2_MA200', 0.2, 70, 5, 0.03, 2.0),
                ]
            },
            # 조합 2: 추세 추종 중심
            {
                'name': 'Trend_Following_Focus',
                'description': '추세 타고 짧게',
                'max_positions': 5,
                'position_size_pct': 0.12,
                'configs': [
                    StrategyConfig('MA_CROSS', 0.5, 65, 7, 0.05, 3.0),
                    StrategyConfig('ATR_BREAK', 0.5, 70, 10, 0.06, 3.5),
                ]
            },
            # 조합 3: 균형잡힌
            {
                'name': 'Balanced',
                'description': '균형잡힌 접근',
                'max_positions': 4,
                'position_size_pct': 0.125,
                'configs': [
                    StrategyConfig('MA_CROSS', 0.35, 65, 7, 0.05, 3.0),
                    StrategyConfig('ATR_BREAK', 0.35, 70, 10, 0.06, 3.5),
                    StrategyConfig('RSI2_MA200', 0.30, 65, 5, 0.03, 2.0),
                ]
            },
            # 조합 4: 고승률 평균회귀
            {
                'name': 'High_Win_Rate',
                'description': '승률 우선',
                'max_positions': 5,
                'position_size_pct': 0.10,
                'configs': [
                    StrategyConfig('RSI2_MA200', 0.7, 60, 5, 0.03, 1.5),
                    StrategyConfig('MA_CROSS', 0.3, 75, 7, 0.05, 3.0),
                ]
            },
        ]
    
    def get_signals(self, date_str: str, top_n: int = 20) -> List[Dict]:
        """특정 날짜의 모든 전략 신호 수집"""
        conn = sqlite3.connect('data/pivot_strategy.db')
        cursor = conn.cursor()
        
        # 종목 샘플링
        cursor.execute("""
            SELECT DISTINCT s.symbol, s.name
            FROM stock_info s
            JOIN stock_prices p ON s.symbol = p.symbol AND p.date = ?
            ORDER BY RANDOM()
            LIMIT 100
        """, (date_str,))
        
        symbols = cursor.fetchall()
        conn.close()
        
        signals = []
        
        for symbol, name in symbols:
            for strategy_name, strategy in self.strategies.items():
                try:
                    result = strategy.analyze(symbol, date_str)
                    if result and result['signal'] in ['BUY', 'STRONG_BUY']:
                        result['name'] = name
                        signals.append(result)
                except:
                    continue
        
        # 점수 기준 정렬
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:top_n]
    
    def simulate_trade(self, signal: Dict, config: StrategyConfig) -> Optional[Trade]:
        """단일 거래 시뮬레이션"""
        try:
            symbol = signal['symbol']
            entry_date = datetime.strptime(signal['date'], '%Y-%m-%d')
            entry_price = signal['price']
            
            # 손절/목표가 계산
            stop_loss = entry_price * (1 - config.stop_loss_pct)
            
            if config.target_rr:
                risk = entry_price - stop_loss
                target = entry_price + (risk * config.target_rr)
            else:
                target = entry_price * 1.10  # 기본 10%
            
            # 보유 기간 데이터 로드
            exit_start = entry_date + timedelta(days=config.hold_days - 2)
            exit_end = entry_date + timedelta(days=config.hold_days + 5)
            
            df = get_price(symbol, 
                          exit_start.strftime('%Y-%m-%d'),
                          exit_end.strftime('%Y-%m-%d'))
            
            if df is None or df.empty:
                return None
            
            # 시뮬레이션
            df = df.reset_index()
            date_col = 'Date' if 'Date' in df.columns else df.columns[0]
            df['Date'] = pd.to_datetime(df[date_col])
            
            exit_price = df['Close'].iloc[min(config.hold_days-1, len(df)-1)]
            exit_date = df['Date'].iloc[min(config.hold_days-1, len(df)-1)]
            exit_reason = '보유만기'
            
            # 중간 청산 체크
            for idx in range(min(config.hold_days, len(df))):
                if idx == 0:
                    continue
                
                row = df.iloc[idx]
                
                if row['Low'] <= stop_loss:
                    exit_price = stop_loss
                    exit_date = row['Date']
                    exit_reason = '손절'
                    break
                
                if row['High'] >= target:
                    exit_price = target
                    exit_date = row['Date']
                    exit_reason = '목표도달'
                    break
            
            return_pct = ((exit_price - entry_price) / entry_price) * 100
            
            return Trade(
                strategy=config.name,
                symbol=symbol,
                entry_date=entry_date.strftime('%Y-%m-%d'),
                exit_date=exit_date.strftime('%Y-%m-%d') if isinstance(exit_date, pd.Timestamp) else signal['date'],
                entry_price=round(entry_price, 0),
                exit_price=round(exit_price, 0),
                return_pct=round(return_pct, 2),
                exit_reason=exit_reason,
                rr_ratio=config.target_rr
            )
            
        except Exception as e:
            return None
    
    def run_portfolio_backtest(self, config_set: Dict, test_dates: List[str]) -> Dict:
        """포트폴리오 백테스트 실행"""
        print(f"\n{'='*70}")
        print(f"📊 {config_set['name']} - {config_set['description']}")
        print(f"{'='*70}")
        
        trades = []
        capital = self.initial_capital
        max_positions = config_set['max_positions']
        position_size = capital * config_set['position_size_pct']
        
        for date_str in test_dates:
            print(f"\n📅 {date_str}")
            
            # 신호 수집
            signals = self.get_signals(date_str, top_n=30)
            
            if not signals:
                print("   신호 없음")
                continue
            
            # 각 전략별 신호 분류
            strategy_signals = {cfg.name: [] for cfg in config_set['configs']}
            
            for signal in signals:
                for cfg in config_set['configs']:
                    if signal['strategy'].startswith(cfg.name.split('_')[0]):
                        if signal['score'] >= cfg.min_score:
                            strategy_signals[cfg.name].append(signal)
            
            # 가중치 기반 포지션 선정
            day_trades = []
            
            for cfg in config_set['configs']:
                if len(day_trades) >= max_positions:
                    break
                
                weight = int(cfg.weight * max_positions)
                selected = strategy_signals[cfg.name][:weight]
                
                for signal in selected:
                    if len(day_trades) >= max_positions:
                        break
                    
                    trade = self.simulate_trade(signal, cfg)
                    if trade:
                        day_trades.append(trade)
                        emoji = '📈' if trade.return_pct > 0 else '📉'
                        print(f"   {emoji} {trade.symbol}: {trade.return_pct:+.2f}% ({cfg.name})")
            
            trades.extend(day_trades)
        
        # 결과 분석
        return self.analyze_results(trades, config_set)
    
    def analyze_results(self, trades: List[Trade], config: Dict) -> Dict:
        """결과 분석"""
        if not trades:
            return {
                'config_name': config['name'],
                'total_trades': 0,
                'message': '거래 없음'
            }
        
        returns = [t.return_pct for t in trades]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]
        
        win_rate = len(wins) / len(returns) * 100 if returns else 0
        avg_return = np.mean(returns)
        total_return = np.sum(returns)
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 샤프 비율 (간단)
        sharpe = avg_return / np.std(returns) if np.std(returns) > 0 else 0
        
        # 최대 낙폭
        cumulative = np.cumsum(returns)
        max_dd = 0
        peak = 0
        for val in cumulative:
            if val > peak:
                peak = val
            dd = peak - val
            if dd > max_dd:
                max_dd = dd
        
        return {
            'config_name': config['name'],
            'description': config['description'],
            'total_trades': len(trades),
            'win_rate': round(win_rate, 1),
            'avg_return': round(avg_return, 2),
            'total_return': round(total_return, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'rr_ratio': round(rr_ratio, 2),
            'sharpe': round(sharpe, 2),
            'max_drawdown': round(max_dd, 2),
            'trades': [
                {
                    'strategy': t.strategy,
                    'symbol': t.symbol,
                    'entry': t.entry_date,
                    'exit': t.exit_date,
                    'return': t.return_pct,
                    'reason': t.exit_reason
                } for t in trades
            ]
        }
    
    def run_all_backtests(self, test_dates: List[str]):
        """모든 조합 백테스트"""
        print("=" * 70)
        print("🔥 다중 전략 포트폴리오 백테스트")
        print("=" * 70)
        print(f"테스트 기간: {test_dates[0]} ~ {test_dates[-1]}")
        print(f"테스트 일수: {len(test_dates)}일")
        
        results = []
        
        for config in self.strategy_configs:
            result = self.run_portfolio_backtest(config, test_dates)
            results.append(result)
        
        # 비교 결과
        print("\n" + "=" * 70)
        print("📊 전략 조합 비교")
        print("=" * 70)
        
        comparison = []
        for r in results:
            if 'total_trades' in r and r['total_trades'] > 0:
                comparison.append({
                    'name': r['config_name'],
                    'trades': r['total_trades'],
                    'win_rate': r['win_rate'],
                    'total_return': r['total_return'],
                    'rr_ratio': r['rr_ratio'],
                    'sharpe': r['sharpe'],
                    'max_dd': r['max_drawdown']
                })
        
        # 정렬 (총 수익률 기준)
        comparison.sort(key=lambda x: x['total_return'], reverse=True)
        
        print(f"\n{'순위':<4} {'전략명':<20} {'거래':<6} {'승률':<8} {'총수익':<10} {'R:R':<6} {'샤프':<6} {'MDD':<8}")
        print("-" * 70)
        
        for i, c in enumerate(comparison, 1):
            print(f"{i:<4} {c['name']:<20} {c['trades']:<6} {c['win_rate']:<8.1f} {c['total_return']:<10.2f} {c['rr_ratio']:<6.2f} {c['sharpe']:<6.2f} {c['max_dd']:<8.2f}")
        
        # 최적 전략 저장
        if comparison:
            best = comparison[0]
            print(f"\n🏆 최적 전략: {best['name']}")
            print(f"   총 수익률: {best['total_return']:+.2f}%")
            print(f"   승률: {best['win_rate']:.1f}%")
            print(f"   R:R: 1:{best['rr_ratio']:.2f}")
        
        return results


if __name__ == '__main__':
    # 테스트 기간 설정
    test_dates = []
    start = datetime(2026, 3, 3)
    for i in range(3):  # 3주
        test_dates.append((start + timedelta(days=i*7)).strftime('%Y-%m-%d'))
    
    # 백테스트 실행
    portfolio = MultiStrategyPortfolio(initial_capital=100_000_000)
    results = portfolio.run_all_backtests(test_dates)
    
    # 결과 저장
    with open('docs/multi_strategy_backtest.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 결과 저장: docs/multi_strategy_backtest.json")
