#!/usr/bin/env python3
"""
V전략 + 네이버 증권 통합 리포트
================================
V전략 스캔 결과 + 네이버 Finance 실시간 데이터 통합
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from scrapling import Fetcher

sys.path.insert(0, '/root/.openclaw/workspace/strg')


class NaverStockScraper:
    """네이버 금융 주식 정보 스크래퍼"""
    
    def __init__(self):
        self.fetcher = Fetcher()
        self.base_url = "https://finance.naver.com/item/main.naver?code={}"
    
    def get_stock_info(self, symbol):
        """종목 상세 정보 스크래핑"""
        try:
            # 6자리 코드로 변환
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
                'volume': None,
                'market_cap': None,
                'per': None,
                'pbr': None,
                'dividend_yield': None,
                '52w_high': None,
                '52w_low': None,
                'chart_url': f"https://finance.naver.com/item/fchart.naver?code={code}",
                'detail_url': url,
                'scraped_at': datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 종목명
            try:
                name_elem = page.css('.wrap_company h2 a')
                if name_elem:
                    info['name'] = name_elem[0].text.strip()
                else:
                    # 백업 선택자
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
                    
                    # 상승/하띓 판단
                    up_elem = page.css('.no_exday .ico_up')
                    down_elem = page.css('.no_exday .ico_down')
                    if up_elem:
                        info['direction'] = 'up'
                    elif down_elem:
                        info['direction'] = 'down'
                        info['change'] = -info['change']
                        info['change_percent'] = -info['change_percent']
                    else:
                        info['direction'] = 'neutral'
            except:
                pass
            
            # 거래대금/시가총액 등 테이블 데이터
            try:
                table_data = {}
                rows = page.css('#tab_con1 .first tr')
                for row in rows:
                    th_elems = row.css('th')
                    td_elems = row.css('td')
                    for th, td in zip(th_elems, td_elems):
                        key = th.text.strip()
                        val = td.text.strip()
                        table_data[key] = val
                
                # PER
                if 'PER' in table_data:
                    try:
                        info['per'] = float(table_data['PER'].replace('배', '').replace(',', ''))
                    except:
                        pass
                
                # PBR
                if 'PBR' in table_data:
                    try:
                        info['pbr'] = float(table_data['PBR'].replace('배', '').replace(',', ''))
                    except:
                        pass
                
                # 시가총액
                if '시가총액' in table_data:
                    cap_text = table_data['시가총액'].replace('억원', '').replace(',', '')
                    try:
                        info['market_cap'] = int(cap_text)
                    except:
                        pass
                
                # 52주 최고/최저
                if '52주 최고' in table_data:
                    high_text = table_data['52주 최고'].replace(',', '').split()[0]
                    try:
                        info['52w_high'] = int(high_text)
                    except:
                        pass
                
                if '52주 최저' in table_data:
                    low_text = table_data['52주 최저'].replace(',', '').split()[0]
                    try:
                        info['52w_low'] = int(low_text)
                    except:
                        pass
                
                # 배당수익률
                if '배당수익률' in table_data:
                    div_text = table_data['배당수익률'].replace('%', '')
                    try:
                        info['dividend_yield'] = float(div_text)
                    except:
                        pass
                        
            except Exception as e:
                print(f"  테이블 파싱 오류: {e}")
            
            # 거래대금
            try:
                volume_elem = page.css('#tab_con1 span.sptxt.sp_txt6 + em')
                if volume_elem:
                    vol_text = volume_elem[0].text.strip().replace(',', '')
                    info['volume'] = int(vol_text)
            except:
                pass
            
            return info
            
        except Exception as e:
            print(f"❌ {symbol} 스크래핑 오류: {e}")
            return {'symbol': symbol, 'error': str(e)}


class VStrategyFinalReport:
    """V전략 최종 리포트 생성기"""
    
    def __init__(self):
        self.kst = timezone(timedelta(hours=9))
        self.today = datetime.now(self.kst)
        self.today_str = self.today.strftime('%Y%m%d')
        self.scraper = NaverStockScraper()
    
    def load_v_results(self):
        """V전략 스캔 결과 로드"""
        result_file = Path(f'/root/.openclaw/workspace/strg/reports/v_series/v_series_scan_20260320.json')
        
        # 최신 파일 찾기
        v_series_dir = Path('/root/.openclaw/workspace/strg/reports/v_series')
        if v_series_dir.exists():
            json_files = sorted(v_series_dir.glob('v_series_scan_*.json'), reverse=True)
            if json_files:
                result_file = json_files[0]
        
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # top_stocks 리스트 추출
        results = data.get('top_stocks', []) if isinstance(data, dict) else data
        
        print(f"📊 V전략 결과 로드: {len(results)}개 종목 ({result_file.name})")
        return results
    
    def scrape_top_stocks(self, v_results, top_n=20):
        """상위 종목 네이버 데이터 스크래핑"""
        print(f"\n🔍 네이버 금융 스크래핑 시작 (상위 {top_n}개)")
        print("=" * 60)
        
        enriched = []
        for i, result in enumerate(v_results[:top_n], 1):
            symbol = result['symbol']
            print(f"[{i}/{top_n}] {symbol} 스크래핑 중...", end=' ')
            
            naver_data = self.scraper.get_stock_info(symbol)
            
            if 'error' not in naver_data:
                print(f"✅ {naver_data.get('name', 'N/A')}")
                
                # 데이터 병합
                enriched_data = {**result, 'naver': naver_data}
                
                # 가격 차이 계산 (V전략 예상가 vs 실제 현재가)
                if naver_data.get('current_price') and result.get('entry_price'):
                    price_diff = naver_data['current_price'] - result['entry_price']
                    price_diff_pct = (price_diff / result['entry_price']) * 100
                    enriched_data['price_diff'] = price_diff
                    enriched_data['price_diff_pct'] = price_diff_pct
                
                enriched.append(enriched_data)
            else:
                print(f"❌ 오류")
                enriched.append({**result, 'naver': naver_data})
        
        return enriched
    
    def generate_html_report(self, enriched_data):
        """HTML 최종 리포트 생성"""
        
        # 상위 15개만 리포트에 포함
        display_data = enriched_data[:15]
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V전략 최종 리포트 - {self.today.strftime('%Y.%m.%d')}</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --text-color: #c9d1d9;
            --heading-color: #58a6ff;
            --up-color: #238636;
            --down-color: #da3633;
            --border-color: #30363d;
            --card-bg: #161b22;
            --highlight: #f0883e;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            padding: 20px;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid var(--border-color);
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: var(--heading-color);
            font-size: 2.2em;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: #8b949e;
            font-size: 1.1em;
        }}
        
        .timestamp {{
            color: #6e7681;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .summary-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        
        .summary-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: var(--heading-color);
        }}
        
        .summary-card .label {{
            color: #8b949e;
            margin-top: 5px;
        }}
        
        .stock-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }}
        
        .stock-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.2s, border-color 0.2s;
        }}
        
        .stock-card:hover {{
            transform: translateY(-2px);
            border-color: var(--heading-color);
        }}
        
        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .stock-rank {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--highlight);
        }}
        
        .stock-info {{
            text-align: right;
        }}
        
        .stock-name {{
            font-size: 1.2em;
            font-weight: bold;
            color: var(--text-color);
        }}
        
        .stock-code {{
            color: #6e7681;
            font-size: 0.9em;
        }}
        
        .price-section {{
            display: flex;
            justify-content: space-between;
            margin: 15px 0;
        }}
        
        .price-box {{
            text-align: center;
        }}
        
        .price-label {{
            color: #8b949e;
            font-size: 0.8em;
        }}
        
        .price-value {{
            font-size: 1.3em;
            font-weight: bold;
        }}
        
        .price-up {{ color: var(--up-color); }}
        .price-down {{ color: var(--down-color); }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid var(--border-color);
        }}
        
        .metric {{
            text-align: center;
        }}
        
        .metric-value {{
            font-weight: bold;
            color: var(--heading-color);
        }}
        
        .metric-label {{
            font-size: 0.75em;
            color: #6e7681;
        }}
        
        .chart-link {{
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: var(--border-color);
            color: var(--text-color);
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.9em;
        }}
        
        .chart-link:hover {{
            background: var(--heading-color);
            color: white;
        }}
        
        .home-link {{
            display: inline-block;
            margin-bottom: 20px;
            padding: 10px 20px;
            background: var(--border-color);
            color: var(--text-color);
            text-decoration: none;
            border-radius: 8px;
        }}
        
        .strategy-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75em;
            background: var(--border-color);
            color: #8b949e;
        }}
        
        footer {{
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: #6e7681;
            border-top: 1px solid var(--border-color);
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="./" class="home-link">← 홈으로</a>
        
        <header>
            <h1>🎯 V전략 최종 리포트</h1>
            <p class="subtitle">Value + Fibonacci + ATR 전략 기반 선정 종목</p>
            <p class="timestamp">생성 시간: {self.today.strftime('%Y년 %m월 %d일 %H:%M')} KST | 데이터: 네이버 금융</p>
        </header>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number">{len(enriched_data)}</div>
                <div class="label">V전략 선정 종목</div>
            </div>
            <div class="summary-card">
                <div class="number">{len([s for s in enriched_data[:15] if s.get('naver', {}).get('current_price')])}</div>
                <div class="label">실시간 가격 확보</div>
            </div>
            <div class="summary-card">
                <div class="number">{len([s for s in enriched_data[:15] if s.get('naver', {}).get('name')])}</div>
                <div class="label">종목명 확인</div>
            </div>
            <div class="summary-card">
                <div class="number">1:{sum([s.get('rr_ratio', 0) for s in enriched_data[:5]])/5:.1f}</div>
                <div class="label">평균 손익비 (TOP5)</div>
            </div>
        </div>
        
        <h2 style="color: var(--heading-color); margin-bottom: 20px;">🏆 TOP 선정 종목</h2>
        
        <div class="stock-grid">
"""
        
        # 종목 카드 생성
        for i, stock in enumerate(display_data, 1):
            naver = stock.get('naver', {})
            name = naver.get('name') or stock.get('name') or stock['symbol']
            code = stock['symbol']
            
            # 가격 정보
            current = naver.get('current_price')
            change = naver.get('change')
            change_pct = naver.get('change_percent')
            
            price_class = 'price-up' if change and change > 0 else 'price-down' if change and change < 0 else ''
            change_sign = '+' if change and change > 0 else ''
            
            # V전략 데이터
            entry = stock.get('entry_price', 0)
            target = stock.get('target_price', 0)
            stop = stock.get('stop_loss', 0)
            rr = stock.get('rr_ratio', 0)
            value_score = stock.get('value_score', 0)
            strategy = stock.get('strategy_type', 'Unknown')
            fib = stock.get('fib_level', '-')
            
            # 가격 차이
            price_diff = stock.get('price_diff_pct')
            diff_text = f"{price_diff:+.1f}%" if price_diff else "-"
            
            html += f"""
            <div class="stock-card">
                <div class="stock-header">
                    <span class="stock-rank">#{i}</span>
                    <div class="stock-info">
                        <div class="stock-name">{name}</div>
                        <div class="stock-code">{code}</div>
                    </div>
                </div>
                
                <div class="price-section">
                    <div class="price-box">
                        <div class="price-label">현재가</div>
                        <div class="price-value {price_class}">
                            {f"₩{current:,}" if current else "N/A"}
                        </div>
                        {f'<div style="font-size:0.85em;{price_class}">{change_sign}{change:,} ({change_sign}{change_pct:.2f}%)</div>' if change else ''}
                    </div>
                    <div class="price-box">
                        <div class="price-label">V전략 진입가</div>
                        <div class="price-value">₩{entry:,.0f}</div>
                        <div style="font-size:0.85em;color:#8b949e">{diff_text}</div>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 10px 0;">
                    <div class="price-box" style="background: var(--bg-color); padding: 8px; border-radius: 6px;">
                        <div class="price-label">목표가</div>
                        <div class="price-value price-up">₩{target:,.0f}</div>
                    </div>
                    <div class="price-box" style="background: var(--bg-color); padding: 8px; border-radius: 6px;">
                        <div class="price-label">손절가</div>
                        <div class="price-value price-down">₩{stop:,.0f}</div>
                    </div>
                </div>
                
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">1:{rr:.1f}</div>
                        <div class="metric-label">손익비</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{value_score:.0f}</div>
                        <div class="metric-label">가치점수</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{fib.replace('fib_', '')}</div>
                        <div class="metric-label">Fib</div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 10px;">
                    <span class="strategy-badge">{strategy}</span>
                </div>
                
                <div style="text-align: center;">
                    <a href="{naver.get('chart_url', '#')}" class="chart-link" target="_blank">📊 차트 보기</a>
                    <a href="{naver.get('detail_url', '#')}" class="chart-link" target="_blank" style="margin-left: 5px;">📋 상세 정보</a>
                </div>
            </div>
"""
        
        # 푸터
        html += f"""
        </div>
        
        <footer>
            <p>V전략: 가치투자 + Fibonacci 되돌림 + ATR 리스크관리</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                데이터 출처: 네이버 금융 | 
                이 리포트는 투자 참고 자료이며 투자 손실에 대한 책임은 투자자 본인에게 있습니다.
            </p>
        </footer>
    </div>
</body>
</html>
"""
        
        # 저장
        output_dir = Path('/root/.openclaw/workspace/strg/docs')
        output_path = output_dir / f'V_Strategy_Final_{self.today_str}.html'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def run(self):
        """전체 실행"""
        print("=" * 70)
        print("🎯 V전략 + 네이버 금융 통합 리포트 생성")
        print("=" * 70)
        
        # 1. V전략 결과 로드
        v_results = self.load_v_results()
        
        # 2. 네이버 데이터 스크래핑
        enriched = self.scrape_top_stocks(v_results, top_n=20)
        
        # 3. HTML 리포트 생성
        report_path = self.generate_html_report(enriched)
        
        print(f"\n✅ 최종 리포트 생성 완료!")
        print(f"   📄 {report_path}")
        print(f"\n📊 선정 종목 요약:")
        for i, s in enumerate(enriched[:5], 1):
            name = s.get('naver', {}).get('name') or s['symbol']
            price = s.get('naver', {}).get('current_price')
            print(f"   {i}. {name} ({s['symbol']}): " + 
                  (f"₩{price:,}" if price else "가격 확인 불가"))
        
        return report_path


def main():
    generator = VStrategyFinalReport()
    report_path = generator.run()
    print(f"\n🔗 리포트 URL: https://lubanana.github.io/kstock-dashboard/docs/{report_path.name}")


if __name__ == '__main__':
    main()
