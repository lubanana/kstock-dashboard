#!/usr/bin/env python3
"""
Generate Level 1 HTML Report
Level 1 분석 결과 HTML 리포트 생성
"""

import json
from datetime import datetime

# Load Level 1 data
with open('/home/programs/kstock_analyzer/data/level1_daily/level1_fullmarket_20260309_2312.json', 'r') as f:
    l1_data = json.load(f)

results = l1_data.get('results', [])

# Sort by score
top_stocks = sorted(results, key=lambda x: x.get('avg_score', 0), reverse=True)[:100]

# Generate HTML
html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Level 1 Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.2em; opacity: 0.9; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{ color: #667eea; font-size: 2em; margin-bottom: 5px; }}
        .stat-card p {{ color: #666; }}
        .section {{ padding: 30px; }}
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            position: sticky;
            top: 0;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .score-high {{ color: #4CAF50; font-weight: bold; }}
        .score-mid {{ color: #FF9800; font-weight: bold; }}
        .score-low {{ color: #F44336; font-weight: bold; }}
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .badge-buy {{ background: #4CAF50; color: white; }}
        .badge-hold {{ background: #FF9800; color: white; }}
        .badge-sell {{ background: #F44336; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 KStock Level 1 Analysis Report</h1>
            <p>종목별 기술/재무 분석 | {datetime.now().strftime('%Y년 %m월 %d일')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>{len(results):,}</h3>
                <p>분석 종목</p>
            </div>
            <div class="stat-card">
                <h3>{sum(1 for r in results if r.get('consensus') == 'BUY')}</h3>
                <p>BUY 추천</p>
            </div>
            <div class="stat-card">
                <h3>{sum(1 for r in results if r.get('consensus') == 'HOLD')}</h3>
                <p>HOLD 추천</p>
            </div>
            <div class="stat-card">
                <h3>{sum(1 for r in results if r.get('consensus') == 'SELL')}</h3>
                <p>SELL 추천</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 상위 100종목</h2>
            <table>
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>종목명</th>
                        <th>코드</th>
                        <th>시장</th>
                        <th>점수</th>
                        <th>추천</th>
                    </tr>
                </thead>
                <tbody>
"""

# Add table rows
for i, stock in enumerate(top_stocks, 1):
    score = stock.get('avg_score', 0)
    score_class = 'score-high' if score >= 60 else 'score-mid' if score >= 40 else 'score-low'
    rec = stock.get('consensus', 'HOLD')
    badge_class = 'badge-buy' if rec == 'BUY' else 'badge-hold' if rec == 'HOLD' else 'badge-sell'
    
    html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{stock.get('name', 'N/A')}</td>
                        <td>{stock.get('code', 'N/A')}</td>
                        <td>{stock.get('market', 'N/A')}</td>
                        <td class="{score_class}">{score:.1f}</td>
                        <td><span class="badge {badge_class}">{rec}</span></td>
                    </tr>
"""

html += """
                </tbody>
            </table>
        </div>
        
        <div class="section" style="text-align: center; padding: 20px; color: #666;">
            <p>© 2026 KStock Analyzer | Data Source: PyKRX</p>
        </div>
    </div>
</body>
</html>
"""

# Save
with open('/home/programs/kstock_analyzer/docs/level1_report.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Level 1 Report saved: docs/level1_report.html")
print(f"   Total stocks: {len(results)}")
print(f"   Top 100 included")
