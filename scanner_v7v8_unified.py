#!/usr/bin/env python3
"""
2604 V7 + V8 Unified Scanner
===========================
V7과 V8을 동시에 실행하고 결과를 통합하는 스캐너

Features:
- V7 (100점 만점, 80점 threshold) + V8 (120점 만점, 90점 threshold)
- 선정 종목에 V7/V8 표기
- 추천 보유일수 계산
- 통합 리포트 생성
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import pandas as pd
import numpy as np
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from trading_calendar import TradingCalendarManager


@dataclass
class Signal:
    """통합 신호 데이터 클래스"""
    code: str
    name: str
    date: str
    v7_score: Optional[int] = None
    v8_score: Optional[int] = None
    price: float = 0.0
    selection_type: str = ""  # "V7", "V8", "V7+V8"
    holding_days: int = 5
    stop_loss: float = 0.0
    target_price: float = 0.0
    reasons: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


class V7V8UnifiedScanner:
    """V7 + V8 통합 스캐너"""
    
    def __init__(self, db_path: str = 'data/level1_prices.db'):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.v7_signals: List[Dict] = []
        self.v8_signals: List[Dict] = []
        
    def connect(self):
        """DB 연결"""
        self.conn = sqlite3.connect(self.db_path)
        
    def close(self):
        """DB 연결 종료"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def run_v7_scan(self, scan_date: str) -> List[Dict]:
        """V7 스캔 실행 (임포트하여 사용)"""
        from scanner_2604_v7_hybrid import Scanner2604V7Hybrid
        
        scanner = Scanner2604V7Hybrid(use_krx=True)
        scanner.connect()
        
        print("🔥 V7 Hybrid 스캔 중...")
        signals = scanner.run_scan(scan_date, top_n=20)
        
        scanner.close()
        return signals
    
    def run_v8_scan(self, scan_date: str) -> List[Dict]:
        """V8 스캔 실행"""
        from scanner_2604_v8_unified import Scanner2604V8Unified
        
        scanner = Scanner2604V8Unified()
        scanner.connect()
        
        print("🔥 V8 Unified 스캔 중...")
        signals = []
        
        # 종목 리스트 로드
        query = f"""
        SELECT DISTINCT code, name 
        FROM price_data 
        WHERE date = '{scan_date}'
        ORDER BY code
        """
        stocks_df = pd.read_sql_query(query, scanner.conn)
        total_stocks = len(stocks_df)
        
        print(f"   대상 종목: {total_stocks}개")
        
        processed = 0
        for idx, row in stocks_df.iterrows():
            code = row['code']
            name = row['name']
            
            try:
                df = scanner.fetch_stock_data(code, scan_date)
                if df is None:
                    continue
                
                df = scanner.calculate_indicators(df)
                latest = df.iloc[-1]
                
                # 하드 필터
                if not (40 <= latest['rsi'] <= 70):
                    continue
                if latest['adx'] < 20:
                    continue
                vol_ratio = latest['volume'] / latest['volume_ma20'] if latest['volume_ma20'] > 0 else 0
                if vol_ratio < 1.5:
                    continue
                
                # 일목균형표
                ichimoku = scanner.generate_ichimoku_signal(df)
                
                # 점수 계산
                scores = {}
                reasons = []
                
                # 거래량 (25점)
                vol_score = 0
                if vol_ratio >= 5.0:
                    vol_score = 25
                    reasons.append(f"거래량 폭발 ({vol_ratio:.1f}x)")
                elif vol_ratio >= 3.0:
                    vol_score = 20
                    reasons.append(f"거래량 급증 ({vol_ratio:.1f}x)")
                elif vol_ratio >= 2.0:
                    vol_score = 15
                    reasons.append(f"거래량 증가 ({vol_ratio:.1f}x)")
                elif vol_ratio >= 1.5:
                    vol_score = 10
                scores['volume'] = vol_score
                
                # 기술적 (20점)
                tech_score = 0
                if 40 <= latest['rsi'] <= 60:
                    tech_score += 10
                    reasons.append(f"RSI 적정 ({latest['rsi']:.1f})")
                if latest['macd_hist'] > 0:
                    tech_score += 5
                if latest['close'] > latest['ma5'] > latest['ma20']:
                    tech_score += 5
                    reasons.append("정배열")
                scores['technical'] = tech_score
                
                # 피볼나치 (20점)
                fib_score = 0
                from fibonacci_target_integrated import calculate_scanner_targets
                targets = calculate_scanner_targets(
                    df=df, entry=latest['close'], atr=latest['atr'], method='hybrid'
                )
                if targets:
                    fib_dist = abs(latest['close'] - targets.get('fib_382', latest['close'])) / latest['close'] * 100
                    if fib_dist < 3:
                        fib_score = 20
                        reasons.append("피볼나치 38.2% 근접")
                    elif fib_dist < 5:
                        fib_score = 15
                        reasons.append("피볼나치 되돌림")
                scores['fibonacci'] = fib_score
                
                # 시장맥락 (15점)
                market_score = 0
                if latest['close'] > latest['ma20']:
                    market_score += 8
                if -3 <= latest['change_pct'] <= 5:
                    market_score += 7
                    reasons.append("안정적 상승")
                scores['market'] = market_score
                
                # 모멘텀 (10점)
                mom_score = 0
                change_20d = (latest['close'] - df.iloc[-20]['close']) / df.iloc[-20]['close'] * 100 if len(df) >= 20 else 0
                if 5 <= change_20d <= 30:
                    mom_score += 10
                elif 0 <= change_20d < 5:
                    mom_score += 5
                scores['momentum'] = mom_score
                
                # 일목균형표 (20점)
                ichi_score = ichimoku.score
                if ichimoku.tk_cross_bullish:
                    reasons.append("TK_CROSS")
                scores['ichimoku'] = ichi_score
                
                # 캔들 (10점)
                candle_score = 0
                body = abs(latest['close'] - latest['open'])
                range_val = latest['high'] - latest['low']
                if range_val > 0 and body / range_val > 0.6:
                    candle_score = 10
                scores['candle'] = candle_score
                
                total_score = sum(scores.values())
                
                # V8: 90점 threshold
                if total_score >= 90:
                    volatility = latest['atr'] / latest['close'] * 100
                    holding, _ = scanner.calculate_holding_period(
                        total_score=total_score,
                        ichimoku=ichimoku,
                        adx=latest['adx'],
                        volatility=volatility
                    )
                    
                    signal = {
                        'code': code,
                        'name': name,
                        'date': scan_date,
                        'score': total_score,
                        'price': latest['close'],
                        'scores': scores,
                        'reasons': reasons,
                        'holding_min': holding.min_days,
                        'holding_max': holding.max_days,
                        'targets': targets,
                        'metadata': {
                            'volume_ratio': vol_ratio,
                            'rsi': latest['rsi'],
                            'adx': latest['adx'],
                            'atr': latest['atr']
                        }
                    }
                    signals.append(signal)
                
            except Exception as e:
                pass
            
            processed += 1
            if processed % 500 == 0:
                print(f"   진행: {processed}/{total_stocks} ({len(signals)}개 신호)")
        
        signals.sort(key=lambda x: x['score'], reverse=True)
        scanner.close()
        return signals
    
    def merge_signals(self, v7_signals: List[Dict], v8_signals: List[Dict]) -> List[Signal]:
        """V7과 V8 신호 통합"""
        merged: Dict[str, Signal] = {}
        
        # V7 신호 추가
        for s in v7_signals:
            code = s['code']
            merged[code] = Signal(
                code=code,
                name=s['name'],
                date=s['date'],
                v7_score=s['score'],
                v8_score=None,
                price=s['price'],
                selection_type="V7",
                holding_days=5,  # V7 기본
                stop_loss=s.get('targets', {}).get('stop_loss', s['price'] * 0.93),
                target_price=s.get('targets', {}).get('tp2', s['price'] * 1.15),
                reasons=s.get('reasons', [])
            )
        
        # V8 신호 추가/병합
        for s in v8_signals:
            code = s['code']
            if code in merged:
                # V7+V8 모두 선정
                merged[code].v8_score = s['score']
                merged[code].selection_type = "V7+V8 ⭐"
                # 보유일수는 V8 기준 사용 (더 정교함)
                merged[code].holding_days = s.get('holding_max', 10)
            else:
                # V8만 선정
                merged[code] = Signal(
                    code=code,
                    name=s['name'],
                    date=s['date'],
                    v7_score=None,
                    v8_score=s['score'],
                    price=s['price'],
                    selection_type="V8 🔥",
                    holding_days=s.get('holding_max', 10),
                    stop_loss=s.get('targets', {}).get('stop_loss', s['price'] * 0.93),
                    target_price=s.get('targets', {}).get('tp2', s['price'] * 1.15),
                    reasons=s.get('reasons', [])
                )
        
        # 점수 기준 정렬 (V7+V8 > V8 > V7)
        def sort_key(sig: Signal):
            if sig.selection_type == "V7+V8 ⭐":
                return (0, -(sig.v7_score or 0 + sig.v8_score or 0))
            elif sig.selection_type == "V8 🔥":
                return (1, -(sig.v8_score or 0))
            else:
                return (2, -(sig.v7_score or 0))
        
        return sorted(merged.values(), key=sort_key)
    
    def generate_html_report(self, signals: List[Signal], scan_date: str, output_file: str):
        """통합 HTML 리포트 생성"""
        
        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2604 V7+V8 통합 리포트 - {scan_date}</title>
    <style>
        :root {{
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #00d084;
            --warning: #ffa502;
            --danger: #ff4757;
            --dark-bg: #1a1a2e;
            --card-bg: #252542;
            --text-primary: #ffffff;
            --text-secondary: #b8b8d1;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', -apple-system, sans-serif;
            background: var(--dark-bg);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border-radius: 16px;
            margin-bottom: 30px;
        }}
        h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .subtitle {{ color: rgba(255,255,255,0.9); font-size: 1.1rem; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .summary-card.v7 {{ border-color: var(--warning); }}
        .summary-card.v8 {{ border-color: var(--danger); }}
        .summary-card.both {{ border-color: var(--success); }}
        .summary-card h3 {{ color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 10px; }}
        .summary-card .value {{ font-size: 2.5rem; font-weight: bold; color: var(--text-primary); }}
        .section-title {{
            font-size: 1.5rem;
            margin: 30px 0 20px;
            padding-left: 16px;
            border-left: 4px solid var(--primary);
        }}
        .signal-table {{
            width: 100%;
            background: var(--card-bg);
            border-radius: 12px;
            overflow: hidden;
            border-collapse: collapse;
        }}
        .signal-table th, .signal-table td {{
            padding: 16px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .signal-table th {{
            background: rgba(255,255,255,0.05);
            font-weight: 600;
            color: var(--text-secondary);
        }}
        .signal-table tr:hover {{ background: rgba(255,255,255,0.03); }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        .badge-v7 {{ background: rgba(255,165,2,0.2); color: var(--warning); }}
        .badge-v8 {{ background: rgba(255,71,87,0.2); color: var(--danger); }}
        .badge-both {{ background: rgba(0,208,132,0.2); color: var(--success); }}
        .score {{ font-weight: bold; font-size: 1.1rem; }}
        .score-v7 {{ color: var(--warning); }}
        .score-v8 {{ color: var(--danger); }}
        .holding-days {{ color: var(--success); font-weight: bold; }}
        .reasons {{ font-size: 0.85rem; color: var(--text-secondary); }}
        .empty-state {{
            text-align: center;
            padding: 60px;
            background: var(--card-bg);
            border-radius: 12px;
            color: var(--text-secondary);
        }}
        @media (max-width: 768px) {{
            h1 {{ font-size: 1.8rem; }}
            .signal-table {{ font-size: 0.85rem; }}
            .signal-table th, .signal-table td {{ padding: 12px 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔥 2604 V7 + V8 통합 리포트</h1>
            <p class="subtitle">Scan Date: {scan_date} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </header>

        <div class="summary">
            <div class="summary-card v7">
                <h3>🔥 V7 Only (80점+)</h3>
                <div class="value">{sum(1 for s in signals if s.selection_type == "V7")}</div>
            </div>
            <div class="summary-card v8">
                <h3>📈 V8 Only (90점+)</h3>
                <div class="value">{sum(1 for s in signals if s.selection_type == "V8 🔥")}</div>
            </div>
            <div class="summary-card both">
                <h3>⭐ V7 + V8 (Both)</h3>
                <div class="value">{sum(1 for s in signals if s.selection_type == "V7+V8 ⭐")}</div>
            </div>
            <div class="summary-card">
                <h3>📊 Total Signals</h3>
                <div class="value">{len(signals)}</div>
            </div>
        </div>
"""
        
        if signals:
            html += f"""
        <h2 class="section-title">📋 선정 종목 상세</h2>
        <table class="signal-table">
            <thead>
                <tr>
                    <th>종목</th>
                    <th>유형</th>
                    <th>V7 점수</th>
                    <th>V8 점수</th>
                    <th>현재가</th>
                    <th>목표가</th>
                    <th>손절가</th>
                    <th>보유일수</th>
                    <th>선정 사유</th>
                </tr>
            </thead>
            <tbody>
"""
            for s in signals:
                badge_class = "badge-both" if "V7+V8" in s.selection_type else ("badge-v8" if "V8" in s.selection_type else "badge-v7")
                v7_display = f"<span class='score score-v7'>{s.v7_score}</span>" if s.v7_score else "-"
                v8_display = f"<span class='score score-v8'>{s.v8_score}</span>" if s.v8_score else "-"
                
                html += f"""
                <tr>
                    <td><strong>{s.name}</strong><br/><small>{s.code}</small></td>
                    <td><span class="badge {badge_class}">{s.selection_type}</span></td>
                    <td>{v7_display}</td>
                    <td>{v8_display}</td>
                    <td>{s.price:,.0f}원</td>
                    <td><span class="positive">{s.target_price:,.0f}원</span></td>
                    <td><span class="negative">{s.stop_loss:,.0f}원</span></td>
                    <td><span class="holding-days">{s.holding_days}일</span></td>
                    <td class="reasons">{', '.join(s.reasons[:3])}</td>
                </tr>
"""
            html += """
            </tbody>
        </table>
"""
        else:
            html += """
        <div class="empty-state">
            <h2>📭 No Signals Detected</h2>
            <p>V7 (80점+) 및 V8 (90점+) 기준을 만족하는 종목이 없습니다.</p>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ HTML 리포트: {output_file}")


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='2604 V7+V8 통합 스캐너')
    parser.add_argument('--date', type=str, default=None, help='스캔 날짜 (YYYY-MM-DD)')
    args = parser.parse_args()
    
    scan_date = args.date if args.date else datetime.now().strftime('%Y-%m-%d')
    
    # 거래일 캘린더로 조정
    cal_manager = TradingCalendarManager()
    cal_manager.connect()
    
    trading_day = cal_manager.adjust_to_trading_day(scan_date, direction='previous')
    if trading_day != scan_date:
        print(f"📅 거래일 조정: {scan_date} → {trading_day}")
    
    # DB 데이터 확인
    conn = sqlite3.connect('data/level1_prices.db')
    query = f"SELECT COUNT(*) as count FROM price_data WHERE date = '{trading_day}'"
    date_check = pd.read_sql_query(query, conn)
    
    if date_check['count'].iloc[0] == 0:
        print(f"⚠️  {trading_day}에 데이터가 없습니다. 이전 거래일 검색...")
        past_days = cal_manager.get_trading_days(
            (datetime.strptime(trading_day, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d'),
            trading_day
        )
        found_date = None
        for day in reversed(past_days[:-1]):
            query = f"SELECT COUNT(*) as count FROM price_data WHERE date = '{day}'"
            check = pd.read_sql_query(query, conn)
            if check['count'].iloc[0] > 0:
                found_date = day
                break
        
        if found_date:
            scan_date = found_date
            print(f"✅ {scan_date}로 스캔 진행")
        else:
            print("❌ 사용 가능한 데이터가 없습니다.")
            conn.close()
            cal_manager.close()
            return
    else:
        scan_date = trading_day
    
    conn.close()
    cal_manager.close()
    
    # 통합 스캔 실행
    print("=" * 70)
    print("🔥 2604 V7 + V8 통합 스캐너")
    print("=" * 70)
    print(f"📅 스캔 날짜: {scan_date}")
    print(f"   - V7: 100점 만점, 80점 threshold")
    print(f"   - V8: 120점 만점, 90점 threshold")
    print("=" * 70)
    
    unified = V7V8UnifiedScanner()
    unified.connect()
    
    # V7 스캔
    v7_signals = unified.run_v7_scan(scan_date)
    print(f"   ✅ V7: {len(v7_signals)}개 신호\n")
    
    # V8 스캔
    v8_signals = unified.run_v8_scan(scan_date)
    print(f"   ✅ V8: {len(v8_signals)}개 신호\n")
    
    # 통합
    merged = unified.merge_signals(v7_signals, v8_signals)
    print(f"📊 통합 결과: {len(merged)}개 종목")
    print(f"   - V7 Only: {sum(1 for s in merged if s.selection_type == 'V7')}")
    print(f"   - V8 Only: {sum(1 for s in merged if s.selection_type == 'V8 🔥')}")
    print(f"   - V7+V8: {sum(1 for s in merged if s.selection_type == 'V7+V8 ⭐')}")
    
    # JSON 저장
    if merged:
        timestamp = datetime.now().strftime('%H%M')
        json_file = f"reports/2604_v7v8_unified_{scan_date.replace('-', '')}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump([{
                'code': s.code,
                'name': s.name,
                'selection_type': s.selection_type,
                'v7_score': s.v7_score,
                'v8_score': s.v8_score,
                'price': s.price,
                'holding_days': s.holding_days,
                'target_price': s.target_price,
                'stop_loss': s.stop_loss,
                'reasons': s.reasons
            } for s in merged], f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 저장: {json_file}")
    
    # HTML 리포트
    timestamp = datetime.now().strftime('%H%M')
    html_file = f"docs/2604_v7v8_unified_{scan_date.replace('-', '')}_{timestamp}.html"
    unified.generate_html_report(merged, scan_date, html_file)
    
    unified.close()
    
    print("\n" + "=" * 70)
    print("✅ V7+V8 통합 스캔 완료!")
    print("=" * 70)


if __name__ == '__main__':
    main()
