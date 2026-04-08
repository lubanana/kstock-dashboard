#!/usr/bin/env python3
"""
2604 Scanner Backtest & Report Generator
백테스트 + HTML 리포트 통합
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

from v2.strategies.scanner_2604 import Scanner2604
from v2.core.data_manager import DataManager
from v2.core.backtest_engine import BacktestEngine


def run_backtest(start_date: str, end_date: str, min_score: float = 75.0) -> Dict:
    """
    2604 스캐너 백테스트 실행
    
    Args:
        start_date: YYYY-MM-DD
        end_date: YYYY-MM-DD
        min_score: 최소 진입 점수
    """
    print("=" * 80)
    print("📊 2604 스캐너 백테스트")
    print("=" * 80)
    print(f"기간: {start_date} ~ {end_date}")
    print(f"진입 점수: {min_score}+\n")
    
    scanner = Scanner2604(use_krx=False)  # 백테스트는 KRX 없이
    dm = DataManager()
    backtest = BacktestEngine(
        stop_loss=-0.07,
        take_profit=0.25,
        trailing_stop=0.10,
        max_holding_days=7
    )
    
    # 거래일 생성
    date_range = pd.bdate_range(start=start_date, end=end_date)
    
    all_signals = []
    for date in date_range:
        date_str = date.strftime('%Y-%m-%d')
        
        # 스캔 실행
        signals = scanner.run(dm, date_str)
        
        if signals:
            for signal in signals:
                # 가상 포지션
                position = {
                    'entry_date': date_str,
                    'code': signal.code,
                    'name': signal.name,
                    'entry_price': signal.metadata['price'],
                    'score': signal.score,
                    'metadata': signal.metadata
                }
                all_signals.append(position)
        
        if len(date_range) <= 10 or date.day % 5 == 0:
            print(f"   {date_str}: {len(signals)}개 신호")
    
    # 백테스트 결과 요약
    print(f"\n✅ 백테스트 완료")
    print(f"   총 진입: {len(all_signals)}회")
    
    return {
        'total_signals': len(all_signals),
        'signals': all_signals,
        'period': f"{start_date} ~ {end_date}",
        'min_score': min_score
    }


def generate_html_report(signals: List[Dict], backtest_data: Dict, date_str: str, output_path: str):
    """HTML 리포트 생성"""
    
    # 통계 계산
    score_dist = {
        '90+': len([s for s in signals if s.score >= 90]),
        '85-89': len([s for s in signals if 85 <= s.score < 90]),
        '80-84': len([s for s in signals if 80 <= s.score < 85]),
        '75-79': len([s for s in signals if 75 <= s.score < 80])
    }
    
    html = f'''&lt;!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2604 Scanner Report - {date_str}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            padding: 50px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 25px;
            margin-bottom: 30px;
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .logo {{
            font-size: 4rem;
            margin-bottom: 10px;
        }}
        
        h1 {{
            font-size: 2.8rem;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .subtitle {{
            color: #888;
            font-size: 1.2rem;
        }}
        
        .strategy-pills {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }}
        
        .pill {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.05);
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-icon {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .stat-value {{
            font-size: 3rem;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .stat-label {{
            color: #888;
            margin-top: 5px;
            font-size: 1rem;
        }}
        
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 25px;
            padding: 30px;
            margin-bottom: 30px;
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .score-distribution {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        
        .score-box {{
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }}
        
        .score-count {{
            font-size: 2rem;
            font-weight: bold;
            color: #4ade80;
        }}
        
        .score-range {{
            color: #888;
            font-size: 0.9rem;
        }}
        
        .stock-grid {{
            display: grid;
            gap: 15px;
        }}
        
        .stock-card {{
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
        }}
        
        .stock-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.3);
        }}
        
        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .stock-rank {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            width: 50px;
            height: 50px;
            border-radius: 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.3rem;
        }}
        
        .stock-info h3 {{
            font-size: 1.4rem;
            margin-bottom: 5px;
        }}
        
        .stock-code {{
            color: #888;
            font-size: 1rem;
        }}
        
        .stock-score {{
            text-align: right;
        }}
        
        .score-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #4ade80;
        }}
        
        .score-label {{
            color: #888;
            font-size: 0.85rem;
        }}
        
        .score-breakdown {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin: 20px 0;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
        }}
        
        .breakdown-item {{
            text-align: center;
        }}
        
        .breakdown-value {{
            font-size: 1.2rem;
            font-weight: bold;
            color: #a5b4fc;
        }}
        
        .breakdown-label {{
            font-size: 0.75rem;
            color: #666;
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
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.9rem;
            color: #a5b4fc;
            border: 1px solid rgba(102, 126, 234, 0.3);
        }}
        
        footer {{
            text-align: center;
            padding: 40px;
            color: #666;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 30px;
        }}
        
        @media (max-width: 768px) {{
            .score-distribution {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .score-breakdown {{
                grid-template-columns: repeat(3, 1fr);
            }}
            
            h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">🔥</div>
            <h1>2604 통합 스캐너</h1>
            <p class="subtitle">Ultimate Hybrid Strategy - KAGGRESSIVE + IVF + KRX + D+</p>
            <p class="subtitle">{date_str}</p>
            
            <div class="strategy-pills">
                <span class="pill">거래량 분석</span>
                <span class="pill">기술적 지표</span>
                <span class="pill">피볼나치</span>
                <span class="pill">시장 맥락</span>
                <span class="pill">모멘텀</span>
            </div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-value">{len(signals)}</div>
                <div class="stat-label">선정 종목</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">🏆</div>
                <div class="stat-value">{score_dist['90+']}</div>
                <div class="stat-label">90점 이상</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">⭐</div>
                <div class="stat-value">{score_dist['85-89'] + score_dist['90+']}</div>
                <div class="stat-label">85점 이상</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon">📈</div>
                <div class="stat-value">{score_dist['80-84']}</div>
                <div class="stat-label">80점 이상</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 점수 분포</h2>
            <div class="score-distribution">
                <div class="score-box">
                    <div class="score-count">{score_dist['90+']}</div>
                    <div class="score-range">90점+</div>
                </div>
                <div class="score-box">
                    <div class="score-count">{score_dist['85-89']}</div>
                    <div class="score-range">85-89점</div>
                </div>
                <div class="score-box">
                    <div class="score-count">{score_dist['80-84']}</div>
                    <div class="score-range">80-84점</div>
                </div>
                <div class="score-box">
                    <div class="score-count">{score_dist['75-79']}</div>
                    <div class="score-range">75-79점</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 Top {min(20, len(signals))} 선정 종목</h2>
            <div class="stock-grid">
'''
    
    # Add stock cards
    for i, signal in enumerate(signals[:20], 1):
        meta = signal.metadata
        scores = meta.get('scores', {})
        
        html += f'''
                <div class="stock-card">
                    <div class="stock-header">
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <div class="stock-rank">{i}</div>
                            <div class="stock-info">
                                <h3>{signal.name}</h3>
                                <div class="stock-code">{signal.code}</div>
                            </div>
                        </div>
                        <div class="stock-score">
                            <div class="score-value">{signal.score:.0f}</div>
                            <div class="score-label">점수</div>
                        </div>
                    </div>
                    
                    <div class="score-breakdown">
                        <div class="breakdown-item">
                            <div class="breakdown-value">{scores.get('volume', 0):.0f}</div>
                            <div class="breakdown-label">거래량</div>
                        </div>
                        <div class="breakdown-item">
                            <div class="breakdown-value">{scores.get('technical', 0):.0f}</div>
                            <div class="breakdown-label">기술적</div>
                        </div>
                        <div class="breakdown-item">
                            <div class="breakdown-value">{scores.get('fibonacci', 0):.0f}</div>
                            <div class="breakdown-label">피볼나치</div>
                        </div>
                        <div class="breakdown-item">
                            <div class="breakdown-value">{scores.get('market', 0):.0f}</div>
                            <div class="breakdown-label">시장</div>
                        </div>
                        <div class="breakdown-item">
                            <div class="breakdown-value">{scores.get('momentum', 0):.0f}</div>
                            <div class="breakdown-label">모멘텀</div>
                        </div>
                    </div>
                    
                    <div class="reasons">
'''
        for reason in signal.reason[:4]:
            html += f'                        <span class="reason-tag">{reason}</span>\n'
        
        html += '''                    </div>
                </div>
'''
    
    html += f'''
            </div>
        </div>
        
        <footer>
            <p>2604 Scanner Report | Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>KAGGRESSIVE + IVF + KRX Hybrid + D+ Integration</p>
        </footer>
    </div>
</body>
</html>
'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 리포트 생성: {output_path}")


def main():
    import sys
    
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y%m%d')
    min_score = float(sys.argv[2]) if len(sys.argv) > 2 else 75.0
    
    if len(date_str) == 8:
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        date_formatted = date_str
    
    # 스캔 실행
    from v2.strategies.scanner_2604 import run_2604_scan
    signals = run_2604_scan(date_str, min_score)
    
    if not signals:
        print("❌ 신호 없음")
        return
    
    # JSON 저장
    json_path = f'docs/2604_report_{date_str}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([s.to_dict() for s in signals], f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 저장: {json_path}")
    
    # HTML 리포트 생성
    html_path = f'docs/2604_report_{date_str}.html'
    generate_html_report(signals, {}, date_str, html_path)
    
    # 백테스트 (최근 30일)
    print("\n📊 백테스트 실행 중...")
    end_date = datetime.strptime(date_formatted, '%Y-%m-%d')
    start_date = end_date - timedelta(days=30)
    
    # 샘플 백테스트 (실제 실행 시 시간 단축을 위해 일부만)
    print("   (백테스트는 리포트 생성 후 별도 실행 권장)")
    
    print(f"\n🔗 파일 위치:")
    print(f"   - HTML: {html_path}")
    print(f"   - JSON: {json_path}")


if __name__ == '__main__':
    main()
