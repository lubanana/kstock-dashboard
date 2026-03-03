#!/usr/bin/env python3
"""
Integrated Level 3 Report Generator
통합 Level 3 리포트 생성기 - Level 1, 2, 3 내용 모두 포함
"""

import json
import os
from datetime import datetime
from typing import Dict, List

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/docs'
DATA_PATH = f'{BASE_PATH}/data'


def load_all_data():
    """모든 레벨 데이터 로드"""
    # Level 1
    l1_files = [f for f in os.listdir(f'{DATA_PATH}/level1_daily') 
                if f.startswith('level1_fullmarket_') and f.endswith('.json')] if os.path.exists(f'{DATA_PATH}/level1_daily') else []
    l1_data = {}
    if l1_files:
        with open(f'{DATA_PATH}/level1_daily/{sorted(l1_files)[-1]}', 'r', encoding='utf-8') as f:
            l1_data = json.load(f)
    
    # Level 2
    sector_files = [f for f in os.listdir(f'{DATA_PATH}/level2_daily')
                    if f.startswith('sector_analysis_') and f.endswith('.json')] if os.path.exists(f'{DATA_PATH}/level2_daily') else []
    macro_files = [f for f in os.listdir(f'{DATA_PATH}/level2_daily')
                   if f.startswith('macro_analysis_') and f.endswith('.json')] if os.path.exists(f'{DATA_PATH}/level2_daily') else []
    l2_sector = {}
    l2_macro = {}
    if sector_files:
        with open(f'{DATA_PATH}/level2_daily/{sorted(sector_files)[-1]}', 'r', encoding='utf-8') as f:
            l2_sector = json.load(f)
    if macro_files:
        with open(f'{DATA_PATH}/level2_daily/{sorted(macro_files)[-1]}', 'r', encoding='utf-8') as f:
            l2_macro = json.load(f)
    
    # Level 3
    l3_files = [f for f in os.listdir(f'{DATA_PATH}/level3_daily')
                if f.startswith('portfolio_report_') and f.endswith('.json')] if os.path.exists(f'{DATA_PATH}/level3_daily') else []
    l3_data = {}
    if l3_files:
        with open(f'{DATA_PATH}/level3_daily/{sorted(l3_files)[-1]}', 'r', encoding='utf-8') as f:
            l3_data = json.load(f)
    
    return l1_data, l2_sector, l2_macro, l3_data


def generate_html(l1_data, l2_sector, l2_macro, l3_data) -> str:
    """통합 HTML 리포트 생성"""
    
    date = l3_data.get('analysis_date', datetime.now().isoformat())
    
    # Level 3 데이터
    l3_summary = l3_data.get('portfolio_summary', {})
    l3_portfolio = l3_data.get('portfolio', {})
    long_positions = l3_portfolio.get('long', [])
    short_positions = l3_portfolio.get('short', [])
    rankings = l3_data.get('all_rankings', [])
    
    # Level 1 데이터
    l1_results = [r for r in l1_data.get('results', []) if r.get('status') == 'success']
    l1_sorted = sorted(l1_results, key=lambda x: x.get('avg_score', 0), reverse=True)
    
    # Level 2 데이터
    sectors = l2_sector.get('sectors', {})
    sorted_sectors = sorted(sectors.items(), key=lambda x: x[1]['average_score'], reverse=True)
    macro_indicators = l2_macro.get('macro_indicators', {})
    macro_adj = l2_macro.get('adjustment', {})
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Integrated Analysis Report - {date[:10]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #333; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ opacity: 0.9; font-size: 1.2em; }}
        .header .date {{ opacity: 0.8; margin-top: 10px; }}
        
        /* 네비게이션 */
        .nav {{ display: flex; gap: 10px; margin-bottom: 30px; flex-wrap: wrap; justify-content: center; }}
        .nav-btn {{ padding: 12px 25px; background: rgba(255,255,255,0.95); border: none; border-radius: 25px; cursor: pointer; font-weight: 500; transition: all 0.3s; text-decoration: none; color: #333; }}
        .nav-btn:hover {{ background: #3498db; color: white; }}
        
        /* 섹션 스타일 */
        .section {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; margin-bottom: 25px; }}
        .section h2 {{ color: #2c3e50; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #3498db; display: flex; align-items: center; gap: 10px; }}
        .section h3 {{ color: #34495e; margin: 20px 0 15px; }}
        
        /* 레벨 3 - 핵심 포트폴리오 */
        .l3-highlight {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
        .l3-highlight h2 {{ border-bottom-color: rgba(255,255,255,0.3); color: white; }}
        
        .portfolio-summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px; }}
        .portfolio-card {{ background: rgba(255,255,255,0.2); padding: 25px; border-radius: 15px; text-align: center; backdrop-filter: blur(10px); }}
        .portfolio-value {{ font-size: 2.5em; font-weight: bold; }}
        .portfolio-label {{ opacity: 0.9; margin-top: 5px; }}
        
        .allocation-bar {{ display: flex; height: 40px; border-radius: 20px; overflow: hidden; margin: 20px 0; }}
        .alloc-long {{ background: #27ae60; }}
        .alloc-short {{ background: #e74c3c; }}
        .alloc-cash {{ background: #95a5a6; }}
        
        /* 테이블 스타일 */
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        .data-table th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
        .data-table td {{ padding: 12px; border-bottom: 1px solid #ecf0f1; }}
        .data-table tr:hover {{ background: #f8f9fa; }}
        
        .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 500; }}
        .badge-strong-buy {{ background: #27ae60; color: white; }}
        .badge-buy {{ background: #2ecc71; color: white; }}
        .badge-hold {{ background: #f39c12; color: white; }}
        .badge-sell {{ background: #e74c3c; color: white; }}
        .badge-strong {{ background: #27ae60; color: white; }}
        .badge-moderate {{ background: #f39c12; color: white; }}
        .badge-weak {{ background: #e74c3c; color: white; }}
        
        .score-high {{ color: #27ae60; font-weight: bold; }}
        .score-mid {{ color: #f39c12; font-weight: bold; }}
        .score-low {{ color: #e74c3c; font-weight: bold; }}
        
        /* 매크로 카드 */
        .macro-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }}
        .macro-card {{ padding: 20px; border-radius: 15px; text-align: center; color: white; }}
        .macro-value {{ font-size: 1.8em; font-weight: bold; }}
        .macro-label {{ font-size: 0.9em; opacity: 0.9; }}
        
        .card-treasury {{ background: linear-gradient(135deg, #ff6b6b, #ee5a24); }}
        .card-currency {{ background: linear-gradient(135deg, #4834d4, #686de0); }}
        .card-vix {{ background: linear-gradient(135deg, #00d2d3, #01a3a4); }}
        .card-kospi {{ background: linear-gradient(135deg, #5f27cd, #341f97); }}
        
        /* 탭 컨텐츠 */
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        
        /* 토글 섹션 */
        .toggle-section {{ margin-top: 30px; border-top: 2px dashed #bdc3c7; padding-top: 30px; }}
        .toggle-header {{ cursor: pointer; display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #ecf0f1; border-radius: 10px; margin-bottom: 15px; }}
        .toggle-header:hover {{ background: #d5dbdb; }}
        .toggle-icon {{ font-size: 1.5em; transition: transform 0.3s; }}
        .toggle-section.open .toggle-icon {{ transform: rotate(180deg); }}
        .toggle-body {{ display: none; }}
        .toggle-section.open .toggle-body {{ display: block; }}
        
        .methodology-box {{ background: #f8f9fa; padding: 20px; border-radius: 12px; margin: 15px 0; }}
        .methodology-box h4 {{ color: #2c3e50; margin-bottom: 10px; }}
        
        footer {{ text-align: center; padding: 30px; color: rgba(255,255,255,0.8); }}
        
        @media (max-width: 1024px) {{
            .portfolio-summary {{ grid-template-columns: repeat(2, 1fr); }}
            .macro-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 헤더 -->
        <div class="header">
            <h1>📊 KStock Integrated Analysis Report</h1>
            <div class="subtitle">Multi-Level Investment Analysis System</div>
            <div class="date">{date[:10]} | Level 1 → 2 → 3 Pipeline Complete</div>
        </div>
        
        <!-- 네비게이션 -->
        <div class="nav">
            <a href="#level3" class="nav-btn">🎯 Level 3 (Final)</a>
            <a href="#methodology" class="nav-btn">📋 Methodology</a>
            <a href="#level2" class="nav-btn">🌍 Level 2 (Sector/Macro)</a>
            <a href="#level1" class="nav-btn">🔍 Level 1 (Stock Analysis)</a>
        </div>
        
        <!-- LEVEL 3: 최종 포트폴리오 -->
        <div id="level3" class="section l3-highlight">
            <h2>🎯 Level 3: Final Portfolio</h2>
            
            <div class="portfolio-summary">
                <div class="portfolio-card">
                    <div class="portfolio-value">{l3_summary.get('long_count', 0)}</div>
                    <div class="portfolio-label">Long Positions</div>
                </div>
                <div class="portfolio-card">
                    <div class="portfolio-value">{l3_summary.get('short_count', 0)}</div>
                    <div class="portfolio-label">Short Positions</div>
                </div>
                <div class="portfolio-card">
                    <div class="portfolio-value">{l3_summary.get('long_weight', 0)*100:.1f}%</div>
                    <div class="portfolio-label">Long Allocation</div>
                </div>
                <div class="portfolio-card">
                    <div class="portfolio-value">{l3_summary.get('cash_weight', 0)*100:.1f}%</div>
                    <div class="portfolio-label">Cash</div>
                </div>
            </div>
            
            <div class="allocation-bar">
                <div class="alloc-long" style="width: {l3_summary.get('long_weight', 0)*100}%"></div>
                <div class="alloc-short" style="width: {l3_summary.get('short_weight', 0)*100}%"></div>
                <div class="alloc-cash" style="width: {l3_summary.get('cash_weight', 0)*100}%"></div>
            </div>
            
            <h3>📈 Long Positions ({len(long_positions)})</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Stock</th>
                        <th>Sector</th>
                        <th>Final Score</th>
                        <th>Rating</th>
                        <th>Weight</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Long positions
    for i, pos in enumerate(long_positions, 1):
        badge_class = 'badge-strong-buy' if pos['rating'] == 'STRONG_BUY' else 'badge-buy'
        score_class = 'score-high' if pos['final_score'] >= 75 else 'score-mid'
        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><strong>{pos['name']}</strong><br><small>{pos['symbol']}</small></td>
                        <td>{pos['sector']}</td>
                        <td class="{score_class}">{pos['final_score']}</td>
                        <td><span class="badge {badge_class}">{pos['rating']}</span></td>
                        <td>{pos['position_size']*100:.0f}%</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
            
            <h3 style="margin-top: 25px;">📉 Short Positions (Top 5)</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Stock</th>
                        <th>Sector</th>
                        <th>Final Score</th>
                        <th>Rating</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Short positions (TOP 5)
    for i, pos in enumerate(short_positions[:5], 1):
        badge_class = 'badge-sell'
        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><strong>{pos['name']}</strong><br><small>{pos['symbol']}</small></td>
                        <td>{pos['sector']}</td>
                        <td class="score-low">{pos['final_score']}</td>
                        <td><span class="badge {badge_class}">{pos['rating']}</span></td>
                    </tr>
"""
    
    html += f"""
                </tbody>
            </table>
        </div>
        
        <!-- 방법론 -->
        <div id="methodology" class="section">
            <h2>📋 Score Calculation Methodology</h2>
            
            <div class="methodology-box">
                <h4>🧮 Final Score Formula</h4>
                <p><strong>Final Score = (Level 1 × 50%) + (Level 2 Sector × 30%) + (Level 2 Macro × 20%)</strong></p>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-top: 20px;">
                <div class="methodology-box">
                    <h4>📊 Level 1 Components (50%)</h4>
                    <ul style="margin-left: 20px; line-height: 1.8;">
                        <li>Technical Analysis (TECH_001)</li>
                        <li>Quantitative Analysis (QUANT_001)</li>
                        <li>Qualitative Analysis (QUAL_001)</li>
                        <li>News Sentiment (NEWS_001)</li>
                    </ul>
                </div>
                <div class="methodology-box">
                    <h4>🌍 Level 2 Components (50%)</h4>
                    <ul style="margin-left: 20px; line-height: 1.8;">
                        <li>Sector Rotation Analysis (30%)</li>
                        <li>Macro Environment (20%)</li>
                        <li>Interest Rates, FX, VIX, KOSPI</li>
                    </ul>
                </div>
            </div>
            
            <div class="methodology-box" style="margin-top: 15px;">
                <h4>🎯 Investment Thresholds (Conservative)</h4>
                <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; text-align: center;">
                    <div style="padding: 10px; background: #27ae60; color: white; border-radius: 8px;">
                        <div style="font-weight: bold;">STRONG BUY</div>
                        <div>≥ 75</div>
                    </div>
                    <div style="padding: 10px; background: #2ecc71; color: white; border-radius: 8px;">
                        <div style="font-weight: bold;">BUY</div>
                        <div>≥ 70</div>
                    </div>
                    <div style="padding: 10px; background: #f39c12; color: white; border-radius: 8px;">
                        <div style="font-weight: bold;">HOLD</div>
                        <div>≥ 50</div>
                    </div>
                    <div style="padding: 10px; background: #e74c3c; color: white; border-radius: 8px;">
                        <div style="font-weight: bold;">SELL</div>
                        <div>≥ 40</div>
                    </div>
                    <div style="padding: 10px; background: #c0392b; color: white; border-radius: 8px;">
                        <div style="font-weight: bold;">STRONG SELL</div>
                        <div>&lt; 35</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- LEVEL 2: 섹터/매크로 -->
        <div id="level2" class="section">
            <h2>🌍 Level 2: Sector & Macro Analysis</h2>
            
            <h3>📈 Macro Indicators</h3>
            <div class="macro-grid">
                <div class="macro-card card-treasury">
                    <div class="macro-value">{macro_indicators.get('us_treasury', {}).get('current', '-'):.2f}%</div>
                    <div class="macro-label">US 10Y Treasury</div>
                </div>
                <div class="macro-card card-currency">
                    <div class="macro-value">{macro_indicators.get('usd_krw', {}).get('current', '-'):,.0f}</div>
                    <div class="macro-label">USD/KRW</div>
                </div>
                <div class="macro-card card-vix">
                    <div class="macro-value">{macro_indicators.get('vix', {}).get('current', '-')}</div>
                    <div class="macro-label">VIX</div>
                </div>
                <div class="macro-card card-kospi">
                    <div class="macro-value">{macro_indicators.get('kospi', {}).get('current', '-'):,.0f}</div>
                    <div class="macro-label">KOSPI</div>
                </div>
            </div>
            
            <div style="padding: 15px; background: {'#d4edda' if 'BULL' in macro_adj.get('market_condition', '') else '#f8d7da' if 'BEAR' in macro_adj.get('market_condition', '') else '#fff3cd'}; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                <div style="font-size: 1.3em; font-weight: bold;">Market Condition: {macro_adj.get('market_condition', 'NEUTRAL')}</div>
                <div>Macro Adjustment: {macro_adj.get('pct', 0):+.0f}%</div>
            </div>
            
            <h3>📊 Sector Rankings (Top 15)</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Sector</th>
                        <th>Avg Score</th>
                        <th>Strength</th>
                        <th>Rel. Strength</th>
                        <th>Top Stock</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Sectors (TOP 15)
    for i, (name, data) in enumerate(sorted_sectors[:15], 1):
        badge_class = 'badge-strong' if data['strength'] == 'STRONG' else 'badge-weak' if data['strength'] == 'WEAK' else 'badge-moderate'
        rel_color = 'score-high' if data['relative_strength_pct'] > 0 else 'score-low'
        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><strong>{name}</strong></td>
                        <td>{data['average_score']}</td>
                        <td><span class="badge {badge_class}">{data['strength']}</span></td>
                        <td class="{rel_color}">{data['relative_strength_pct']:+.1f}%</td>
                        <td>{data['top_performer']['name']} ({data['top_performer']['score']})</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <!-- LEVEL 1: 개별 종목 분석 -->
        <div id="level1" class="section">
            <h2>🔍 Level 1: Individual Stock Analysis</h2>
            
            <h3>🏆 Top 20 Rankings</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Stock</th>
                        <th>Market</th>
                        <th>Sector</th>
                        <th>TECH</th>
                        <th>QUANT</th>
                        <th>QUAL</th>
                        <th>NEWS</th>
                        <th>Avg</th>
                        <th>Consensus</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Level 1 TOP 20
    for i, stock in enumerate(l1_sorted[:20], 1):
        agents = stock.get('agents', {})
        tech = agents.get('TECH', {}).get('score', 0)
        quant = agents.get('QUANT', {}).get('score', 0)
        qual = agents.get('QUAL', {}).get('score', 0)
        news = agents.get('NEWS', {}).get('score', 0)
        avg = stock.get('avg_score', 0)
        consensus = stock.get('consensus', 'HOLD')
        
        badge_class = 'badge-strong-buy' if consensus == 'STRONG BUY' else 'badge-buy' if consensus == 'BUY' else 'badge-hold'
        score_class = 'score-high' if avg >= 70 else 'score-mid' if avg >= 50 else 'score-low'
        
        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><strong>{stock['name']}</strong><br><small>{stock['symbol']}</small></td>
                        <td>{stock.get('market', 'KOSPI')}</td>
                        <td>{stock.get('sector', '-')}</td>
                        <td>{tech}</td>
                        <td>{quant}</td>
                        <td>{qual}</td>
                        <td>{news}</td>
                        <td class="{score_class}">{avg}</td>
                        <td><span class="badge {badge_class}">{consensus}</span></td>
                    </tr>
"""
    
    html += f"""
                </tbody>
            </table>
            
            <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 10px;">
                <h4>📋 Analysis Summary</h4>
                <p><strong>Total Stocks Analyzed:</strong> {len(l1_results)}</p>
                <p><strong>Average Score:</strong> {sum(r.get('avg_score', 0) for r in l1_results) / len(l1_results):.1f}</p>
                <p><strong>Data Source:</strong> KOSPI 39 + KOSDAQ 20 stocks</p>
            </div>
        </div>
        
        <footer>
            <p>KStock Multi-Level Analysis System | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>Level 1 (4 Agents) → Level 2 (2 Agents) → Level 3 (1 PM) Pipeline</p>
        </footer>
    </div>
    
    <script>
        // Smooth scroll for navigation
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {{
            anchor.addEventListener('click', function (e) {{
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({{
                    behavior: 'smooth'
                }});
            }});
        }});
    </script>
</body>
</html>
"""
    
    return html


def main():
    print("Loading all level data...")
    l1_data, l2_sector, l2_macro, l3_data = load_all_data()
    
    if not l3_data:
        print("No Level 3 data found!")
        return
    
    print(f"Level 1: {len(l1_data.get('results', []))} stocks")
    print(f"Level 2: {len(l2_sector.get('sectors', {}))} sectors")
    print(f"Level 3: {l3_data.get('portfolio_summary', {}).get('long_count', 0)} long positions")
    
    print("Generating integrated report...")
    html = generate_html(l1_data, l2_sector, l2_macro, l3_data)
    
    output_file = f"{OUTPUT_PATH}/level3_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report saved: {output_file}")
    
    summary = l3_data.get('portfolio_summary', {})
    print("\n" + "=" * 60)
    print("📊 INTEGRATED REPORT SUMMARY")
    print("=" * 60)
    print(f"Level 3: {summary.get('long_count', 0)} long / {summary.get('short_count', 0)} short")
    print(f"Allocation: {summary.get('long_weight', 0)*100:.1f}% long / {summary.get('cash_weight', 0)*100:.1f}% cash")
    print("=" * 60)


if __name__ == '__main__':
    main()
