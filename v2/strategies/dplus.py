"""
V2 Strategy - D+ Leading Stock (홍인기 D+ 주도주)
홍인기 D+ 주도주 매매법
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

import pandas as pd
from typing import Optional, List, Dict, Any
from strategy_base import StrategyBase, Signal, StrategyConfig


class DPlusStrategy(StrategyBase):
    """
    홍인기 D+ 주도주 스캐너
    
    핵심 개념:
    - 주도 테마 감지 (동일 섹터 5개+ 상한가)
    - 대장주 선별 (거래대금, 상승률)
    - D+0~D+2 스윙 매매
    
    매매 규칙:
    1. 상한가 5개+ 섹터 = 주도 테마
    2. 대장주 선별 (거래대금 10억+, 소형주 제외)
    3. 9:30AM 테마 확인 후 진입
    4. D+0: 상한가 일부 수익 + 오버나잇
    5. D+1: 갭상승 추가 수익
    6. D+2: 전량 수익 실현
    """
    
    def __init__(self):
        config = StrategyConfig(
            name="홍인기 D+ 주도주",
            description="주도 테마 대장주 D+0~D+2 스윙",
            min_score=70.0,
            position_size=0.20,
            stop_loss=-0.07,
            take_profit=0.30
        )
        super().__init__(config)
        self.market_data = None
    
    def set_market_data(self, market_df: pd.DataFrame):
        """전체 시장 데이터 설정"""
        self.market_data = market_df
    
    def analyze(self, df: pd.DataFrame, code: str, date: str) -> Optional[Signal]:
        """
        개별 종목 분석
        D+ 전략은 개별 종목보다 시장 맥락이 중요
        """
        if self.market_data is None or len(df) < 5:
            return None
        
        latest = df.iloc[-1]
        
        # 상한가 체크 (KOSDAQ 30%, KOSPI 15%)
        change_pct = latest.get('change_pct', 0) or 0
        is_limit_up = change_pct >= 29.5
        is_strong_rise = change_pct >= 15.0
        
        if not (is_limit_up or is_strong_rise):
            return None
        
        # 거래대금 체크 (10억원 이상)
        amount = latest.get('close', 0) * latest.get('volume', 0)
        if amount < 1_000_000_000:  # 10억원
            return None
        
        # 점수 계산
        score = 0.0
        reasons = []
        metadata = {}
        
        # 상한가 본점
        if is_limit_up:
            score += 50
            reasons.append("상한가 달성")
        elif is_strong_rise:
            score += 30
            reasons.append(f"강한 상승 (+{change_pct:.1f}%)")
        
        # 거래대금 본점
        if amount >= 100_000_000_000:  # 100억+
            score += 25
            reasons.append(f"대형 거래대금 ({amount/1e8:.0f}억)")
        elif amount >= 10_000_000_000:  # 10억+
            score += 15
            reasons.append(f"충분한 거래대금 ({amount/1e8:.0f}억)")
        
        # 연속 상승 체크
        if len(df) >= 3:
            recent_changes = [df.iloc[i]['change_pct'] or 0 for i in range(-3, 0)]
            consecutive_up = sum(1 for c in recent_changes if c > 0)
            if consecutive_up >= 3:
                score += 10
                reasons.append("3일 연속 상승")
        
        metadata['change_pct'] = change_pct
        metadata['amount'] = amount
        metadata['is_limit_up'] = is_limit_up
        
        # Signal 생성
        signal_type = 'buy' if score >= 80 else 'hold'
        
        return Signal(
            code=code,
            name=latest.get('name', code),
            date=date,
            signal_type=signal_type,
            score=score,
            reason=reasons,
            metadata=metadata
        )
    
    def detect_dominant_themes(self, date: str, min_limit_up: int = 5) -> List[Dict]:
        """
        주도 테마 감지
        
        Returns:
            [{'sector': str, 'count': int, 'leaders': [...]}, ...]
        """
        if self.market_data is None:
            return []
        
        daily_data = self.market_data[self.market_data['date'] == date].copy()
        
        # 상한가 종목 필터
        daily_data['is_limit_up'] = daily_data.get('change_pct', 0) >= 29.5
        
        # 섹터별 그룹화
        sector_stats = daily_data.groupby('sector').agg({
            'is_limit_up': 'sum',
            'code': 'count',
            'amount': 'sum'
        }).rename(columns={'code': 'total_stocks', 'is_limit_up': 'limit_up_count'})
        
        # 주도 테마 필터
        dominant = sector_stats[sector_stats['limit_up_count'] >= min_limit_up]
        
        themes = []
        for sector in dominant.index:
            sector_stocks = daily_data[daily_data['sector'] == sector]
            leaders = sector_stocks.nlargest(3, 'change_pct')['code'].tolist()
            
            themes.append({
                'sector': sector,
                'count': dominant.loc[sector, 'limit_up_count'],
                'total': dominant.loc[sector, 'total_stocks'],
                'amount': dominant.loc[sector, 'amount'],
                'leaders': leaders
            })
        
        return sorted(themes, key=lambda x: x['count'], reverse=True)
