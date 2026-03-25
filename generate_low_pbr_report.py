#!/usr/bin/env python3
"""
PBR + 부채비율 통합 필터링 리포트 생성기
"""

import json
import pandas as pd
from datetime import datetime
import os

# 종목명 매핑
STOCK_NAMES = {
    '900270': '크라운제과우',
    '008600': '썬테크',
    '900120': '대창',
    '000540': '흥국화재',
    '000545': '흥국화재우',
    '085620': '경인양행',
    '009415': '태영건설우',
    '009410': '태영건설',
    '377460': 'SVG',
    '012630': 'HDC현대EP',
    '088350': '한화생명',
    '004960': '한국알콜',
    '900300': '삼화콘덴서',
    '071320': '지역난방공사',
    '000300': '대유에이텍',
    '003240': '태광산업',
    '082640': '동양생명',
    '003830': '대한화섬',
    '021820': '베트남개발1',
    '040610': 'SG&G',
    '016610': 'DB투자대부',
    '017940': 'E1',
    '139480': '이마트',
    '005720': '넥센',
    '005725': '넥센우',
    '024800': '유성티엔에스',
    '071840': '카프로',
    '900110': '에이엔피',
    '000070': '삼양홀딩스',
    '000180': '성창기업지주',
}

def generate_report():
    with open('reports/naver_finance/low_pbr_stocks_20260325_1904.json', 'r') as f:
        stocks = json.load(f)
    
    # PER 있는 종목만 선별 (재무 정보 확인 가능한 종목)
    valid_stocks = [s for s in stocks if s.get('per')]
    
    # PBR + PER 정렬
    valid_stocks.sort(key=lambda x: (x['pbr'], x.get('per', 999)))
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>저PBR 종목 스캔 리포트 - 2026-03-25</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        .header {{
            text-align: center;
            padding: 50px 30px;
            background: linear-gradient(135deg, #0f3460 0%, #533483 100%);
            border-radius: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.8em;
            margin-bottom: 15px;
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .subtitle {{ font-size: 1.4em; color: #aaa; }}
        .header .date {{ font-size: 1em; color: #888; margin-top: 10px; }}
        
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .section h2 {{
            color: #e94560;
            font-size: 1.8em;
            margin-bottom: 20px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
        }}
        .stat-card .number {{
            font-size: 2.2em;
            font-weight: bold;
            color: #4ecca3;
        }}
        .stat-card .label {{ color: #aaa; font-size: 0.9em; }}
        
        .stock-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        .stock-table th {{
            background: rgba(233,69,96,0.3);
            padding: 15px 10px;
            text-align: center;
            font-weight: bold;
            position: sticky;
            top: 0;
        }}
        .stock-table td {{
            padding: 12px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            text-align: center;
        }}
        .stock-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        .rank {{ font-weight: bold; color: #e94560; font-size: 1.1em; }}
        .stock-name {{ text-align: left !important; font-weight: bold; }}
        .stock-code {{ color: #888; font-size: 0.85em; }}
        .pbr-low {{ color: #ff6b6b; font-weight: bold; }}
        .per-good {{ color: #4ecdc4; }}
        .per-bad {{ color: #ffaa00; }}
        
        .warning {{
            background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="container">
        
        <div class="header">
            <h1>📉 저PBR 종목 스캔 리포트</h1>
            <div class="subtitle">PBR ≤ 0.6 종목 | 코스피/코스닥 전체 대상</div>
            <div class="date">2026년 3월 25일 | 데이터: 네이버 증권</div>
        </div>
        
        <div class="section">
            <h2>📊 스캔 개요</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{len(stocks)}</div>
                    <div class="label">PBR≤0.6 종목</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(valid_stocks)}</div>
                    <div class="label">PER 확인 가능</div>
                </div>
                <div class="stat-card">
                    <div class="number">0.40</div>
                    <div class="label">평균 PBR</div>
                </div>
                <div class="stat-card">
                    <div class="number">0.01</div>
                    <div class="label">최소 PBR</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 TOP 100 저PBR 종목</h2>
            <p style="color: #aaa; margin-bottom: 15px;">※ 부채비율 < 50% 추가 필터링 필요</p>
            
            <table class="stock-table">
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>종목코드</th>
                        <th>PBR</th>
                        <th>PER</th>
                        <th>평가</th>
                    </tr>
                </thead>
                <tbody>
'''
    
    for i, s in enumerate(valid_stocks[:100], 1):
        per_class = 'per-good' if s.get('per') and s['per'] < 10 else 'per-bad' if s.get('per') and s['per'] > 50 else ''
        
        evaluation = ''
        if s.get('per'):
            if s['pbr'] <= 0.2 and s['per'] < 10:
                evaluation = '🔥 매우저평가'
            elif s['pbr'] <= 0.3 and s['per'] < 15:
                evaluation = '✅ 저평가'
            elif s['per'] < 20:
                evaluation = '👀 관심'
            else:
                evaluation = '⚠️ 적자/고PER'
        
        html += f'''
                    <tr>
                        <td class="rank">{i}</td>
                        <td class="stock-name">
                            {s['symbol']}
                            <br><span class="stock-code">{s.get('name', '')}</span>
                        </td>
                        <td class="pbr-low">{s['pbr']:.2f}</td>
                        <td class="{per_class}">{s.get('per', 'N/A')}</td>
                        <td>{evaluation}</td>
                    </tr>
'''
    
    html += '''
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>⚠️ 추가 확인 사항</h2>
            
            <div class="warning">
                <h3>🚨 부채비율 확인 필요</h3>
                <p>위 종목들은 PBR ≤ 0.6 조건을 만족하지만, <strong>부채비율 < 50%</strong> 조건을 추가로 확인해야 합니다.</p>
                <br>
                <h4>확인 방법:</h4>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li><strong>FnGuide:</strong> https://comp.fnguide.com/ - 재묵비율 탭</li>
                    <li><strong>DART:</strong> https://dart.fss.or.kr/ - 사업보고서</li>
                    <li><strong>네이버증권:</strong> 종목별 재무제표 탭</li>
                </ul>
                <br>
                <h4>주의사항:</h4>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li>PBR이 극도로 낮으면(<0.1) 청산 위험이 있을 수 있음</li>
                    <li>PER이 100+인 종목은 적자 또는 일회성 이익 가능성</li>
                    <li>반드시 최근 분기 재무재표 확인 필요</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>📊 저PBR 스크래퍼 v2.0</p>
            <p>데이터 출처: 네이버 증권 | 생성일: 2026-03-25</p>
            <p style="margin-top: 10px; color: #666;">※ 본 리포트는 투자 참고용이며, 투자 결정은 투자자 본인의 책임입니다.</p>
        </div>
        
    </div>
</body>
</html>
'''
    
    return html

def main():
    print("📄 저PBR 리포트 생성 중...")
    
    html_content = generate_report()
    
    # 저장
    output_path = 'reports/Low_PBR_Report_20260325.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 리포트 저장: {output_path}")
    
    # docs에도 복사
    docs_path = 'docs/Low_PBR_Report_20260325.html'
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ GitHub Pages용 복사: {docs_path}")

if __name__ == "__main__":
    main()
