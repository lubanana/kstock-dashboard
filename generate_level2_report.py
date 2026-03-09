#!/usr/bin/env python3
"""
Generate Level 2 HTML Report
Level 2 섹터/매크로 분석 결과 HTML 리포트 생성
"""

import json
from datetime import datetime

# Load Level 2 data
with open('/home/programs/kstock_analyzer/data/level2_daily/sector_analysis_20260309_2312.json', 'r') as f:
    l2_sector = json.load(f)

with open('/home/programs/kstock_analyzer/data/level2_daily/macro_analysis_20260309_2312.json', 'r') as f:
    l2_macro = json.load(f)

# Get adjustment data
adj = l2_macro.get('adjustment', {})
macro_adj = adj.get('pct', 0)
market_condition = adj.get('market_condition', 'NEUTRAL')

# Generate HTML
html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Level 2 Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
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
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.2em; opacity: 0.9; }}
        .section {{ padding: 30px; }}
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #11998e;
        }}
        .macro-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
        }}
        .macro-card h3 {{ font-size: 1.5em; margin-bottom: 15px; }}
        .macro-stat {{
            display: inline-block;
            margin-right: 30px;
            margin-top: 10px;
        }}
        .macro-stat strong {{
            display: block;
            font-size: 2em;
            margin-bottom: 5px;
        }}
        .status-indicator {{
            display: inline-block;
            padding: 10px 25px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.2em;
        }}
        .status-bullish {{ background: #4CAF50; color: white; }}
        .status-neutral {{ background: #FF9800; color: white; }}
        .status-bearish {{ background: #F44336; color: white; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 15px;
            text-align: left;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .adjustment-box {{
            background: #f8f9fa;
            border-left: 5px solid #11998e;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 10px 10px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 KStock Level 2 Analysis Report</h1>
            <p>섹터 & 매크로 분석 | {datetime.now().strftime('%Y년 %m월 %d일')}</p>
        </div>
        
        <div class="section">
            <div class="macro-card">
                <h3>🌍 거시경제 지표</h3>
                <div class="macro-stat">
                    <strong>{macro_adj:+d}%</strong>
                    <span>매크로 조정</span>
                </div>
                <div class="macro-stat">
                    <strong class="status-indicator status-{market_condition.lower()}">{market_condition}</strong>
                    <span>시장 상황</span>
                </div>
            </div>
            
            <div class="adjustment-box">
                <h4>📋 조정 사유</h4>
                <p>{adj.get('reason', 'N/A')}</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🏭 섹터 분석</h2>
            <table>
                <thead>
                    <tr>
                        <th>섹터</th>
                        <th>평균 점수</th>
                        <th>조정</th>
                        <th>포지션</th>
                    </tr>
                </thead>
                <tbody>
"""

# Add sector data
sectors = l2_sector.get('sectors', {})
if isinstance(sectors, dict):
    # sectors is a dict
    for name, data in sorted(sectors.items(), key=lambda x: x[1].get('avg_score', 0) if isinstance(x[1], dict) else 0, reverse=True):
        if isinstance(data, dict):
            score = data.get('avg_score', 0)
            adj_val = data.get('adjustment', 0)
            position = data.get('position', 'NEUTRAL')
        else:
            score, adj_val, position = 0, 0, 'NEUTRAL'
        
        html += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{score:.1f}pts</td>
                        <td>{adj_val:+d}%</td>
                        <td>{position}</td>
                    </tr>
"""
elif isinstance(sectors, list):
    # sectors is a list
    for sector in sorted(sectors, key=lambda x: x.get('avg_score', 0) if isinstance(x, dict) else 0, reverse=True):
        if isinstance(sector, dict):
            name = sector.get('name', 'N/A')
            score = sector.get('avg_score', 0)
            adj_val = sector.get('adjustment', 0)
            position = sector.get('position', 'NEUTRAL')
            
            html += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{score:.1f}pts</td>
                        <td>{adj_val:+d}%</td>
                        <td>{position}</td>
                    </tr>
"""

html += """
                </tbody>
            </table>
        </div>
        
        <div class="section" style="text-align: center; padding: 20px; color: #666;">
            <p>© 2026 KStock Analyzer | Level 2: Sector & Macro Analysis</p>
        </div>
    </div>
</body>
</html>
"""

# Save
with open('/home/programs/kstock_analyzer/docs/level2_report.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Level 2 Report saved: docs/level2_report.html")
print(f"   Macro adjustment: {macro_adj}%")
print(f"   Market condition: {market_condition}")
print(f"   Sectors: {len(sectors)}")
