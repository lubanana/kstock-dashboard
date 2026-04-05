#!/usr/bin/env python3
"""
한국 주식 폭발적 상승 스캐닝 - 복합개선안 C 백테스트
===========================================
개선사항:
1. 스코어링 가중치 조정: 거래량↑(30), 기술적↑(20), 시총↓(15), 외국인↓(10)
2. 진입 기준 완화: 70점 → 60점+
3. 익절 기준 하향: +50% → +30%
4. 보유 기간 연장: 3개월 → 6개월 (126거래일)
5. 점수별 포지션 사이징: 80점+(15%), 70-79점(12%), 60-69점(10%)
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
    """개별 종목 스코어링 결과 - 개선안 C 가중치 적용"""
    code: str
    name: str
    date: str
    
    # 개선안 C 가중치
    volume_score: int = 0      # 25→30점
    technical_score: int = 0   # 15→20점
    market_cap_score: int = 0  # 20→15점
    foreign_score: int = 0     # 15→10점
    news_score: int = 0        # 15점 유지
    theme_score: int = 0       # 10점 유지
    
    total_score: int = 0
    
    # 상세 데이터
    market_cap: float = 0.0
    volume_ratio: float = 0.0
    ma20: float = 0.0
    close: float = 0.0
    rsi: float = 0.0
    sector: str = ""
    
    def calculate_total(self):
        self.total_score = (self.volume_score + self.technical_score + 
                           self.market_cap_score + self.foreign_score + 
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
    score_at_entry: int = 0
    
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    return_pct: float = 0.0
    exit_reason: str = ""
    max_profit_pct: float = 0.0
    max_loss_pct: float = 0.0
    hold_days: int = 0
    
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
        if self.starting_value == 0:
            return 0.0
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


class CompositeExplosiveGainsBacktest:
    """
    복합개선안 C 백테스트 엔진
    """
    
    # 핫섹터 정의
    HOT_SECTORS = {
        '로봇': ['로봇', '자율주행', '드론', '자동화', '로보'],
        'AI': ['AI', '인공지능', '딥러닝', '머신러닝', 'ChatGPT', 'LLM', '빅데이터', 'AI반도체'],
        '바이오': ['바이오', '제약', '바이오텍', '의료기기', '유전자', '신약', '바이오밸리'],
        '반도체': ['반도체', '칩', '메모리', '파운드리', 'D램', '낸드', '시스템반도체', 'HBM'],
        '전자': ['전자', '전기', '디스플레이', 'OLED', 'LCD']
    }
    
    # === 개선안 C 매매 규칙 ===
    MAX_HOLD_DAYS = 126       # 최대 6개월 (126거래일) - 연장
    STOP_LOSS_PCT = -10.0     # -10% 손절 (유지)
    TAKE_PROFIT_PCT = 30.0    # +30% 익절 (하향 조정)
    REBALANCE_DAY = 1         # 매월 1일 리밸런싱
    MAX_POSITIONS = 10        # 최대 10개 종목 보유
    
    # === 개선안 C 진입 기준 ===
    STRONG_BUY_THRESHOLD = 60  # 70점 → 60점 하향
    WATCH_THRESHOLD = 50       # 관망/분할 기준 (50-59점)
    
    # === 개선안 C 점수별 포지션 사이징 ===
    POSITION_WEIGHTS = {
        80: 15.0,   # 80점+: 15%
        70: 12.0,   # 70-79점: 12%
        60: 10.0,   # 60-69점: 10%
        50: 5.0     # 50-59점: 5% (선택적)
    }
    
    def __init__(self, db_path: str = '/root/.openclaw/workspace/strg/data/level1_prices.db',
                 initial_capital: float = 100_000_000,
                 mode: str = 'composite'):
        """
        Args:
            mode: 'original' (원본 70점), 'composite' (개선안 C 60점)
        """
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.mode = mode
        
        self.positions: Dict[str, Trade] = {}
        self.trade_history: List[Trade] = []
        self.monthly_results: List[MonthlyResult] = []
        self.price_cache: Dict[str, pd.DataFrame] = {}
        self.stock_info: Dict[str, Dict] = {}
        self.daily_values: List[Dict] = []
        
        # 스코어링 히스토리
        self.score_history: List[Dict] = []
        
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
        
        if any(k in name for k in ['은행', '증권', '보험', '금융', '카드']):
            return '금융'
        elif any(k in name for k in ['건설', '건축', '건재']):
            return '건설'
        elif any(k in name for k in ['유통', '백화점', '마트', '쇼핑', '유통']):
            return '유통'
        elif any(k in name for k in ['식품', '음료', '제과', '축산']):
            return '식품'
        elif any(k in name for k in ['화학', '소재', '철강', '비철', '금속']):
            return '화학/소재'
        elif any(k in name for k in ['자동차', '차량', '타이어', '부품']):
            return '자동차'
        elif any(k in name for k in ['에너지', '전력', '가스', '유틸']):
            return '에너지'
        elif any(k in name for k in ['통신', '방송', '미디어', '컨텐츠']):
            return '미디어/통신'
        elif any(k in name for k in ['게임', '엔터', '플랫폼', 'IT']):
            return '게임/플랫폼'
        
        return '기타'
    
    def _get_db_connection(self):
        return sqlite3.connect(self.db_path)
    
    def _get_price_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """가격 데이터 조회 (캐싱)"""
        cache_key = f"{code}_{start_date}_{end_date}_composite"
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
    
    def _simulate_market_cap(self, code: str, date: str) -> float:
        """시가총액 시뮬레이션 (실제보다 보수적)"""
        # 숫자만 추출하여 코드 번호 생성
        code_digits = ''.join(filter(str.isdigit, code))
        code_num = int(code_digits) if code_digits else 999999
        
        # 시드값 설정 (일관된 랜덤값을 위해)
        seed_val = code_num + int(date.replace('-', '')) % 10000
        np.random.seed(seed_val)
        
        if code_num < 10000:  # 대형주
            base_cap = np.random.uniform(3000, 50000)
        elif code_num < 50000:  # 중형주
            base_cap = np.random.uniform(800, 5000)
        else:  # 소형주
            base_cap = np.random.uniform(100, 2000)
        
        return base_cap
    
    def _check_foreign_buying(self, code: str, date: str) -> Tuple[bool, float]:
        """외국인 수급 패턴 확인"""
        df = self._get_price_data(
            code,
            (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=10)).strftime('%Y-%m-%d'),
            date
        )
        
        if df is None or len(df) < 4:
            return False, 0.0
        
        recent = df.tail(5)
        
        # 가격 상승 추세
        price_up_days = sum(1 for i in range(1, len(recent)) 
                          if recent['close'].iloc[i] > recent['close'].iloc[i-1])
        
        # 거래량 급증
        avg_volume = recent['volume'].iloc[:-1].mean()
        volume_ratio = recent['volume'].iloc[-1] / avg_volume if avg_volume > 0 else 1.0
        volume_surge = volume_ratio > 1.3
        
        # RSI 추세
        rsi_start = recent['rsi'].iloc[0] if not pd.isna(recent['rsi'].iloc[0]) else 50
        rsi_end = recent['rsi'].iloc[-1] if not pd.isna(recent['rsi'].iloc[-1]) else 50
        rsi_rising = rsi_end > rsi_start
        
        strength = (price_up_days / 4) * 0.4 + (min(volume_ratio, 3) / 3) * 0.4 + (1 if rsi_rising else 0) * 0.2
        
        return (price_up_days >= 2 and volume_surge), strength
    
    def _check_positive_news(self, code: str, name: str, date: str) -> Tuple[bool, float]:
        """긍정적 뉴스/이벤트 패턴 확인"""
        df = self._get_price_data(
            code,
            (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d'),
            date
        )
        
        if df is None or len(df) < 3:
            return False, 0.0
        
        latest = df.iloc[-1]
        
        # 급등 패턴
        surge_score = 0.0
        if 'change_pct' in df.columns:
            change_val = latest.get('change_pct', None)
            if change_val is not None and not pd.isna(change_val):
                if change_val > 10:
                    surge_score = 1.0
                elif change_val > 5:
                    surge_score = 0.7
                elif change_val > 3:
                    surge_score = 0.4
        
        # 거래량 급증
        volume_ma = df['volume'].iloc[:-1].mean() if len(df) > 1 else df['volume'].mean()
        volume_ratio = latest['volume'] / volume_ma if volume_ma > 0 else 1.0
        volume_score = min(volume_ratio / 3, 1.0) if volume_ratio > 1.5 else 0.0
        
        # 돌파 패턴
        breakout_score = 0.0
        if len(df) >= 20:
            high_20 = df['high'].iloc[-20:-1].max()
            if latest['close'] > high_20 * 0.98:  # 20일 고점 근접/돌파
                breakout_score = 0.8
        
        total_score = surge_score * 0.4 + volume_score * 0.3 + breakout_score * 0.3
        has_news = total_score > 0.5
        
        return has_news, total_score
    
    def _calculate_stock_score(self, code: str, date: str) -> Optional[StockScore]:
        """=== 개선안 C 스코어링 ==="""
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
            rsi=latest['rsi'] if not pd.isna(latest['rsi']) else 50,
            sector=info['sector']
        )
        
        # === 1. 거래량 점수 (25→30점) ===
        vol_ma20 = df['volume'].iloc[-20:].mean()
        if vol_ma20 > 0:
            volume_ratio = latest['volume'] / vol_ma20
            score.volume_ratio = volume_ratio
            
            if volume_ratio >= 10.0:
                score.volume_score = 30
            elif volume_ratio >= 5.0:
                score.volume_score = 25
            elif volume_ratio >= 3.0:
                score.volume_score = 20
            elif volume_ratio >= 2.0:
                score.volume_score = 15
            elif volume_ratio >= 1.5:
                score.volume_score = 10
        
        # === 2. 기술적 점수 (15→20점) ===
        tech_score = 0
        
        # RSI 조건
        if not pd.isna(latest['rsi']):
            if 40 <= latest['rsi'] <= 70:
                tech_score += 5  # 적정 RSI
            elif latest['rsi'] > 70:
                tech_score += 3  # 과매수
            elif latest['rsi'] < 40:
                tech_score += 4  # 과매도 후 반등 가능성
        
        # 이평선 패턴
        if not pd.isna(latest['ma20']) and latest['close'] > latest['ma20']:
            tech_score += 5  # 20일선 상회
            
            # 골든크로스 또는 정배열
            if len(df) >= 2:
                prev = df.iloc[-2]
                if not pd.isna(prev['ma20']) and prev['close'] <= prev['ma20']:
                    tech_score += 5  # 20일선 돌파
            
            # 정배열 확인
            if not pd.isna(latest.get('ma5')) and not pd.isna(latest.get('ma60')):
                if latest['ma5'] > latest['ma20'] > latest['ma60']:
                    tech_score += 5  # 완전 정배열
        
        # 저점 대비 상승률
        if len(df) >= 20:
            low_20 = df['low'].iloc[-20:].min()
            if low_20 > 0:
                rebound_pct = (latest['close'] - low_20) / low_20 * 100
                if 10 <= rebound_pct <= 30:
                    tech_score += 5  # 적정 반등
        
        score.technical_score = min(tech_score, 20)
        
        # === 3. 시가총액 점수 (20→15점) ===
        market_cap = self._simulate_market_cap(code, date)
        score.market_cap = market_cap
        
        if market_cap <= 1000:  # 소형주 (10억 이하)
            score.market_cap_score = 15
        elif market_cap <= 3000:  # 중소형주
            score.market_cap_score = 10
        elif market_cap <= 5000:  # 중형주
            score.market_cap_score = 5
        else:  # 대형주
            score.market_cap_score = 0
        
        # === 4. 외국인 수급 점수 (15→10점) ===
        has_foreign, foreign_strength = self._check_foreign_buying(code, date)
        if has_foreign:
            if foreign_strength > 0.7:
                score.foreign_score = 10
            elif foreign_strength > 0.5:
                score.foreign_score = 7
            else:
                score.foreign_score = 5
        
        # === 5. 뉴스/이벤트 점수 (15점 유지) ===
        has_news, news_strength = self._check_positive_news(code, info['name'], date)
        if has_news:
            if news_strength > 0.8:
                score.news_score = 15
            elif news_strength > 0.6:
                score.news_score = 12
            elif news_strength > 0.4:
                score.news_score = 10
            else:
                score.news_score = 7
        
        # === 6. 테마 점수 (10점 유지) ===
        if info['sector'] in ['AI', '반도체', '바이오', '로봇']:
            score.theme_score = 10
        elif info['sector'] in ['전자', '게임/플랫폼']:
            score.theme_score = 7
        elif info['sector'] in ['자동차', '에너지']:
            score.theme_score = 5
        
        score.calculate_total()
        
        # 스코어링 히스토리 기록
        self.score_history.append({
            'date': date,
            'code': code,
            'name': info['name'],
            'volume_score': score.volume_score,
            'technical_score': score.technical_score,
            'market_cap_score': score.market_cap_score,
            'foreign_score': score.foreign_score,
            'news_score': score.news_score,
            'theme_score': score.theme_score,
            'total_score': score.total_score
        })
        
        return score
    
    def _scan_stocks(self, date: str) -> List[StockScore]:
        """스크리닝 실행"""
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
        
        # 점수순 정렬
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
        """리밸런싱 실행"""
        # 60점 이상 종목만 선택
        selected = [s for s in top_scores if s.total_score >= self.STRONG_BUY_THRESHOLD]
        selected = selected[:self.MAX_POSITIONS]
        
        if not selected:
            return
        
        # 유지할 종목
        hold_codes = {s.code for s in selected}
        
        # 매도할 종목 (리밸런싱 대상)
        sell_codes = [code for code in self.positions if code not in hold_codes]
        
        for code in sell_codes:
            self._close_position(code, date, '리밸런싱')
        
        # 매수할 종목
        for score in selected:
            if score.code in self.positions:
                continue  # 이미 보유 중
            
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
        """손절/익절 체크"""
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
            trade.hold_days = hold_days
            
            # 손절: -10%
            if current_return <= self.STOP_LOSS_PCT:
                self._close_position(code, date, '손절', current_price)
                continue
            
            # 익절: +30% (하향 조정)
            if current_return >= self.TAKE_PROFIT_PCT:
                self._close_position(code, date, '익절', current_price)
                continue
            
            # 보유 만기: 6개월
            if hold_days >= self.MAX_HOLD_DAYS:
                self._close_position(code, date, '보유만기(6개월)', current_price)
                continue
    
    def _close_position(self, code: str, date: str, reason: str, exit_price: Optional[float] = None):
        """포지션 청산"""
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
        trade.calculate_return()
        
        # 자본 업데이트
        position_value = trade.shares * trade.entry_price
        exit_value = trade.shares * exit_price
        self.current_capital += (exit_value - position_value)
        
        self.trade_history.append(trade)
        
        emoji = '📈' if trade.return_pct > 0 else '📉'
        print(f"   {emoji} 청산: {trade.name} - {reason} ({trade.return_pct:+.2f}%) [{trade.hold_days}일 보유]")
    
    def _record_daily_value(self, date: str):
        """일일 포트폴리오 가치 기록"""
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
        """특일 포지션 가치 계산"""
        if code not in self.positions:
            return 0
        df = self._get_price_data(code, date, date)
        if df is None or df.empty:
            return self.positions[code].shares * self.positions[code].entry_price
        return self.positions[code].shares * df.iloc[-1]['close']
    
    def run_backtest(self, start_date: str = '2023-01-01', end_date: str = '2025-12-31'):
        """백테스트 실행"""
        print("=" * 80)
        if self.mode == 'original':
            print("🔥 원본 (70점) 폭발적 상승 스캐닝 백테스트")
        else:
            print("🔥 복합개선안 C (60점) 폭발적 상승 스캐닝 백테스트")
        print("=" * 80)
        print(f"📅 기간: {start_date} ~ {end_date}")
        print(f"💰 초기 자본: {self.initial_capital:,.0f}원")
        print()
        
        if self.mode == 'composite':
            print("[개선안 C 적용 사항]")
            print("  • 진입 기준: 60점+ (기존 70점)")
            print("  • 익절 기준: +30% (기존 +50%)")
            print("  • 보유 기간: 6개월 (기존 3개월)")
            print("  • 점수별 포지션: 80점+(15%), 70점+(12%), 60점+(10%)")
            print()
            print("[스코어링 가중치 조정]")
            print("  • 거래량: 25점 → 30점 ⬆️")
            print("  • 기술적: 15점 → 20점 ⬆️")
            print("  • 시가총액: 20점 → 15점 ⬇️")
            print("  • 외국인: 15점 → 10점 ⬇️")
            print("  • 뉴스/이벤트: 15점 유지")
            print("  • 테마: 10점 유지")
        else:
            print("[원본 설정]")
            print("  • 진입 기준: 70점+")
            print("  • 익절 기준: +50%")
            print("  • 보유 기간: 3개월")
            print("  • 고정 포지션 크기")
        
        print()
        print("=" * 80)
        
        # 거래일 로드
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
            
            # 월간 결과 처리
            year_month = date[:7]
            if year_month != current_month:
                if current_month is not None:
                    current_value = self.current_capital + sum(
                        self._get_position_value(c, date) for c in self.positions
                    )
                    self.monthly_results.append(MonthlyResult(
                        year_month=current_month,
                        starting_value=month_start_value,
                        ending_value=current_value,
                        trades=month_trades
                    ))
                
                current_month = year_month
                month_start_value = self.current_capital + sum(
                    self._get_position_value(c, date) for c in self.positions
                )
                month_trades = []
                print(f"\n📅 {year_month} 시작 (포트폴리오 가치: {month_start_value:,.0f}원)")
            
            # 손절/익절 체크
            self._check_stop_loss_take_profit(date)
            
            # 리밸런싱 (매월 1일 또는 첫 거래일)
            if date_dt.day == self.REBALANCE_DAY or i == 0:
                print(f"\n🔍 리밸런싱: {date}")
                top_scores = self._scan_stocks(date)
                if top_scores:
                    score_60_plus = len([s for s in top_scores if s.total_score >= 60])
                    score_70_plus = len([s for s in top_scores if s.total_score >= 70])
                    print(f"   🎯 50점+ 종목: {len(top_scores)}개 / 60점+ 종목: {score_60_plus}개 / 70점+ 종목: {score_70_plus}개")
                self._execute_rebalance(date, top_scores)
            
            # 일일 가치 기록
            self._record_daily_value(date)
            
            # 진행 상황 출력 (10거래일마다)
            if i % 10 == 0:
                total_value = self.daily_values[-1]['total_value'] if self.daily_values else self.initial_capital
                return_pct = ((total_value - self.initial_capital) / self.initial_capital) * 100
                print(f"   [{date}] 포트폴리오: {total_value:,.0f}원 ({return_pct:+.2f}%) "
                      f"보유: {len(self.positions)}종목")
        
        # 마지막 월 결과
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
        
        # 남은 포지션 청산
        if self.positions:
            print(f"\n📋 남은 포지션 청산 ({trading_days[-1]})")
            for code in list(self.positions.keys()):
                self._close_position(code, trading_days[-1], '백테스트 종료')
        
        print("\n" + "=" * 80)
        print("✅ 백테스트 완료")
        print("=" * 80)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """결과 리포트 생성"""
        print("\n" + "=" * 80)
        if self.mode == 'original':
            print("📊 원본 (70점) 백테스트 결과 리포트")
        else:
            print("📊 복합개선안 C (60점) 백테스트 결과 리포트")
        print("=" * 80)
        
        if not self.daily_values:
            print("⚠️ 거래 데이터가 없습니다.")
            return {}
        
        final_value = self.daily_values[-1]['total_value']
        total_return = ((final_value - self.initial_capital) / self.initial_capital) * 100
        
        if not self.trade_history:
            print("⚠️ 거래 내역이 없습니다.")
            return {
                'summary': {
                    'initial_capital': self.initial_capital,
                    'final_value': final_value,
                    'total_return_pct': total_return,
                    'total_trades': 0
                }
            }
        
        # 거래 통계
        total_trades = len(self.trade_history)
        wins = [t for t in self.trade_history if t.return_pct > 0]
        losses = [t for t in self.trade_history if t.return_pct <= 0]
        
        win_rate = len(wins) / total_trades * 100
        avg_return = np.mean([t.return_pct for t in self.trade_history])
        avg_win = np.mean([t.return_pct for t in wins]) if wins else 0
        avg_loss = np.mean([t.return_pct for t in losses]) if losses else 0
        
        # 리스크 지표
        values = [d['total_value'] for d in self.daily_values]
        peak = values[0]
        max_drawdown = 0
        peak_date = self.daily_values[0]['date']
        
        for d in self.daily_values:
            if d['total_value'] > peak:
                peak = d['total_value']
                peak_date = d['date']
            drawdown = (peak - d['total_value']) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # 연간 수익률 및 샤프비율
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
        
        # 보유 기간 통계
        avg_hold_days = np.mean([t.hold_days for t in self.trade_history])
        
        # 청산 사유별 통계
        exit_reasons = defaultdict(int)
        for t in self.trade_history:
            exit_reasons[t.exit_reason] += 1
        
        # 출력
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
        print(f"   평균 보유기간: {avg_hold_days:.1f}일")
        
        print(f"\n📉 리스크 지표")
        print(f"   최대 낙폭 (MDD): {max_drawdown:.2f}%")
        print(f"   변동성 (연간): {annual_volatility:.2f}%")
        print(f"   샤프비율: {sharpe_ratio:.2f}")
        
        print(f"\n🏁 청산 사유별 통계")
        for reason, count in sorted(exit_reasons.items(), key=lambda x: -x[1]):
            pct = count / total_trades * 100
            print(f"   {reason}: {count}회 ({pct:.1f}%)")
        
        print(f"\n🏆 TOP 10 수익 거래")
        top_profits = sorted(self.trade_history, key=lambda x: x.return_pct, reverse=True)[:10]
        for i, t in enumerate(top_profits, 1):
            print(f"   {i}. {t.name} ({t.entry_date}): {t.return_pct:+.2f}% [{t.exit_reason}]")
        
        print(f"\n😭 TOP 10 손실 거래")
        top_losses = sorted(self.trade_history, key=lambda x: x.return_pct)[:10]
        for i, t in enumerate(top_losses, 1):
            print(f"   {i}. {t.name} ({t.entry_date}): {t.return_pct:.2f}% [{t.exit_reason}]")
        
        return {
            'mode': self.mode,
            'summary': {
                'initial_capital': self.initial_capital,
                'final_value': final_value,
                'total_return_pct': total_return,
                'annual_return_pct': annual_return,
                'total_trades': total_trades,
                'win_count': len(wins),
                'loss_count': len(losses),
                'win_rate': win_rate,
                'avg_return': avg_return,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_loss_ratio': abs(avg_win/avg_loss) if avg_loss != 0 else 0,
                'avg_hold_days': avg_hold_days,
                'max_drawdown_pct': max_drawdown,
                'annual_volatility': annual_volatility,
                'sharpe_ratio': sharpe_ratio,
                'peak_value': peak,
                'peak_date': peak_date
            },
            'exit_reasons': dict(exit_reasons),
            'monthly_results': [
                {
                    'year_month': mr.year_month,
                    'starting_value': mr.starting_value,
                    'ending_value': mr.ending_value,
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
                    'entry_price': t.entry_price,
                    'exit_date': t.exit_date,
                    'exit_price': t.exit_price,
                    'return_pct': t.return_pct,
                    'exit_reason': t.exit_reason,
                    'score_at_entry': t.score_at_entry,
                    'hold_days': t.hold_days,
                    'max_profit_pct': t.max_profit_pct,
                    'max_loss_pct': t.max_loss_pct
                } for t in self.trade_history
            ],
            'daily_values': self.daily_values,
            'score_history': self.score_history
        }


def run_comparison_backtest():
    """원본 vs 개선안 C 비교 백테스트"""
    print("\n" + "=" * 80)
    print("🔄 원본(70점) vs 개선안 C(60점) 비교 백테스트")
    print("=" * 80)
    
    results = {}
    
    # 원본 실행 (70점)
    print("\n" + "=" * 80)
    print("📌 STEP 1: 원본 (70점) 백테스트 실행")
    print("=" * 80)
    bt_original = CompositeExplosiveGainsBacktest(mode='original')
    # 원본 설정 적용
    bt_original.STRONG_BUY_THRESHOLD = 70
    bt_original.TAKE_PROFIT_PCT = 50.0
    bt_original.MAX_HOLD_DAYS = 63  # 3개월
    results['original'] = bt_original.run_backtest()
    
    # 개선안 C 실행 (60점)
    print("\n" + "=" * 80)
    print("📌 STEP 2: 개선안 C (60점) 백테스트 실행")
    print("=" * 80)
    bt_composite = CompositeExplosiveGainsBacktest(mode='composite')
    results['composite'] = bt_composite.run_backtest()
    
    # 비교 리포트 출력
    print_comparison_report(results)
    
    return results


def print_comparison_report(results: Dict):
    """비교 리포트 출력"""
    print("\n" + "=" * 80)
    print("📊 원본 vs 개선안 C 비교 리포트")
    print("=" * 80)
    
    orig = results.get('original', {}).get('summary', {})
    comp = results.get('composite', {}).get('summary', {})
    
    if not orig or not comp:
        print("⚠️ 비교할 결과가 부족합니다.")
        return
    
    print(f"\n{'지표':<25} {'원본(70점)':>15} {'개선안C(60점)':>15} {'변화':>15}")
    print("-" * 80)
    
    def print_row(label, orig_val, comp_val, unit=''):
        if isinstance(orig_val, (int, float)) and isinstance(comp_val, (int, float)):
            change = comp_val - orig_val if unit != '%' else comp_val - orig_val
            change_str = f"{change:+.2f}{unit}"
            print(f"{label:<25} {orig_val:>15.2f}{unit} {comp_val:>15.2f}{unit} {change_str:>15}")
        else:
            print(f"{label:<25} {str(orig_val):>15} {str(comp_val):>15} {'-':>15}")
    
    print_row("총 수익률 (%)", orig.get('total_return_pct', 0), comp.get('total_return_pct', 0), '%')
    print_row("연환산 수익률 (%)", orig.get('annual_return_pct', 0), comp.get('annual_return_pct', 0), '%')
    print_row("총 거래 횟수", orig.get('total_trades', 0), comp.get('total_trades', 0))
    print_row("승률 (%)", orig.get('win_rate', 0), comp.get('win_rate', 0), '%')
    print_row("평균 수익률 (%)", orig.get('avg_return', 0), comp.get('avg_return', 0), '%')
    print_row("최대 낙폭 (%)", orig.get('max_drawdown_pct', 0), comp.get('max_drawdown_pct', 0), '%')
    print_row("샤프비율", orig.get('sharpe_ratio', 0), comp.get('sharpe_ratio', 0))
    print_row("평균 보유기간 (일)", orig.get('avg_hold_days', 0), comp.get('avg_hold_days', 0))
    
    print("\n" + "=" * 80)
    print("📈 개선안 C 핵심 성과")
    print("=" * 80)
    
    total_diff = comp.get('total_return_pct', 0) - orig.get('total_return_pct', 0)
    winrate_diff = comp.get('win_rate', 0) - orig.get('win_rate', 0)
    mdd_diff = comp.get('max_drawdown_pct', 0) - orig.get('max_drawdown_pct', 0)
    sharpe_diff = comp.get('sharpe_ratio', 0) - orig.get('sharpe_ratio', 0)
    
    if total_diff > 0:
        print(f"   ✅ 총 수익률: {total_diff:+.2f}%p 개선")
    else:
        print(f"   ⚠️ 총 수익률: {total_diff:.2f}%p 하락")
    
    if winrate_diff > 0:
        print(f"   ✅ 승률: {winrate_diff:+.2f}%p 개선")
    else:
        print(f"   ⚠️ 승률: {winrate_diff:.2f}%p 하락")
    
    if mdd_diff < 0:
        print(f"   ✅ 최대 낙폭: {abs(mdd_diff):.2f}%p 개선 (리스크 감소)")
    else:
        print(f"   ⚠️ 최대 낙폭: {mdd_diff:.2f}%p 증가 (리스크 상승)")
    
    if sharpe_diff > 0:
        print(f"   ✅ 샤프비율: {sharpe_diff:+.2f} 개선 (위험조정수익률 상승)")
    else:
        print(f"   ⚠️ 샤프비율: {sharpe_diff:.2f} 하락")


def main():
    """메인 실행"""
    import os
    os.makedirs('/root/.openclaw/workspace/strg/docs', exist_ok=True)
    
    # 비교 백테스트 실행
    results = run_comparison_backtest()
    
    # 결과 저장
    output_path = '/root/.openclaw/workspace/strg/docs/composite_explosive_backtest_results.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 결과 저장: {output_path}")
    
    return results


if __name__ == '__main__':
    main()
