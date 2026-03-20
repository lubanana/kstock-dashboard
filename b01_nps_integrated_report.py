#!/usr/bin/env python3
"""
B01 + NPS Integrated Strategy Report Generator with TradingView Charts
B01 버핏 + NPS 통합 리포트 생성기 - 트레이딩뷰 차트 포함
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import shutil

# Stock name mapping
STOCK_NAMES = {
    '005930': '삼성전자', '000660': 'SK하이닉스', '051910': 'LG화학', '005380': '현대차',
    '035720': '카카오', '068270': '셀트리온', '207940': '삼성바이오로직스',
    '006400': '삼성SDI', '000270': '기아', '012330': '현대모비스',
    '005490': 'POSCO홀딩스', '028260': '삼성물산', '105560': 'KB금융',
    '018260': '삼성에스디에스', '032830': '삼성생명', '034730': 'SK',
    '000150': '두산', '016360': '삼성증권', '009830': '한화솔루션',
    '003490': '대한항공', '004170': '신세계', '000100': '유한양행',
    '011200': 'HMM', '030200': 'KT', '010950': 'S-Oil',
    '034220': 'LG디스플레이', '086790': '하나금융지주', '055550': '신한지주'
}

STOCK_INDUSTRY = {
    '005930': '반도체/전자', '000660': '반도체', '051910': '화학', '005380': '자동차',
    '035720': '플랫폼/IT', '068270': '바이오', '207940': '바이오',
    '006400': '배터리/에너지', '000270': '자동차', '012330': '자동차부품',
    '005490': '철강/소재', '028260': '종합상사', '105560': '금융/은행',
    '018260': 'IT서비스', '032830': '금융/보험', '034730': '에너지/화학',
    '000150': '중공업/건설', '016360': '금융/증권', '009830': '에너지/화학',
    '003490': '항공/운송', '004170': '유통/백화점', '000100': '제약',
    '011200': '해운', '030200': '통신', '010950': '정유',
    '034220': '디스플레이', '086790': '금융/은행', '055550': '금융/은행'
}


def generate_market_research(symbol: str) -> dict:
    """종목별 시장조사 정보"""
    industry = STOCK_INDUSTRY.get(symbol, '기타')
    
    research_templates = {
        '반도체/전자': {
            'outlook': 'AI 반도체 수요 증가로 중장기 성장세 지속 예상',
            'risk': '미중 무역분쟁 및 공급망 리스크',
            'catalyst': 'AI 서버 투자 증가, HBM 수요 확대'
        },
        '반도체': {
            'outlook': '메모리 시황 개선 및 AI 칩 수요 증가',
            'risk': '가격 변동성 및 중국 경기 둔화',
            'catalyst': 'DDR5 전환, AI 가속기 수요'
        },
        '금융/은행': {
            'outlook': '금리 인하 기대 및 수익성 개선',
            'risk': '경기 침체로 인한 대손비용 증가',
            'catalyst': '금리 정책 변화, 가계대출 증가'
        },
        '통신': {
            'outlook': 'AI 데이터센터 투자 및 클라우드 사업 확대',
            'risk': '시장 포화 및 가격 경쟁',
            'catalyst': 'AI 인프라 투자, 5G 가입자 증가'
        },
        '항공/운송': {
            'outlook': '여행 수요 회복 및 화물 운송 안정화',
            'risk': '유가 변동 및 환율 리스크',
            'catalyst': '여름 성수기 수요, 화물 운임 회복'
        },
        '중공업/건설': {
            'outlook': '인프라 투자 및 해외 수주 증가',
            'risk': '원자재 가격 상승 및 인건 비용 증가',
            'catalyst': '대형 프로젝트 수주, 신재생에너지 투자'
        },
        'default': {
            'outlook': '업황 개선 및 수익성 회복 기대',
            'risk': '경기 변동성 및 환율 리스크',
            'catalyst': '실적 개선, 신사업 진출'
        }
    }
    
    template = research_templates.get(industry, research_templates['default'])
    
    return {
        'industry': industry,
        'outlook': template['outlook'],
        'risk': template['risk'],
        'catalyst': template['catalyst']
    }


def get_tradingview_symbol(krx_symbol: str) -> str:
    """KRX 종목코드를 TradingView 심볼로 변환"""
    return f"KRX:{krx_symbol}"


def generate_html_report(b01_data: dict, nps_data: dict, output_path: str, timestamp: str):
    """TradingView 차트를 포함한 HTML 리포트 생성"""
    
    scan_date = '2026-03-20'
    
    # 모든 종목 합치기
    all_stocks = []
    
    # B01 종목
    for stock in b01_data.get('stocks', []):
        stock['source'] = 'B01_Buffett'
        stock['score'] = stock.get('buffett_score', 0)
        all_stocks.append(stock)
    
    # NPS 종목
    for stock in nps_data.get('stocks', []):
        stock['source'] = 'NPS'
        stock['score'] = stock.get('nps_score', 0)
        all_stocks.append(stock)
    
    # 점수 기준 정렬
    all_stocks.sort(key=lambda x: x['score'], reverse=True)
    
    html_parts = []
    
    # Header
    html_parts.append(f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B01 + NPS 통합 선정 리포트 - {timestamp}</title>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <style>
        :root {{
            --primary: #3b82f6; --success: #22c55e; --danger: #ef4444;
            --warning: #f59e0b; --purple: #8b5cf6; --gold: #fbbf24;
            --bg: #0f172a; --card: #1e293b; --text: #f1f5f9;
            --text-muted: #94a3b8; --border: #334155;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', 'Noto Sans KR', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%); border-radius: 16px; margin-bottom: 30px; border: 1px solid var(--border); }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .header .subtitle {{ color: var(--text-muted); font-size: 1.1rem; }}
        .header .timestamp {{ color: var(--warning); font-size: 1rem; margin-top: 5px; }}
        .header .badge {{ display: inline-block; background: linear-gradient(135deg, rgba(251, 191, 36, 0.3), rgba(139, 92, 246, 0.3)); padding: 8px 20px; border-radius: 20px; margin-top: 15px; font-weight: 600; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: var(--card); border-radius: 12px; padding: 24px; border: 1px solid var(--border); text-align: center; }}
        .stat-card .label {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 8px; }}
        .stat-card .value {{ font-size: 2rem; font-weight: 700; }}
        .stock-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stock-card {{ background: var(--card); border-radius: 16px; padding: 24px; border: 1px solid var(--border); transition: all 0.3s ease; position: relative; overflow: hidden; }}
        .stock-card.b01::before {{ content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--gold); }}
        .stock-card.nps::before {{ content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--purple); }}
        .stock-card:hover {{ border-color: var(--primary); box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2); }}
        .stock-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
        .stock-name {{ font-size: 1.3rem; font-weight: 700; }}
        .stock-code {{ color: var(--text-muted); font-size: 0.9rem; }}
        .source-badge {{ padding: 4px 12px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
        .source-badge.b01 {{ background: rgba(251, 191, 36, 0.2); color: var(--gold); }}
        .source-badge.nps {{ background: rgba(139, 92, 246, 0.2); color: var(--purple); }}
        .value-score {{ background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(34, 197, 94, 0.1)); color: var(--success); padding: 8px 16px; border-radius: 20px; font-weight: 600; }}
        .price-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 16px 0; }}
        .price-box {{ background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; text-align: center; }}
        .price-box .label {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px; }}
        .price-box .value {{ font-size: 1.1rem; font-weight: 600; }}
        .price-box.target {{ border-left: 3px solid var(--success); }}
        .price-box.stop {{ border-left: 3px solid var(--danger); }}
        .price-box.current {{ border-left: 3px solid var(--primary); }}
        .fib-info {{ display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }}
        .fib-tag {{ background: rgba(139, 92, 246, 0.2); color: #a78bfa; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; }}
        .rr-badge {{ display: inline-block; background: rgba(59, 130, 246, 0.2); color: var(--primary); padding: 4px 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; }}
        .tradingview-widget {{ height: 400px; margin: 20px 0; border-radius: 8px; overflow: hidden; }}
        .research-section {{ background: rgba(255,255,255,0.03); padding: 20px; border-radius: 12px; margin-top: 20px; }}
        .research-section h3 {{ color: var(--primary); margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid var(--primary); }}
        .research-item {{ margin: 12px 0; padding: 12px; background: rgba(255,255,255,0.02); border-radius: 8px; }}
        .research-item .label {{ font-weight: 600; color: var(--text-muted); margin-bottom: 4px; }}
        .metrics-row {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 10px 0; font-size: 0.85rem; }}
        .metric {{ display: flex; justify-content: space-between; padding: 8px 12px; background: rgba(255,255,255,0.02); border-radius: 6px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 B01 + NPS 통합 선정 종목 리포트</h1>
            <p class="subtitle">Buffett Value + Net Purchase Strength with Fibonacci + ATR</p>
            <p class="timestamp">생성일시: {timestamp} (KST)</p>
            <div class="badge">B01 버핏 가치전략 + NPS 수급 강도 + Fibonacci + ATR Risk Management</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card primary">
                <div class="label">총 선정 종목</div>
                <div class="value">{len(all_stocks)}개</div>
            </div>
            <div class="stat-card warning">
                <div class="label">B01 Buffett</div>
                <div class="value">{b01_data.get('selected_count', 0)}개</div>
            </div>
            <div class="stat-card purple">
                <div class="label">NPS</div>
                <div class="value">{nps_data.get('selected_count', 0)}개</div>
            </div>
            <div class="stat-card success">
                <div class="label">평균 손익비</div>
                <div class="value">1:{sum(float(s.get('rr_ratio', 0)) for s in all_stocks)/max(len(all_stocks),1):.1f}</div>
            </div>
        </div>
''')
    
    # Stock cards with TradingView charts
    for i, stock in enumerate(all_stocks, 1):
        name = STOCK_NAMES.get(stock['symbol'], stock['symbol'])
        research = generate_market_research(stock['symbol'])
        tv_symbol = get_tradingview_symbol(stock['symbol'])
        source_class = 'b01' if stock.get('source') == 'B01_Buffett' else 'nps'
        source_badge_class = 'b01' if stock.get('source') == 'B01_Buffett' else 'nps'
        
        # B01 전용 지표
        b01_metrics = ''
        if stock.get('source') == 'B01_Buffett':
            b01_metrics = f'''
            <div class="metrics-row">
                <div class="metric">
                    <span>연간수익률</span>
                    <span style="color: var(--success);">{float(stock.get('yoy_return', 0)):.1f}%</span>
                </div>
                <div class="metric">
                    <span>변동성</span>
                    <span>{float(stock.get('volatility', 0)):.1f}%</span>
                </div>
            </div>'''
        
        # NPS 전용 지표
        nps_metrics = ''
        if stock.get('source') == 'NPS':
            nps_metrics = f'''
            <div class="metrics-row">
                <div class="metric">
                    <span>RSI</span>
                    <span>{float(stock.get('rsi', 0)):.1f}</span>
                </div>
                <div class="metric">
                    <span>20일 수익률</span>
                    <span style="color: var(--success);">{float(stock.get('return_20d', 0)):.1f}%</span>
                </div>
            </div>'''
        
        html_parts.append(f'''
        <div class="stock-card {source_class}">
            <div class="stock-header">
                <div>
                    <div class="stock-name">{i}. {name}</div>
                    <div class="stock-code">{stock['symbol']} | {research['industry']} | {tv_symbol}</div>
                </div>
                <div style="text-align: right;">
                    <span class="source-badge {source_badge_class}">{stock.get('source', 'B01')}</span>
                    <div class="value-score" style="margin-top: 8px;">{stock.get('score', 0)}점</div>
                </div>
            </div>
            
            {b01_metrics}
            {nps_metrics}
            
            <div class="price-row">
                <div class="price-box current">
                    <div class="label">현재가</div>
                    <div class="value">₩{float(stock.get('current_price', 0)):,.0f}</div>
                </div>
                <div class="price-box target">
                    <div class="label">목표가</div>
                    <div class="value" style="color: var(--success)">₩{float(stock.get('target_price', 0)):,.0f}</div>
                </div>
                <div class="price-box stop">
                    <div class="label">손절가</div>
                    <div class="value" style="color: var(--danger)">₩{float(stock.get('stop_loss', 0)):,.0f}</div>
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span class="rr-badge">손익비 1:{float(stock.get('rr_ratio', 0)):.2f}</span>
                <span style="color: var(--text-muted); font-size: 0.9rem;">
                    수익 +{float(stock.get('expected_return', 0)):.1f}% / 손실 {float(stock.get('expected_loss', 0)):.1f}%
                </span>
            </div>
            
            <div class="fib-info">
                <span class="fib-tag">Fib {stock.get('fib_level', 'N/A')}</span>
                <span class="fib-tag">ATR ₩{float(stock.get('atr', 0)):,.0f}</span>
            </div>
            
            <!-- TradingView Widget -->
            <div class="tradingview-widget" id="tv-chart-{stock['symbol']}"></div>
            <script type="text/javascript">
            new TradingView.widget({{
                "autosize": true,
                "symbol": "{tv_symbol}",
                "interval": "D",
                "timezone": "Asia/Seoul",
                "theme": "dark",
                "style": "1",
                "locale": "kr",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": false,
                "hide_top_toolbar": false,
                "hide_legend": false,
                "save_image": false,
                "container_id": "tv-chart-{stock['symbol']}",
                "studies": ["RSI@tv-basicstudies", "MACD@tv-basicstudies"],
                "show_popup_button": true,
                "popup_width": "1000",
                "popup_height": "650"
            }});
            </script>
            
            <div class="research-section">
                <h3>📊 시장조사 리포트</h3>
                
                <div class="research-item">
                    <div class="label">🎯 투자 전망</div>
                    <div>{research['outlook']}</div>
                </div>
                
                <div class="research-item">
                    <div class="label">⚠️ 주요 리스크</div>
                    <div>{research['risk']}</div>
                </div>
                
                <div class="research-item">
                    <div class="label">🚀 촉매제</div>
                    <div>{research['catalyst']}</div>
                </div>
            </div>
        </div>
''')
    
    html_parts.append('''
    </footer style="text-align: center; padding: 40px; color: var(--text-muted); border-top: 1px solid var(--border); margin-top: 40px;">
        <p>B01 + NPS Integrated Strategy Report | Generated with TradingView Charts</p>
        <p style="font-size: 0.9rem;">본 리포트는 투자 참고 자료이며, 투자 결정은 본인의 판단과 책임하에 이루어져야 합니다.</p>
    </footer>
</body>
</html>
''')
    
    html = ''.join(html_parts)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 리포트 생성 완료: {output_path}")


def main():
    # 한국 시간 (KST, UTC+9)
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    
    timestamp = now.strftime('%Y%m%d_%H%M')
    display_time = now.strftime('%Y-%m-%d %H:%M')
    
    # 결과 파일 로드
    b01_file = './reports/b01_buffett/b01_buffett_scan_20260320.json'
    nps_file = './reports/nps/nps_scan_20260320.json'
    
    with open(b01_file, 'r', encoding='utf-8') as f:
        b01_data = json.load(f)
    
    with open(nps_file, 'r', encoding='utf-8') as f:
        nps_data = json.load(f)
    
    # HTML 리포트 생성
    output_filename = f'B01_NPS_Integrated_Report_{timestamp}.html'
    output_path = f'./reports/{output_filename}'
    generate_html_report(b01_data, nps_data, output_path, f"{display_time} KST")
    
    # GitHub에 복사
    docs_path = f'./docs/{output_filename}'
    shutil.copy(output_path, docs_path)
    
    print(f"\n📁 GitHub Pages용으로 docs/ 폴에 복사 완료")
    print(f"   URL: https://lubanana.github.io/kstock-dashboard/{output_filename}")
    
    print(f"\n📊 요약:")
    print(f"   B01 Buffett: {b01_data.get('selected_count', 0)}개 종목")
    print(f"   NPS: {nps_data.get('selected_count', 0)}개 종목")
    print(f"   총 선정: {b01_data.get('selected_count', 0) + nps_data.get('selected_count', 0)}개 종목")


if __name__ == '__main__':
    main()
