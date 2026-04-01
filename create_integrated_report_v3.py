#!/usr/bin/env python3
"""
통합 프리미엄 리포트 생성기 v3 (목표가/손절가 포함)
KAGGRESSIVE + 단기 급등 + 심층분석 + 리스크 관리
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/strg')

from kagg import KAggressiveScanner
from short_term_momentum_scanner import ShortTermMomentumScanner
from stock_deep_analyzer import StockDeepAnalyzer
from risk_calculator import RiskCalculator
from datetime import datetime
import json


def create_integrated_report_v3():
    """통합 리포트 생성 (목표가/손절가 포함)"""
    
    print('='*70)
    print('🔥 통합 프리미엄 리포트 v3 + 리스크 관리')
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
    
    tier1 = []
    tier2 = []
    
    for r in kagg_results:
        item = {
            'source': 'KAGGRESSIVE',
            'name': r['name'],
            'symbol': r['symbol'],
            'price': r['price'],
            'score': r['kagg_score'],
            'rsi': r['rsi'],
            'signals': r['signals'],
            'grade': '적극매수' if r['kagg_score'] >= 70 else '관심'
        }
        if r['kagg_score'] >= 70:
            tier1.append(item)
        else:
            tier2.append(item)
    
    for r in momentum_results:
        item = {
            'source': '단기급등',
            'name': r['name'],
            'symbol': r['symbol'],
            'price': r['price'],
            'score': r['score'],
            'rsi': r['rsi'],
            'signals': r['signals'][:3],
            'grade': '적극매수' if r['score'] >= 70 else '관심'
        }
        if r['score'] >= 70:
            tier1.append(item)
        else:
            tier2.append(item)
    
    tier1.sort(key=lambda x: x['score'], reverse=True)
    tier2.sort(key=lambda x: x['score'], reverse=True)
    
    # 4. 고득점 종목 심층 분석
    print('\n🔍 고득점 종목 심층 분석 중...')
    analyzer = StockDeepAnalyzer()
    deep_analysis = analyzer.analyze_high_score_stocks(tier1)
    analyzer.close()
    
    # 5. 리스크 관리 계산 (목표가/손절가)
    print('\n📈 목표가/손절가 계산 중...')
    risk_data = {}
    for stock in tier1:
        plan = RiskCalculator.get_trading_plan(stock['symbol'], stock['name'], stock['score'])
        if plan:
            risk_data[stock['symbol']] = plan
            print(f"   ✓ {stock['name']}: TP {plan['target']:,.0f}원 / SL {plan['stop_loss']:,.0f}원 (R:R {plan['r_ratio']}:1)")
    
    # 6. 리포트 생성
    date_str = datetime.now().strftime('%Y%m%d')
    html = generate_html_report_v3(tier1, tier2, deep_analysis, risk_data, date_str)
    
    # 저장
    html_path = f'docs/INTEGRATED_PREMIUM_{date_str}.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    json_path = f'docs/integrated_premium_{date_str}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'tier1': tier1,
            'tier2': tier2,
            'deep_analysis': deep_analysis,
            'risk_management': risk_data
        }, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 리포트 생성 완료:')
    print(f'   - {html_path}')
    print(f'   - {json_path}')
    
    return tier1, tier2, deep_analysis, risk_data


def generate_html_report_v3(tier1, tier2, deep_analysis, risk_data, date_str):
    """HTML 리포트 생성 (목표가/손절가 포함)"""
    
    tier1_cards = ""
    for r in tier1:
        color = "#00ff88"
        deep = next((d for d in deep_analysis if d['symbol'] == r['symbol']), None)
        risk = risk_data.get(r['symbol'])
        
        # 리스크 관리 HTML
        risk_html = ""
        if risk:
            # 목표가 옵션
            target_options = ""
            for level in ['conservative', 'moderate', 'aggressive']:
                if level in risk['all_targets']:
                    t = risk['all_targets'][level]
                    is_recommended = risk['target'] == t['target']
                    bg_color = "#00ff88" if is_recommended else "rgba(255,255,255,0.05)"
                    text_color = "#000" if is_recommended else "#fff"
                    badge = " (추천)" if is_recommended else ""
                    target_options += f"""
                    <div style="background: {bg_color}; padding: 8px 12px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 10px; color: {'#333' if is_recommended else '#868e96'};">{level}{badge}</div>
                        <div style="font-weight: bold; color: {text_color};">{t['target']:,.0f}원</div>
                        <div style="font-size: 11px; color: {'#333' if is_recommended else '#adb5bd'};">R:R {t['r_ratio']}:1</div>
                    </div>
                    """
            
            risk_html = f"""
            <div style="margin-top: 15px; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="color: #00ff88; font-size: 13px; margin-bottom: 12px; font-weight: bold;">📊 매매 전략 (피본acci + ATR)</div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                    <div style="background: rgba(255,0,0,0.1); padding: 12px; border-radius: 8px; border-left: 3px solid #ff6b6b;">
                        <div style="font-size: 11px; color: #ff6b6b; margin-bottom: 4px;">🛑 손절가 (ATR×1.5)</div>
                        <div style="font-size: 18px; font-weight: bold; color: #fff;">{risk['stop_loss']:,.0f}원</div>
                        <div style="font-size: 12px; color: #ff6b6b;">{risk['stop_loss_pct']:+.1f}%</div>
                    </div>
                    
                    <div style="background: rgba(0,255,136,0.1); padding: 12px; border-radius: 8px; border-left: 3px solid #00ff88;">
                        <div style="font-size: 11px; color: #00ff88; margin-bottom: 4px;">🎯 목표가 (추천)</div>
                        <div style="font-size: 18px; font-weight: bold; color: #fff;">{risk['target']:,.0f}원</div>
                        <div style="font-size: 12px; color: #00ff88;">+{risk['target_pct']:.1f}% (R:R {risk['r_ratio']}:1)</div>
                    </div>
                </div>
                
                <div style="color: #868e96; font-size: 11px; margin-bottom: 10px;">목표가 옵션:</div>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                    {target_options}
                </div>
            </div>
            """
        
        # 심층분석 HTML
        sentiment_html = ""
        links_html = ""
        if deep:
            sentiment = deep['sentiment']
            mood_color = "#00ff88" if sentiment['overall'] == '긍정' else "#fcc419" if sentiment['overall'] == '중립' else "#ff6b6b"
            
            sentiment_html = f"""
            <div style="margin-top: 15px; padding: 12px; background: rgba(0,255,136,0.05); border-radius: 8px; border: 1px solid rgba(0,255,136,0.2);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="color: #868e96; font-size: 12px;">📊 여론 분석</span>
                    <span style="color: {mood_color}; font-weight: bold; font-size: 14px;">{sentiment['overall']} ({sentiment['score']}/100)</span>
                </div>
                <div style="color: #adb5bd; font-size: 12px; margin-bottom: 8px;">키워드: {', '.join(sentiment['keywords'])}</div>
                <div style="color: #fff; font-size: 12px; line-height: 1.5;">💬 {sentiment['community_mood']}</div>
            </div>
            """
            
            links = deep['links']
            links_html = f"""
            <div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;">
                <a href="{links['main']}" target="_blank" style="background: #1971c2; color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 11px; text-decoration: none;">네이버 종합</a>
                <a href="{links['news']}" target="_blank" style="background: #2f9e44; color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 11px; text-decoration: none;">뉴스</a>
                <a href="{links['community']}" target="_blank" style="background: #e03131; color: #fff; padding: 6px 12px; border-radius: 6px; font-size: 11px; text-decoration: none;">종토방</a>
            </div>
            """
        
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
            {risk_html}
            {sentiment_html}
            {links_html}
        </div>
        """
    
    # Tier 2 카드 (기존과 동일)
    tier2_cards = ""
    for r in tier2[:10]:
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
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통합 프리미엄 리포트 v3 - {date_str}</title>
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
        .legend {{ background: rgba(255,255,255,0.03); padding: 20px; border-radius: 12px; margin-bottom: 30px; font-size: 12px; color: #adb5bd; }}
        .legend-title {{ color: #fff; font-weight: bold; margin-bottom: 10px; }}
        .footer {{ text-align: center; padding: 30px; color: #868e96; border-top: 1px solid #333; margin-top: 40px; font-size: 12px; }}
        a:hover {{ opacity: 0.8; transition: opacity 0.2s; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 통합 프리미엄 리포트 v3</h1>
            <p>KAGGRESSIVE + 단기 급등 + 심층분석 + 리스크관리</p>
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
        
        <div class="legend">
            <div class="legend-title">📊 매매 전략 가이드</div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                <div>
                    <strong style="color: #ff6b6b;">🛑 손절가</strong>: ATR(14) × 1.5 (최대 -10%) <br/>
                    평균 진폭을 활용한 리스크 관리
                </div>
                <div>
                    <strong style="color: #00ff88;">🎯 목표가</strong>: 피본acci 확장 (1.272 / 1.618 / 2.618) <br/>
                    R:R 2:1 이상인 레벨 추천
                </div>
            </div>
        </div>
        
        <div class="section tier1">
            <div class="section-title">
                <span>🎯 적극매수 (70점+ / 승률 80%)</span>
                <span style="font-size: 14px;">총 {len(tier1)}개 + 전략</span>
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
            <p style="margin-top: 10px; color: #495057;">목표가: 피본acci 확장 | 손절가: ATR(14) × 1.5</p>
        </div>
    </div>
</body>
</html>"""
    
    return html


if __name__ == '__main__':
    tier1, tier2, deep, risk = create_integrated_report_v3()
    
    print('\n' + '='*70)
    print('📋 최종 선정 결과 + 매매 전략')
    print('='*70)
    print(f'\n🔥 적극매수 (70점+): {len(tier1)}개')
    for r in tier1:
        if r['symbol'] in risk:
            p = risk[r['symbol']]
            print(f"   • {r['name']} ({r['symbol']}): {r['score']}점")
            print(f"     진입: {p['entry']:,.0f}원 → 목표: {p['target']:,.0f}원 (+{p['target_pct']:.1f}%)")
            print(f"     손절: {p['stop_loss']:,.0f}원 ({p['stop_loss_pct']:+.1f}%) / R:R {p['r_ratio']}:1")
    
    print(f'\n👀 관심 (60-69점): {len(tier2)}개')
    for r in tier2[:5]:
        print(f"   • {r['name']} ({r['symbol']}): {r['score']}점")
    
    print('\n' + '='*70)
