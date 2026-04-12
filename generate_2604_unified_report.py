#!/usr/bin/env python3
"""
2604 V7 Hybrid Report Generator
통합 리포트 생성 (unified_report.py 확장)
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path

def generate_2604_report(json_file: str, output_html: str = None):
    """2604 V7 결과로 통합 리포트 생성"""
    
    # JSON 로드
    with open(json_file, 'r', encoding='utf-8') as f:
        signals = json.load(f)
    
    if not signals:
        print("No signals found")
        return
    
    date = signals[0]['date']
    
    if not output_html:
        output_html = f"reports/2604_v7_unified_{date.replace('-', '')}.html"
    
    # 통계 계산
    total = len(signals)
    avg_score = sum(s['score'] for s in signals) / total
    avg_rr = sum(s['targets']['risk_reward_tp2'] for s in signals) / total
    
    # HTML 테마 (fire 테마)
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2604 V7 Hybrid Report - {date}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #2d1b1b 0%, #1a1a2e 100%);
            min-height: 100vh;
            color: #ffe4d6;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        .header {{
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            color: white;
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 1.1rem; }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,107,53,0.1);
            padding: 25px;
            border-radius: 16px;
            text-align: center;
            border: 1px solid rgba(255,107,53,0.3);
        }}
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #ff6b35;
            margin: 10px 0;
        }}
        .stat-label {{ opacity: 0.7; font-size: 0.9rem; }}
        
        .section {{
            background: rgba(255,107,53,0.05);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,107,53,0.2);
        }}
        .section h2 {{
            color: #ff6b35;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255,107,53,0.5);
        }}
        
        .stock-card {{
            background: rgba(0,0,0,0.2);
            padding: 25px;
            border-radius: 16px;
            margin-bottom: 20px;
            border-left: 4px solid #ff6b35;
        }}
        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .stock-name {{ font-size: 1.4rem; font-weight: bold; }}
        .stock-code {{ opacity: 0.6; font-size: 0.9rem; }}
        .score {{
            background: linear-gradient(135deg, #ff6b35, #f7931e);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.2rem;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            text-align: center;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
        }}
        .metric-value {{ font-size: 1.3rem; font-weight: bold; color: #f7931e; }}
        .metric-label {{ font-size: 0.8rem; opacity: 0.6; margin-top: 5px; }}
        
        .targets {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 20px 0;
            padding: 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
        }}
        .target {{
            text-align: center;
            padding: 15px;
            border-radius: 10px;
        }}
        .target.stop {{ background: rgba(255,71,87,0.2); }}
        .target.tp {{ background: rgba(76,209,55,0.2); }}
        .target.tp2 {{ background: rgba(254,202,87,0.2); border: 1px solid rgba(254,202,87,0.5); }}
        .target-price {{ font-size: 1.2rem; font-weight: bold; }}
        .target-pct {{ font-size: 0.85rem; margin-top: 5px; }}
        .stop .target-price {{ color: #ff4757; }}
        .stop .target-pct {{ color: #ff4757; }}
        .tp .target-price {{ color: #4cd137; }}
        .tp .target-pct {{ color: #4cd137; }}
        .tp2 .target-price {{ color: #feca57; }}
        .tp2 .target-pct {{ color: #feca57; }}
        
        .reasons {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }}
        .reason-tag {{
            background: rgba(255,107,53,0.2);
            color: #ffaa7f;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
        }}
        
        .chart-container {{ height: 300px; margin: 20px 0; }}
        
        footer {{
            text-align: center;
            padding: 40px;
            opacity: 0.5;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 2604 V7 Hybrid</h1>
            <p>통합 폭발적 상승 패턴 스캐너</p>
            <div style="margin-top: 15px; opacity: 0.8;">{date}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">선정 종목</div>
                <div class="stat-value">{total}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">평균 점수</div>
                <div class="stat-value">{avg_score:.0f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">평균 손익비</div>
                <div class="stat-value">1:{avg_rr:.1f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">최고 점수</div>
                <div class="stat-value">{max(s['score'] for s in signals)}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 점수 분포</h2>
            <div class="chart-container">
                <canvas id="scoreChart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 선정 종목 상세</h2>
"""
    
    # 종목 카드 생성
    for i, s in enumerate(signals, 1):
        t = s['targets']
        html += f"""
            <div class="stock-card">
                <div class="stock-header">
                    <div>
                        <div class="stock-name">{i}. {s['name']}</div>
                        <div class="stock-code">{s['code']} | 현재가: {s['price']:,.0f}원</div>
                    </div>
                    <div class="score">{s['score']}점</div>
                </div>
                
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">{s['scores']['volume']}</div>
                        <div class="metric-label">거래량</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{s['scores']['technical']}</div>
                        <div class="metric-label">기술적</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{s['scores']['fibonacci']}</div>
                        <div class="metric-label">피볼나치</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{s['scores']['market']}</div>
                        <div class="metric-label">시장맥락</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{s['scores']['momentum']}</div>
                        <div class="metric-label">모멘텀</div>
                    </div>
                </div>
                
                <div class="targets">
                    <div class="target stop">
                        <div style="color: #888; font-size: 0.8rem; margin-bottom: 5px;">🛑 손절가</div>
                        <div class="target-price">{t['stop_loss']:,.0f}원</div>
                        <div class="target-pct">{t['stop_pct']:+.1f}%</div>
                    </div>
                    <div class="target tp">
                        <div style="color: #888; font-size: 0.8rem; margin-bottom: 5px;">🎯 TP1</div>
                        <div class="target-price">{t['tp1']:,.0f}원</div>
                        <div class="target-pct">{(t['tp1']/s['price']-1)*100:+.1f}%</div>
                    </div>
                    <div class="target tp2">
                        <div style="color: #888; font-size: 0.8rem; margin-bottom: 5px;">⭐ TP2 (추천)</div>
                        <div class="target-price">{t['tp2']:,.0f}원</div>
                        <div class="target-pct">{(t['tp2']/s['price']-1)*100:+.1f}% | 1:{t['risk_reward_tp2']:.1f}</div>
                    </div>
                    <div class="target tp">
                        <div style="color: #888; font-size: 0.8rem; margin-bottom: 5px;">🚀 TP3</div>
                        <div class="target-price">{t['tp3']:,.0f}원</div>
                        <div class="target-pct">{(t['tp3']/s['price']-1)*100:+.1f}%</div>
                    </div>
                </div>
                
                <div class="reasons">
"""
        for reason in s['reasons']:
            html += f'                    <span class="reason-tag">{reason}</span>\n'
        
        html += """                </div>
            </div>
"""
    
    # 차트 데이터
    scores = [s['score'] for s in signals]
    names = [s['name'] for s in signals]
    
    html += f"""
        </div>
        
        <footer>
            <p>2604 V7 Hybrid Scanner | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p style="margin-top: 10px; font-size: 0.8rem;">* 과거 성과가 미래 수익을 보장하지 않습니다</p>
        </footer>
    </div>
    
    <script>
        const ctx = document.getElementById('scoreChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {names},
                datasets: [{{
                    label: '종합 점수',
                    data: {scores},
                    backgroundColor: [
                        'rgba(255, 107, 53, 0.8)',
                        'rgba(247, 147, 30, 0.8)',
                        'rgba(254, 202, 87, 0.8)',
                        'rgba(255, 159, 67, 0.8)',
                        'rgba(255, 99, 72, 0.8)',
                        'rgba(255, 71, 87, 0.8)',
                        'rgba(76, 209, 55, 0.8)'
                    ],
                    borderRadius: 10
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 100,
                        ticks: {{ color: '#ffe4d6' }},
                        grid: {{ color: 'rgba(255,255,255,0.1)' }}
                    }},
                    x: {{
                        ticks: {{ color: '#ffe4d6' }},
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    # 저장
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Report saved: {output_html}")
    return output_html


if __name__ == '__main__':
    import sys
    
    json_file = sys.argv[1] if len(sys.argv) > 1 else 'reports/2604_v7_hybrid_20260409.json'
    generate_2604_report(json_file)
