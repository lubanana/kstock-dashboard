#!/usr/bin/env python3
"""
Level 1 Daily Report Generator
Level 1 분석 결과 리포트 생성기
"""

import json
import os
from datetime import datetime
from typing import List, Dict

BASE_PATH = '/home/programs/kstock_analyzer'
DATA_PATH = f'{BASE_PATH}/data/level1_daily'
OUTPUT_PATH = f'{BASE_PATH}/docs'


def load_latest_results() -> Dict:
    """최신 분석 결과 로드"""
    files = [f for f in os.listdir(DATA_PATH) if f.startswith('level1_fullmarket_') and f.endswith('.json')]
    if not files:
        return {}
    
    latest = sorted(files)[-1]
    with open(f'{DATA_PATH}/{latest}', 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_html(data: Dict) -> str:
    """HTML 리포트 생성"""
    date = data.get('date', datetime.now().isoformat())
    results = data.get('results', [])
    
    # 성공한 결과만
    success_results = [r for r in results if r.get('status') == 'success']
    
    # TOP 20
    top20 = sorted(success_results, key=lambda x: x.get('avg_score', 0), reverse=True)[:20]
    
    # BUY 추천 종목
    buy_stocks = [r for r in success_results if r.get('consensus') in ['BUY', 'STRONG BUY']]
    buy_stocks = sorted(buy_stocks, key=lambda x: x.get('avg_score', 0), reverse=True)
    
    # 섹터별 평균
    sector_scores = {}
    for r in success_results:
        sector = r.get('sector', 'Unknown')
        if sector not in sector_scores:
            sector_scores[sector] = []
        sector_scores[sector].append(r.get('avg_score', 0))
    
    sector_avg = {s: round(sum(scores)/len(scores), 1) for s, scores in sector_scores.items()}
    sorted_sectors = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Level 1 Analysis Report - {date[:10]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', -apple-system, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #333;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            color: white;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .date {{ font-size: 1.1em; opacity: 0.9; }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.95);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .stat-value {{ font-size: 2.2em; font-weight: bold; color: #2c3e50; }}
        .stat-label {{ color: #7f8c8d; font-size: 0.9em; margin-top: 5px; }}
        
        .section {{
            background: rgba(255,255,255,0.95);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
            font-size: 1.5em;
        }}
        
        .stock-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95em;
        }}
        .stock-table th {{
            background: linear-gradient(135deg, #34495e, #2c3e50);
            color: white;
            padding: 12px;
            text-align: left;
        }}
        .stock-table td {{ padding: 12px; border-bottom: 1px solid #ecf0f1; }}
        .stock-table tr:hover {{ background: #f8f9fa; }}
        
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        .badge-buy {{ background: #d4edda; color: #155724; }}
        .badge-hold {{ background: #fff3cd; color: #856404; }}
        .badge-sell {{ background: #f8d7da; color: #721c24; }}
        
        .score-high {{ color: #27ae60; font-weight: bold; }}
        .score-mid {{ color: #f39c12; font-weight: bold; }}
        .score-low {{ color: #e74c3c; font-weight: bold; }}
        
        .sector-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        .sector-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: rgba(255,255,255,0.8);
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .sector-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 KStock Level 1 Analysis Report</h1>
            <div class="date">{date[:10]} | {data.get('total', 0)} Stocks Analyzed</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{data.get('total', 0)}</div>
                <div class="stat-label">Total Stocks</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data.get('success', 0)}</div>
                <div class="stat-label">Success</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(buy_stocks)}</div>
                <div class="stat-label">BUY Signals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{round(sum(r.get('avg_score', 0) for r in success_results) / len(success_results), 1) if success_results else 0}</div>
                <div class="stat-label">Avg Score</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 TOP 20 Rankings</h2>
            <table class="stock-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Name</th>
                        <th>Market</th>
                        <th>Sector</th>
                        <th>Score</th>
                        <th>Consensus</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # TOP 20 행 추가
    for i, r in enumerate(top20, 1):
        score = r.get('avg_score', 0)
        score_class = 'score-high' if score >= 60 else 'score-mid' if score >= 50 else 'score-low'
        consensus = r.get('consensus', 'HOLD')
        badge_class = 'badge-buy' if consensus in ['BUY', 'STRONG BUY'] else 'badge-hold' if consensus == 'HOLD' else 'badge-sell'
        
        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><strong>{r['name']}</strong></td>
                        <td>{r.get('market', '-')}</td>
                        <td>{r.get('sector', '-')}</td>
                        <td class="{score_class}">{score}</td>
                        <td><span class="badge {badge_class}">{consensus}</span></td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📈 Sector Performance</h2>
            <div class="sector-grid">
"""
    
    # 섹터 행 추가
    for sector, avg_score in sorted_sectors[:15]:
        html += f"""
                <div class="sector-item">
                    <span>{sector}</span>
                    <span><strong>{avg_score} pts</strong></span>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <div class="footer">
            <p>KStock Level 1 Analysis | Generated by AI Agents</p>
            <p>TECH + QUANT + QUAL + NEWS Agents</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def main():
    """메인 함수"""
    print("Loading latest Level 1 results...")
    data = load_latest_results()
    
    if not data:
        print("No data found!")
        return
    
    print(f"Loaded: {data.get('total', 0)} stocks")
    
    # HTML 생성
    html = generate_html(data)
    
    # 저장
    output_file = f"{OUTPUT_PATH}/level1_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report saved: {output_file}")
    
    # 요약 출력
    results = data.get('results', [])
    success = [r for r in results if r.get('status') == 'success']
    buy_count = len([r for r in success if r.get('consensus') in ['BUY', 'STRONG BUY']])
    
    print(f"\n📊 Summary:")
    print(f"   Total: {len(results)}")
    print(f"   Success: {len(success)}")
    print(f"   BUY Signals: {buy_count}")
    print(f"   Avg Score: {sum(r.get('avg_score', 0) for r in success) / len(success):.1f}")


if __name__ == '__main__':
    main()
