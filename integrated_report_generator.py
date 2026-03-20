#!/usr/bin/env python3
"""
Integrated Multi-Strategy Report Generator
"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

def get_stock_name(symbol):
    """종목명 조회 - DB 우선, 매핑은 fallback"""
    try:
        conn = sqlite3.connect('data/pivot_strategy.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM stock_info WHERE symbol = ?', (symbol,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except:
        pass
    
    # Fallback: 매핑 테이블
    names = {
        '005930': '삼성전자', '000660': 'SK하이닉스', '051910': 'LG화학',
        '005380': '현대차', '035720': '카카오', '068270': '셀트리온',
        '207940': '삼성바이오로직스', '006400': '삼성SDI', '000270': '기아',
        '012330': '현대모비스', '005490': 'POSCO홀딩스', '028260': '삼성물산',
        '105560': 'KB금융', '018260': '삼성에스디에스', '032830': '삼성생명',
        '034730': 'SK', '000150': '두산', '016360': '삼성증권',
        '009830': '한화솔루션', '003490': '대한항공', '004170': '신세계',
        '000100': '유한양행', '011200': 'HMM', '030200': 'KT',
        '010950': 'S-Oil', '034220': 'LG디스플레이', '086790': '하나금융지주',
        '055550': '신한지주', '047050': '포스코DX', '032640': 'LG유플러스',
        '009540': '삼성전기', '030000': '제일제당', '018880': '한온시스템',
        '000810': '삼성화재', '024110': '기업은행', '005940': 'NH투자증권',
        '010140': '삼성중공업', '001040': 'CJ', '003550': 'LG',
        '008770': '호텔신라', '007310': '오뚜기', '006800': '미래에셋증권',
        '000120': 'CJ대한통운', '001120': 'LG이노텍', '010130': '고려아연',
        '002790': '아모레퍼시픽', '001800': '오리온', '003000': '포스코인터내셔널',
        '005420': '코스모화학', '000020': '동화약품', '000040': 'KR모터스',
        '000050': '경방', '000070': '삼양홀딩스', '000080': '하이트진로',
        '000140': '하이트진로홀딩스', '000180': '성창기업지주', '000210': 'DL',
        '000240': '한국테크놀로지', '000250': '삼천당제약', '000300': '대유플러스',
        '000320': '노서아', '000370': '한화손핳보험', '000400': '롯데손핳보험',
        '000430': '대원강업', '000480': '조선내화', '000490': '대동공업',
        '000500': '가온전선', '000520': '삼일제약', '000540': '흥국화재',
        '000590': 'CS홀딩스', '000640': '동아쏘시오홀딩스', '000650': '천일고속',
        '000670': '영풍', '000680': '유수홀딩스', '000700': '유수홀딩스우',
        '000720': '현대건설', '000725': '현대건설우', '000760': '삼성증권우',
        '000815': '삼성화재우', '000850': '화천기공', '000860': '강남제비스코',
        '000880': '한화', '000885': '한화우', '000890': '보해양조',
        '000910': '유니온', '000950': '전방', '000970': '한국주철관',
        '000990': 'DB하이텍', '001020': '페이퍼코리아', '001060': 'JW중외제약',
        '001065': 'JW중외제약우', '001070': '대한방직', '001130': '대한제당',
        '001200': '유진투자증권', '001210': '우리은행', '001230': '동국제강',
        '001250': 'GS글로벌', '001260': '남광토건', '001270': '부국증권',
        '001280': '대창', '001290': '상상인증권', '001330': '삼성공조',
        '001340': '백광소재', '001360': '삼성제약', '001380': 'SG세계물산',
        '001390': 'KB캐피탈', '001430': '세아베스틸', '001440': '대한전선',
        '001450': '현대해상', '001460': 'BYC', '001465': 'BYC우',
        '001470': '삼부토건', '001500': '현대차증권', '001510': 'SK증권',
        '001520': '동양', '001550': '조비', '001560': '제일연마',
        '001570': '금양', '001620': '케이비아이동국증권', '049720': '고려신용정보',
        '139480': '이마트', '154030': '아이윈', '001750': '한양증권',
        '002870': '신풍', '003300': '한일홀딩스', '049770': '대우증권',
        '049800': '우진플라임', '002600': '조흥',
    }
    return names.get(symbol, symbol)

def generate_html_report(data, timestamp):
    """리포트 HTML 생성"""
    
    # 모든 종목 합치기
    all_stocks = []
    for strategy, items in data.items():
        for stock in items.get('stocks', []):
            stock['strategy'] = strategy
            # 종목명이 없거나 코드와 같으면 다시 조회
            if not stock.get('name') or stock.get('name') == stock.get('symbol'):
                stock['name'] = get_stock_name(stock['symbol'])
            all_stocks.append(stock)
    
    # 점수 기준 정렬
    all_stocks.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 전략별 상위 10개만 표시
    display_stocks = all_stocks[:40]  # 최대 40개 (전략당 10개)
    
    stocks_json = json.dumps(display_stocks, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통합 멀티 전략 리포트 - {timestamp}</title>
    <style>
        :root {{ --primary: #3b82f6; --success: #22c55e; --danger: #ef4444; --warning: #f59e0b; 
                 --purple: #8b5cf6; --gold: #fbbf24; --cyan: #06b6d4; --bg: #0f172a; 
                 --card: #1e293b; --text: #f1f5f9; --text-muted: #94a3b8; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        header {{ text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); 
                  border-radius: 16px; margin-bottom: 30px; border: 1px solid #334155; }}
        h1 {{ font-size: 2.5em; margin-bottom: 10px; background: linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .subtitle {{ color: var(--text-muted); font-size: 1.1em; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: var(--card); padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #334155; }}
        .summary-card.v {{ border-top: 3px solid #8b5cf6; }}
        .summary-card.nps {{ border-top: 3px solid #22c55e; }}
        .summary-card.b01 {{ border-top: 3px solid #f59e0b; }}
        .summary-card.multi {{ border-top: 3px solid #06b6d4; }}
        .summary-card h3 {{ font-size: 2em; margin-bottom: 5px; }}
        .summary-card p {{ color: var(--text-muted); font-size: 0.9em; }}
        
        .filters {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; justify-content: center; }}
        .filter-btn {{ padding: 10px 20px; border: 1px solid #334155; background: var(--card); color: var(--text); 
                      border-radius: 8px; cursor: pointer; transition: all 0.3s; font-weight: 500; }}
        .filter-btn:hover {{ background: #334155; }}
        .filter-btn.active {{ background: var(--primary); border-color: var(--primary); }}
        .filter-btn.v.active {{ background: #8b5cf6; border-color: #8b5cf6; }}
        .filter-btn.nps.active {{ background: #22c55e; border-color: #22c55e; }}
        .filter-btn.b01.active {{ background: #f59e0b; border-color: #f59e0b; }}
        .filter-btn.multi.active {{ background: #06b6d4; border-color: #06b6d4; }}
        
        .stocks-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
        .stock-card {{ background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid #334155; 
                      transition: transform 0.2s, box-shadow 0.2s; cursor: pointer; }}
        .stock-card:hover {{ transform: translateY(-4px); box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
        .stock-card.v {{ border-left: 4px solid #8b5cf6; }}
        .stock-card.nps {{ border-left: 4px solid #22c55e; }}
        .stock-card.b01 {{ border-left: 4px solid #f59e0b; }}
        .stock-card.multi {{ border-left: 4px solid #06b6d4; }}
        
        .stock-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .stock-info {{ display: flex; align-items: center; gap: 10px; }}
        .stock-rank {{ font-size: 1.5em; font-weight: bold; color: var(--text-muted); }}
        .stock-name {{ font-size: 1.3em; font-weight: 600; }}
        .stock-code {{ font-size: 0.85em; color: var(--text-muted); background: #334155; padding: 2px 8px; border-radius: 4px; }}
        .strategy-badge {{ padding: 4px 12px; border-radius: 20px; font-size: 0.75em; font-weight: 600; text-transform: uppercase; }}
        .strategy-badge.v {{ background: rgba(139, 92, 246, 0.2); color: #a78bfa; }}
        .strategy-badge.nps {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; }}
        .strategy-badge.b01 {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .strategy-badge.multi {{ background: rgba(6, 182, 212, 0.2); color: #22d3ee; }}
        
        .score-display {{ display: flex; align-items: center; gap: 15px; margin-bottom: 15px; }}
        .score-value {{ font-size: 2em; font-weight: bold; }}
        .score-bar {{ flex: 1; height: 8px; background: #334155; border-radius: 4px; overflow: hidden; }}
        .score-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s ease; }}
        .score-fill.high {{ background: linear-gradient(90deg, #22c55e, #4ade80); }}
        .score-fill.medium {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
        .score-fill.low {{ background: linear-gradient(90deg, #ef4444, #f87171); }}
        
        .price-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 15px; }}
        .price-box {{ background: #0f172a; padding: 12px; border-radius: 8px; text-align: center; }}
        .price-box.label {{ font-size: 0.75em; color: var(--text-muted); margin-bottom: 4px; text-transform: uppercase; }}
        .price-box.value {{ font-size: 1.1em; font-weight: 600; }}
        .price-box.target {{ color: #4ade80; }}
        .price-box.stop {{ color: #f87171; }}
        
        .rr-ratio {{ display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 10px 15px; border-radius: 8px; }}
        .rr-label {{ font-size: 0.85em; color: var(--text-muted); }}
        .rr-value {{ font-size: 1.1em; font-weight: bold; color: #fbbf24; }}
        
        .detail-btn {{ width: 100%; margin-top: 15px; padding: 12px; background: var(--primary); color: white; 
                      border: none; border-radius: 8px; cursor: pointer; font-weight: 500; transition: background 0.2s; }}
        .detail-btn:hover {{ background: #2563eb; }}
        
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                  background: rgba(0,0,0,0.8); z-index: 1000; justify-content: center; align-items: center; padding: 20px; }}
        .modal.active {{ display: flex; }}
        .modal-content {{ background: var(--card); border-radius: 16px; width: 100%; max-width: 1000px; 
                         max-height: 90vh; overflow-y: auto; border: 1px solid #334155; }}
        .modal-header {{ display: flex; justify-content: space-between; align-items: center; 
                        padding: 20px; border-bottom: 1px solid #334155; }}
        .modal-title {{ font-size: 1.5em; }}
        .modal-close {{ background: none; border: none; color: var(--text); font-size: 1.5em; cursor: pointer; }}
        .modal-body {{ padding: 20px; }}
        .chart-container {{ height: 400px; background: #0f172a; border-radius: 8px; margin-bottom: 20px; }}
        
        .loading {{ text-align: center; padding: 60px; color: var(--text-muted); }}
        .spinner {{ width: 40px; height: 40px; border: 3px solid #334155; border-top-color: var(--primary); 
                   border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        
        @media (max-width: 768px) {{
            .stocks-grid {{ grid-template-columns: 1fr; }}
            .price-grid {{ grid-template-columns: 1fr; }}
            h1 {{ font-size: 1.8em; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 통합 멀티 전략 리포트</h1>
            <p class="subtitle">V-Strategy · NPS · B01 · Multi | {timestamp}</p>
        </header>
        
        <div class="summary">
            <div class="summary-card v">
                <h3 id="v-count">0</h3>
                <p>V-Strategy</p>
            </div>
            <div class="summary-card nps">
                <h3 id="nps-count">0</h3>
                <p>NPS</p>
            </div>
            <div class="summary-card b01">
                <h3 id="b01-count">0</h3>
                <p>B01 Buffett</p>
            </div>
            <div class="summary-card multi">
                <h3 id="multi-count">0</h3>
                <p>Multi-Strategy</p>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-btn active" data-filter="all">전체</button>
            <button class="filter-btn v" data-filter="V">V-Strategy</button>
            <button class="filter-btn nps" data-filter="NPS">NPS</button>
            <button class="filter-btn b01" data-filter="B01">B01</button>
            <button class="filter-btn multi" data-filter="Multi">Multi</button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>데이터 로딩 중...</p>
        </div>
        
        <div class="stocks-grid" id="stocks-grid"></div>
    </div>
    
    <div class="modal" id="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title" id="modal-title">종목 상세</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div id="tradingview-chart" class="chart-container"></div>
                <div id="modal-details"></div>
            </div>
        </div>
    </div>

    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
        const stocks = {stocks_json};
        
        // 카운트 업데이트
        const counts = {{ V: 0, NPS: 0, B01: 0, Multi: 0 }};
        stocks.forEach(s => {{ counts[s.strategy] = (counts[s.strategy] || 0) + 1; }});
        document.getElementById('v-count').textContent = counts.V;
        document.getElementById('nps-count').textContent = counts.NPS;
        document.getElementById('b01-count').textContent = counts.B01;
        document.getElementById('multi-count').textContent = counts.Multi;
        
        // 로딩 숨기기
        document.getElementById('loading').style.display = 'none';
        
        let currentFilter = 'all';
        let tvWidget = null;
        
        function formatPrice(price) {{
            if (price >= 1000000) return (price / 1000000).toFixed(2) + 'M';
            if (price >= 1000) return (price / 1000).toFixed(1) + 'K';
            return price.toLocaleString();
        }}
        
        function renderStocks() {{
            const grid = document.getElementById('stocks-grid');
            grid.innerHTML = '';
            
            const filtered = currentFilter === 'all' 
                ? stocks 
                : stocks.filter(s => s.strategy === currentFilter);
            
            filtered.forEach((stock, index) => {{
                const card = document.createElement('div');
                card.className = `stock-card ${{stock.strategy.toLowerCase()}}`;
                
                const scoreClass = stock.score >= 80 ? 'high' : stock.score >= 60 ? 'medium' : 'low';
                
                card.innerHTML = `
                    <div class="stock-header">
                        <div class="stock-info">
                            <span class="stock-rank">#${{index + 1}}</span>
                            <div>
                                <div class="stock-name">${{stock.name}}</div>
                                <span class="stock-code">${{stock.symbol}}</span>
                            </div>
                        </div>
                        <span class="strategy-badge ${{stock.strategy.toLowerCase()}}">${{stock.strategy}}</span>
                    </div>
                    
                    <div class="score-display">
                        <span class="score-value">${{stock.score.toFixed(1)}}</span>
                        <div class="score-bar">
                            <div class="score-fill ${{scoreClass}}" style="width: ${{stock.score}}%"></div>
                        </div>
                    </div>
                    
                    <div class="price-grid">
                        <div class="price-box">
                            <div class="price-box label">현재가</div>
                            <div class="price-box value">₩${{formatPrice(stock.current_price)}}</div>
                        </div>
                        <div class="price-box">
                            <div class="price-box label">목표가</div>
                            <div class="price-box value target">₩${{formatPrice(stock.target_price)}}</div>
                        </div>
                        <div class="price-box">
                            <div class="price-box label">손절가</div>
                            <div class="price-box value stop">₩${{formatPrice(stock.stop_loss)}}</div>
                        </div>
                    </div>
                    
                    <div class="rr-ratio">
                        <span class="rr-label">손익비 (R:R)</span>
                        <span class="rr-value">1:${{stock.rr_ratio.toFixed(2)}}</span>
                    </div>
                    
                    <button class="detail-btn" onclick="openModal('${{stock.symbol}}', '${{stock.name}}', '${{stock.strategy}}')">
                        차트 보기
                    </button>
                `;
                
                grid.appendChild(card);
            }});
        }}
        
        // 필터 버튼 이벤트
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                renderStocks();
            }});
        }});
        
        // 모달 함수
        function openModal(symbol, name, strategy) {{
            document.getElementById('modal-title').textContent = `${{name}} (${{symbol}}) - ${{strategy}}`;
            document.getElementById('modal').classList.add('active');
            
            if (tvWidget) {{
                tvWidget.remove();
            }}
            
            tvWidget = new TradingView.widget({{
                container_id: 'tradingview-chart',
                symbol: 'KRX:' + symbol,
                interval: 'D',
                timezone: 'Asia/Seoul',
                theme: 'dark',
                style: '1',
                locale: 'kr',
                toolbar_bg: '#1e293b',
                enable_publishing: false,
                hide_top_toolbar: false,
                hide_legend: false,
                save_image: false,
                height: 400,
                studies: ['RSI@tv-basicstudies', 'MASimple@tv-basicstudies'],
                overrides: {{
                    'mainSeriesProperties.candleStyle.upColor': '#22c55e',
                    'mainSeriesProperties.candleStyle.downColor': '#ef4444'
                }}
            }});
        }}
        
        function closeModal() {{
            document.getElementById('modal').classList.remove('active');
            if (tvWidget) {{
                tvWidget.remove();
                tvWidget = null;
            }}
        }}
        
        // 초기 렌더링
        renderStocks();
        
        // ESC 키로 모달 닫기
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});
        
        // 모달 외부 클릭으로 닫기
        document.getElementById('modal').addEventListener('click', (e) => {{
            if (e.target.id === 'modal') closeModal();
        }});
    </script>
</body>
</html>'''
    return html

def main():
    # 결과 파일 로드
    data = {}
    result_dir = Path('./reports/multi_strategy')
    
    for strategy in ['V', 'B01', 'NPS', 'Multi']:
        file_path = result_dir / f'{strategy.lower()}_scan_20260320.json'
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data[strategy] = json.load(f)
    
    # 타임스탬프
    kst = timezone(timedelta(hours=9))
    timestamp = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    # HTML 생성
    html = generate_html_report(data, timestamp)
    
    # 저장
    report_file = f'./reports/Integrated_Multi_Strategy_Report_{datetime.now(kst).strftime("%Y%m%d_%H%M")}.html'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # docs 폭사본
    docs_file = f'./docs/Integrated_Multi_Strategy_Report_{datetime.now(kst).strftime("%Y%m%d_%H%M")}.html'
    with open(docs_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # 최신 버전 링크
    latest_file = './docs/index.html'
    if latest_file:
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = f.read()
        # 리포트 링크 업데이트 (간단한 방식)
    
    print(f"✅ 리포트 생성 완료: {report_file}")
    print(f"\n📊 결과 요약:")
    for strategy in ['V', 'B01', 'NPS', 'Multi']:
        if strategy in data:
            print(f"   {strategy}: {data[strategy].get('selected_count', 0)}개 종목")
    
    print(f"\n🔗 URL: https://lubanana.github.io/kstock-dashboard/{Path(report_file).name}")

if __name__ == '__main__':
    main()
