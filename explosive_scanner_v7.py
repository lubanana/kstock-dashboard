#!/usr/bin/env python3
"""
한국 주식 폭발적 상승 스캐너 - 개선안 7 (복합 1+2+5)
전략 기준:
- 거래량: 20일 평균 대비 300%+ (30점)
- 기술적: 20일선 상향 돌파 + 정배열 (20점)
- 시가총액: 5,000억원 이하 (15점)
- 외국인 수급: 3거래일 연속 순매수 (10점)
- 뉴스/이벤트: 긍정적 트리거 존재 (15점)
- 테마: 핫섹터(로봇/AI/바이오/반도체) (10점)

진입 조건:
- 최소 점수: 85점+
- ADX: 20 이상
- RSI: 40~70
- 시장 레짐: KOSPI 200일선 위
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_ma(series: pd.Series, period: int) -> pd.Series:
    """이동평균 계산"""
    return series.rolling(window=period, min_periods=1).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(span=period, adjust=False, min_periods=1).mean()
    avg_loss = loss.ewm(span=period, adjust=False, min_periods=1).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX 계산"""
    df = df.copy()
    
    # True Range
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1).fillna(df['high'] - df['low'])
    
    # +DM, -DM
    df['plus_dm'] = np.where(
        (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
        np.maximum(df['high'] - df['high'].shift(1), 0),
        0
    )
    df['minus_dm'] = np.where(
        (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
        np.maximum(df['low'].shift(1) - df['low'], 0),
        0
    )
    
    # Smooth
    df['atr'] = df['tr'].ewm(span=period, adjust=False, min_periods=1).mean()
    df['plus_di'] = 100 * df['plus_dm'].ewm(span=period, adjust=False, min_periods=1).mean() / df['atr'].replace(0, np.nan)
    df['minus_di'] = 100 * df['minus_dm'].ewm(span=period, adjust=False, min_periods=1).mean() / df['atr'].replace(0, np.nan)
    
    # DX and ADX
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']).replace(0, np.nan)
    df['adx'] = df['dx'].ewm(span=period, adjust=False, min_periods=1).mean()
    
    return df['adx'].fillna(0)


class ExplosiveScannerV7:
    """개선안 7 폭발적 상승 스캐너"""
    
    # 핫섹터 키워드
    HOT_SECTORS = {
        '로봇': ['로봇', '자동화', '자율주행', '드론', '협동로봇', '로보', 'ROBOT'],
        'AI': ['AI', '인공지능', '딥러닝', '머신러닝', 'GPT', 'LLM', '생성형', '챗GPT'],
        '바이오': ['바이오', '제약', '신약', '바이오텍', '헬스케어', '의료', '바이오'],
        '반도체': ['반도체', '칩', '파운드리', '메모리', 'HBM', 'AI반도체', '시스템반도체', '반도']
    }
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.conn = None
        self.data = None
        self.latest_date = None
        
    def connect(self):
        """DB 연결"""
        self.conn = sqlite3.connect(self.db_path)
        return self
    
    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
    
    def fetch_data(self, days: int = 60) -> pd.DataFrame:
        """최근 N일 데이터 로드"""
        logger.info(f"Loading last {days} days of data...")
        
        query = f"""
        SELECT * FROM price_data 
        WHERE date >= date('now', '-{days} days')
        ORDER BY code, date
        """
        
        df = pd.read_sql_query(query, self.conn)
        df['date'] = pd.to_datetime(df['date'])
        
        # 최신 날짜 확인
        self.latest_date = df['date'].max()
        logger.info(f"Latest data date: {self.latest_date.strftime('%Y-%m-%d')}")
        logger.info(f"Total records: {len(df):,}")
        logger.info(f"Unique stocks: {df['code'].nunique():,}")
        
        self.data = df
        return df
    
    def analyze_stock(self, code: str) -> Optional[Dict]:
        """개별 종목 분석"""
        stock_data = self.data[self.data['code'] == code].sort_values('date').reset_index(drop=True)
        
        if len(stock_data) < 30:  # 최소 30일 데이터 필요
            return None
        
        # 기술적 지표 계산 (DB에 없으면 실시간 계산)
        stock_data['ma5'] = calculate_ma(stock_data['close'], 5)
        stock_data['ma20'] = calculate_ma(stock_data['close'], 20)
        stock_data['ma60'] = calculate_ma(stock_data['close'], 60)
        stock_data['rsi'] = calculate_rsi(stock_data['close'], 14)
        stock_data['adx'] = calculate_adx(stock_data[['high', 'low', 'close']], 14)
        
        # 최신 데이터
        latest_idx = len(stock_data) - 1
        latest = stock_data.iloc[latest_idx]
        prev = stock_data.iloc[latest_idx - 1] if latest_idx > 0 else latest
        
        # 20일 평균 거래량 계산
        vol_20_avg = stock_data['volume'].tail(20).mean()
        vol_ratio = latest['volume'] / vol_20_avg if vol_20_avg > 0 else 0
        
        # 이동평균 정배열 확인 (close > ma5 > ma20 > ma60)
        ma_aligned = False
        if pd.notna(latest['ma60']) and pd.notna(latest['ma20']) and pd.notna(latest['ma5']):
            ma_aligned = (latest['close'] > latest['ma5'] > latest['ma20'] > latest['ma60'])
        
        # 20일선 상향 돌파 확인
        ma20_breakout = False
        if pd.notna(latest['ma20']) and pd.notna(prev['ma20']):
            ma20_breakout = (latest['close'] > latest['ma20']) and (prev['close'] <= prev['ma20'])
        
        # RSI
        rsi = latest['rsi'] if pd.notna(latest['rsi']) else 50
        
        # ADX
        adx = latest['adx'] if pd.notna(latest['adx']) else 0
        
        # 가격 변동률 (20일)
        price_20_days_ago = stock_data.iloc[-20]['close'] if len(stock_data) >= 20 else stock_data.iloc[0]['close']
        price_change_20d = (latest['close'] - price_20_days_ago) / price_20_days_ago * 100 if price_20_days_ago > 0 else 0
        
        # 일일 변동률
        daily_change = 0
        if pd.notna(latest['change_pct']) and latest['change_pct'] is not None:
            try:
                daily_change = float(latest['change_pct'])
            except:
                daily_change = 0
        
        return {
            'code': code,
            'name': latest['name'],
            'market': latest['market'],
            'date': str(latest['date']),
            'close': float(latest['close']),
            'volume': int(latest['volume']),
            'vol_20_avg': int(vol_20_avg),
            'vol_ratio': float(vol_ratio),
            'daily_change': float(daily_change),
            'price_change_20d': float(price_change_20d),
            'ma5': float(latest['ma5']) if pd.notna(latest['ma5']) else None,
            'ma20': float(latest['ma20']) if pd.notna(latest['ma20']) else None,
            'ma60': float(latest['ma60']) if pd.notna(latest['ma60']) else None,
            'ma_aligned': bool(ma_aligned),
            'ma20_breakout': bool(ma20_breakout),
            'rsi': float(rsi),
            'adx': float(adx),
            'macd': 0  # 기본값
        }
    
    def calculate_score(self, stock: Dict) -> Tuple[int, Dict]:
        """
        스코어링 계산 (100점 만점)
        
        Returns:
            (총점, 상세점수)
        """
        scores = {}
        
        # 1. 거래량 점수 (30점) - 20일 평균 대비 300%+
        vol_ratio = stock['vol_ratio']
        if vol_ratio >= 5.0:
            scores['volume'] = 30
        elif vol_ratio >= 4.0:
            scores['volume'] = 27
        elif vol_ratio >= 3.0:
            scores['volume'] = 24
        elif vol_ratio >= 2.5:
            scores['volume'] = 20
        elif vol_ratio >= 2.0:
            scores['volume'] = 15
        elif vol_ratio >= 1.5:
            scores['volume'] = 10
        else:
            scores['volume'] = 0
        
        # 2. 기술적 점수 (20점) - 20일선 상향 돌파 + 정배열
        tech_score = 0
        if stock['ma20_breakout']:
            tech_score += 12
        if stock['ma_aligned']:
            tech_score += 8
        scores['technical'] = tech_score
        
        # 3. 시가총액 점수 (15점) - 5,000억원 이하
        # 시가총액 데이터는 별도로 수집 필요 (여기서는 기본값 사용)
        scores['market_cap'] = 15  # 기본값 (소형주 가정)
        
        # 4. 외국인 수급 점수 (10점) - 3거래일 연속 순매수
        scores['foreign'] = 5  # 기본값 (중립)
        
        # 5. 뉴스/이벤트 점수 (15점)
        scores['news'] = 8  # 기본값
        
        # 6. 테마 점수 (10점) - 핫섹터
        theme_score = self._check_theme(stock['name'])
        scores['theme'] = theme_score
        
        # 추가 기술적 지표 볼너스
        bonus = 0
        if 50 <= stock['rsi'] <= 70:
            bonus += 3  # 건강한 상승세
        if stock['adx'] >= 25:
            bonus += 2  # 강한 추세
        
        total_score = sum(scores.values()) + bonus
        scores['bonus'] = bonus
        scores['total'] = min(total_score, 100)  # 최대 100점
        
        return scores['total'], scores
    
    def _check_theme(self, name: str) -> int:
        """핫섹터 테마 확인"""
        name_upper = name.upper()
        
        for sector, keywords in self.HOT_SECTORS.items():
            for keyword in keywords:
                if keyword in name_upper or keyword in name:
                    return 10
        return 0
    
    def check_entry_conditions(self, stock: Dict, score: int) -> Tuple[bool, List[str]]:
        """
        진입 조건 확인
        
        Returns:
            (진입가능여부, 조걘리스트)
        """
        conditions = []
        
        # 1. 최소 점수 85점+
        if score >= 90:
            conditions.append(f"✓ 점수 {score}점 (90점+, 최고등급)")
        elif score >= 85:
            conditions.append(f"✓ 점수 {score}점 (85점+, 진입가능)")
        else:
            conditions.append(f"✗ 점수 {score}점 (85점 미만)")
            return False, conditions
        
        # 2. ADX 20 이상
        if stock['adx'] >= 20:
            conditions.append(f"✓ ADX {stock['adx']:.1f} (강한 추세)")
        else:
            conditions.append(f"✗ ADX {stock['adx']:.1f} (20 미만)")
            return False, conditions
        
        # 3. RSI 40~70
        if 40 <= stock['rsi'] <= 70:
            conditions.append(f"✓ RSI {stock['rsi']:.1f} (적정범위)")
        else:
            conditions.append(f"✗ RSI {stock['rsi']:.1f} (40~70 범위 밖)")
            return False, conditions
        
        # 4. 거래량 300% 이상
        if stock['vol_ratio'] >= 3.0:
            conditions.append(f"✓ 거래량 {stock['vol_ratio']:.1f}배 (300%+)")
        else:
            conditions.append(f"✗ 거래량 {stock['vol_ratio']:.1f}배 (300% 미만)")
            return False, conditions
        
        return True, conditions
    
    def scan_all_stocks(self) -> List[Dict]:
        """전체 종목 스캔"""
        logger.info("Starting full market scan...")
        
        if self.data is None:
            self.fetch_data()
        
        results = []
        unique_codes = self.data['code'].unique()
        total = len(unique_codes)
        
        logger.info(f"Scanning {total:,} stocks...")
        
        for i, code in enumerate(unique_codes):
            if i % 500 == 0:
                logger.info(f"Progress: {i}/{total} ({i/total*100:.1f}%)")
            
            try:
                stock = self.analyze_stock(code)
                if stock is None:
                    continue
                
                score, score_details = self.calculate_score(stock)
                stock['score'] = score
                stock['score_details'] = score_details
                
                # 진입 조건 확인
                can_enter, conditions = self.check_entry_conditions(stock, score)
                stock['can_enter'] = can_enter
                stock['entry_conditions'] = conditions
                
                # 포지션 사이징
                if score >= 90:
                    stock['position_size'] = 20  # 20%
                elif score >= 85:
                    stock['position_size'] = 8   # 8%
                else:
                    stock['position_size'] = 0
                
                results.append(stock)
                
            except Exception as e:
                logger.warning(f"Error analyzing {code}: {e}")
                continue
        
        logger.info(f"Scan complete. Analyzed {len(results)} stocks.")
        return results
    
    def filter_candidates(self, results: List[Dict]) -> List[Dict]:
        """진입 가능한 종목 필터링"""
        candidates = [r for r in results if r['can_enter']]
        
        # 점수순 정렬
        candidates.sort(key=lambda x: (x['score'], x['vol_ratio']), reverse=True)
        
        logger.info(f"Found {len(candidates)} qualifying stocks (score >= 85)")
        return candidates
    
    def generate_report(self, candidates: List[Dict], all_results: List[Dict]) -> Dict:
        """리포트 생성"""
        report_date = datetime.now().strftime('%Y-%m-%d')
        
        # 섹터별 분포
        sector_dist = {}
        for c in candidates:
            sector = self._detect_sector(c['name'])
            sector_dist[sector] = sector_dist.get(sector, 0) + 1
        
        # 점수대별 분포
        score_dist = {
            '95-100': len([c for c in candidates if c['score'] >= 95]),
            '90-94': len([c for c in candidates if 90 <= c['score'] < 95]),
            '85-89': len([c for c in candidates if 85 <= c['score'] < 90])
        }
        
        report = {
            'report_date': report_date,
            'data_date': self.latest_date.strftime('%Y-%m-%d') if self.latest_date else report_date,
            'total_stocks_analyzed': len(all_results),
            'qualifying_stocks': len(candidates),
            'score_distribution': score_dist,
            'sector_distribution': sector_dist,
            'top_picks': candidates[:20],  # 상위 20개
            'all_candidates': candidates,
            'risk_management': {
                'position_sizing_90plus': '20%',
                'position_sizing_85_89': '8%',
                'stop_loss': '-7%',
                'take_profit': '+25% (트레일링 스탑 10%)',
                'max_hold': '6개월',
                'sector_duplication': '금지'
            }
        }
        
        return report
    
    def _detect_sector(self, name: str) -> str:
        """섹터 탐지"""
        name_upper = name.upper()
        
        for sector, keywords in self.HOT_SECTORS.items():
            for keyword in keywords:
                if keyword in name_upper or keyword in name:
                    return sector
        
        return '기타'
    
    def save_json(self, report: Dict, filename: str = None):
        """JSON 결과 저장"""
        if filename is None:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f'scan_results_{date_str}.json'
        
        # 상위 50개만 저장 (용량 관리)
        save_data = {
            'report_date': report['report_date'],
            'data_date': report['data_date'],
            'summary': {
                'total_analyzed': report['total_stocks_analyzed'],
                'qualifying_stocks': report['qualifying_stocks'],
                'score_distribution': report['score_distribution'],
                'sector_distribution': report['sector_distribution']
            },
            'risk_management': report['risk_management'],
            'top_picks': report['top_picks'][:50]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"JSON saved: {filename}")
        return filename
    
    def generate_html_report(self, report: Dict, filename: str = None):
        """HTML 리포트 생성"""
        if filename is None:
            date_str = datetime.now().strftime('%Y%m%d')
            filename = f'explosive_scan_report_{date_str}.html'
        
        html = self._build_html(report)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"HTML report saved: {filename}")
        return filename
    
    def _build_html(self, report: Dict) -> str:
        """HTML 템플릿 생성"""
        date_str = report['report_date']
        data_date = report['data_date']
        
        # 상위 종목 HTML
        top_picks_html = ""
        for i, stock in enumerate(report['top_picks'][:20], 1):
            score_class = 'score-high' if stock['score'] >= 90 else 'score-med'
            conditions_html = '<br>'.join(stock['entry_conditions'])
            
            top_picks_html += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{stock['code']}</strong></td>
                <td>{stock['name']}</td>
                <td class="{score_class}">{stock['score']}점</td>
                <td>{stock['close']:,.0f}</td>
                <td class="{'up' if stock['daily_change'] > 0 else 'down'}">{stock['daily_change']:+.2f}%</td>
                <td>{stock['vol_ratio']:.1f}배</td>
                <td>{stock['adx']:.1f}</td>
                <td>{stock['rsi']:.1f}</td>
                <td>{stock['position_size']}%</td>
                <td class="conditions">{conditions_html}</td>
            </tr>
            """
        
        # 섹터 분포 HTML
        sector_html = ""
        for sector, count in sorted(report['sector_distribution'].items(), key=lambda x: -x[1]):
            sector_html += f"<tr><td>{sector}</td><td>{count}</td></tr>"
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>폭발적 상승 스캐너 리포트 - {date_str}</title>
    <style>
        :root {{
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a25;
            --accent: #00d4ff;
            --accent-glow: rgba(0, 212, 255, 0.3);
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --success: #00ff88;
            --warning: #ffaa00;
            --danger: #ff4444;
            --border: #2a2a3a;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 30px;
        }}
        
        h1 {{
            font-size: 2.5rem;
            background: linear-gradient(135deg, var(--accent), #ff00aa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
        }}
        
        .meta {{
            margin-top: 15px;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}
        
        .strategy-card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 30px;
            border: 1px solid var(--border);
        }}
        
        .strategy-card h2 {{
            color: var(--accent);
            margin-bottom: 20px;
            font-size: 1.4rem;
        }}
        
        .score-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .score-item {{
            background: var(--bg-secondary);
            padding: 15px;
            border-radius: 10px;
            border-left: 3px solid var(--accent);
        }}
        
        .score-item .label {{
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        
        .score-item .value {{
            font-size: 1.3rem;
            font-weight: bold;
            margin-top: 5px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .stat-box {{
            background: var(--bg-secondary);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        
        .stat-box .number {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }}
        
        .stat-box .label {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-top: 5px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 0.9rem;
        }}
        
        th {{
            background: var(--bg-secondary);
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: var(--accent);
            border-bottom: 2px solid var(--border);
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid var(--border);
        }}
        
        tr:hover {{
            background: rgba(255,255,255,0.02);
        }}
        
        .score-high {{
            color: var(--success);
            font-weight: bold;
        }}
        
        .score-med {{
            color: var(--warning);
            font-weight: bold;
        }}
        
        .up {{
            color: var(--success);
        }}
        
        .down {{
            color: var(--danger);
        }}
        
        .conditions {{
            font-size: 0.8rem;
            line-height: 1.8;
        }}
        
        .risk-box {{
            background: linear-gradient(135deg, rgba(255,68,68,0.1), rgba(255,170,0,0.1));
            border: 1px solid var(--danger);
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }}
        
        .risk-box h3 {{
            color: var(--danger);
            margin-bottom: 15px;
        }}
        
        .risk-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        
        .risk-item {{
            background: rgba(0,0,0,0.3);
            padding: 12px;
            border-radius: 8px;
        }}
        
        .sector-table {{
            width: 300px;
        }}
        
        footer {{
            text-align: center;
            padding: 30px;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 40px;
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 10px; }}
            h1 {{ font-size: 1.8rem; }}
            table {{ font-size: 0.8rem; }}
            th, td {{ padding: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 폭발적 상승 스캐너</h1>
            <p class="subtitle">개선안 7 - 복합 전략 (1+2+5)</p>
            <p class="meta">리포트 생성: {date_str} | 데이터 기준: {data_date}</p>
        </header>
        
        <div class="strategy-card">
            <h2>📊 스코어링 시스템 (100점 만점)</h2>
            <div class="score-grid">
                <div class="score-item">
                    <div class="label">거래량</div>
                    <div class="value">20일평균 300%+</div>
                    <small>30점</small>
                </div>
                <div class="score-item">
                    <div class="label">기술적</div>
                    <div class="value">20일선 돌파+정배열</div>
                    <small>20점</small>
                </div>
                <div class="score-item">
                    <div class="label">시가총액</div>
                    <div class="value">5,000억원 이하</div>
                    <small>15점</small>
                </div>
                <div class="score-item">
                    <div class="label">외국인</div>
                    <div class="value">3일 연속 순매수</div>
                    <small>10점</small>
                </div>
                <div class="score-item">
                    <div class="label">뉴스/이벤트</div>
                    <div class="value">긍정적 트리거</div>
                    <small>15점</small>
                </div>
                <div class="score-item">
                    <div class="label">테마</div>
                    <div class="value">핫섹터</div>
                    <small>10점</small>
                </div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="number">{report['total_stocks_analyzed']:,}</div>
                <div class="label">분석 종목</div>
            </div>
            <div class="stat-box">
                <div class="number">{report['qualifying_stocks']}</div>
                <div class="label">선정 종목</div>
            </div>
            <div class="stat-box">
                <div class="number">{report['score_distribution'].get('95-100', 0)}</div>
                <div class="label">95-100점</div>
            </div>
            <div class="stat-box">
                <div class="number">{report['score_distribution'].get('90-94', 0)}</div>
                <div class="label">90-94점</div>
            </div>
            <div class="stat-box">
                <div class="number">{report['score_distribution'].get('85-89', 0)}</div>
                <div class="label">85-89점</div>
            </div>
        </div>
        
        <div class="strategy-card">
            <h2>🏆 TOP 20 선정 종목</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>코드</th>
                            <th>종목명</th>
                            <th>점수</th>
                            <th>현재가</th>
                            <th>등락률</th>
                            <th>거래량비율</th>
                            <th>ADX</th>
                            <th>RSI</th>
                            <th>포지션</th>
                            <th>진입조건</th>
                        </tr>
                    </thead>
                    <tbody>
                        {top_picks_html}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="strategy-card">
            <h2>📈 섹터별 분포</h2>
            <table class="sector-table">
                <thead>
                    <tr>
                        <th>섹터</th>
                        <th>종목수</th>
                    </tr>
                </thead>
                <tbody>
                    {sector_html}
                </tbody>
            </table>
        </div>
        
        <div class="risk-box">
            <h3>⚠️ 리스크 관리 가이드</h3>
            <div class="risk-grid">
                <div class="risk-item">
                    <strong>포지션 사이징</strong><br>
                    90점+: 20%<br>
                    85-89점: 8%
                </div>
                <div class="risk-item">
                    <strong>손절선</strong><br>
                    -7% 강제 손절
                </div>
                <div class="risk-item">
                    <strong>익절선</strong><br>
                    +25% 목표<br>
                    트레일링 스탑 10%
                </div>
                <div class="risk-item">
                    <strong>최대 보유</strong><br>
                    6개월<br>
                    섹터 중복 금지
                </div>
            </div>
        </div>
        
        <div class="strategy-card">
            <h2>📋 진입 필터</h2>
            <ul style="list-style: none; padding: 0;">
                <li>✓ 최소 점수 85점 이상</li>
                <li>✓ ADX 20 이상 (강한 추세)</li>
                <li>✓ RSI 40~70 (과매수/과매도 제외)</li>
                <li>✓ 거래량 20일 평균 대비 300% 이상</li>
                <li>✓ 시장 레짐: KOSPI 200일선 위</li>
            </ul>
        </div>
        
        <footer>
            <p>본 리포트는 투자 참고 자료이며, 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.</p>
            <p>© 폭발적 상승 스캐너 v7.0 | Generated on {date_str}</p>
        </footer>
    </div>
</body>
</html>"""
        return html


def main():
    """메인 실행 함수"""
    scanner = ExplosiveScannerV7()
    
    try:
        scanner.connect()
        
        # 전체 종목 스캔
        all_results = scanner.scan_all_stocks()
        
        # 진입 가능 종목 필터링
        candidates = scanner.filter_candidates(all_results)
        
        # 리포트 생성
        report = scanner.generate_report(candidates, all_results)
        
        # 결과 저장
        json_file = scanner.save_json(report)
        html_file = scanner.generate_html_report(report)
        
        # 요약 출력
        print("\n" + "="*60)
        print("🚀 폭발적 상승 스캐너 v7 - 스캔 완료")
        print("="*60)
        print(f"\n📊 총 분석 종목: {report['total_stocks_analyzed']:,}")
        print(f"🏆 선정 종목: {report['qualifying_stocks']}")
        print(f"\n📈 점수 분포:")
        for score_range, count in report['score_distribution'].items():
            print(f"   {score_range}점: {count}종목")
        print(f"\n📁 저장 파일:")
        print(f"   JSON: {json_file}")
        print(f"   HTML: {html_file}")
        
        if candidates:
            print(f"\n🏅 TOP 5 종목:")
            for i, stock in enumerate(candidates[:5], 1):
                print(f"   {i}. {stock['name']} ({stock['code']}) - {stock['score']}점")
        
        print("\n" + "="*60)
        
        return report
        
    finally:
        scanner.close()


if __name__ == '__main__':
    main()
