#!/usr/bin/env python3
"""
Value Stock Scanner - Backtest Module
=======================================
저평가 종목 선정 전략의 역사적 성과 검증
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys
import os

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)


class ValueScannerBacktest:
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.results = []
    
    def get_price_on_date(self, symbol, target_date, days_back=60):
        """특정 날짜의 가격 데이터 로드"""
        query = '''SELECT date, open, high, low, close, volume 
                   FROM stock_prices 
                   WHERE symbol = ? 
                   AND date >= date(?, '-{} days')
                   AND date <= date(?)
                   ORDER BY date'''.format(days_back)
        df = pd.read_sql_query(query, self.conn, params=(symbol, target_date, target_date))
        if df.empty or len(df) < 20:
            return None
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    
    def get_future_return(self, symbol, start_date, hold_days=20):
        """미래 수익률 계산"""
        query = '''SELECT date, close 
                   FROM stock_prices 
                   WHERE symbol = ? 
                   AND date > date(?)
                   ORDER BY date
                   LIMIT ?'''
        df = pd.read_sql_query(query, self.conn, params=(symbol, start_date, hold_days + 1))
        
        if len(df) < hold_days:
            return None, None
        
        entry_price = df['close'].iloc[0]
        exit_price = df['close'].iloc[min(hold_days, len(df)-1)]
        max_price = df['close'].iloc[:min(hold_days, len(df)-1)].max()
        min_price = df['close'].iloc[:min(hold_days, len(df)-1)].min()
        
        total_return = (exit_price - entry_price) / entry_price * 100
        max_return = (max_price - entry_price) / entry_price * 100
        max_drawdown = (min_price - entry_price) / entry_price * 100
        
        return {
            'return': total_return,
            'max_return': max_return,
            'max_drawdown': max_drawdown,
            'exit_date': df['date'].iloc[min(hold_days, len(df)-1)]
        }, exit_price
    
    def run_backtest(self, start_date='2025-01-01', end_date='2026-03-20', 
                     rebalance_days=20, top_n=10):
        """백테스트 실행"""
        print("=" * 70)
        print("📊 Value Stock Scanner - Backtest")
        print("=" * 70)
        print(f"백테스트 기간: {start_date} ~ {end_date}")
        print(f"리밸런싱 주기: {rebalance_days}일")
        print(f"선정 종목수: 상위 {top_n}개")
        print()
        
        # 리밸런싱 날짜 생성
        dates = pd.date_range(start=start_date, end=end_date, freq=f'{rebalance_days}D')
        
        all_signals = []
        portfolio_values = []
        
        initial_capital = 100000000  # 1억원
        current_capital = initial_capital
        
        for i, date in enumerate(dates):
            date_str = date.strftime('%Y-%m-%d')
            print(f"\n[리밸런싱 {i+1}/{len(dates)}] {date_str}")
            
            # 해당 날짜의 신호 생성 (간소화된 버전)
            signals = self._generate_signals_on_date(date_str, top_n)
            
            if not signals:
                print("   해당일 선정 종목 없음")
                continue
            
            print(f"   선정 종목: {len(signals)}개")
            for s in signals:
                print(f"     • {s['name']}: {s['price']:,.0f}원 (점수: {s['score']})")
            
            # 미래 수익률 계산
            position_size = current_capital / len(signals)
            period_return = 0
            
            for signal in signals:
                future_result, exit_price = self.get_future_return(
                    signal['symbol'], date_str, rebalance_days
                )
                
                if future_result:
                    signal['future_return'] = future_result['return']
                    signal['max_return'] = future_result['max_return']
                    signal['max_drawdown'] = future_result['max_drawdown']
                    signal['exit_price'] = exit_price
                    
                    position_return = future_result['return']
                    period_return += position_return / len(signals)
                    
                    all_signals.append(signal)
            
            # 포트폴리오 가치 업데이트
            current_capital *= (1 + period_return / 100)
            portfolio_values.append({
                'date': date_str,
                'value': current_capital,
                'return': period_return
            })
            
            print(f"   기간 수익률: {period_return:+.2f}% | 누적 자산: {current_capital:,.0f}원")
        
        # 결과 분석
        self._analyze_results(all_signals, portfolio_values, initial_capital)
        
        return all_signals, portfolio_values
    
    def _generate_signals_on_date(self, date_str, top_n=10):
        """특정 날짜의 신호 생성 (간소화된 버전)"""
        cursor = self.conn.cursor()
        
        # 해당 날짜에 데이터가 있는 종목 조회
        query = '''
            SELECT DISTINCT symbol FROM stock_prices 
            WHERE date = ? AND volume > 0
        '''
        cursor.execute(query, (date_str,))
        symbols = [row[0] for row in cursor.fetchall()]
        
        signals = []
        
        for symbol in symbols:
            # 가격 데이터 로드
            df = self.get_price_on_date(symbol, date_str)
            if df is None or len(df) < 20:
                continue
            
            # 기본 지표 계산
            close = df['close'].iloc[-1]
            volume = df['volume'].iloc[-1]
            vol_ma20 = df['volume'].tail(20).mean()
            
            if vol_ma20 == 0:
                continue
            
            vol_ratio = volume / vol_ma20
            
            # 52주 고가/저가
            high_52w = df['high'].tail(252).max() if len(df) >= 252 else df['high'].max()
            low_52w = df['low'].tail(252).min() if len(df) >= 252 else df['low'].min()
            
            if high_52w <= low_52w:
                continue
            
            position_52w = (close - low_52w) / (high_52w - low_52w)
            
            # RSI 계산
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            current_rsi = rsi.iloc[-1]
            
            # 간소화된 점수 계산
            score = 0
            
            # 52주 위치 (저점 근처 선호)
            if position_52w < 0.3:
                score += 300
            elif position_52w < 0.5:
                score += 200
            
            # RSI (과매도 선호)
            if current_rsi < 30:
                score += 200
            elif current_rsi < 40:
                score += 150
            elif current_rsi < 50:
                score += 100
            
            # 거래량
            if vol_ratio > 2:
                score += 100
            elif vol_ratio > 1:
                score += 50
            
            # 최소 점수 필터
            if score >= 400:
                # 종목명 조회
                name_query = 'SELECT name FROM stock_info WHERE symbol = ?'
                cursor.execute(name_query, (symbol,))
                row = cursor.fetchone()
                name = row[0] if row else symbol
                
                signals.append({
                    'symbol': symbol,
                    'name': name,
                    'price': close,
                    'score': score,
                    'rsi': current_rsi,
                    'position_52w': position_52w,
                    'vol_ratio': vol_ratio,
                    'date': date_str
                })
        
        # 점수 순 정렬
        signals.sort(key=lambda x: x['score'], reverse=True)
        return signals[:top_n]
    
    def _analyze_results(self, signals, portfolio_values, initial_capital):
        """백테스트 결과 분석"""
        if not signals:
            print("\n❌ 백테스트 결과 없음")
            return
        
        print("\n" + "=" * 70)
        print("📈 백테스트 결과 분석")
        print("=" * 70)
        
        # 전체 통계
        returns = [s['future_return'] for s in signals if 'future_return' in s]
        
        if not returns:
            print("수익률 데이터 없음")
            return
        
        print(f"\n총 매매 횟수: {len(returns)}회")
        print(f"평균 수익률: {np.mean(returns):+.2f}%")
        print(f"중앙값 수익률: {np.median(returns):+.2f}%")
        print(f"최대 수익: {max(returns):+.2f}%")
        print(f"최대 손실: {min(returns):+.2f}%")
        print(f"승률: {len([r for r in returns if r > 0]) / len(returns) * 100:.1f}%")
        
        # 포트폴리오 성과
        if portfolio_values:
            final_value = portfolio_values[-1]['value']
            total_return = (final_value - initial_capital) / initial_capital * 100
            
            print(f"\n포트폴리오 성과:")
            print(f"  초기 자본: {initial_capital:,.0f}원")
            print(f"  최종 자산: {final_value:,.0f}원")
            print(f"  총 수익률: {total_return:+.2f}%")
            
            # 연환산 수익률
            days = (datetime.strptime(portfolio_values[-1]['date'], '%Y-%m-%d') - 
                   datetime.strptime(portfolio_values[0]['date'], '%Y-%m-%d')).days
            if days > 0:
                annualized = ((final_value / initial_capital) ** (365 / days) - 1) * 100
                print(f"  연환산 수익률: {annualized:+.2f}%")
        
        # 월별 분포
        print(f"\n수익률 분포:")
        bins = [(-float('inf'), -10), (-10, -5), (-5, 0), (0, 5), (5, 10), (10, float('inf'))]
        labels = ['-10% 이하', '-10~-5%', '-5~0%', '0~5%', '5~10%', '10% 이상']
        
        for (low, high), label in zip(bins, labels):
            count = len([r for r in returns if low <= r < high])
            pct = count / len(returns) * 100
            print(f"  {label}: {count}건 ({pct:.1f}%)")


def main():
    backtest = ValueScannerBacktest()
    
    # 백테스트 실행 (최근 3개월)
    end_date = '2026-03-20'
    start_date = '2026-01-01'
    
    signals, portfolio = backtest.run_backtest(
        start_date=start_date,
        end_date=end_date,
        rebalance_days=20,
        top_n=10
    )
    
    # 결과 저장
    if signals:
        result_data = {
            'backtest_period': {'start': start_date, 'end': end_date},
            'signals': signals,
            'portfolio': portfolio
        }
        
        with open('./reports/value_scanner_backtest.json', 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print("\n💾 백테스트 결과 저장: reports/value_scanner_backtest.json")
    
    backtest.conn.close()


if __name__ == '__main__':
    main()
