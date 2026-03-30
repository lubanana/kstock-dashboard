#!/usr/bin/env python3
"""
RSI + 볼린저밴드 단타 전략 - 페이퍼 트레이딩 시스템
현재 국면: 변동성 확대 속 횡보장 (조정된 파라미터 적용)

[조정된 파라미터]
- 손절: -2% → -3% (변동성 확대 대응)
- 포지션: 100% → 50% (리스크 관리)
- RSI: 25~35 → 20~40 (과매도 구간 확대)
- 최대 보유: 3일 → 2일 (단기 대응)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import sys

sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

class RSIBBPaperTrader:
    """RSI+BB 페이퍼 트레이딩 엔진"""
    
    def __init__(self, initial_capital=10000000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {ticker: {'entry_price': x, 'entry_date': y, 'quantity': z, 'entry_rsi': w}}
        
        # 조정된 파라미터 (변동성 확대 속 횡보장 대응)
        self.fee_rate = 0.00015
        self.sl_rate = 0.03  # 손절 -3% (기존 -2%에서 확대)
        self.tp_rate = 0.03  # 익절 +3%
        self.tp_rate_ext = 0.05  # 확장 익절 +5%
        self.max_hold_days = 2  # 최대 보유 2일 (기존 3일에서 축소)
        self.position_ratio = 0.5  # 포지션 50% (기존 100%에서 축소)
        
        # 기술적 지표
        self.bb_period = 20
        self.bb_std = 2
        self.rsi_period = 14
        self.rsi_lower = 20  # RSI 하한 확대 (기존 25)
        self.rsi_upper = 40  # RSI 상한 확대 (기존 35)
        self.volume_threshold = 1.3
        
        # 거래 내역
        self.trades = []
        self.daily_logs = []
        
        # 상태 파일
        self.state_file = '/root/.openclaw/workspace/strg/paper_trading_state.json'
        self.load_state()
    
    def load_state(self):
        """이전 상태 로드"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                self.cash = state.get('cash', self.initial_capital)
                self.positions = state.get('positions', {})
                self.trades = state.get('trades', [])
                self.daily_logs = state.get('daily_logs', [])
                print(f"📂 이전 상태 로드 완료: 현금 {self.cash:,.0f}원, 보유 {len(self.positions)}종목")
    
    def save_state(self):
        """상태 저장"""
        state = {
            'cash': self.cash,
            'positions': self.positions,
            'trades': self.trades,
            'daily_logs': self.daily_logs,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def calculate_rsi(self, prices, period=14):
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_indicators(self, df):
        """기술적 지표 계산"""
        df = df.copy()
        
        # RSI
        df['RSI'] = self.calculate_rsi(df['Close'], self.rsi_period)
        
        # 볼린저밴드
        df['BB_Middle'] = df['Close'].rolling(window=self.bb_period).mean()
        df['BB_Std'] = df['Close'].rolling(window=self.bb_period).std()
        df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * self.bb_std)
        df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * self.bb_std)
        
        # 거래량
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        return df
    
    def check_buy_signal(self, df):
        """매수 신호 체크"""
        if len(df) < 35:
            return False, None
        
        df = self.calculate_indicators(df)
        latest = df.iloc[-1]
        
        # 조정된 매수 조건
        signal = {
            'rsi': latest['RSI'],
            'price': latest['Close'],
            'bb_lower': latest['BB_Lower'],
            'volume_ratio': latest['Volume_Ratio'],
            'is_bullish': latest['Close'] > latest['Open'],
            'date': df.index[-1].strftime('%Y-%m-%d')
        }
        
        # 매수 조건 (조정됨: RSI 20~40)
        if (
            self.rsi_lower <= latest['RSI'] <= self.rsi_upper and
            latest['Close'] <= latest['BB_Lower'] * 1.02 and
            latest['Volume_Ratio'] >= self.volume_threshold and
            latest['Close'] > latest['Open']  # 양봉
        ):
            return True, signal
        
        return False, signal
    
    def check_sell_signals(self, ticker, current_price, current_date):
        """매도 신호 체크"""
        if ticker not in self.positions:
            return None
        
        pos = self.positions[ticker]
        entry_price = pos['entry_price']
        entry_date = datetime.strptime(pos['entry_date'], '%Y-%m-%d')
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        
        holding_days = (current_dt - entry_date).days
        pnl_rate = (current_price - entry_price) / entry_price
        
        # 청산 조건
        if pnl_rate <= -self.sl_rate:
            return {'reason': 'STOP_LOSS', 'pnl_rate': pnl_rate, 'price': current_price}
        elif pnl_rate >= self.tp_rate_ext:
            return {'reason': 'TP_EXT', 'pnl_rate': pnl_rate, 'price': current_price}
        elif pnl_rate >= self.tp_rate:
            return {'reason': 'TAKE_PROFIT', 'pnl_rate': pnl_rate, 'price': current_price}
        elif holding_days >= self.max_hold_days:
            return {'reason': 'TIME_EXIT', 'pnl_rate': pnl_rate, 'price': current_price}
        
        return None
    
    def enter_position(self, ticker, name, signal):
        """포지션 진입"""
        # 이미 보유 중이면 스킵
        if ticker in self.positions:
            return False
        
        price = signal['price']
        
        # 투자금액 (조정된 포지션 비율 50%)
        invest_amount = self.cash * self.position_ratio
        quantity = int(invest_amount / price)
        
        if quantity < 1:
            return False
        
        # 수수료 차감
        fee = price * quantity * self.fee_rate
        total_cost = price * quantity + fee
        
        if total_cost > self.cash:
            return False
        
        # 포지션 저장
        self.positions[ticker] = {
            'name': name,
            'entry_price': price,
            'entry_date': signal['date'],
            'quantity': quantity,
            'entry_rsi': signal['rsi'],
            'invested': total_cost
        }
        
        self.cash -= total_cost
        
        print(f"✅ 매수: {ticker} ({name})")
        print(f"   가격: {price:,.0f}원 | 수량: {quantity}주 | RSI: {signal['rsi']:.1f}")
        print(f"   투자금: {total_cost:,.0f}원 | 잔여현금: {self.cash:,.0f}원")
        
        return True
    
    def exit_position(self, ticker, exit_info):
        """포지션 청산"""
        if ticker not in self.positions:
            return False
        
        pos = self.positions[ticker]
        exit_price = exit_info['price']
        quantity = pos['quantity']
        
        # 수익률 계산
        pnl_rate = exit_info['pnl_rate']
        gross_pnl = (exit_price - pos['entry_price']) * quantity
        fee = (pos['entry_price'] + exit_price) * quantity * self.fee_rate
        net_pnl = gross_pnl - fee
        
        # 현금 회수
        proceeds = exit_price * quantity - fee
        self.cash += proceeds
        
        # 거래 기록
        trade = {
            'ticker': ticker,
            'name': pos['name'],
            'entry_date': pos['entry_date'],
            'exit_date': datetime.now().strftime('%Y-%m-%d'),
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'quantity': quantity,
            'entry_rsi': pos['entry_rsi'],
            'exit_reason': exit_info['reason'],
            'pnl_rate': pnl_rate * 100,
            'net_pnl': net_pnl,
            'result': 'WIN' if net_pnl > 0 else 'LOSS'
        }
        self.trades.append(trade)
        
        # 포지션 제거
        del self.positions[ticker]
        
        emoji = "🟢" if net_pnl > 0 else "🔴"
        print(f"{emoji} 청산: {ticker} ({pos['name']})")
        print(f"   진입: {pos['entry_price']:,.0f}원 → 청산: {exit_price:,.0f}원")
        print(f"   사유: {exit_info['reason']} | 수익률: {pnl_rate*100:+.2f}%")
        print(f"   실현손익: {net_pnl:,.0f}원 | 잔여현금: {self.cash:,.0f}원")
        
        return True
    
    def scan_and_trade(self, stocks, current_date=None):
        """스캔 및 거래 실행"""
        if current_date is None:
            current_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n{'='*70}")
        print(f"📊 페이퍼 트레이딩 - {current_date}")
        print(f"{'='*70}")
        print(f"💰 초기자본: {self.initial_capital:,.0f}원")
        print(f"💵 현재현금: {self.cash:,.0f}원")
        print(f"📈 보유포지션: {len(self.positions)}종목")
        
        # 1. 기존 포지션 청산 체크
        print(f"\n[1] 기존 포지션 청산 체크")
        for ticker in list(self.positions.keys()):
            try:
                df = get_price(ticker, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), current_date)
                if df is not None and len(df) > 0:
                    current_price = df['Close'].iloc[-1]
                    exit_info = self.check_sell_signals(ticker, current_price, current_date)
                    if exit_info:
                        self.exit_position(ticker, exit_info)
            except Exception as e:
                print(f"   ⚠️ {ticker} 체크 오류: {e}")
        
        # 2. 신규 매수 신호 스캔
        print(f"\n[2] 신규 매수 신호 스캔 (상위 {len(stocks)}개 종목)")
        signals_found = 0
        
        for stock in stocks:
            ticker = stock['code']
            name = stock.get('name', '')
            
            # 이미 보유 중이면 스킵
            if ticker in self.positions:
                continue
            
            try:
                # 데이터 조회
                end_date = current_date
                start_date = (datetime.strptime(current_date, '%Y-%m-%d') - timedelta(days=60)).strftime('%Y-%m-%d')
                df = get_price(ticker, start_date, end_date)
                
                if df is None or len(df) < 35:
                    continue
                
                # 매수 신호 체크
                is_signal, signal = self.check_buy_signal(df)
                
                if is_signal:
                    signals_found += 1
                    print(f"\n🎯 신호 감지: {ticker} ({name})")
                    print(f"   RSI: {signal['rsi']:.1f} | 가격: {signal['price']:,.0f}원")
                    print(f"   BB하단: {signal['bb_lower']:,.0f}원 | 거래량: {signal['volume_ratio']:.1f}배")
                    
                    # 포지션 진입
                    self.enter_position(ticker, name, signal)
                    
                    # 테스트용으로 첫 신호만
                    if signals_found >= 3:  # 하루 최대 3종목
                        break
                
            except Exception as e:
                continue
        
        if signals_found == 0:
            print("   매수 신호 없음")
        
        # 3. 일간 요약 저장
        self.save_daily_summary(current_date)
        self.save_state()
        
        # 4. 포트폴리오 현황
        self.print_portfolio(current_date)
    
    def save_daily_summary(self, date):
        """일간 요약 저장"""
        # 총 자산 계산
        total_value = self.cash
        for ticker, pos in self.positions.items():
            total_value += pos['entry_price'] * pos['quantity']
        
        log = {
            'date': date,
            'cash': self.cash,
            'positions_value': total_value - self.cash,
            'total_value': total_value,
            'return_rate': (total_value - self.initial_capital) / self.initial_capital * 100,
            'position_count': len(self.positions)
        }
        self.daily_logs.append(log)
    
    def print_portfolio(self, date):
        """포트폴리오 현황 출력"""
        print(f"\n{'='*70}")
        print(f"📊 포트폴리오 현황 - {date}")
        print(f"{'='*70}")
        
        # 총 자산
        total_value = self.cash
        for ticker, pos in self.positions.items():
            total_value += pos['entry_price'] * pos['quantity']
        
        total_return = (total_value - self.initial_capital) / self.initial_capital * 100
        
        print(f"💰 총 자산: {total_value:,.0f}원 (수익률: {total_return:+.2f}%)")
        print(f"💵 현금: {self.cash:,.0f}원 ({self.cash/total_value*100:.1f}%)")
        print(f"📈 포지션: {total_value - self.cash:,.0f}원 ({(total_value-self.cash)/total_value*100:.1f}%)")
        
        if self.positions:
            print(f"\n📋 보유 종목:")
            for ticker, pos in self.positions.items():
                print(f"   {ticker} ({pos['name'][:8]}): {pos['quantity']}주 @ {pos['entry_price']:,.0f}원 (RSI: {pos['entry_rsi']:.1f})")
        
        # 거래 통계
        if self.trades:
            wins = sum(1 for t in self.trades if t['result'] == 'WIN')
            total_trades = len(self.trades)
            win_rate = wins / total_trades * 100
            total_pnl = sum(t['net_pnl'] for t in self.trades)
            
            print(f"\n📈 거래 통계:")
            print(f"   총 거래: {total_trades}회 | 승률: {win_rate:.1f}% ({wins}승/{total_trades-wins}패)")
            print(f"   누적 실현손익: {total_pnl:,.0f}원")
        
        print(f"{'='*70}\n")
    
    def generate_report(self):
        """최종 리포트 생성"""
        report_file = f'/root/.openclaw/workspace/strg/docs/paper_trading_report_{datetime.now().strftime("%Y%m%d")}.md'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# RSI+BB 페이퍼 트레이딩 리포트\n\n")
            f.write(f"**생성일:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            f.write("## 전략 파라미터\n\n")
            f.write(f"- 초기자본: {self.initial_capital:,.0f}원\n")
            f.write(f"- 손절: -{self.sl_rate*100:.0f}% | 익절: +{self.tp_rate*100:.0f}% / +{self.tp_rate_ext*100:.0f}%\n")
            f.write(f"- 최대보유: {self.max_hold_days}일 | 포지션비율: {self.position_ratio*100:.0f}%\n")
            f.write(f"- RSI: {self.rsi_lower}~{self.rsi_upper} | 거래량: {self.volume_threshold}배+\n\n")
            
            if self.trades:
                f.write("## 거래 내역\n\n")
                f.write("| 종목 | 진입일 | 청산일 | 진입가 | 청산가 | 수익률 | 결과 | 사유 |\n")
                f.write("|:---|:---|:---|---:|---:|---:|:---|:---|\n")
                for t in self.trades:
                    f.write(f"| {t['ticker']} | {t['entry_date']} | {t['exit_date']} | {t['entry_price']:,.0f} | {t['exit_price']:,.0f} | {t['pnl_rate']:+.2f}% | {t['result']} | {t['exit_reason']} |\n")
            
            if self.daily_logs:
                f.write("\n## 일간 자산 추이\n\n")
                f.write("| 날짜 | 총자산 | 수익률 | 포지션수 |\n")
                f.write("|:---|---:|---:|---:|\n")
                for log in self.daily_logs:
                    f.write(f"| {log['date']} | {log['total_value']:,.0f} | {log['return_rate']:+.2f}% | {log['position_count']} |\n")
        
        print(f"📄 리포트 저장: {report_file}")


def main():
    """메인 실행"""
    # 페이퍼 트레이더 생성
    trader = RSIBBPaperTrader(initial_capital=10000000)  # 1,000만원 시작
    
    # 종목 리스트 (대형주 중심)
    import sqlite3
    conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, name FROM stock_info 
        WHERE market IN ('KOSPI', 'KOSDAQ')
        ORDER BY COALESCE(market_cap, 0) DESC
        LIMIT 50
    """)
    stocks = [{'code': row[0], 'name': row[1]} for row in cursor.fetchall()]
    conn.close()
    
    # 오늘 날짜 스캔
    today = datetime.now().strftime('%Y-%m-%d')
    
    print("="*70)
    print("🚀 RSI+BB 페이퍼 트레이딩 시스템 시작")
    print("="*70)
    print(f"📅 오늘 날짜: {today}")
    print(f"💰 초기 자본: 10,000,000원")
    print(f"📊 대상 종목: {len(stocks)}개")
    print(f"\n[조정된 파라미터 - 변동성 확대 대응]")
    print(f"   손절: -3% | 포지션: 50% | RSI: 20~40 | 보유: 2일")
    
    # 스캔 및 거래
    trader.scan_and_trade(stocks, today)
    
    # 리포트 생성
    trader.generate_report()
    
    print("\n✅ 페이퍼 트레이딩 완료!")
    print(f"   상태 파일: {trader.state_file}")
    print(f"   내일 다시 실행하면 연속 트레이딩 가능")


if __name__ == '__main__':
    main()
