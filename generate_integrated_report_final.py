#!/usr/bin/env python3
"""
통합 스캔 리포트 생성기 (2026-04-03)
- explosive_scanner_v7 결과
- honginki_dplus_scanner 결과
- 통합 HTML 리포트 생성
"""

import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List


def load_stock_name_mapping(db_path: str = 'data/level1_prices.db') -> Dict[str, str]:
    """DB에서 종목명 매핑 로드"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT code, name FROM price_data WHERE date = "2026-04-03" AND name IS NOT NULL')
    mapping = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return mapping


def generate_integrated_report():
    """통합 리포트 생성"""
    
    # 종목명 매핑 로드
    name_mapping = load_stock_name_mapping()
    print(f"✅ 종목명 매핑 로드: {len(name_mapping)}개")
    
    # 1. Explosive Scanner 결과 로드
    try:
        with open('scan_results_20260403.json', 'r', encoding='utf-8') as f:
            explosive_data = json.load(f)
        print(f"✅ Explosive Scanner 결과 로드: {explosive_data.get('total_stocks_analyzed', 0)}개 분석")
    except Exception as e:
        print(f"⚠️ Explosive Scanner 결과 없음: {e}")
        explosive_data = {'top_picks': [], 'total_stocks_analyzed': 0, 'qualifying_stocks': 0}
    
    # 2. Honginki Scanner 결과 로드
    try:
        with open('honginki_scan_results_20260403.json', 'r', encoding='utf-8') as f:
            honginki_data = json.load(f)
        print(f"✅ Honginki Scanner 결과 로드: {honginki_data.get('limit_up_count', 0)}개 상한가")
    except Exception as e:
        print(f"⚠️ Honginki Scanner 결과 없음: {e}")
        honginki_data = {'dominant_themes': [], 'strong_stocks': [], 'limit_up_count': 0}
    
    # 상한가 종목 정보
    limit_up_stocks = []
    for theme in honginki_data.get('dominant_themes', []):
        for stock in theme.get('all_stocks', []):
            code = stock.get('code', '')
            name = stock.get('name', '') or name_mapping.get(code, code)
            limit_up_stocks.append({
                'code': code,
                'name': name,
                'sector': theme.get('sector', '기타'),
                'change_pct': stock.get('change_pct', 0),
                'trading_value': stock.get('trading_value', 0)
            })
    
    # 강한 상승 종목
    strong_stocks = []
    for stock in honginki_data.get('strong_stocks', []):
        code = stock.get('code', '')
        name = stock.get('name', '') or name_mapping.get(code, code)
        strong_stocks.append({
            'code': code,
            'name': name,
            'sector': stock.get('sector', '기타'),
            'change_pct': stock.get('change_pct', 0),
            'trading_value': stock.get('trading_value', 0)
        })
    
    # Explosive Scanner TOP 종목
    explosive_picks = []
    for stock in explosive_data.get('top_picks', [])[:20]:
        code = stock.get('code', '')
        name = stock.get('name', '') or name_mapping.get(code, code)
        explosive_picks.append({
            'code': code,
            'name': name,
            'score': stock.get('score', 0),
            'close': stock.get('close', 0),
            'vol_ratio': stock.get('vol_ratio', 0),
            'rsi': stock.get('rsi', 0),
            'adx': stock.get('adx', 0)
        })
    
    # HTML 리포트 생성
    date_str = '2026-04-03'
    date_str_compact = '20260403'
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통합 스캔 리포트 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(90deg, #0f3460, #533483);
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(83, 52, 131, 0.3);
        }}
        h1 {{ font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .subtitle {{ font-size: 1.2em; opacity: 0.9; }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: rgba(255,255,255,0.05);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }}
        .card-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #e94560;
            margin: 10px 0;
        }}
        .card-label {{ color: #aaa; font-size: 0.9em; }}
        .section {{
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .section h2 {{
            color: #e94560;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e94560;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th {{
            background: rgba(233, 69, 96, 0.2);
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #e94560;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .badge-limit-up {{ background: #e94560; color: white; }}
        .badge-strong {{ background: #4ecca3; color: #1a1a2e; }}
        .badge-theme {{ background: #533483; color: white; }}
        .change-up {{ color: #4ecca3; font-weight: bold; }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #888;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 통합 스캔 리포트</h1>
            <div class="subtitle">{date_str} | KOSPI/KOSDAQ 시장 분석</div>
        </header>
        
        <div class="summary-cards">
            <div class="card">
                <div class="card-label">분석 종목</div>
                <div class="card-value">{explosive_data.get('total_stocks_analyzed', 0):,}</div>
            </div>
            <div class="card">
                <div class="card-label">상한가 종목</div>
                <div class="card-value">{honginki_data.get('limit_up_count', 0)}</div>
            </div>
            <div class="card">
                <div class="card-label">주도 테마</div>
                <div class="card-value">{len(honginki_data.get('dominant_themes', []))}</div>
            </div>
            <div class="card">
                <div class="card-label">강한 상승 (+15%)</div>
                <div class="card-value">{len(strong_stocks)}</div>
            </div>
        </div>
"""
    
    # 상한가 종목 섹션
    if limit_up_stocks:
        html += f"""
        <div class="section">
            <h2>🚀 상한가 종목</h2>
            <table>
                <thead>
                    <tr>
                        <th>코드</th>
                        <th>종목명</th>
                        <th>섹터</th>
                        <th>상승률</th>
                        <th>거래대금</th>
                    </tr>
                </thead>
                <tbody>
"""
        for stock in limit_up_stocks:
            html += f"""
                    <tr>
                        <td>{stock['code']}</td>
                        <td><strong>{stock['name']}</strong></td>
                        <td><span class="badge badge-theme">{stock['sector']}</span></td>
                        <td class="change-up">+{stock['change_pct']:.1f}%</td>
                        <td>{stock['trading_value']/1e8:.0f}억</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # 강한 상승 종목 섹션
    if strong_stocks:
        html += f"""
        <div class="section">
            <h2>📈 강한 상승 종목 (+15% 이상)</h2>
            <table>
                <thead>
                    <tr>
                        <th>코드</th>
                        <th>종목명</th>
                        <th>섹터</th>
                        <th>상승률</th>
                        <th>거래대금</th>
                    </tr>
                </thead>
                <tbody>
"""
        for stock in strong_stocks:
            html += f"""
                    <tr>
                        <td>{stock['code']}</td>
                        <td><strong>{stock['name']}</strong></td>
                        <td><span class="badge badge-theme">{stock['sector']}</span></td>
                        <td class="change-up">+{stock['change_pct']:.1f}%</td>
                        <td>{stock['trading_value']/1e8:.0f}억</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # Explosive Scanner TOP 종목 섹션
    if explosive_picks:
        html += f"""
        <div class="section">
            <h2>⚡ KAGGRESSIVE V7 TOP 종목</h2>
            <table>
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>코드</th>
                        <th>종목명</th>
                        <th>점수</th>
                        <th>현재가</th>
                        <th>거래량비율</th>
                        <th>RSI</th>
                        <th>ADX</th>
                    </tr>
                </thead>
                <tbody>
"""
        for i, stock in enumerate(explosive_picks, 1):
            html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{stock['code']}</td>
                        <td><strong>{stock['name']}</strong></td>
                        <td><span class="badge badge-strong">{stock['score']}점</span></td>
                        <td>{stock['close']:,.0f}</td>
                        <td>{stock['vol_ratio']:.1f}x</td>
                        <td>{stock['rsi']:.1f}</td>
                        <td>{stock['adx']:.1f}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # Footer
    html += f"""
        <div class="footer">
            <p>통합 스캔 리포트 | 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                본 리포트는 투자 참고 자료이며, 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    # 파일 저장
    output_file = f'docs/integrated_scan_report_{date_str_compact}.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 통합 리포트 생성 완료: {output_file}")
    
    # 요약 출력
    print("\n" + "="*60)
    print("📊 통합 리포트 요약")
    print("="*60)
    print(f"상한가 종목: {len(limit_up_stocks)}개")
    print(f"강한 상승 종목: {len(strong_stocks)}개")
    print(f"Explosive TOP: {len(explosive_picks)}개")
    print("="*60)


if __name__ == '__main__':
    generate_integrated_report()
