#!/usr/bin/env python3
"""
Level 2 Interactive Report Generator
Level 2 분석 결과 인터랙티브 리포트 생성기
"""

import json
import os
from datetime import datetime
from typing import Dict, List

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/docs'
DATA_PATH = f'{BASE_PATH}/data/level2_daily'


def load_latest_results() -> tuple:
    """최신 Level 2 데이터 로드"""
    sector_file = None
    macro_file = None
    
    files = os.listdir(DATA_PATH) if os.path.exists(DATA_PATH) else []
    
    sector_files = [f for f in files if f.startswith('sector_analysis_') and f.endswith('.json')]
    macro_files = [f for f in files if f.startswith('macro_analysis_') and f.endswith('.json')]
    
    if sector_files:
        with open(f'{DATA_PATH}/{sorted(sector_files)[-1]}', 'r', encoding='utf-8') as f:
            sector_data = json.load(f)
    else:
        sector_data = {}
    
    if macro_files:
        with open(f'{DATA_PATH}/{sorted(macro_files)[-1]}', 'r', encoding='utf-8') as f:
            macro_data = json.load(f)
    else:
        macro_data = {}
    
    return sector_data, macro_data


def generate_html(sector_data: Dict, macro_data: Dict) -> str:
    """인터랙티브 HTML 리포트 생성"""
    
    date = sector_data.get('analysis_date', datetime.now().isoformat())
    sectors = sector_data.get('sectors', {})
    adjustments = sector_data.get('adjustments', {})
    
    macro_indicators = macro_data.get('macro_indicators', {})
    macro_adj = macro_data.get('adjustment', {})
    
    # 섹터 정렬
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1]['average_score'], reverse=True)
    
    # 추천 분류
    overweight = sector_data.get('recommendations', {}).get('overweight', [])
    neutral = sector_data.get('recommendations', {}).get('neutral', [])
    underweight = sector_data.get('recommendations', {}).get('underweight', [])
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Level 2 Analysis Report - {date[:10]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #333; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .date {{ opacity: 0.9; }}
        
        .main-content {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-bottom: 25px; }}
        
        .section {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; }}
        .section h2 {{ color: #2c3e50; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #3498db; }}
        
        /* 매크로 카드 */
        .macro-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }}
        .macro-card {{ padding: 20px; border-radius: 15px; text-align: center; transition: transform 0.3s; }}
        .macro-card:hover {{ transform: translateY(-5px); }}
        .macro-value {{ font-size: 2em; font-weight: bold; margin-bottom: 5px; }}
        .macro-label {{ font-size: 0.9em; opacity: 0.9; }}
        .macro-trend {{ font-size: 0.8em; margin-top: 5px; }}
        
        .card-treasury {{ background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; }}
        .card-currency {{ background: linear-gradient(135deg, #4834d4, #686de0); color: white; }}
        .card-vix {{ background: linear-gradient(135deg, #00d2d3, #01a3a4); color: white; }}
        .card-kospi {{ background: linear-gradient(135deg, #5f27cd, #341f97); color: white; }}
        
        /* 섹터 테이블 */
        .sector-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        .sector-table th {{ background: #34495e; color: white; padding: 12px; text-align: left; position: sticky; top: 0; }}
        .sector-table td {{ padding: 12px; border-bottom: 1px solid #ecf0f1; cursor: pointer; transition: background 0.2s; }}
        .sector-table tr:hover {{ background: #e3f2fd; }}
        .sector-table tr.active {{ background: #bbdefb; }}
        
        .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 500; }}
        .badge-strong {{ background: #27ae60; color: white; }}
        .badge-moderate {{ background: #f39c12; color: white; }}
        .badge-weak {{ background: #e74c3c; color: white; }}
        
        .adj-positive {{ color: #27ae60; font-weight: bold; }}
        .adj-negative {{ color: #e74c3c; font-weight: bold; }}
        .adj-neutral {{ color: #7f8c8d; }}
        
        /* 조정 패널 */
        .adjustment-panel {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; margin-bottom: 25px; }}
        .adj-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .adj-value {{ font-size: 3em; font-weight: bold; }}
        .adj-positive-big {{ color: #27ae60; }}
        .adj-negative-big {{ color: #e74c3c; }}
        .adj-neutral-big {{ color: #f39c12; }}
        
        .recommendation-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px; }}
        .rec-card {{ padding: 20px; border-radius: 15px; text-align: center; }}
        .rec-overweight {{ background: #d4edda; border: 2px solid #28a745; }}
        .rec-neutral {{ background: #fff3cd; border: 2px solid #ffc107; }}
        .rec-underweight {{ background: #f8d7da; border: 2px solid #dc3545; }}
        .rec-title {{ font-weight: bold; margin-bottom: 10px; }}
        .rec-count {{ font-size: 2em; }}
        
        /* 상세 패널 */
        .detail-panel {{ position: sticky; top: 20px; }}
        .detail-card {{ background: rgba(255,255,255,0.95); padding: 25px; border-radius: 20px; }}
        .detail-header {{ margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #ecf0f1; }}
        .detail-title {{ font-size: 1.5em; color: #2c3e50; }}
        
        .stock-list {{ max-height: 300px; overflow-y: auto; }}
        .stock-item {{ display: flex; justify-content: space-between; padding: 10px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; }}
        .stock-item:hover {{ background: #e3f2fd; }}
        
        .empty-state {{ text-align: center; padding: 60px 20px; color: #7f8c8d; }}
        .empty-state-icon {{ font-size: 4em; margin-bottom: 20px; }}
        
        @media (max-width: 1024px) {{
            .main-content {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌍 Level 2 Analysis Report</h1>
            <div class="date">{date[:10]} | Sector & Macro Analysis</div>
        </div>
        
        <!-- 매크로 지표 -->
        <div class="section" style="margin-bottom: 25px;">
            <h2>📊 Macro Indicators</h2>
            <div class="macro-grid">
                <div class="macro-card card-treasury">
                    <div class="macro-value">{macro_indicators.get('us_treasury', {}).get('current', '-')}%</div>
                    <div class="macro-label">US 10Y Treasury</div>
                    <div class="macro-trend">{macro_indicators.get('us_treasury', {}).get('trend', '-')}</div>
                </div>
                <div class="macro-card card-currency">
                    <div class="macro-value">{macro_indicators.get('usd_krw', {}).get('current', '-'):,.0f}</div>
                    <div class="macro-label">USD/KRW</div>
                    <div class="macro-trend">{macro_indicators.get('usd_krw', {}).get('trend', '-')}</div>
                </div>
                <div class="macro-card card-vix">
                    <div class="macro-value">{macro_indicators.get('vix', {}).get('current', '-')}</div>
                    <div class="macro-label">VIX</div>
                    <div class="macro-trend">{macro_indicators.get('vix', {}).get('sentiment', '-')}</div>
                </div>
                <div class="macro-card card-kospi">
                    <div class="macro-value">{macro_indicators.get('kospi', {}).get('current', '-'):,.0f}</div>
                    <div class="macro-label">KOSPI</div>
                    <div class="macro-trend">{macro_indicators.get('kospi', {}).get('trend', '-')}</div>
                </div>
            </div>
        </div>
        
        <!-- 조정 요약 -->
        <div class="adjustment-panel">
            <h2>🎯 Adjustment Summary</h2>
            <div class="adj-header">
                <div>
                    <div class="detail-title">Sector Adjustment</div>
                    <div style="color: #7f8c8d;">Per sector: -15% to +15%</div>
                </div>
                <div style="text-align: center;">
                    <div class="detail-title">Macro Adjustment</div>
                    <div class="adj-value {('adj-positive-big' if macro_adj.get('pct', 0) > 0 else 'adj-negative-big' if macro_adj.get('pct', 0) < 0 else 'adj-neutral-big')}">{macro_adj.get('pct', 0):+.0f}%</div>
                    <div style="color: #7f8c8d;">{macro_adj.get('market_condition', '-')}</div>
                </div>
            </div>
            
            <div class="recommendation-grid">
                <div class="rec-card rec-overweight">
                    <div class="rec-title">📈 Overweight</div>
                    <div class="rec-count">{len(overweight)}</div>
                    <div style="font-size: 0.8em; color: #666; margin-top: 10px;">{' • '.join(overweight[:5])}{'...' if len(overweight) > 5 else ''}</div>
                </div>
                <div class="rec-card rec-neutral">
                    <div class="rec-title">⚖️ Neutral</div>
                    <div class="rec-count">{len(neutral)}</div>
                    <div style="font-size: 0.8em; color: #666; margin-top: 10px;">{' • '.join(neutral[:5])}{'...' if len(neutral) > 5 else ''}</div>
                </div>
                <div class="rec-card rec-underweight">
                    <div class="rec-title">📉 Underweight</div>
                    <div class="rec-count">{len(underweight)}</div>
                    <div style="font-size: 0.8em; color: #666; margin-top: 10px;">{' • '.join(underweight[:5])}{'...' if len(underweight) > 5 else ''}</div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <!-- 섹터 테이블 -->
            <div class="left-panel">
                <div class="section">
                    <h2>📋 Sector Rankings (Click for Details)</h2>
                    <div style="max-height: 600px; overflow-y: auto;">
                        <table class="sector-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Sector</th>
                                    <th>Avg Score</th>
                                    <th>Strength</th>
                                    <th>Adj</th>
                                </tr>
                            </thead>
                            <tbody id="sectorTableBody">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- 상세 패널 -->
            <div class="detail-panel">
                <div id="detailContent">
                    <div class="detail-card empty-state">
                        <div class="empty-state-icon">📊</div>
                        <h3>Select a Sector</h3>
                        <p>Click on any sector from the list to view detailed analysis and stock rankings.</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="section" style="text-align: center; color: #7f8c8d;">
            <p>KStock Level 2 Analysis | Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """</p>
            <p>Agents: SECTOR_001 | MACRO_001</p>
        </div>
    </div>
    
    <script>
        const sectorData = {json.dumps([{'name': k, **v} for k, v in sorted_sectors], ensure_ascii=False)};
        const adjustments = {json.dumps(adjustments, ensure_ascii=False)};
        
        let selectedSector = null;
        
        function renderTable() {{
            const tbody = document.getElementById('sectorTableBody');
            tbody.innerHTML = '';
            
            sectorData.forEach((sector, index) => {{
                const row = document.createElement('tr');
                row.className = selectedSector === sector.name ? 'active' : '';
                row.onclick = () => showDetail(sector);
                
                const adj = adjustments[sector.name] || {{adjustment_pct: 0}};
                const adjClass = adj.adjustment_pct > 0 ? 'adj-positive' : adj.adjustment_pct < 0 ? 'adj-negative' : 'adj-neutral';
                
                const badgeClass = sector.strength === 'STRONG' ? 'badge-strong' : 
                                  sector.strength === 'WEAK' ? 'badge-weak' : 'badge-moderate';
                
                row.innerHTML = `
                    <td>${{index + 1}}</td>
                    <td><strong>${{sector.name}}</strong> (${{sector.stock_count}})</td>
                    <td>${{sector.average_score}}</td>
                    <td><span class="badge ${{badgeClass}}">${{sector.strength}}</span></td>
                    <td class="${{adjClass}}">${{adj.adjustment_pct > 0 ? '+' : ''}}${{adj.adjustment_pct}}%</td>
                `;
                tbody.appendChild(row);
            }});
        }}
        
        function showDetail(sector) {{
            selectedSector = sector.name;
            renderTable();
            
            const adj = adjustments[sector.name] || {{adjustment_pct: 0, reason: ''}};
            
            let stocksHtml = '';
            sector.all_stocks.forEach((stock, idx) => {{
                const badgeClass = stock.consensus === 'BUY' ? 'badge-strong' : stock.consensus === 'SELL' ? 'badge-weak' : 'badge-moderate';
                stocksHtml += `
                    <div class="stock-item">
                        <div>
                            <strong>${{idx + 1}}. ${{stock.name}}</strong>
                            <span class="badge ${{badgeClass}}" style="margin-left: 10px;">${{stock.consensus}}</span>
                        </div>
                        <div style="font-weight: bold; color: ${{stock.score >= 70 ? '#27ae60' : stock.score >= 50 ? '#f39c12' : '#e74c3c'}};">${{stock.score}} pts</div>
                    </div>
                `;
            }});
            
            const detailHtml = `
                <div class="detail-card">
                    <div class="detail-header">
                        <div>
                            <div class="detail-title">${{sector.name}}</div>
                            <div style="color: #7f8c8d;">${{sector.stock_count}} stocks | Avg: ${{sector.average_score}} pts</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 2em; font-weight: bold; color: ${{adj.adjustment_pct > 0 ? '#27ae60' : adj.adjustment_pct < 0 ? '#e74c3c' : '#f39c12'}};">${{adj.adjustment_pct > 0 ? '+' : ''}}${{adj.adjustment_pct}}%</div>
                            <div style="font-size: 0.8em; color: #666;">Adjustment</div>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                            <span>Relative Strength:</span>
                            <span style="font-weight: bold; color: ${{sector.relative_strength_pct > 0 ? '#27ae60' : '#e74c3c'}};">${{sector.relative_strength_pct > 0 ? '+' : ''}}${{sector.relative_strength_pct}}%</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                            <span>Rotation Signal:</span>
                            <span class="badge ${{sector.rotation_signal === 'Overweight' ? 'badge-strong' : sector.rotation_signal === 'Underweight' ? 'badge-weak' : 'badge-moderate'}}">${{sector.rotation_signal}}</span>
                        </div>
                        
                        <div style="background: #f8f9fa; padding: 10px; border-radius: 8px; margin-top: 10px; font-size: 0.9em; color: #666;">
                            ${{adj.reason}}
                        </div>
                    </div>
                    
                    <h3 style="margin-bottom: 15px; color: #2c3e50;">🏆 Top Performer</h3>
                    <div class="stock-item" style="background: #d4edda; border: 1px solid #28a745;">
                        <div>
                            <strong>${{sector.top_performer.name}}</strong>
                            <span class="badge badge-strong" style="margin-left: 10px;">${{sector.top_performer.consensus}}</span>
                        </div>
                        <div style="font-weight: bold; color: #27ae60;">${{sector.top_performer.score}} pts</div>
                    </div>
                    
                    <h3 style="margin: 20px 0 15px; color: #2c3e50;">📊 All Stocks</h3>
                    <div class="stock-list">
                        ${{stocksHtml}}
                    </div>
                </div>
            `;
            
            document.getElementById('detailContent').innerHTML = detailHtml;
        }}
        
        // 초기 렌더링
        renderTable();
    </script>
</body>
</html>"""
    
    return html


def main():
    print("Loading Level 2 results...")
    sector_data, macro_data = load_latest_results()
    
    if not sector_data or not macro_data:
        print("No data found!")
        return
    
    print(f"Sector data: {len(sector_data.get('sectors', {}))} sectors")
    print(f"Macro data: {len(macro_data.get('macro_indicators', {}))} indicators")
    
    print("Generating interactive HTML report...")
    html = generate_html(sector_data, macro_data)
    
    output_file = f"{OUTPUT_PATH}/level2_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report saved: {output_file}")
    
    # 요약
    sectors = sector_data.get('sectors', {})
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1]['average_score'], reverse=True)
    
    print("\n" + "=" * 60)
    print("📊 LEVEL 2 REPORT SUMMARY")
    print("=" * 60)
    print(f"Sectors: {len(sectors)}")
    print(f"Macro Condition: {macro_data.get('adjustment', {}).get('market_condition', '-')}")
    print(f"Macro Adjustment: {macro_data.get('adjustment', {}).get('pct', 0):+.0f}%")
    print(f"\n🏆 TOP 3 Sectors:")
    for i, (name, data) in enumerate(sorted_sectors[:3], 1):
        print(f"  {i}. {name}: {data['average_score']} pts ({data['strength']})")
    print("=" * 60)


if __name__ == '__main__':
    main()
