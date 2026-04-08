#!/usr/bin/env python3
"""
KRX Hybrid Strategy Report Generator
KRX 하이브리드 전략 리포트 생성기
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
from datetime import datetime
from v2.strategies.krx_hybrid import run_krx_hybrid_scan


def generate_html_report(signals, date_str, output_path):
    """HTML 리포트 생성"""
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KRX Hybrid Strategy Report - {date_str}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            padding: 40px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .subtitle {{
            color: #888;
            font-size: 1.1rem;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.05);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-label {{
            color: #888;
            margin-top: 5px;
        }}
        
        .stock-grid {{
            display: grid;
            gap: 15px;
        }}
        
        .stock-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }}
        
        .stock-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}
        
        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .stock-rank {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.2rem;
        }}
        
        .stock-info h3 {{
            font-size: 1.3rem;
            margin-bottom: 3px;
        }}
        
        .stock-code {{
            color: #888;
            font-size: 0.9rem;
        }}
        
        .stock-score {{
            text-align: right;
        }}
        
        .score-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #4ade80;
        }}
        
        .score-label {{
            color: #888;
            font-size: 0.8rem;
        }}
        
        .stock-metrics {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 15px 0;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
        }}
        
        .metric {{
            text-align: center;
        }}
        
        .metric-value {{
            font-size: 1.3rem;
            font-weight: bold;
            color: #fff;
        }}
        
        .metric-label {{
            font-size: 0.8rem;
            color: #888;
            margin-top: 3px;
        }}
        
        .reasons {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 15px;
        }}
        
        .reason-tag {{
            background: rgba(102, 126, 234, 0.2);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            color: #a5b4fc;
        }}
        
        .positive {{
            color: #4ade80;
        }}
        
        .negative {{
            color: #f87171;
        }}
        
        footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            margin-top: 30px;
        }}
        
        @media (max-width: 768px) {{
            .stock-metrics {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            h1 {{
                font-size: 1.8rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 KRX Hybrid Strategy</h1>
            <p class="subtitle">실시간 KRX 데이터 + 기술적 분석 하이브리드 전략</p>
            <p class="subtitle">{date_str}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(signals)}</div>
                <div class="stat-label">선정 종목</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len([s for s in signals if s.score >= 80])}</div>
                <div class="stat-label">80점 이상</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len([s for s in signals if s.score >= 75])}</div>
                <div class="stat-label">75점 이상</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">962</div>
                <div class="stat-label">분석 대상</div>
            </div>
        </div>
        
        <div class="stock-grid">
'''
    
    # Add stock cards
    for i, signal in enumerate(signals, 1):
        meta = signal.metadata
        krx = meta.get('krx', {})
        tech = meta.get('technical', {})
        
        change_pct = krx.get('change_pct', 0)
        change_class = 'positive' if change_pct >= 0 else 'negative'
        change_sign = '+' if change_pct >= 0 else ''
        
        html += f'''
            <div class="stock-card">
                <div class="stock-header">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div class="stock-rank">{i}</div>
                        <div class="stock-info">
                            <h3>{signal.name}</h3>
                            <div class="stock-code">{signal.code} | {krx.get('market', 'KOSPI')}</div>
                        </div>
                    </div>
                    <div class="stock-score">
                        <div class="score-value">{signal.score:.1f}</div>
                        <div class="score-label">점수</div>
                    </div>
                </div>
                
                <div class="stock-metrics">
                    <div class="metric">
                        <div class="metric-value {change_class}">{change_sign}{change_pct:.2f}%</div>
                        <div class="metric-label">등락률</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{krx.get('price', 0):,.0f}원</div>
                        <div class="metric-label">현재가</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{tech.get('rsi', 'N/A')}</div>
                        <div class="metric-label">RSI(14)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{tech.get('volume_ratio', 'N/A')}x</div>
                        <div class="metric-label">거래량</div>
                    </div>
                </div>
                
                <div class="reasons">
'''
        for reason in signal.reason:
            html += f'                    <span class="reason-tag">{reason}</span>\n'
        
        html += '''                </div>
            </div>
'''
    
    html += f'''
        </div>
        
        <footer>
            <p>KRX Hybrid Strategy Report | Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>Data Source: KRX Open API + Technical Analysis</p>
        </footer>
    </div>
</body>
</html>
'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 리포트 생성 완료: {output_path}")


def main():
    import sys
    
    # 날짜 설정
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y%m%d')
    min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 70.0
    
    # 스캔 실행
    signals = run_krx_hybrid_scan(date_str, min_score)
    
    if not signals:
        print("❌ 신호 없음")
        return
    
    # JSON 저장
    json_path = f'docs/krx_hybrid_report_{date_str}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([s.to_dict() for s in signals], f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 저장: {json_path}")
    
    # HTML 리포트 생성
    html_path = f'docs/krx_hybrid_report_{date_str}.html'
    generate_html_report(signals, date_str, html_path)
    
    print(f"\n📊 리포트 요약:")
    print(f"   - 선정 종목: {len(signals)}개")
    print(f"   - 80점 이상: {len([s for s in signals if s.score >= 80])}개")
    print(f"   - 75점 이상: {len([s for s in signals if s.score >= 75])}개")
    print(f"\n🔗 파일 위치:")
    print(f"   - HTML: {html_path}")
    print(f"   - JSON: {json_path}")


if __name__ == '__main__':
    main()
