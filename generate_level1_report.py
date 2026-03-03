#!/usr/bin/env python3
"""
Level 1 Report Generator
Level 1 분석 결과 HTML 리포트 생성기
"""

import json
import os
from datetime import datetime
from typing import List, Dict

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/docs'
DATA_PATH = f'{BASE_PATH}/data/level1_daily'


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
    results = data.get('results', [])
    date = data.get('date', datetime.now().isoformat())
    
    # 정렬 및 필터링
    success_results = [r for r in results if r.get('status') == 'success']
    sorted_results = sorted(success_results, key=lambda x: x.get('avg_score', 0), reverse=True)
    
    # TOP 20
    top20 = sorted_results[:20]
    
    # 섹터별 평균
    sector_data = {}
    for r in success_results:
        sector = r.get('sector', 'Unknown')
        if sector not in sector_data:
            sector_data[sector] = []
        sector_data[sector].append(r['avg_score'])
    
    sector_avg = {s: round(sum(scores)/len(scores), 1) for s, scores in sector_data.items()}
    sorted_sectors = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)
    
    # 추천 집계
    strong_buy = len([r for r in success_results if r.get('consensus') == 'STRONG BUY'])
    buy = len([r for r in success_results if r.get('consensus') == 'BUY'])
    hold = len([r for r in success_results if r.get('consensus') == 'HOLD'])
    sell = len([r for r in success_results if r.get('consensus') == 'SELL'])
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Level 1 Analysis Report - {date[:10]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .date {{ opacity: 0.9; }}
        
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; text-align: center; }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; color: #2c3e50; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
        
        .section {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; margin-bottom: 25px; }}
        .section h2 {{ color: #2c3e50; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #3498db; }}
        
        .stock-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        .stock-table th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
        .stock-table td {{ padding: 12px; border-bottom: 1px solid #ecf0f1; }}
        .stock-table tr:hover {{ background: #f8f9fa; }}
        
        .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 500; }}
        .badge-strong-buy {{ background: #27ae60; color: white; }}
        .badge-buy {{ background: #2ecc71; color: white; }}
        .badge-hold {{ background: #f39c12; color: white; }}
        .badge-sell {{ background: #e74c3c; color: white; }}
        
        .score-high {{ color: #27ae60; font-weight: bold; }}
        .score-mid {{ color: #f39c12; font-weight: bold; }}
        .score-low {{ color: #e74c3c; font-weight: bold; }}
        
        .sector-list {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
        .sector-item {{ display: flex; justify-content: space-between; padding: 10px; background: #f8f9fa; border-radius: 8px; }}
        
        .recommendation-chart {{ display: flex; gap: 10px; margin-top: 20px; }}
        .chart-bar {{ padding: 15px; border-radius: 10px; color: white; text-align: center; flex: 1; }}
        .chart-strong-buy {{ background: #27ae60; }}
        .chart-buy {{ background: #2ecc71; }}
        .chart-hold {{ background: #f39c12; }}
        .chart-sell {{ background: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Level 1 Analysis Report</h1>
            <div class="date">{date[:10]} | {data.get('total', 0)} Stocks Analyzed</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{data.get('success', 0)}</div>
                <div class="stat-label">Stocks Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{round(sum(r.get('avg_score', 0) for r in success_results) / len(success_results), 1) if success_results else 0}</div>
                <div class="stat-label">Average Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{strong_buy + buy}</div>
                <div class="stat-label">BUY Signals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sorted_results[0].get('avg_score', 0) if sorted_results else 0}</div>
                <div class="stat-label">Top Score</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Recommendation Distribution</h2>
            <div class="recommendation-chart">
                <div class="chart-bar chart-strong-buy">
                    <div style="font-size: 2em;">{strong_buy}</div>
                    <div>STRONG BUY</div>
                </div>
                <div class="chart-bar chart-buy">
                    <div style="font-size: 2em;">{buy}</div>
                    <div>BUY</div>
                </div>
                <div class="chart-bar chart-hold">
                    <div style="font-size: 2em;">{hold}</div>
                    <div>HOLD</div>
                </div>
                <div class="chart-bar chart-sell">
                    <div style="font-size: 2em;">{sell}</div>
                    <div>SELL</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 TOP 20 Stocks</h2>
            <table class="stock-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Name</th>
                        <th>Market</th>
                        <th>Sector</th>
                        <th>Score</th>
                        <th>Consensus</th>
                        <th>Agents</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # TOP 20 행 추가
    for i, r in enumerate(top20, 1):
        score = r.get('avg_score', 0)
        score_class = 'score-high' if score >= 70 else 'score-mid' if score >= 50 else 'score-low'
        
        consensus = r.get('consensus', 'HOLD')
        badge_class = {
            'STRONG BUY': 'badge-strong-buy',
            'BUY': 'badge-buy',
            'HOLD': 'badge-hold',
            'SELL': 'badge-sell'
        }.get(consensus, 'badge-hold')
        
        agents = r.get('agents', {})
        agent_scores = f"T:{agents.get('TECH', {}).get('score', 0)} Q:{agents.get('QUANT', {}).get('score', 0)} L:{agents.get('QUAL', {}).get('score', 0)} N:{agents.get('NEWS', {}).get('score', 0)}"
        
        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><strong>{r.get('name', '')}</strong></td>
                        <td>{r.get('market', '')}</td>
                        <td>{r.get('sector', '')}</td>
                        <td class="{score_class}">{score}</td>
                        <td><span class="badge {badge_class}">{consensus}</span></td>
                        <td><small>{agent_scores}</small></td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📊 Sector Performance</h2>
            <div class="sector-list">
"""
    
    # 섹터별 평균
    for sector, avg_score in sorted_sectors[:10]:
        html += f"""
                <div class="sector-item">
                    <span>{sector}</span>
                    <span><strong>{avg_score} pts</strong> ({len(sector_data[sector])} stocks)</span>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <div class="section" style="text-align: center; color: #7f8c8d;">
            <p>KStock Level 1 Analysis | Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """</p>
            <p>Agents: TECH_001 | QUANT_001 | QUAL_001 | NEWS_001</p>
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
    
    print("Generating HTML report...")
    html = generate_html(data)
    
    output_file = f"{OUTPUT_PATH}/level1_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report saved: {output_file}")
    
    # 요약 출력
    results = [r for r in data.get('results', []) if r.get('status') == 'success']
    sorted_results = sorted(results, key=lambda x: x.get('avg_score', 0), reverse=True)
    
    print("\n" + "=" * 60)
    print("📊 LEVEL 1 REPORT SUMMARY")
    print("=" * 60)
    print(f"Total Stocks: {len(results)}")
    print(f"Average Score: {round(sum(r.get('avg_score', 0) for r in results) / len(results), 1) if results else 0}")
    
    print("\n🏆 TOP 5:")
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"  {i}. {r['name']} ({r['market']}): {r['avg_score']} pts - {r['consensus']}")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
