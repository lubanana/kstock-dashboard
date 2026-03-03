#!/usr/bin/env python3
"""
Level 3 Final Report Generator
최종 포트폴리오 리포트 생성기
"""

import json
import os
from datetime import datetime
from typing import Dict, List

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/docs'
DATA_PATH = f'{BASE_PATH}/data/level3_daily'


def load_latest_report() -> Dict:
    """최신 Level 3 리포트 로드"""
    files = [f for f in os.listdir(DATA_PATH) if f.startswith('portfolio_report_') and f.endswith('.json')] if os.path.exists(DATA_PATH) else []
    if not files:
        return {}
    
    latest = sorted(files)[-1]
    with open(f'{DATA_PATH}/{latest}', 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_html(report: Dict) -> str:
    """HTML 리포트 생성"""
    
    date = report.get('analysis_date', datetime.now().isoformat())
    summary = report.get('portfolio_summary', {})
    portfolio = report.get('portfolio', {})
    outlook = report.get('market_outlook', {})
    methodology = report.get('methodology', {})
    
    long_positions = portfolio.get('long', [])
    short_positions = portfolio.get('short', [])
    rankings = report.get('all_rankings', [])
    
    # 커트라인
    thresholds = methodology.get('thresholds', {})
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Level 3 Final Portfolio Report - {date[:10]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ opacity: 0.9; font-size: 1.2em; }}
        .header .date {{ opacity: 0.8; margin-top: 10px; }}
        
        .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; text-align: center; }}
        .summary-value {{ font-size: 2.5em; font-weight: bold; color: #2c3e50; }}
        .summary-label {{ color: #7f8c8d; margin-top: 5px; }}
        
        .allocation-bar {{ display: flex; height: 40px; border-radius: 20px; overflow: hidden; margin: 20px 0; }}
        .alloc-long {{ background: #27ae60; }}
        .alloc-short {{ background: #e74c3c; }}
        .alloc-cash {{ background: #95a5a6; }}
        
        .section {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; margin-bottom: 25px; }}
        .section h2 {{ color: #2c3e50; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid #3498db; }}
        
        .position-table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
        .position-table th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
        .position-table td {{ padding: 12px; border-bottom: 1px solid #ecf0f1; }}
        .position-table tr:hover {{ background: #f8f9fa; }}
        
        .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 500; }}
        .badge-strong-buy {{ background: #27ae60; color: white; }}
        .badge-buy {{ background: #2ecc71; color: white; }}
        .badge-hold {{ background: #f39c12; color: white; }}
        .badge-sell {{ background: #e74c3c; color: white; }}
        .badge-strong-sell {{ background: #c0392b; color: white; }}
        
        .score-high {{ color: #27ae60; font-weight: bold; }}
        .score-mid {{ color: #f39c12; font-weight: bold; }}
        .score-low {{ color: #e74c3c; font-weight: bold; }}
        
        .methodology-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }}
        .method-card {{ padding: 20px; background: #f8f9fa; border-radius: 12px; text-align: center; }}
        .method-value {{ font-size: 1.5em; font-weight: bold; color: #2c3e50; }}
        .method-label {{ color: #7f8c8d; font-size: 0.9em; margin-top: 5px; }}
        
        .threshold-list {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
        .threshold-item {{ display: flex; justify-content: space-between; padding: 10px; background: #f8f9fa; border-radius: 8px; }}
        
        .outlook-card {{ padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }}
        .outlook-bullish {{ background: #d4edda; border: 2px solid #28a745; }}
        .outlook-neutral {{ background: #fff3cd; border: 2px solid #ffc107; }}
        .outlook-bearish {{ background: #f8d7da; border: 2px solid #dc3545; }}
        .outlook-title {{ font-size: 1.5em; font-weight: bold; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Level 3 Final Portfolio Report</h1>
            <div class="subtitle">Portfolio Manager (PM_001) - Conservative Strategy</div>
            <div class="date">{date[:10]} | {summary.get('total_stocks', 0)} Stocks Analyzed</div>
        </div>
        
        <!-- 포트폴리오 요약 -->
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-value" style="color: #27ae60;">{summary.get('long_count', 0)}</div>
                <div class="summary-label">Long Positions</div>
            </div>
            <div class="summary-card">
                <div class="summary-value" style="color: #e74c3c;">{summary.get('short_count', 0)}</div>
                <div class="summary-label">Short Positions</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{summary.get('long_weight', 0)*100:.1f}%</div>
                <div class="summary-label">Long Allocation</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{summary.get('cash_weight', 0)*100:.1f}%</div>
                <div class="summary-label">Cash</div>
            </div>
        </div>
        
        <!-- 자산 배분 바 -->
        <div class="section">
            <h2>📊 Portfolio Allocation</h2>
            <div class="allocation-bar">
                <div class="alloc-long" style="width: {summary.get('long_weight', 0)*100}%;"></div>
                <div class="alloc-short" style="width: {summary.get('short_weight', 0)*100}%;"></div>
                <div class="alloc-cash" style="width: {summary.get('cash_weight', 0)*100}%;"></div>
            </div>
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div>
                    <div style="color: #27ae60; font-weight: bold;">Long</div>
                    <div>{summary.get('long_weight', 0)*100:.1f}%</div>
                </div>
                <div>
                    <div style="color: #e74c3c; font-weight: bold;">Short</div>
                    <div>{summary.get('short_weight', 0)*100:.1f}%</div>
                </div>
                <div>
                    <div style="color: #95a5a6; font-weight: bold;">Cash</div>
                    <div>{summary.get('cash_weight', 0)*100:.1f}%</div>
                </div>
            </div>
        </div>
        
        <!-- 시장 전망 -->
        <div class="section">
            <h2>🌍 Market Outlook</h2>
            
            <div class="outlook-card {'outlook-bullish' if 'BULL' in outlook.get('macro_condition', '') else 'outlook-bearish' if 'BEAR' in outlook.get('macro_condition', '') else 'outlook-neutral'}">
                <div class="outlook-title">{outlook.get('macro_condition', 'NEUTRAL')}</div>
                <div>Macro Adjustment: {outlook.get('macro_adjustment', 0):+.0f}%</div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                <div style="padding: 15px; background: #f8f9fa; border-radius: 10px; text-align: center;">
                    <div style="font-weight: bold; color: #2c3e50;">Equity Exposure</div>
                    <div>{outlook.get('recommendations', {}).get('equity_exposure', 'Neutral')}</div>
                </div>
                <div style="padding: 15px; background: #f8f9fa; border-radius: 10px; text-align: center;">
                    <div style="font-weight: bold; color: #2c3e50;">Risk Mode</div>
                    <div>{outlook.get('recommendations', {}).get('risk_on_off', 'Neutral')}</div>
                </div>
                <div style="padding: 15px; background: #f8f9fa; border-radius: 10px; text-align: center;">
                    <div style="font-weight: bold; color: #2c3e50;">Defensive</div>
                    <div>{'Yes' if outlook.get('recommendations', {}).get('defensive_sectors') else 'No'}</div>
                </div>
            </div>
        </div>
        
        <!-- Long 포지션 -->
        <div class="section">
            <h2>📈 Long Positions ({len(long_positions)})</h2>
            
            <table class="position-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Name</th>
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
        badge_class = {
            'STRONG_BUY': 'badge-strong-buy',
            'BUY': 'badge-buy'
        }.get(pos['rating'], 'badge-buy')
        
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
    
    if not long_positions:
        html += '<tr><td colspan="6" style="text-align: center; color: #95a5a6;">No long positions selected</td></tr>'
    
    html += """
                </tbody>
            </table>
        </div>
        
        <!-- Short 포지션 -->
        <div class="section">
            <h2>📉 Short Positions ({len(short_positions)})</h2>
            
            <table class="position-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Name</th>
                        <th>Sector</th>
                        <th>Final Score</th>
                        <th>Rating</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Short positions (TOP 10만)
    for i, pos in enumerate(short_positions[:10], 1):
        badge_class = {
            'STRONG_SELL': 'badge-strong-sell',
            'SELL': 'badge-sell'
        }.get(pos['rating'], 'badge-sell')
        
        html += f"""
                    <tr>
                        <td>{i}</td>
                        <td><strong>{pos['name']}</strong><br><small>{pos['symbol']}</small></td>
                        <td>{pos['sector']}</td>
                        <td class="score-low">{pos['final_score']}</td>
                        <td><span class="badge {badge_class}">{pos['rating']}</span></td>
                    </tr>
"""
    
    if not short_positions:
        html += '<tr><td colspan="5" style="text-align: center; color: #95a5a6;">No short positions selected</td></tr>'
    elif len(short_positions) > 10:
        html += f'<tr><td colspan="5" style="text-align: center; color: #95a5a6;">... and {len(short_positions) - 10} more</td></tr>'
    
    html += """
                </tbody>
            </table>
        </div>
        
        <!-- 방법론 -->
        <div class="section">
            <h2>📋 Methodology</h2>
            
            <h3 style="margin-bottom: 15px;">Score Weights</h3>
            <div class="methodology-grid">
                <div class="method-card">
                    <div class="method-value">50%</div>
                    <div class="method-label">Level 1 Analysis</div>
                </div>
                <div class="method-card">
                    <div class="method-value">30%</div>
                    <div class="method-label">Sector Adjustment</div>
                </div>
                <div class="method-card">
                    <div class="method-value">20%</div>
                    <div class="method-label">Macro Adjustment</div>
                </div>
            </div>
            
            <h3 style="margin: 25px 0 15px;">Score Thresholds (Conservative)</h3>
            <div class="threshold-list">
                <div class="threshold-item">
                    <span>STRONG BUY</span>
                    <span style="font-weight: bold; color: #27ae60;">>= {thresholds.get('STRONG_BUY', 75)}</span>
                </div>
                <div class="threshold-item">
                    <span>BUY</span>
                    <span style="font-weight: bold; color: #2ecc71;">>= {thresholds.get('BUY', 70)}</span>
                </div>
                <div class="threshold-item">
                    <span>HOLD</span>
                    <span style="font-weight: bold; color: #f39c12;">>= {thresholds.get('HOLD', 50)}</span>
                </div>
                <div class="threshold-item">
                    <span>SELL</span>
                    <span style="font-weight: bold; color: #e74c3c;">>= {thresholds.get('SELL', 40)}</span>
                </div>
            </div>
        </div>
        
        <div class="section" style="text-align: center; color: #7f8c8d;">
            <p>KStock Level 3 Final Portfolio | Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M') + """</p>
            <p>PM_001 | Conservative Strategy | Multi-Level Analysis</p>
        </div>
    </div>
</body>
</html>"""
    
    return html


def main():
    print("Loading Level 3 report...")
    report = load_latest_report()
    
    if not report:
        print("No report found!")
        return
    
    print(f"Portfolio: {report.get('portfolio_summary', {}).get('long_count', 0)} long, "
          f"{report.get('portfolio_summary', {}).get('short_count', 0)} short")
    
    print("Generating HTML report...")
    html = generate_html(report)
    
    output_file = f"{OUTPUT_PATH}/level3_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report saved: {output_file}")
    
    summary = report.get('portfolio_summary', {})
    print("\n" + "=" * 60)
    print("📊 LEVEL 3 FINAL REPORT SUMMARY")
    print("=" * 60)
    print(f"Long: {summary.get('long_count', 0)} stocks ({summary.get('long_weight', 0)*100:.1f}%)")
    print(f"Short: {summary.get('short_count', 0)} stocks ({summary.get('short_weight', 0)*100:.1f}%)")
    print(f"Cash: {summary.get('cash_weight', 0)*100:.1f}%")
    print("=" * 60)


if __name__ == '__main__':
    main()
