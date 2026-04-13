#!/usr/bin/env python3
"""
2604 + V7 통합 스캐너
- 2604 V2의 기술적 지표 + 피볼나치 파동
- V7의 거래량 기반 폭발적 상승 패턴
- KRX 코스닥 지수 연동

통합 스코어링 (100점):
- 거래량 (30점): V7 방식 - 20일 평균 대비 300%+
- 기술적 (25점): 2604 방식 - RSI, MACD, 볼린저, ADX
- 피볼나치 (20점): 2604 방식 - 38.2%~61.8% 되돌림
- 시장맥락 (15점): 코스닥 대비 아웃퍼폼 + 안정적 상승
- 모멘텀 (10점): 20일 가격 변동률 + 연속 상승일

진입 조건: 80점+, ADX 20+, RSI 40~70
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

from v2.core.krx_datasource import KRXDataSource
from v2.core.indicators import Indicators
from fibonacci_target_integrated import calculate_scanner_targets
from trading_calendar_utils import ensure_trading_day_in_db  # 거래일 유틸리티


class Scanner2604V7Hybrid:
    """2604 + V7 통합 스캐너"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db', use_krx: bool = True):
        self.db_path = db_path
        self.use_krx = use_krx
        self.krx = KRXDataSource() if use_krx else None
        self.conn = None
        self.kosdaq_change = 0.0
        
    def connect(self):
        """DB 연결"""
        self.conn = sqlite3.connect(self.db_path)
        return self
    
    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
    
    def fetch_stock_data(self, code: str, end_date: str, days: int = 60) -> Optional[pd.DataFrame]:
        """개별 종목 데이터 로드"""
        query = f"""
        SELECT * FROM price_data 
        WHERE code = '{code}' 
        AND date <= '{end_date}'
        AND date >= date('{end_date}', '-{days} days')
        ORDER BY date ASC
        """
        df = pd.read_sql_query(query, self.conn)
        if len(df) < 30:
            return None
        return df
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        df = df.copy()
        
        # 이동평균
        df['ma5'] = df['close'].rolling(5, min_periods=1).mean()
        df['ma20'] = df['close'].rolling(20, min_periods=1).mean()
        df['ma60'] = df['close'].rolling(60, min_periods=1).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(span=14, adjust=False, min_periods=1).mean()
        avg_loss = loss.ewm(span=14, adjust=False, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False, min_periods=1).mean()
        ema26 = df['close'].ewm(span=26, adjust=False, min_periods=1).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False, min_periods=1).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 볼린저 밴드
        df['bb_middle'] = df['close'].rolling(20, min_periods=1).mean()
        bb_std = df['close'].rolling(20, min_periods=1).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std
        
        # ADX
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1).fillna(df['high'] - df['low'])
        df['atr'] = df['tr'].ewm(span=14, adjust=False, min_periods=1).mean()
        
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0), 0)
        df['minus_dm'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0), 0)
        
        df['plus_di'] = 100 * df['plus_dm'].ewm(span=14, adjust=False, min_periods=1).mean() / df['atr'].replace(0, np.nan)
        df['minus_di'] = 100 * df['minus_dm'].ewm(span=14, adjust=False, min_periods=1).mean() / df['atr'].replace(0, np.nan)
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']).replace(0, np.nan)
        df['adx'] = df['dx'].ewm(span=14, adjust=False, min_periods=1).mean()
        df['adx'] = df['adx'].fillna(0)
        
        # 거래량
        df['volume_ma20'] = df['volume'].rolling(20, min_periods=1).mean()
        
        return df
    
    def analyze_stock(self, code: str, name: str, date: str) -> Optional[Dict]:
        """개별 종목 분석"""
        df = self.fetch_stock_data(code, date)
        if df is None or len(df) < 30:
            return None
        
        # 지표 계산
        df = self.calculate_indicators(df)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # 필수 필터 체크
        rsi = latest['rsi']
        adx = latest['adx']
        vol_ratio = latest['volume'] / latest['volume_ma20'] if latest['volume_ma20'] > 0 else 0
        
        # 하드 필터
        if not (40 <= rsi <= 70):
            return None
        if adx < 20:
            return None
        if vol_ratio < 1.5:
            return None
        
        # 거래정지 필터
        if latest['volume'] == 0:
            return None
        if latest['high'] == latest['low'] == latest['open']:
            return None
        if latest['high'] == 0 or latest['low'] == 0:
            return None
        
        scores = {}
        reasons = []
        metadata = {}
        
        # 1. 거래량 (30점) - V7 방식
        vol_score = 0
        if vol_ratio >= 5.0:
            vol_score = 30
            reasons.append(f"거래량 폭발 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 3.0:
            vol_score = 25
            reasons.append(f"거래량 급증 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 2.0:
            vol_score = 20
            reasons.append(f"거래량 증가 ({vol_ratio:.1f}x)")
        elif vol_ratio >= 1.5:
            vol_score = 15
            reasons.append(f"거래량 확대 ({vol_ratio:.1f}x)")
        
        scores['volume'] = vol_score
        metadata['volume_ratio'] = vol_ratio
        
        # 2. 기술적 (25점) - 2604 방식
        tech_score = 0
        
        # RSI 적정
        if 40 <= rsi <= 60:
            tech_score += 10
            reasons.append(f"RSI 적정 ({rsi:.1f})")
        elif 35 <= rsi < 40 or 60 < rsi <= 65:
            tech_score += 5
        
        # MACD 반전
        macd_bullish = latest['macd_hist'] > 0 and prev['macd_hist'] <= 0
        if macd_bullish:
            tech_score += 8
            reasons.append("MACD 반전")
        elif latest['macd_hist'] > 0:
            tech_score += 4
        
        # 볼린저 하단
        bb_pos = (latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower'])
        if bb_pos < 0.3:
            tech_score += 7
            reasons.append("볼린저 하단")
        
        # 정배열
        ma_aligned = (latest['close'] > latest['ma20'] > latest['ma60'])
        if ma_aligned:
            tech_score += 5
            reasons.append("정배열")
        
        # ADX 강한 추세
        if adx >= 25:
            tech_score += 5
        
        scores['technical'] = min(tech_score, 25)
        metadata['rsi'] = rsi
        metadata['adx'] = adx
        metadata['macd_bullish'] = macd_bullish
        metadata['bb_position'] = bb_pos
        
        # 3. 피볼나치 (20점) - 2604 방식
        fib_score = 0
        recent = df.tail(40)
        swing_high = recent['high'].max()
        swing_low = recent['low'].min()
        
        if swing_high != swing_low:
            diff = swing_high - swing_low
            fib_382 = swing_high - diff * 0.382
            fib_618 = swing_high - diff * 0.618
            current_price = latest['close']
            
            if fib_382 >= current_price >= fib_618:
                fib_score = 20
                reasons.append("피볼나치 되돌림")
        
        scores['fibonacci'] = fib_score
        
        # 4. 시장맥락 (15점)
        market_score = 0
        change_pct = ((latest['close'] - latest['open']) / latest['open']) * 100
        
        if -1 <= change_pct <= 3:
            market_score += 8
            reasons.append(f"안정적 상승 ({change_pct:+.1f}%)")
        
        # 코스닥 대비 아웃퍼폼
        if self.use_krx and self.kosdaq_change != 0:
            vs_kosdaq = change_pct - self.kosdaq_change
            if vs_kosdaq > 3:
                market_score += 7
                reasons.append(f"코스닥대비 강세 (+{vs_kosdaq:.1f}%)")
            elif vs_kosdaq > 0:
                market_score += 3
            metadata['vs_kosdaq'] = vs_kosdaq
        
        scores['market'] = min(market_score, 15)
        metadata['change_pct'] = change_pct
        
        # 5. 모멘텀 (10점)
        mom_score = 0
        
        # 20일 가격 변동률
        price_20_days_ago = df.iloc[-20]['close'] if len(df) >= 20 else df.iloc[0]['close']
        change_20d = (latest['close'] - price_20_days_ago) / price_20_days_ago * 100
        
        if change_20d > 10:
            mom_score += 5
            reasons.append(f"20일 상승률 +{change_20d:.1f}%")
        elif change_20d > 5:
            mom_score += 3
        
        # 연속 상승일
        recent_changes = df.tail(5)['close'].pct_change().dropna()
        up_days = sum(1 for c in recent_changes if c > 0)
        if up_days >= 3:
            mom_score += 5
            reasons.append(f"연속상승 {up_days}일")
        elif up_days >= 2:
            mom_score += 3
        
        scores['momentum'] = min(mom_score, 10)
        metadata['change_20d'] = change_20d
        
        # 총점
        total_score = sum(scores.values())
        
        # 진입 조건: 80점+
        if total_score < 80:
            return None
        
        # 목표가/손절가 계산 (통합 모듈 사용)
        try:
            targets = calculate_scanner_targets(df, latest['close'])
        except Exception as e:
            targets = None
        
        # numpy 타입을 Python 타입으로 변환
        result = {
            'code': code,
            'name': name,
            'date': date,
            'score': int(total_score),
            'price': float(latest['close']),
            'scores': {k: int(v) for k, v in scores.items()},
            'reasons': reasons[:5],
            'metadata': {k: float(v) if isinstance(v, (int, float, np.number)) else bool(v) if isinstance(v, (np.bool_, bool)) else v for k, v in metadata.items()},
            'targets': targets  # 목표가/손절가 추가
        }
        
        return result
    
    def run_scan(self, scan_date: str = None, top_n: int = 20) -> List[Dict]:
        """전체 스캔 실행"""
        print("=" * 70)
        print("🔥 2604 + V7 통합 스캐너")
        print("=" * 70)
        
        if scan_date is None:
            scan_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n📅 스캔 날짜: {scan_date}")
        
        # KRX 시장 데이터
        if self.use_krx and self.krx:
            date_krx = scan_date.replace('-', '')
            market_status = self.krx.get_market_status(date_krx)
            self.kosdaq_change = market_status.get('kosdaq', 0.0)
            print(f"📈 시장 상태: 코스피 {market_status.get('kospi', 0):+.2f}%, 코스닥 {self.kosdaq_change:+.2f}%")
        
        # 대상 종목 로드
        query = f"SELECT DISTINCT code, name FROM price_data WHERE date = '{scan_date}'"
        stocks_df = pd.read_sql_query(query, self.conn)
        
        print(f"📊 대상 종목: {len(stocks_df)}개")
        print("=" * 70)
        
        # 스캔
        results = []
        for i, row in stocks_df.iterrows():
            if i % 500 == 0:
                print(f"   진행: {i}/{len(stocks_df)} ({len(results)}개 신호)")
            
            result = self.analyze_stock(row['code'], row['name'], scan_date)
            if result:
                results.append(result)
        
        # 정렬
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        print("\n" + "=" * 70)
        print(f"✅ 스캔 완료: {len(results)}개 신호 발견")
        print("=" * 70)
        
        return results[:top_n]


def generate_html_report(signals: List[Dict], date: str, output_file: str):
    """HTML 리포트 생성"""
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2604+V7 통합 리포트 - {date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; background: linear-gradient(45deg, #ff6b6b, #feca57); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header p {{ color: #888; font-size: 1.1rem; }}
        .strategy-tag {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 0.9rem;
            margin-top: 10px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-card h3 {{ color: #888; font-size: 0.9rem; margin-bottom: 10px; text-transform: uppercase; }}
        .stat-card .value {{ font-size: 2rem; font-weight: bold; color: #feca57; }}
        .signal-list {{ display: flex; flex-direction: column; gap: 15px; }}
        .signal-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .signal-card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
        .signal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .signal-title {{ display: flex; align-items: center; gap: 15px; }}
        .rank {{
            width: 40px; height: 40px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 1.2rem;
        }}
        .rank.gold {{ background: linear-gradient(135deg, #ffd700, #ffed4e); color: #333; }}
        .rank.silver {{ background: linear-gradient(135deg, #c0c0c0, #e8e8e8); color: #333; }}
        .rank.bronze {{ background: linear-gradient(135deg, #cd7f32, #daa520); color: #fff; }}
        .rank.normal {{ background: rgba(255,255,255,0.2); color: #fff; }}
        .stock-name {{ font-size: 1.3rem; font-weight: bold; }}
        .stock-name a {{ color: #fff; text-decoration: none; }}
        .stock-name a:hover {{ color: #feca57; }}
        .stock-code {{ color: #888; font-size: 0.9rem; }}
        .score {{
            background: linear-gradient(135deg, #ff6b6b, #feca57);
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.1rem;
        }}
        .signal-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}
        .detail-item {{ text-align: center; }}
        .detail-item .label {{ color: #888; font-size: 0.8rem; margin-bottom: 5px; }}
        .detail-item .value {{ font-size: 1.1rem; font-weight: bold; }}
        .reasons {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .reason-tag {{
            background: rgba(255,255,255,0.1);
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
            color: #feca57;
        }}
        .footer {{
            text-align: center;
            padding: 30px 0;
            margin-top: 30px;
            border-top: 2px solid rgba(255,255,255,0.1);
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 2604 + V7 통합 스캐너</h1>
            <p>개선된 거래량 기반 + 기술적 분석 하이브리드</p>
            <span class="strategy-tag">진입 점수: 80+ | ADX 20+ | RSI 40~70</span>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>총 신호</h3>
                <div class="value">{len(signals)}</div>
            </div>
            <div class="stat-card">
                <h3>평균 점수</h3>
                <div class="value">{sum(s['score'] for s in signals) / len(signals):.1f}</div>
            </div>
            <div class="stat-card">
                <h3>최고 점수</h3>
                <div class="value">{max((s['score'] for s in signals), default=0):.0f}</div>
            </div>
            <div class="stat-card">
                <h3>90점 이상</h3>
                <div class="value">{sum(1 for s in signals if s['score'] >= 90)}</div>
            </div>
        </div>
        
        <div class="signal-list">
"""
    
    for i, signal in enumerate(signals, 1):
        scores = signal['scores']
        
        if i == 1:
            rank_class = "gold"
        elif i == 2:
            rank_class = "silver"
        elif i == 3:
            rank_class = "bronze"
        else:
            rank_class = "normal"
        
        html += f"""
            <div class="signal-card">
                <div class="signal-header">
                    <div class="signal-title">
                        <div class="rank {rank_class}">{i}</div>
                        <div>
                            <div class="stock-name"><a href="https://finance.naver.com/item/main.nhn?code={signal['code']}" target="_blank">{signal['name']} ↗</a></div>
                            <div class="stock-code">{signal['code']}</div>
                        </div>
                    </div>
                    <div class="score">{signal['score']:.0f}점</div>
                </div>
                <div class="signal-details">
                    <div class="detail-item">
                        <div class="label">현재가</div>
                        <div class="value">{signal['price']:,.0f}원</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">거래량</div>
                        <div class="value">{scores.get('volume', 0):.0f}점</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">기술적</div>
                        <div class="value">{scores.get('technical', 0):.0f}점</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">피볼나치</div>
                        <div class="value">{scores.get('fibonacci', 0):.0f}점</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">시장맥락</div>
                        <div class="value">{scores.get('market', 0):.0f}점</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">모멘텀</div>
                        <div class="value">{scores.get('momentum', 0):.0f}점</div>
                    </div>
                </div>
                <div class="targets" style="background: rgba(255,255,255,0.03); border-radius: 10px; padding: 15px; margin: 15px 0; border: 1px solid rgba(254,202,87,0.2);">
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; text-align: center;">
                        <div>
                            <div style="color: #888; font-size: 0.75rem; margin-bottom: 3px;">손절가</div>
                            <div style="color: #ff6b6b; font-weight: bold; font-size: 0.95rem;">{signal.get('targets', {}).get('stop_loss', 0):,.0f}원</div>
                            <div style="color: #ff6b6b; font-size: 0.7rem;">{signal.get('targets', {}).get('stop_pct', 0):+.1f}%</div>
                        </div>
                        <div>
                            <div style="color: #888; font-size: 0.75rem; margin-bottom: 3px;">TP1</div>
                            <div style="color: #4cd137; font-weight: bold; font-size: 0.95rem;">{signal.get('targets', {}).get('tp1', 0):,.0f}원</div>
                            <div style="color: #4cd137; font-size: 0.7rem;">{signal.get('targets', {}).get('tp1_pct', 0):+.1f}%</div>
                        </div>
                        <div>
                            <div style="color: #888; font-size: 0.75rem; margin-bottom: 3px;">TP2 ⭐</div>
                            <div style="color: #feca57; font-weight: bold; font-size: 0.95rem;">{signal.get('targets', {}).get('tp2', 0):,.0f}원</div>
                            <div style="color: #feca57; font-size: 0.7rem;">{signal.get('targets', {}).get('tp2_pct', 0):+.1f}% | 1:{signal.get('targets', {}).get('risk_reward_tp2', 0):.1f}</div>
                        </div>
                        <div>
                            <div style="color: #888; font-size: 0.75rem; margin-bottom: 3px;">TP3</div>
                            <div style="color: #4cd137; font-weight: bold; font-size: 0.95rem;">{signal.get('targets', {}).get('tp3', 0):,.0f}원</div>
                            <div style="color: #4cd137; font-size: 0.7rem;">{signal.get('targets', {}).get('tp3_pct', 0):+.1f}%</div>
                        </div>
                    </div>
                </div>
                <div class="reasons">
"""
        for reason in signal['reasons'][:5]:
            html += f'                    <span class="reason-tag">{reason}</span>\n'
        
        html += """                </div>
            </div>
"""
    
    html += f"""        
        </div>
        
        <div class="footer">
            <p>2604+V7 Hybrid Scanner | Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin-top: 10px; font-size: 0.85rem;">※ 본 리포트는 투자 참고용이며, 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.</p>
        </div>
    </div>
</body>
</html>"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 리포트: {output_file}")


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='2604+V7 통합 스캐너')
    parser.add_argument('--date', type=str, default=None, help='스캔 날짜 (YYYY-MM-DD)')
    args = parser.parse_args()
    
    scan_date = args.date if args.date else datetime.now().strftime('%Y-%m-%d')
    
    scanner = Scanner2604V7Hybrid(use_krx=True)
    scanner.connect()
    
    # 거래일 조정 (주말/공휴일 → 최근 거래일)
    scan_date = ensure_trading_day_in_db(scan_date, db_path=scanner.db_path)
    
    signals = scanner.run_scan(scan_date, top_n=20)
    
    if signals:
        # JSON 저장
        json_file = f"reports/2604_v7_hybrid_{scan_date.replace('-', '')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 저장: {json_file}")
        
        # HTML 리포트
        html_file = f"docs/2604_v7_hybrid_{scan_date.replace('-', '')}.html"
        generate_html_report(signals, scan_date, html_file)
        
        # 콘솔 출력
        print("\n" + "=" * 70)
        print("📊 TOP 신호")
        print("=" * 70)
        for i, s in enumerate(signals[:5], 1):
            print(f"\n{i}. {s['name']} ({s['code']}) - {s['score']:.0f}점")
            print(f"   현재가: {s['price']:,.0f}원")
            # 목표가/손절가 출력
            if s.get('targets'):
                t = s['targets']
                print(f"   🛑 손절가: {t['stop_loss']:,.0f}원 ({t['stop_pct']:+.1f}%)")
                print(f"   🎯 TP2: {t['tp2']:,.0f}원 ({t['tp2_pct']:+.1f}%) | 손익비 1:{t['risk_reward_tp2']:.1f}")
            print(f"   사유: {', '.join(s['reasons'][:3])}")
    
    scanner.close()
    
    print("\n" + "=" * 70)
    print("✅ 2604+V7 통합 스캔 완료!")
    print("=" * 70)


if __name__ == '__main__':
    main()
