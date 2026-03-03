#!/usr/bin/env python3
"""
Interactive Level 1 Report Generator
종목 클릭 시 상세 데이터 표시되는 인터랙티브 리포트
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
    """인터랙티브 HTML 리포트 생성"""
    results = data.get('results', [])
    date = data.get('date', datetime.now().isoformat())
    
    success_results = [r for r in results if r.get('status') == 'success']
    sorted_results = sorted(success_results, key=lambda x: x.get('avg_score', 0), reverse=True)
    
    # 추천 집계
    strong_buy = len([r for r in success_results if r.get('consensus') == 'STRONG BUY'])
    buy = len([r for r in success_results if r.get('consensus') == 'BUY'])
    hold = len([r for r in success_results if r.get('consensus') == 'HOLD'])
    sell = len([r for r in success_results if r.get('consensus') == 'SELL'])
    
    # 섹터별 데이터
    sector_data = {}
    for r in success_results:
        sector = r.get('sector', 'Unknown')
        if sector not in sector_data:
            sector_data[sector] = []
        sector_data[sector].append(r['avg_score'])
    
    sector_avg = {s: round(sum(scores)/len(scores), 1) for s, scores in sector_data.items()}
    sorted_sectors = sorted(sector_avg.items(), key=lambda x: x[1], reverse=True)
    
    # JSON 데이터를 JavaScript에 포함
    js_data = json.dumps(success_results, ensure_ascii=False)
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Level 1 Analysis Report - {date[:10]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #333; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .date {{ opacity: 0.9; }}
        
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; text-align: center; }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; color: #2c3e50; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
        
        .main-content {{ display: grid; grid-template-columns: 1fr 450px; gap: 25px; }}
        
        .section {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; margin-bottom: 25px; }}
        .section h2 {{ color: #2c3e50; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #3498db; }}
        
        .stock-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        .stock-table th {{ background: #34495e; color: white; padding: 12px; text-align: left; position: sticky; top: 0; }}
        .stock-table td {{ padding: 12px; border-bottom: 1px solid #ecf0f1; cursor: pointer; transition: background 0.2s; }}
        .stock-table tr:hover {{ background: #e3f2fd; }}
        .stock-table tr.active {{ background: #bbdefb; }}
        
        .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 500; }}
        .badge-strong-buy {{ background: #27ae60; color: white; }}
        .badge-buy {{ background: #2ecc71; color: white; }}
        .badge-hold {{ background: #f39c12; color: white; }}
        .badge-sell {{ background: #e74c3c; color: white; }}
        
        .score-high {{ color: #27ae60; font-weight: bold; }}
        .score-mid {{ color: #f39c12; font-weight: bold; }}
        .score-low {{ color: #e74c3c; font-weight: bold; }}
        
        /* 상세 패널 */
        .detail-panel {{ position: sticky; top: 20px; }}
        .detail-card {{ background: rgba(255,255,255,0.95); padding: 25px; border-radius: 20px; margin-bottom: 20px; }}
        .detail-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #ecf0f1; }}
        .detail-title {{ font-size: 1.5em; color: #2c3e50; }}
        .detail-subtitle {{ color: #7f8c8d; font-size: 0.9em; }}
        
        .agent-detail {{ margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 12px; border-left: 4px solid #3498db; }}
        .agent-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .agent-name {{ font-weight: bold; color: #2c3e50; }}
        .agent-score {{ font-size: 1.3em; font-weight: bold; }}
        .agent-score-high {{ color: #27ae60; }}
        .agent-score-mid {{ color: #f39c12; }}
        .agent-score-low {{ color: #e74c3c; }}
        .agent-rec {{ display: inline-block; padding: 3px 10px; border-radius: 15px; font-size: 0.8em; margin-left: 10px; }}
        
        .breakdown-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px; }}
        .breakdown-item {{ display: flex; justify-content: space-between; padding: 8px 12px; background: white; border-radius: 8px; font-size: 0.9em; }}
        
        .empty-state {{ text-align: center; padding: 60px 20px; color: #7f8c8d; }}
        .empty-state-icon {{ font-size: 4em; margin-bottom: 20px; }}
        
        .filter-tabs {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
        .filter-tab {{ padding: 10px 20px; background: #ecf0f1; border: none; border-radius: 25px; cursor: pointer; transition: all 0.3s; }}
        .filter-tab:hover {{ background: #d5dbdb; }}
        .filter-tab.active {{ background: #3498db; color: white; }}
        
        .sector-list {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
        .sector-item {{ display: flex; justify-content: space-between; padding: 10px; background: #f8f9fa; border-radius: 8px; }}
        
        @media (max-width: 1024px) {{
            .main-content {{ grid-template-columns: 1fr; }}
            .detail-panel {{ position: static; }}
        }}
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
        
        <div class="main-content">
            <div class="left-panel">
                <div class="section">
                    <h2>🔍 Filter</h2>
                    <div class="filter-tabs">
                        <button class="filter-tab active" onclick="filterStocks('all')">All</button>
                        <button class="filter-tab" onclick="filterStocks('kospi')">KOSPI</button>
                        <button class="filter-tab" onclick="filterStocks('kosdaq')">KOSDAQ</button>
                        <button class="filter-tab" onclick="filterStocks('buy')">BUY</button>
                        <button class="filter-tab" onclick="filterStocks('hold')">HOLD</button>
                    </div>
                </div>
                
                <div class="section">
                    <h2>📋 Stock List (Click for Details)</h2>
                    <div style="max-height: 600px; overflow-y: auto;">
                        <table class="stock-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Name</th>
                                    <th>Market</th>
                                    <th>Score</th>
                                    <th>Consensus</th>
                                </tr>
                            </thead>
                            <tbody id="stockTableBody">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="detail-panel">
                <div id="detailContent">
                    <div class="detail-card empty-state">
                        <div class="empty-state-icon">📈</div>
                        <h3>Select a Stock</h3>
                        <p>Click on any stock from the list to view detailed analysis from all 4 agents.</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const stockData = {js_data};
        let currentFilter = 'all';
        let selectedStock = null;
        
        function renderTable() {{
            const tbody = document.getElementById('stockTableBody');
            tbody.innerHTML = '';
            
            let filtered = stockData;
            if (currentFilter === 'kospi') {{
                filtered = stockData.filter(s => s.market === 'KOSPI');
            }} else if (currentFilter === 'kosdaq') {{
                filtered = stockData.filter(s => s.market === 'KOSDAQ');
            }} else if (currentFilter === 'buy') {{
                filtered = stockData.filter(s => s.consensus === 'BUY' || s.consensus === 'STRONG BUY');
            }} else if (currentFilter === 'hold') {{
                filtered = stockData.filter(s => s.consensus === 'HOLD');
            }}
            
            filtered.sort((a, b) => b.avg_score - a.avg_score);
            
            filtered.forEach((stock, index) => {{
                const row = document.createElement('tr');
                row.className = selectedStock === stock.symbol ? 'active' : '';
                row.onclick = () => showDetail(stock);
                
                const scoreClass = stock.avg_score >= 70 ? 'score-high' : stock.avg_score >= 50 ? 'score-mid' : 'score-low';
                const badgeClass = stock.consensus === 'STRONG BUY' ? 'badge-strong-buy' : 
                                  stock.consensus === 'BUY' ? 'badge-buy' : 
                                  stock.consensus === 'SELL' ? 'badge-sell' : 'badge-hold';
                
                row.innerHTML = `
                    <td>${{index + 1}}</td>
                    <td><strong>${{stock.name}}</strong><br><small>${{stock.symbol}}</small></td>
                    <td>${{stock.market}}</td>
                    <td class="${{scoreClass}}">${{stock.avg_score}}</td>
                    <td><span class="badge ${{badgeClass}}">${{stock.consensus}}</span></td>
                `;
                tbody.appendChild(row);
            }});
        }}
        
        function showDetail(stock) {{
            selectedStock = stock.symbol;
            renderTable();
            
            const agents = stock.agents;
            const detailHtml = `
                <div class="detail-card">
                    <div class="detail-header">
                        <div>
                            <div class="detail-title">${{stock.name}}</div>
                            <div class="detail-subtitle">${{stock.symbol}} | ${{stock.sector}} | ${{stock.market}}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 2em; font-weight: bold; color: ${{stock.avg_score >= 70 ? '#27ae60' : stock.avg_score >= 50 ? '#f39c12' : '#e74c3c'}}">${{stock.avg_score}}</div>
                            <div><span class="badge ${{stock.consensus === 'STRONG BUY' ? 'badge-strong-buy' : stock.consensus === 'BUY' ? 'badge-buy' : stock.consensus === 'SELL' ? 'badge-sell' : 'badge-hold'}}">${{stock.consensus}}</span></div>
                        </div>
                    </div>
                    
                    <div class="agent-detail" style="border-left-color: #e74c3c;">
                        <div class="agent-header">
                            <span class="agent-name">🔧 Technical Analyst</span>
                            <span>
                                <span class="agent-score agent-score-${{agents.TECH.score >= 70 ? 'high' : agents.TECH.score >= 50 ? 'mid' : 'low'}}">${{agents.TECH.score}}/100</span>
                                <span class="agent-rec badge-${{agents.TECH.rec === 'BUY' ? 'buy' : agents.TECH.rec === 'SELL' ? 'sell' : 'hold'}}">${{agents.TECH.rec}}</span>
                            </span>
                        </div>
                        <div style="font-size: 0.9em; color: #666;">
                            Price Trend, Momentum, Bollinger Bands, Volume Analysis
                        </div>
                    </div>
                    
                    <div class="agent-detail" style="border-left-color: #3498db;">
                        <div class="agent-header">
                            <span class="agent-name">📊 Quant Analyst</span>
                            <span>
                                <span class="agent-score agent-score-${{agents.QUANT.score >= 70 ? 'high' : agents.QUANT.score >= 50 ? 'mid' : 'low'}}">${{agents.QUANT.score}}/100</span>
                                <span class="agent-rec badge-${{agents.QUANT.rec === 'BUY' ? 'buy' : agents.QUANT.rec === 'SELL' ? 'sell' : 'hold'}}">${{agents.QUANT.rec}}</span>
                            </span>
                        </div>
                        <div style="font-size: 0.9em; color: #666;">
                            Profitability, Growth, Stability, Valuation
                        </div>
                    </div>
                    
                    <div class="agent-detail" style="border-left-color: #9b59b6;">
                        <div class="agent-header">
                            <span class="agent-name">🏢 Qualitative Analyst</span>
                            <span>
                                <span class="agent-score agent-score-${{agents.QUAL.score >= 70 ? 'high' : agents.QUAL.score >= 50 ? 'mid' : 'low'}}">${{agents.QUAL.score}}/100</span>
                                <span class="agent-rec badge-${{agents.QUAL.rec === 'BUY' ? 'buy' : agents.QUAL.rec === 'SELL' ? 'sell' : 'hold'}}">${{agents.QUAL.rec}}</span>
                            </span>
                        </div>
                        <div style="font-size: 0.9em; color: #666;">
                            Business Model, Management, Industry Outlook, Risk Factors
                        </div>
                    </div>
                    
                    <div class="agent-detail" style="border-left-color: #f39c12;">
                        <div class="agent-header">
                            <span class="agent-name">📰 News Sentiment Analyst</span>
                            <span>
                                <span class="agent-score agent-score-${{agents.NEWS.score >= 70 ? 'high' : agents.NEWS.score >= 50 ? 'mid' : 'low'}}">${{agents.NEWS.score}}/100</span>
                                <span class="agent-rec badge-${{agents.NEWS.rec === 'BUY' ? 'buy' : agents.NEWS.rec === 'SELL' ? 'sell' : 'hold'}}">${{agents.NEWS.rec}}</span>
                            </span>
                        </div>
                        <div style="font-size: 0.9em; color: #666;">
                            News Sentiment, Social Media, Event Risk, Momentum Signals
                        </div>
                    </div>
                </div>
                
                <div class="detail-card">
                    <h3 style="margin-bottom: 15px; color: #2c3e50;">📊 Score Breakdown</h3>
                    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                        <div style="flex: 1; text-align: center; padding: 15px; background: #ffebee; border-radius: 10px;">
                            <div style="font-size: 1.5em; font-weight: bold; color: #c62828;">${{agents.TECH.score}}</div>
                            <div style="font-size: 0.8em; color: #666;">TECH</div>
                        </div>
                        <div style="flex: 1; text-align: center; padding: 15px; background: #e3f2fd; border-radius: 10px;">
                            <div style="font-size: 1.5em; font-weight: bold; color: #1565c0;">${{agents.QUANT.score}}</div>
                            <div style="font-size: 0.8em; color: #666;">QUANT</div>
                        </div>
                        <div style="flex: 1; text-align: center; padding: 15px; background: #f3e5f5; border-radius: 10px;">
                            <div style="font-size: 1.5em; font-weight: bold; color: #7b1fa2;">${{agents.QUAL.score}}</div>
                            <div style="font-size: 0.8em; color: #666;">QUAL</div>
                        </div>
                        <div style="flex: 1; text-align: center; padding: 15px; background: #fff3e0; border-radius: 10px;">
                            <div style="font-size: 1.5em; font-weight: bold; color: #ef6c00;">${{agents.NEWS.score}}</div>
                            <div style="font-size: 0.8em; color: #666;">NEWS</div>
                        </div>
                    </div>
                </div>
            `;
            
            document.getElementById('detailContent').innerHTML = detailHtml;
        }}
        
        function filterStocks(filter) {{
            currentFilter = filter;
            document.querySelectorAll('.filter-tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');
            renderTable();
        }}
        
        // 초기 렌더링
        renderTable();
    </script>
</body>
</html>"""
    
    return html


def main():
    print("Loading latest Level 1 results...")
    data = load_latest_results()
    
    if not data:
        print("No data found!")
        return
    
    print(f"Loaded: {data.get('total', 0)} stocks")
    
    print("Generating interactive HTML report...")
    html = generate_html(data)
    
    output_file = f"{OUTPUT_PATH}/level1_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report saved: {output_file}")
    
    # 요약
    results = [r for r in data.get('results', []) if r.get('status') == 'success']
    sorted_results = sorted(results, key=lambda x: x.get('avg_score', 0), reverse=True)
    
    print("\n" + "=" * 60)
    print("📊 INTERACTIVE REPORT GENERATED")
    print("=" * 60)
    print(f"Total Stocks: {len(results)}")
    print(f"Average Score: {round(sum(r.get('avg_score', 0) for r in results) / len(results), 1) if results else 0}")
    print(f"\n🏆 TOP 5:")
    for i, r in enumerate(sorted_results[:5], 1):
        print(f"  {i}. {r['name']} ({r['market']}): {r['avg_score']} pts - {r['consensus']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
