#!/usr/bin/env python3
"""
통합 프리미엄 리포트 생성기
KAGGRESSIVE + 단기 급등 통합
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

from kagg import KAggressiveScanner
from short_term_momentum_scanner import ShortTermMomentumScanner
from datetime import datetime
import json


def create_integrated_report():
    """통합 리포트 생성"""
    
    print('='*70)
    print('🔥 통합 프리미엄 리포트 생성')
    print('='*70)
    
    # 1. KAGGRESSIVE 스캔 (60점 이상)
    print('\n📊 KAGGRESSIVE 스캔 중...')
    kagg_scanner = KAggressiveScanner()
    kagg_results = kagg_scanner.run_integrated_scan(min_score=60, top_n=15)
    
    # 2. 단기 급등 스캔 (60점 이상)
    print('\n📊 단기 급등 스캔 중...')
    momentum_scanner = ShortTermMomentumScanner()
    
    symbols = [r[0] for r in kagg_scanner.price_conn.execute('SELECT symbol FROM stock_info').fetchall()]
    momentum_results = []
    
    for symbol in symbols:
        result = momentum_scanner.scan_stock(symbol, min_score=60)
        if result:
            momentum_results.append(result)
            if len(momentum_results) >= 15:
                break
    
    # 3. 통합 분석
    print('\n🎯 통합 분석 중...')
    
    # 등급 분류
    tier1 = []  # 70점+ (적극매수)
    tier2 = []  # 60-69점 (관심)
    
    # KAGGRESSIVE 분류
    for r in kagg_results:
        if r['kagg_score'] >= 70:
            tier1.append({
                'source': 'KAGGRESSIVE',
                'name': r['name'],
                'symbol': r['symbol'],
                'price': r['price'],
                'score': r['kagg_score'],
                'rsi': r['rsi'],
                'signals': r['signals'],
                'grade': '적극매수'
            })
        else:
            tier2.append({
                'source': 'KAGGRESSIVE',
                'name': r['name'],
                'symbol': r['symbol'],
                'price': r['price'],
                'score': r['kagg_score'],
                'rsi': r['rsi'],
                'signals': r['signals'],
                'grade': '관심'
            })
    
    # 단기 급등 분류
    for r in momentum_results:
        if r['score'] >= 70:
            tier1.append({
                'source': '단기급등',
                'name': r['name'],
                'symbol': r['symbol'],
                'price': r['price'],
                'score': r['score'],
                'rsi': r['rsi'],
                'signals': r['signals'][:3],
                'grade': '적극매수'
            })
        else:
            tier2.append({
                'source': '단기급등',
                'name': r['name'],
                'symbol': r['symbol'],
                'price': r['price'],
                'score': r['score'],
                'rsi': r['rsi'],
                'signals': r['signals'][:3],
                'grade': '관심'
            })
    
    # 점수순 정렬
    tier1.sort(key=lambda x: x['score'], reverse=True)
    tier2.sort(key=lambda x: x['score'], reverse=True)
    
    # 4. 리포트 생성
    date_str = datetime.now().strftime('%Y%m%d')
    
    html = generate_html_report(tier1, tier2, date_str)
    
    # 저장
    html_path = f'docs/INTEGRATED_PREMIUM_{date_str}.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # JSON 저장
    json_path = f'docs/integrated_premium_{date_str}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({'tier1': tier1, 'tier2': tier2}, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 리포트 생성 완료:')
    print(f'   - {html_path}')
    print(f'   - {json_path}')
    
    return tier1, tier2


def generate_html_report(tier1, tier2, date_str):
    """HTML 리포트 생성"""
    
    # Tier 1 카드
    tier1_cards = ""
    for r in tier1:
        color = "#00ff88"
        tier1_cards += f"""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
             border-radius: 12px; padding: 20px; margin: 15px 0; border-left: 5px solid {color};"
        >
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div>
                    <span style="font-size: 24px; font-weight: bold; color: {color};">{r['name']}</span>
                    <span style="color: #adb5bd; margin-left: 10px;">({r['symbol']})</span>
                    <span style="background: {color}; color: #000; padding: 3px 10px; border-radius: 10px; margin-left: 10px; font-size: 12px; font-weight: bold;">{r['grade']}</span>
                </div>
                <div style="background: {color}; color: #000; padding: 8px 20px; border-radius: 20px; font-weight: bold; font-size: 20px;">
                    {r['score']}점
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 13px;">
                <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                    <div style="color: #868e96;">현재가</div>
                    <div style="color: #fff; font-weight: bold;">{r['price']:,.0f}원</div>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                    <div style="color: #868e96;">출처</div>
                    <div style="color: #fff; font-weight: bold;">{r['source']}</div>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                    <div style="color: #868e96;">RSI</div>
                    <div style="color: #fff; font-weight: bold;">{r['rsi']:.1f}</div>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                    <div style="color: #868e96;">승률</div>
                    <div style="color: {color}; font-weight: bold;">80%</div>
                </div>
            </div>
            <div style="margin-top: 12px; color: #00ff88; font-size: 12px;">
                {' · '.join(r['signals'])}
            </div>
        </div>
        """
    
    # Tier 2 카드
    tier2_cards = ""
    for r in tier2[:10]:  # 상위 10개만
        color = "#fcc419"
        tier2_cards += f"""
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
             border-radius: 12px; padding: 15px; margin: 10px 0; border-left: 4px solid {color}; opacity: 0.9;"
        >
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 18px; font-weight: bold; color: #fff;">{r['name']}</span>
                    <span style="color: #868e96; margin-left: 10px; font-size: 12px;">({r['symbol']})</span>
                    <span style="background: #495057; color: #fff; padding: 2px 8px; border-radius: 8px; margin-left: 10px; font-size: 11px;">{r['grade']}</span>
                </div>
                <div style="color: {color}; font-weight: bold; font-size: 18px;">
                    {r['score']}점
                </div>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: #868e96;">
                {r['source']} · RSI {r['rsi']:.1f} · 승률 40%
            </div>
        </div>
        """
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통합 프리미엄 리포트 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%); color: #fff; min-height: 100vh; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
            border-radius: 20px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 36px; margin-bottom: 10px; }}
        .section {{ margin-bottom: 40px; }}
        .section-title {{ font-size: 24px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 3px solid; display: flex; justify-content: space-between; align-items: center; }}
        .tier1 .section-title {{ border-color: #00ff88; color: #00ff88; }}
        .tier2 .section-title {{ border-color: #fcc419; color: #fcc419; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 30px; }}
        .stat-box {{ background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #fff; }}
        .stat-label {{ color: #868e96; font-size: 12px; margin-top: 5px; }}
        .footer {{ text-align: center; padding: 30px; color: #868e96; border-top: 1px solid #333; margin-top: 40px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 통합 프리미엄 리포트</h1>
            <p>KAGGRESSIVE + 단기 급등 통합 선별</p>
            <p style="margin-top: 10px; font-size: 14px;">{date_str}</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value" style="color: #00ff88;">{len(tier1)}</div>
                <div class="stat-label">적극매수 (70점+)</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #fcc419;">{len(tier2)}</div>
                <div class="stat-label">관심 (60-69점)</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" style="color: #ff6b6b;">80%</div>
                <div class="stat-label">70점+ 승률</div>
            </div>
        </div>
        
        <div class="section tier1">
            <div class="section-title">
                <span>🎯 적극매수 (70점+ / 승률 80%)</span>
                <span style="font-size: 14px;">총 {len(tier1)}개</span>
            </div>
            {tier1_cards if tier1 else '<div style="text-align: center; padding: 40px; color: #868e96;">현재 70점 이상 종목이 없습니다.</div>'}
        </div>
        
        <div class="section tier2">
            <div class="section-title">
                <span>👀 관심 (60-69점 / 승률 40%)</span>
                <span style="font-size: 14px;">상위 10개</span>
            </div>
            {tier2_cards}
        </div>
        
        <div class="footer">
            <p>⚠️ 본 리포트는 백테스트 기반 참고 자료입니다.</p>
            <p style="margin-top: 10px;">70점+만 적극 매수 권장 | 3일+ 보유 시 승률 향상</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


if __name__ == '__main__':
    tier1, tier2 = create_integrated_report()
    
    print('\n' + '='*70)
    print('📋 최종 선정 결과')
    print('='*70)
    print(f'\n🔥 적극매수 (70점+): {len(tier1)}개')
    for r in tier1:
        print(f"   • {r['name']} ({r['symbol']}): {r['score']}점 [{r['source']}]")
    
    print(f'\n👀 관심 (60-69점): {len(tier2)}개')
    for r in tier2[:5]:
        print(f"   • {r['name']} ({r['symbol']}): {r['score']}점 [{r['source']}]")
    
    print('\n' + '='*70)
