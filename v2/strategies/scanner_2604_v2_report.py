#!/usr/bin/env python3
"""
2604 V2 스캐너 리포트 생성기
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

import json
import pandas as pd
from datetime import datetime
from v2.strategies.scanner_2604_v2 import Scanner2604V2
from v2.core.data_manager import DataManager


def generate_html_report(signals, date, output_file):
    """HTML 리포트 생성"""
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2604 스캐너 리포트 - {date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; background: linear-gradient(45deg, #ff6b6b, #feca57); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header p {{ color: #888; font-size: 1.1rem; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-card h3 {{ color: #888; font-size: 0.9rem; margin-bottom: 10px; text-transform: uppercase; }}
        .stat-card .value {{ font-size: 2rem; font-weight: bold; color: #feca57; }}
        .signal-list {{ display: flex; flex-direction: column; gap: 15px; }}
        .signal-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .signal-card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
        .signal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .signal-title {{ display: flex; align-items: center; gap: 15px; }}
        .rank {{
            width: 40px; height: 40px;
            border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 1.2rem;
        }}
        .rank.gold {{ background: linear-gradient(135deg, #ffd700, #ffed4e); color: #333; }}
        .rank.silver {{ background: linear-gradient(135deg, #c0c0c0, #e8e8e8); color: #333; }}
        .rank.bronze {{ background: linear-gradient(135deg, #cd7f32, #daa520); color: #fff; }}
        .rank.normal {{ background: rgba(255,255,255,0.2); color: #fff; }}
        .stock-name {{ font-size: 1.3rem; font-weight: bold; }}
        .stock-code {{ color: #888; font-size: 0.9rem; }}
        .score {{
            background: linear-gradient(135deg, #ff6b6b, #feca57);
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.1rem;
        }}
        .signal-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}
        .detail-item {{ text-align: center; }}
        .detail-item .label {{ color: #888; font-size: 0.8rem; margin-bottom: 5px; }}
        .detail-item .value {{ font-size: 1.1rem; font-weight: bold; }}
        .reasons {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .reason-tag {{
            background: rgba(255,255,255,0.1);
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
            color: #feca57;
        }}
        .footer {{
            text-align: center;
            padding: 30px 0;
            margin-top: 30px;
            border-top: 2px solid rgba(255,255,255,0.1);
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 2604 통합 스캐너</h1>
            <p>개선된 하이브리드 전략 | {date}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>총 신호</h3>
                <div class="value">{len(signals)}</div>
            </div>
            <div class="stat-card">
                <h3>평균 점수</h3>
                <div class="value">{sum(s.score for s in signals) / len(signals):.1f}</div>
            </div>
            <div class="stat-card">
                <h3>최고 점수</h3>
                <div class="value">{max((s.score for s in signals), default=0):.0f}</div>
            </div>
            <div class="stat-card">
                <h3>80점 이상</h3>
                <div class="value">{sum(1 for s in signals if s.score >= 80)}</div>
            </div>
        </div>
        
        <div class="signal-list">
"""
    
    # 신호 카드 추가
    for i, signal in enumerate(signals, 1):
        meta = signal.metadata
        scores = meta.get('indicators', {}).get('scores', {})
        
        # 순위 스타일
        if i == 1:
            rank_class = "gold"
        elif i == 2:
            rank_class = "silver"
        elif i == 3:
            rank_class = "bronze"
        else:
            rank_class = "normal"
        
        html += f"""
            <div class="signal-card">
                <div class="signal-header">
                    <div class="signal-title">
                        <div class="rank {rank_class}">{i}</div>
                        <div>
                            <div class="stock-name"><a href="https://finance.naver.com/item/main.nhn?code={signal.code}" target="_blank" style="color: #fff; text-decoration: none;">{signal.name} ↗</a></div>
                            <div class="stock-code">{signal.code}</div>
                        </div>
                    </div>
                    <div class="score">{signal.score:.0f}점</div>
                </div>
                <div class="signal-details">
                    <div class="detail-item">
                        <div class="label">현재가</div>
                        <div class="value">{meta.get('price', 0):,.0f}원</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">거래량</div>
                        <div class="value">{scores.get('volume', 0):.0f}점</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">기술적</div>
                        <div class="value">{scores.get('technical', 0):.0f}점</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">피볼나치</div>
                        <div class="value">{scores.get('fibonacci', 0):.0f}점</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">시장맥락</div>
                        <div class="value">{scores.get('market', 0):.0f}점</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">모멘텀</div>
                        <div class="value">{scores.get('momentum', 0):.0f}점</div>
                    </div>
                </div>
                <div class="reasons">
"""
        for reason in signal.reason[:5]:
            html += f'                    <span class="reason-tag">{reason}</span>\n'
        
        html += """                </div>
            </div>
"""
    
    html += f"""        </div>
        
        <div class="footer">
            <p>2604 Ultimate Scanner | Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin-top: 10px; font-size: 0.85rem;">※ 본 리포트는 투자 참고용이며, 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.</p>
        </div>
    </div>
</body>
</html>"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML 리포트 생성: {output_file}")


def main():
    """메인 실행"""
    print("=" * 70)
    print("🔥 2604 V2 스캐너 실행 및 리포트 생성")
    print("=" * 70)
    
    # 날짜 설정 (어제)
    date = '2026-04-07'
    date_display = '20250407'
    
    print(f"\n📅 스캔 날짜: {date}")
    
    # 스캐너 실행
    scanner = Scanner2604V2(use_krx=True)
    dm = DataManager()
    
    signals = scanner.run(dm, date)
    signals = sorted(signals, key=lambda x: x.score, reverse=True)
    
    print(f"\n📊 결과: {len(signals)}개 신호 발견")
    
    if signals:
        print(f"   평균 점수: {sum(s.score for s in signals)/len(signals):.1f}")
        print(f"   최고 점수: {max(s.score for s in signals):.0f}")
        
        # JSON 저장
        json_file = f"reports/2604_v2_report_{date_display}.json"
        json_data = [{
            'code': s.code,
            'name': s.name,
            'date': s.date,
            'score': s.score,
            'price': s.metadata.get('price', 0),
            'reasons': s.reason,
            'scores': s.metadata.get('indicators', {}).get('scores', {})
        } for s in signals]
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 저장: {json_file}")
        
        # HTML 리포트 생성
        html_file = f"docs/2604_v2_report_{date_display}.html"
        generate_html_report(signals, date, html_file)
        
        print("\n" + "=" * 70)
        print("✅ 2604 V2 스캐너 완료!")
        print(f"   - JSON: {json_file}")
        print(f"   - HTML: {html_file}")
        print("=" * 70)
    else:
        print("\n⚠️  신호가 발견되지 않았습니다.")


if __name__ == "__main__":
    main()
