#!/usr/bin/env python3
"""V전략 최종 리포트 생성 (네이버 실시간 데이터)"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from scrapling import Fetcher


class NaverStockScraper:
    def __init__(self):
        self.fetcher = Fetcher()
        self.base_url = 'https://finance.naver.com/item/main.naver?code={}'
    
    def get_stock_info(self, symbol):
        try:
            code = symbol.zfill(6)
            url = self.base_url.format(code)
            page = self.fetcher.get(url)
            
            info = {
                'symbol': symbol,
                'code': code,
                'name': None,
                'current_price': None,
                'change': None,
                'change_percent': None,
                'chart_url': f'https://finance.naver.com/item/fchart.naver?code={code}',
                'detail_url': url,
            }
            
            # 종목명
            try:
                name_elem = page.css('.wrap_company h2 a')
                if name_elem:
                    info['name'] = name_elem[0].text.strip()
                else:
                    name_elem = page.css('.wrap_company h2')
                    if name_elem:
                        info['name'] = name_elem[0].text.strip()
            except:
                pass
            
            # 현재가
            try:
                price_elem = page.css('.no_today .blind')
                if price_elem:
                    price_text = price_elem[0].text.strip().replace(',', '')
                    info['current_price'] = int(price_text)
            except:
                pass
            
            # 등락
            try:
                change_elem = page.css('.no_exday .blind')
                if len(change_elem) >= 2:
                    change = change_elem[0].text.strip().replace(',', '')
                    change_pct = change_elem[1].text.strip().replace('%', '')
                    info['change'] = int(change)
                    info['change_percent'] = float(change_pct)
                    
                    up_elem = page.css('.no_exday .ico_up')
                    down_elem = page.css('.no_exday .ico_down')
                    if up_elem:
                        info['direction'] = 'up'
                    elif down_elem:
                        info['direction'] = 'down'
                        info['change'] = -info['change']
                        info['change_percent'] = -info['change_percent']
            except:
                pass
            
            return info
        except Exception as e:
            return {'symbol': symbol, 'error': str(e)}


def generate_report():
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst)
    today_str = today.strftime('%Y%m%d')
    
    print('='*70)
    print('🎯 V전략 최종 리포트 생성 (네이버 실시간 데이터)')
    print('='*70)
    
    # V전략 결과 로드
    with open('reports/v_series/v_series_scan_20260324.json', 'r') as f:
        data = json.load(f)
        v_results = data['top_stocks']
    
    print(f'📊 V전략 결과: {len(v_results)}개 종목')
    print(f'🔍 네이버 금융 스크래핑 시작 (TOP 20)')
    print('-'*70)
    
    scraper = NaverStockScraper()
    enriched = []
    
    for i, result in enumerate(v_results[:20], 1):
        symbol = result['symbol']
        print(f'[{i}/20] {symbol} 스크래핑 중...', end=' ')
        
        naver_data = scraper.get_stock_info(symbol)
        
        if 'error' not in naver_data:
            name = naver_data.get('name', 'N/A')
            print(f'✅ {name}')
            
            enriched_data = {**result, 'naver': naver_data}
            
            # 가격 차이 계산
            if naver_data.get('current_price') and result.get('entry_price'):
                price_diff = naver_data['current_price'] - result['entry_price']
                price_diff_pct = (price_diff / result['entry_price']) * 100
                enriched_data['price_diff'] = price_diff
                enriched_data['price_diff_pct'] = price_diff_pct
            
            enriched.append(enriched_data)
        else:
            print(f'❌ 오류')
            enriched.append({**result, 'naver': naver_data})
    
    print(f'\n✅ 스크래핑 완료: {len([e for e in enriched if "error" not in e.get("naver", {})])}개 성공')
    
    # HTML 리포트 생성
    html_lines = [
        '<!DOCTYPE html>',
        '<html lang="ko">',
        '<head>',
        '    <meta charset="UTF-8">',
        '    <title>V전략 최종 리포트 - 2026.03.24</title>',
        '    <style>',
        '        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0d1117; color: #c9d1d9; max-width: 1200px; margin: 0 auto; padding: 20px; }',
        '        h1 { color: #58a6ff; border-bottom: 2px solid #30363d; padding-bottom: 10px; }',
        '        .stock-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin: 15px 0; }',
        '        .stock-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }',
        '        .stock-rank { font-size: 1.5em; font-weight: bold; color: #f0883e; }',
        '        .stock-name { font-size: 1.3em; font-weight: bold; }',
        '        .stock-code { color: #6e7681; font-size: 0.9em; }',
        '        .price-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 15px 0; }',
        '        .price-box { text-align: center; padding: 10px; background: #0d1117; border-radius: 8px; }',
        '        .price-label { color: #8b949e; font-size: 0.8em; }',
        '        .price-value { font-size: 1.2em; font-weight: bold; }',
        '        .price-up { color: #238636; }',
        '        .price-down { color: #da3633; }',
        '        .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 15px; padding-top: 15px; border-top: 1px solid #30363d; }',
        '        .metric { text-align: center; }',
        '        .metric-value { font-weight: bold; color: #58a6ff; }',
        '        .metric-label { font-size: 0.75em; color: #6e7681; }',
        '        .chart-link { display: inline-block; margin-top: 10px; padding: 8px 16px; background: #21262d; color: #c9d1d9; text-decoration: none; border-radius: 6px; }',
        '        .chart-link:hover { background: #58a6ff; color: white; }',
        '        .summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }',
        '        .summary-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; text-align: center; }',
        '        .summary-number { font-size: 2.5em; font-weight: bold; color: #58a6ff; }',
        '        .summary-label { color: #8b949e; margin-top: 5px; }',
        '        .home-link { display: inline-block; margin-bottom: 20px; padding: 10px 20px; background: #21262d; color: #c9d1d9; text-decoration: none; border-radius: 8px; }',
        '    </style>',
        '</head>',
        '<body>',
        '    <a href="./" class="home-link">← 홈으로</a>',
        f'    <h1>🎯 V전략 최종 리포트 (2026.03.24 종가 기준)</h1>',
        f'    <p style="color: #8b949e;">생성 시간: {today.strftime("%Y-%m-%d %H:%M")} KST | 데이터: 네이버 금융 실시간</p>',
        '',
        '    <div class="summary">',
        f'        <div class="summary-card"><div class="summary-number">{len(v_results)}</div><div class="summary-label">V전략 선정</div></div>',
        f'        <div class="summary-card"><div class="summary-number">{len([e for e in enriched if e.get("naver", {}).get("current_price")])}</div><div class="summary-label">실시간 가격</div></div>',
        f'        <div class="summary-card"><div class="summary-number">{len([e for e in enriched if e.get("naver", {}).get("name")])}</div><div class="summary-label">종목명 확인</div></div>',
        f'        <div class="summary-card"><div class="summary-number">1:{sum([e.get("rr_ratio", 0) for e in enriched[:5]])/5:.1f}</div><div class="summary-label">평균 손익비</div></div>',
        '    </div>',
    ]
    
    # 종목 카드 생성
    for i, stock in enumerate(enriched[:15], 1):
        naver = stock.get('naver', {})
        name = naver.get('name') or stock.get('name') or stock['symbol']
        code = stock['symbol']
        
        current = naver.get('current_price')
        change = naver.get('change')
        change_pct = naver.get('change_percent')
        
        price_class = 'price-up' if change and change > 0 else 'price-down' if change and change < 0 else ''
        change_sign = '+' if change and change > 0 else ''
        
        entry = stock.get('entry_price', 0)
        target = stock.get('target_price', 0)
        stop = stock.get('stop_loss', 0)
        rr = stock.get('rr_ratio', 0)
        value_score = stock.get('value_score', 0)
        fib = stock.get('fib_level', '-')
        
        price_diff = stock.get('price_diff_pct')
        diff_text = f'{price_diff:+.1f}%' if price_diff else '-'
        diff_class = 'price-up' if price_diff and price_diff > 0 else 'price-down' if price_diff and price_diff < 0 else ''
        
        current_price_str = f"{current:,}" if current else "N/A"
        change_str = f'{change_sign}{change:,}' if change else ''
        change_pct_str = f'{change_sign}{change_pct:.2f}%' if change_pct else ''
        
        html_lines.extend([
            '    <div class="stock-card">',
            '        <div class="stock-header">',
            f'            <span class="stock-rank">#{i}</span>',
            '            <div>',
            f'                <div class="stock-name">{name}</div>',
            f'                <div class="stock-code">{code}</div>',
            '            </div>',
            '        </div>',
            '',
            '        <div class="price-grid">',
            '            <div class="price-box">',
            '                <div class="price-label">실시간 현재가</div>',
            f'                <div class="price-value {price_class}">{current_price_str}</div>',
        ])
        
        if change:
            html_lines.append(f'                <div style="font-size:0.85em;" class="{price_class}">{change_str} ({change_pct_str})</div>')
        
        html_lines.extend([
            '            </div>',
            '            <div class="price-box">',
            '                <div class="price-label">V전략 진입가 (3/24 종가)</div>',
            f'                <div class="price-value">{entry:,.0f}</div>',
            f'                <div style="font-size:0.85em;" class="{diff_class}">{diff_text}</div>',
            '            </div>',
            '            <div class="price-box">',
            '                <div class="price-label">목표가</div>',
            f'                <div class="price-value price-up">{target:,.0f}</div>',
            '            </div>',
            '            <div class="price-box">',
            '                <div class="price-label">손절가</div>',
            f'                <div class="price-value price-down">{stop:,.0f}</div>',
            '            </div>',
            '        </div>',
            '',
            '        <div class="metrics">',
            f'            <div class="metric"><div class="metric-value">1:{rr:.1f}</div><div class="metric-label">손익비</div></div>',
            f'            <div class="metric"><div class="metric-value">{value_score:.0f}</div><div class="metric-label">가치점수</div></div>',
            f'            <div class="metric"><div class="metric-value">{fib.replace("fib_", "")}</div><div class="metric-label">Fib</div></div>',
            '        </div>',
            '',
            '        <div style="text-align: center; margin-top: 10px;">',
            f'            <a href="{naver.get("chart_url", "#")}" class="chart-link" target="_blank">📊 차트 보기</a>',
            f'            <a href="{naver.get("detail_url", "#")}" class="chart-link" target="_blank" style="margin-left: 5px;">📋 상세 정보</a>',
            '        </div>',
            '    </div>',
        ])
    
    # 푸터
    html_lines.extend([
        '    <div style="text-align: center; margin-top: 40px; padding: 20px; color: #6e7681; border-top: 1px solid #30363d;">',
        '        <p>V전략: 가치투자 + Fibonacci 되돌림 + ATR 리스크관리</p>',
        '        <p>데이터 출처: 네이버 금융 | 투자 참고 자료</p>',
        '    </div>',
        '</body>',
        '</html>',
    ])
    
    # 저장
    output_path = Path(f'docs/V_Strategy_Final_{today_str}.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_lines))
    
    print(f'\n✅ 최종 리포트 생성 완료!')
    print(f'   📄 {output_path}')
    
    # TOP 5 요약
    print(f'\n📊 TOP 5 요약:')
    for i, e in enumerate(enriched[:5], 1):
        name = e.get('naver', {}).get('name') or e['symbol']
        current = e.get('naver', {}).get('current_price')
        if current:
            print(f'   {i}. {name}: 현재가 {current:,}')
        else:
            print(f'   {i}. {name}: 가격 확인 불가')
    
    print(f'\n🔗 URL: https://lubanana.github.io/kstock-dashboard/V_Strategy_Final_{today_str}.html')


if __name__ == '__main__':
    generate_report()
