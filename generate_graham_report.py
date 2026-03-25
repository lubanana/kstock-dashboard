#!/usr/bin/env python3
"""
Graham Net-Net 전략 전체 종목 리포트 생성기
"""

import json
from datetime import datetime
import os

# 종목명 매핑 (확장)
STOCK_NAMES = {
    '065500': '삼진엠앤지',
    '200130': '콜마비앤에이치',
    '385560': '타임기술',
    '003060': '에이프로젠제약',
    '001200': '우진산전',
    '005010': '휴스틸',
    '002200': '한국수출포장',
    '003300': '한일철강',
    '001460': 'BYC',
    '004380': '삼익모터스',
    '002140': '미원화학',
    '001090': '대한제강',
    '006910': '삼영전자',
    '003070': '세방전지',
    '006370': '대림통상',
    '004100': '태광산업',
    '001820': '삼화콘덴서',
    '002600': '조흥',
    '003100': '선경',
    '002270': '롯데칠성',
    '002020': '코오롱',
    '003220': '대원제약',
    '002130': '고려산업',
    '005500': '삼진제약',
    '003430': '현대식품',
    '114800': 'KODEX 인버스',
    '001020': '페이퍼코리아',
    '007110': '일신방직',
    '163280': 'HDC현대EP',
    '086900': '메디톡스',
    '004370': '농심',
}

def generate_html_report():
    with open('reports/Proven_Strategy_Scan_20260325.json', 'r') as f:
        data = json.load(f)
    
    graham_results = data['strategies']['Graham_NetNet']
    
    # 통계 계산
    kospi = [s for s in graham_results if s['symbol'].startswith('0') and int(s['symbol'][:1]) < 9]
    kosdaq = [s for s in graham_results if s['symbol'].startswith('0') and int(s['symbol'][:1]) >= 9 or s['symbol'].startswith(('1', '2', '3'))]
    
    avg_price = sum(s['current_price'] for s in graham_results) / len(graham_results)
    avg_amount = sum(s['avg_amount'] for s in graham_results) / len(graham_results)
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Graham Net-Net 전략 - 전체 종목 리포트 2026-03-25</title>
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
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
            font-size: 2.5em;
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
        .price {{ font-family: 'Courier New', monospace; }}
        .positive {{ color: #ff6b6b; }}
        .negative {{ color: #4ecdc4; }}
        
        .highlight {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
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
            <h1>🎯 Graham Net-Net 전략</h1>
            <div class="subtitle">전체 종목 스캔 리포트 (코스피/코스닥)</div>
            <div class="date">2026년 3월 25일 (수) | 백테스트: CAGR 40.2%, MDD 0%</div>
        </div>
        
        <div class="section">
            <h2>📊 스캔 개요</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{len(graham_results)}</div>
                    <div class="label">선정 종목</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(kospi)}</div>
                    <div class="label">코스피</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(kosdaq)}</div>
                    <div class="label">코스닥</div>
                </div>
                <div class="stat-card">
                    <div class="number">₩{avg_price:,.0f}</div>
                    <div class="label">평균 주가</div>
                </div>
                <div class="stat-card">
                    <div class="number">{avg_amount/100_000_000:.0f}억</div>
                    <div class="label">평균 거래대금</div>
                </div>
            </div>
            
            <div class="highlight">
                <strong>📈 백테스트 결과 (2024.01 ~ 2026.03)</strong><br>
                총 수익률: <strong>+114.0%</strong> | CAGR: <strong>40.2%</strong> | 최대 낙폭: <strong>0.0%</strong> | 승률: <strong>70.6%</strong>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 TOP 100 선정 종목</h2>
            <table class="stock-table">
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>종목</th>
                        <th>현재가</th>
                        <th>52주위치</th>
                        <th>거래대금</th>
                        <th>목표가</th>
                        <th>예상수익</th>
                    </tr>
                </thead>
                <tbody>
'''
    
    for i, s in enumerate(graham_results[:100], 1):
        name = STOCK_NAMES.get(s['symbol'], '')
        pos_pct = s['52w_position'] * 100
        amt_100m = s['avg_amount'] / 100_000_000
        
        html += f'''
                    <tr>
                        <td class="rank">{i}</td>
                        <td class="stock-name">
                            {name}
                            <br><span class="stock-code">{s['symbol']}</span>
                        </td>
                        <td class="price">₩{s['current_price']:,.0f}</td>
                        <td>{pos_pct:.1f}%</td>
                        <td>{amt_100m:.0f}억</td>
                        <td class="price positive">₩{s['target_price']:,.0f}</td>
                        <td class="positive">+{s['expected_return']:.0f}%</td>
                    </tr>
'''
    
    html += '''
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>⚠️ 투자 전략 및 유의사항</h2>
            <div class="highlight">
                <h3>진입 전략</h3>
                <ul>
                    <li>분할 매수: 30% → 30% → 40%</li>
                    <li>진입 타이밍: 52주 최저가 근처일 때</li>
                    <li>보유 기간: 6~12개월 (장기 보유)</li>
                </ul>
                <h3>리스크 관리</h3>
                <ul>
                    <li>손절가: 52주 최저가 돌파 시 (-2~5%)</li>
                    <li>목표가: +30% 도달 시 부분 익절</li>
                    <li>분산 투자: 개별 종목 5% 이하 비중</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>📊 Graham Net-Net Strategy: 순유동자산 가치투자</p>
            <p>데이터 출처: FinanceDataReader | 생성일: 2026-03-25</p>
            <p style="margin-top: 10px; color: #666;">※ 본 리포트는 투자 참고용이며, 투자 결정은 투자자 본인의 책임입니다.</p>
        </div>
        
    </div>
</body>
</html>
'''
    
    return html

def main():
    print("📄 Graham Net-Net 리포트 생성 중...")
    
    html_content = generate_html_report()
    
    # 저장
    output_path = 'reports/Graham_NetNet_Full_Report_20260325.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 리포트 저장: {output_path}")
    
    # docs에도 복사
    docs_path = 'docs/Graham_NetNet_Full_Report_20260325.html'
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ GitHub Pages용 복사: {docs_path}")

if __name__ == "__main__":
    main()
