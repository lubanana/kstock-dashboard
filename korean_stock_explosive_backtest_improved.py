#!/usr/bin/env python3
"""
한국 주식 폭발적 상승 스캐닝 - 개선版 백테스트
기준: 60점 진입, 6개월 보유, 점수별 포지션 가중
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')


@dataclass
class StockScore:
    """개별 종목 스코어링 결과"""
    code: str
    name: str
    date: str
    market_cap_score: int = 0
    volume_score: int = 0
    foreign_score: int = 0
    technical_score: int = 0
    news_score: int = 0
    theme_score: int = 0
    total_score: int = 0
    
    market_cap: float = 0.0
    volume_ratio: float = 0.0
    ma20: float = 0.0
    close: float = 0.0
    sector: str = ""
    
    def calculate_total(self):
        self.total_score = (self.market_cap_score + self.volume_score + 
                           self.foreign_score + self.technical_score + 
                           self.news_score + self.theme_score)
        return self.total_score


@dataclass
class Trade:
    """개별 거래 기록"""
    code: str
    name: str
    entry_date: str
    entry_price: float
    shares: int
    position_pct: float
    
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    return_pct: float = 0.0
    exit_reason: str = ""
    score_at_entry: int = 0
    max_profit_pct: float = 0.0
    max_loss_pct: float = 0.0
    
    def calculate_return(self):
        if self.exit_price and self.entry_price:
            self.return_pct = ((self.exit_price - self.entry_price) / self.entry_price) * 100
        return self.return_pct


@dataclass
class MonthlyResult:
    """월간 성과 기록"""
    year_month: str
    starting_value: float
    ending_value: float
    trades: List[Trade] = field(default_factory=list)
    
    @property
    def return_pct(self):
        return ((self.ending_value - self.starting_value) / self.starting_value) * 100
    
    @property
    def num_trades(self):
        return len(self.trades)
    
    @property
    def win_count(self):
        return len([t for t in self.trades if t.return_pct > 0])
    
    @property
    def win_rate(self):
        if self.num_trades == 0:
            return 0.0
        return (self.win_count / self.num_trades) * 100


class ImprovedExplosiveGainsBacktest:
    """
    개선된 폭발적 상승 스캐닝 백테스트
    """
    
    HOT_SECTORS = {
        '로봇': ['로봇', '자율주행', '드론', '자동화'],
        'AI': ['AI', '인공지능', '딥러닝', '머신러닝', 'ChatGPT', 'LLM', '빅데이터'],
        '바이오': ['바이오', '제약', '바이오텍', '의료기기', '유전자', '신약'],
        '반도체': ['반도체', ' chip', '메모리', '파운드리', 'D램', '낸드', 'AI반도체', '시스템반도체']
    }
    
    # 개선된 매매 규칙
    MAX_HOLD_DAYS = 126       # 최대 6개월 (126거래일)
    STOP_LOSS_PCT = -10.0     # -10% 손절
    TAKE_PROFIT_PCT = 30.0    # +30% 익절 (하향 조정)
    REBALANCE_DAY = 1
    MAX_POSITIONS = 10
    
    # 개선된 진입 기준
    STRONG_BUY_THRESHOLD = 60  # 70점 → 60점 하향
    WATCH_THRESHOLD = 50
    
    # 점수별 포지션 가중치
    POSITION_WEIGHTS = {
        80: 15.0,   # 80점+: 15%
        70: 12.0,   # 70-79점: 12%
        60: 10.0,   # 60-69점: 10%
        50: 5.0     # 50-59점: 5%
    }
    
    def __init__(self, db_path: str = '/root/.openclaw/workspace/strg/data/level1_prices.db',
                 initial_capital: float = 100_000_000):
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        self.positions: Dict[str, Trade] = {}
        self.trade_history: List[Trade] = []
        self.monthly_results: List[MonthlyResult] = []
        self.price_cache: Dict[str, pd.DataFrame] = {}
        self.stock_info: Dict[str, Dict] = {}
        self.daily_values: List[Dict] = []
        
        self._load_stock_info()
    
    def _load_stock_info(self):
        """종목 기본 정보 로드"""
        try:
            with open('/root/.openclaw/workspace/strg/data/kospi_stocks.json', 'r') as f:
                kospi_data = json.load(f)
                for stock in kospi_data.get('stocks', []):
                    self.stock_info[stock['code']] = {
                        'name': stock['name'],
                        'market': 'KOSPI',
                        'sector': self._infer_sector(stock['name'])
                    }
        except Exception as e:
            print(f"⚠️ KOSPI 종목 정보 로드 실패: {e}")
        
        try:
            with open('/root/.openclaw/workspace/strg/data/kosdaq_stocks.json', 'r') as f:
                kosdaq_data = json.load(f)
                if isinstance(kosdaq_data, list):
                    for stock in kosdaq_data:
                        if isinstance(stock, dict) and 'code' in stock:
                            self.stock_info[stock['code']] = {
                                'name': stock['name'],
                                'market': 'KOSDAQ',
                                'sector': self._infer_sector(stock['name'])
                            }
        except Exception as e:
            print(f"⚠️ KOSDAQ 종목 정보 로드 실패: {e}")
    
    def _infer_sector(self, name: str) -> str:
        """종목명으로 섹터 추론"""
        name_lower = name.lower()
        
        for sector, keywords in self.HOT_SECTORS.items():
            for keyword in keywords:
                if keyword.lower() in name_lower or keyword in name:
                    return sector
        
        if any(k in name for k in ['은행', '증권', '보험', '금융']):
            return '금융'
        elif any(k in name for k in ['건설', '건축']):
            return '건설'
        elif any(k in name for k in ['유통', '백화점', '마트']):
            return '유통'
        elif any(k in name for k in ['식품', '음료']):
            return '식품'
        elif any(k in name for k in ['화학', '소재', '철강']):
            return '화학/소재'
        elif any(k in name for k in ['전기', '전자']):
            return '전자'
        elif any(k in name for k in ['자동차', '차량']):
            return '자동차'
        
        return '기타'
    
    def _get_db_connection(self):
        return sqlite3.connect(self.db_path)
    
    def _get_price_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        cache_key = f"{code}_{start_date}_{end_date}_v3"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        conn = self._get_db_connection()
        query = """
        SELECT date, open, high, low, close, volume, change_pct, ma5, ma20, ma60, rsi
        FROM price_data 
        WHERE code = ? AND date BETWEEN ? AND ?
        ORDER BY date
        """
        df = pd.read_sql_query(query, conn, params=(code, start_date, end_date))
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            self.price_cache[cache_key] = df
        
        return df
    
    def _simulate_market_cap(self, code: str) -> float:
        code_num = int(code) if code.isdigit() else 999999
        
        if code_num < 10000:
            base_cap = np.random.uniform(5000, 50000)
        elif code_num < 50000:
            base_cap = np.random.uniform(1000, 5000)
        else:
            base_cap = np.random.uniform(100, 2000)
        
        return base_cap
    
    def _check_foreign_buying(self, code: str, date: str) -> bool:
        df = self._get_price_data(
            code,
            (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=10)).strftime('%Y-%m-%d'),
            date
        )
        
        if df is None or len(df) < 4:
            return False
        
        recent = df.tail(4)
        price_up_days = sum(1 for i in range(1, 4) if recent['close'].iloc[i] > recent['close'].iloc[i-1])
        volume_increasing = recent['volume'].iloc[-1] > recent['volume'].iloc[:3].mean() * 1.5
        rsi_rising = recent['rsi'].iloc[-1] > recent['rsi'].iloc[0] if not pd.isna(recent['rsi'].iloc[-1]) else False
        
        return price_up_days >= 2 and volume_increasing and rsi_rising
    
    def _check_positive_news(self, code: str, name: str, date: str) -> bool:
        df = self._get_price_data(
            code,
            (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d'),
            date
        )
        
        if df is None or len(df) < 2:
            return False
        
        latest = df.iloc[-1]
        
        surge = False
        if 'change_pct' in df.columns:
            change_val = latest.get('change_pct', None)
            if change_val is not None and not pd.isna(change_val):
                surge = change_val > 5
        
        if not surge:
            prev = df.iloc[-2]
            change_pct = ((latest['close'] - prev['close']) / prev['close']) * 100
            surge = change_pct > 5
        
        volume_surge = latest['volume'] > df['volume'].iloc[:-1].mean() * 2 if len(df) > 1 else False
        
        return surge and volume_surge
    
    def _calculate_stock_score(self, code: str, date: str) -> Optional[StockScore]:
        info = self.stock_info.get(code, {'name': code, 'market': 'UNKNOWN', 'sector': '기타'})
        
        df = self._get_price_data(
            code,
            (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d'),
            date
        )
        
        if df is None or len(df) < 20:
            return None
        
        latest = df.iloc[-1]
        
        score = StockScore(
            code=code,
            name=info['name'],
            date=date,
            close=latest['close'],
            ma20=latest['ma20'] if not pd.isna(latest['ma20']) else 0,
            sector=info['sector']
        )
        
        # 1. 시가총액 점수
        market_cap = self._simulate_market_cap(code)
        score.market_cap = market_cap
        if market_cap <= 5000:
            score.market_cap_score = 20
        elif market_cap <= 10000:
            score.market_cap_score = 10
        else:
            score.market_cap_score = 0
        
        # 2. 거래량 점수
        vol_ma20 = df['volume'].iloc[-20:].mean()
        if vol_ma20 > 0:
            volume_ratio = latest['volume'] / vol_ma20
            score.volume_ratio = volume_ratio
            if volume_ratio >= 5.0:
                score.volume_score = 25
            elif volume_ratio >= 3.0:
                score.volume_score = 25
            elif volume_ratio >= 2.0:
                score.volume_score = 15
            elif volume_ratio >= 1.5:
                score.volume_score = 10
        
        # 3. 외국인 수급 점수
        if self._check_foreign_buying(code, date):
            score.foreign_score = 15
        
        # 4. 기술적 점수
        if not pd.isna(latest['ma20']) and latest['close'] > latest['ma20']:
            if len(df) >= 2:
                prev = df.iloc[-2]
                if not pd.isna(prev['ma20']) and prev['close'] <= prev['ma20']:
                    score.technical_score = 15
                elif df['close'].iloc[-5:].min() <= latest['ma20'] * 1.02:
                    score.technical_score = 10
                else:
                    score.technical_score = 5
        
        # 5. 뉴스/이벤트 점수
        if self._check_positive_news(code, info['name'], date):
            score.news_score = 15
        
        # 6. 테마 점수
        if info['sector'] in ['AI', '반도체', '바이오', '로봇']:
            score.theme_score = 10
        elif info['sector'] in ['전자']:
            score.theme_score = 5
        
        score.calculate_total()
        return score
    
    def _scan_stocks(self, date: str) -> List[StockScore]:
        all_scores = []
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT DISTINCT code FROM price_data 
        WHERE date = ? AND code NOT LIKE '^%'
        """, (date,))
        codes = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        for code in codes:
            score = self._calculate_stock_score(code, date)
            if score and score.total_score >= self.WATCH_THRESHOLD:
                all_scores.append(score)
        
        all_scores.sort(key=lambda x: x.total_score, reverse=True)
        return all_scores
    
    def _get_position_weight(self, score: int) -> float:
        """점수별 포지션 가중치 반환"""
        if score >= 80:
            return self.POSITION_WEIGHTS[80]
        elif score >= 70:
            return self.POSITION_WEIGHTS[70]
        elif score >= 60:
            return self.POSITION_WEIGHTS[60]
        elif score >= 50:
            return self.POSITION_WEIGHTS[50]
        return 0.0
    
    def _execute_rebalance(self, date: str, top_scores: List[StockScore]):
        selected = [s for s in top_scores if s.total_score >= self.STRONG_BUY_THRESHOLD]
        selected = selected[:self.MAX_POSITIONS]
        
        if not selected:
            return
        
        hold_codes = {s.code for s in selected}
        sell_codes = [code for code in self.positions if code not in hold_codes]
        
        for code in sell_codes:
            self._close_position(code, date, '리밸런싱')
        
        for score in selected:
            if score.code in self.positions:
                continue
            
            weight = self._get_position_weight(score.total_score)
            position_value = self.current_capital * (weight / 100)
            shares = int(position_value / score.close)
            
            if shares > 0:
                trade = Trade(
                    code=score.code,
                    name=score.name,
                    entry_date=date,
                    entry_price=score.close,
                    shares=shares,
                    position_pct=weight,
                    score_at_entry=score.total_score
                )
                self.positions[score.code] = trade
                print(f"   ✅ 진입: {score.name} ({score.code}) @ {score.close:,.0f}원 "
                      f"(점수: {score.total_score}, 비중: {weight}%)")
    
    def _check_stop_loss_take_profit(self, date: str):
        for code, trade in list(self.positions.items()):
            df = self._get_price_data(code, date, date)
            if df is None or df.empty:
                continue
            
            current_price = df.iloc[-1]['close']
            current_return = ((current_price - trade.entry_price) / trade.entry_price) * 100
            
            trade.max_profit_pct = max(trade.max_profit_pct, current_return)
            trade.max_loss_pct = min(trade.max_loss_pct, current_return)
            
            hold_days = (datetime.strptime(date, '%Y-%m-%d') - 
                        datetime.strptime(trade.entry_date, '%Y-%m-%d')).days
            
            if current_return <= self.STOP_LOSS_PCT:
                self._close_position(code, date, '손절', current_price)
                continue
            
            if current_return >= self.TAKE_PROFIT_PCT:
                self._close_position(code, date, '익절', current_price)
                continue
            
            if hold_days >= self.MAX_HOLD_DAYS:
                self._close_position(code, date, '보유만기', current_price)
                continue
    
    def _close_position(self, code: str, date: str, reason: str, exit_price: Optional[float] = None):
        if code not in self.positions:
            return
        
        trade = self.positions.pop(code)
        
        if exit_price is None:
            df = self._get_price_data(code, date, date)
            if df is not None and not df.empty:
                exit_price = df.iloc[-1]['close']
            else:
                exit_price = trade.entry_price
        
        trade.exit_date = date
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.calculate_return()
        
        position_value = trade.shares * trade.entry_price
        exit_value = trade.shares * exit_price
        self.current_capital += (exit_value - position_value)
        
        self.trade_history.append(trade)
        
        emoji = '📈' if trade.return_pct > 0 else '📉'
        print(f"   {emoji} 청산: {trade.name} - {reason} ({trade.return_pct:+.2f}%)")
    
    def _record_daily_value(self, date: str):
        position_value = 0
        for code, trade in self.positions.items():
            df = self._get_price_data(code, date, date)
            if df is not None and not df.empty:
                current_price = df.iloc[-1]['close']
                position_value += trade.shares * current_price
        
        total_value = self.current_capital + position_value
        
        self.daily_values.append({
            'date': date,
            'cash': self.current_capital,
            'position_value': position_value,
            'total_value': total_value,
            'num_positions': len(self.positions)
        })
    
    def _get_position_value(self, code: str, date: str) -> float:
        if code not in self.positions:
            return 0
        df = self._get_price_data(code, date, date)
        if df is None or df.empty:
            return self.positions[code].shares * self.positions[code].entry_price
        return self.positions[code].shares * df.iloc[-1]['close']
    
    def run_backtest(self, start_date: str = '2023-04-01', end_date: str = '2025-12-31'):
        print("=" * 80)
        print("🔥 개선된 폭발적 상승 스캐닝 백테스트")
        print("=" * 80)
        print(f"📅 기간: {start_date} ~ {end_date}")
        print(f"💰 초기 자본: {self.initial_capital:,.0f}원")
        print()
        print("[개선사항]")
        print(f"  • 진입 기준: 60점+ (기존 70점)")
        print(f"  • 익절 기준: +30% (기존 +50%)")
        print(f"  • 보유 기간: 6개월 (기존 3개월)")
        print(f"  • 점수별 포지션: 80점+ 15%, 70점+ 12%, 60점+ 10%")
        print()
        print("=" * 80)
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT DISTINCT date FROM price_data 
        WHERE date BETWEEN ? AND ?
        ORDER BY date
        """, (start_date, end_date))
        trading_days = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        print(f"\n총 {len(trading_days)}거래일 백테스트 시작...\n")
        
        current_month = None
        month_start_value = self.initial_capital
        month_trades = []
        
        for i, date in enumerate(trading_days):
            date_dt = datetime.strptime(date, '%Y-%m-%d')
            
            year_month = date[:7]
            if year_month != current_month:
                if current_month is not None:
                    self.monthly_results.append(MonthlyResult(
                        year_month=current_month,
                        starting_value=month_start_value,
                        ending_value=self.current_capital + sum(
                            self._get_position_value(c, date) for c in self.positions
                        ),
                        trades=month_trades
                    ))
                
                current_month = year_month
                month_start_value = self.current_capital + sum(
                    self._get_position_value(c, date) for c in self.positions
                )
                month_trades = []
                print(f"\n📅 {year_month} 시작 (포트폴리오 가치: {month_start_value:,.0f}원)")
            
            self._check_stop_loss_take_profit(date)
            
            if date_dt.day == self.REBALANCE_DAY or i == 0:
                print(f"\n🔍 리밸런싱: {date}")
                top_scores = self._scan_stocks(date)
                if top_scores:
                    score_60_plus = len([s for s in top_scores if s.total_score >= 60])
                    print(f"   🎯 50점+ 종목: {len(top_scores)}개 / 60점+ 종목: {score_60_plus}개")
                self._execute_rebalance(date, top_scores)
            
            self._record_daily_value(date)
            
            if i % 10 == 0:
                total_value = self.daily_values[-1]['total_value'] if self.daily_values else self.initial_capital
                return_pct = ((total_value - self.initial_capital) / self.initial_capital) * 100
                print(f"   [{date}] 포트폴리오: {total_value:,.0f}원 ({return_pct:+.2f}%) "
                      f"보유: {len(self.positions)}종목")
        
        if current_month:
            final_value = self.current_capital + sum(
                self._get_position_value(c, trading_days[-1]) for c in self.positions
            )
            self.monthly_results.append(MonthlyResult(
                year_month=current_month,
                starting_value=month_start_value,
                ending_value=final_value,
                trades=month_trades
            ))
        
        if self.positions:
            print(f"\n📋 남은 포지션 청산 ({trading_days[-1]})")
            for code in list(self.positions.keys()):
                self._close_position(code, trading_days[-1], '백테스트 종료')
        
        print("\n" + "=" * 80)
        print("✅ 백테스트 완료")
        print("=" * 80)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        print("\n" + "=" * 80)
        print("📊 백테스트 결과 리포트")
        print("=" * 80)
        
        final_value = self.daily_values[-1]['total_value'] if self.daily_values else self.initial_capital
        total_return = ((final_value - self.initial_capital) / self.initial_capital) * 100
        
        total_trades = len(self.trade_history)
        if total_trades == 0:
            print("⚠️ 거래 내역이 없습니다.")
            return {}
        
        wins = [t for t in self.trade_history if t.return_pct > 0]
        losses = [t for t in self.trade_history if t.return_pct <= 0]
        
        win_rate = len(wins) / total_trades * 100
        avg_return = np.mean([t.return_pct for t in self.trade_history])
        avg_win = np.mean([t.return_pct for t in wins]) if wins else 0
        avg_loss = np.mean([t.return_pct for t in losses]) if losses else 0
        
        values = [d['total_value'] for d in self.daily_values]
        peak = values[0]
        max_drawdown = 0
        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        daily_returns = []
        for i in range(1, len(self.daily_values)):
            ret = (self.daily_values[i]['total_value'] - self.daily_values[i-1]['total_value']) / self.daily_values[i-1]['total_value']
            daily_returns.append(ret)
        
        if daily_returns:
            annual_return = np.mean(daily_returns) * 252 * 100
            annual_volatility = np.std(daily_returns) * np.sqrt(252) * 100
            sharpe_ratio = (annual_return - 3) / annual_volatility if annual_volatility > 0 else 0
        else:
            annual_return = annual_volatility = sharpe_ratio = 0
        
        print(f"\n📈 성과 요약")
        print(f"   초기 자본: {self.initial_capital:,.0f}원")
        print(f"   최종 자본: {final_value:,.0f}원")
        print(f"   총 수익률: {total_return:+.2f}%")
        print(f"   연환산 수익률: {annual_return:+.2f}%")
        
        print(f"\n📊 거래 통계")
        print(f"   총 거래: {total_trades}회")
        print(f"   승률: {win_rate:.1f}% ({len(wins)}승 {len(losses)}패)")
        print(f"   평균 수익률: {avg_return:+.2f}%")
        print(f"   평균 수익: {avg_win:+.2f}%")
        print(f"   평균 손실: {avg_loss:.2f}%")
        print(f"   손익비: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "   손익비: N/A")
        
        print(f"\n📉 리스크 지표")
        print(f"   최대 낙폭 (MDD): {max_drawdown:.2f}%")
        print(f"   변동성 (연간): {annual_volatility:.2f}%")
        print(f"   샤프비율: {sharpe_ratio:.2f}")
        
        print(f"\n🏆 TOP 10 수익 거래")
        top_profits = sorted(self.trade_history, key=lambda x: x.return_pct, reverse=True)[:10]
        for i, t in enumerate(top_profits, 1):
            print(f"   {i}. {t.name} ({t.entry_date}): {t.return_pct:+.2f}% ({t.exit_reason})")
        
        print(f"\n😭 TOP 10 손실 거래")
        top_losses = sorted(self.trade_history, key=lambda x: x.return_pct)[:10]
        for i, t in enumerate(top_losses, 1):
            print(f"   {i}. {t.name} ({t.entry_date}): {t.return_pct:.2f}% ({t.exit_reason})")
        
        return {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_value': final_value,
                'total_return_pct': total_return,
                'annual_return_pct': annual_return,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_return': avg_return,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'max_drawdown_pct': max_drawdown,
                'annual_volatility': annual_volatility,
                'sharpe_ratio': sharpe_ratio
            },
            'monthly_results': [
                {
                    'year_month': mr.year_month,
                    'return_pct': mr.return_pct,
                    'num_trades': mr.num_trades,
                    'win_rate': mr.win_rate
                } for mr in self.monthly_results
            ],
            'trades': [
                {
                    'code': t.code,
                    'name': t.name,
                    'entry_date': t.entry_date,
                    'exit_date': t.exit_reason,
                    'return_pct': t.return_pct,
                    'exit_reason': t.exit_reason,
                    'score_at_entry': t.score_at_entry
                } for t in self.trade_history
            ]
        }


def main():
    bt = ImprovedExplosiveGainsBacktest(initial_capital=100_000_000)
    results = bt.run_backtest(start_date='2023-04-01', end_date='2025-12-31')
    
    import os
    os.makedirs('/root/.openclaw/workspace/strg/docs', exist_ok=True)
    
    with open('/root/.openclaw/workspace/strg/docs/improved_explosive_backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print("\n✅ 결과 저장: docs/improved_explosive_backtest_results.json")
    
    return results


if __name__ == '__main__':
    main()
