#!/usr/bin/env python3
"""
Integrated Multi-Strategy Report Generator with Fixed TradingView Charts
통합 멀티 전략 리포트 - 차트 문제 수정
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import shutil

STOCK_NAMES = {
    "005930": "삼성전자", "000660": "SK하이닉스", "051910": "LG화학", "005380": "현대차",
    "035720": "카카오", "068270": "셀트리온", "207940": "삼성바이오로직스",
    "006400": "삼성SDI", "000270": "기아", "012330": "현대모비스",
    "005490": "POSCO홀딩스", "028260": "삼성물산", "105560": "KB금융",
    "018260": "삼성에스디에스", "032830": "삼성생명", "034730": "SK",
    "000150": "두산", "016360": "삼성증권", "009830": "한화솔루션",
    "003490": "대한항공", "004170": "신세계", "000100": "유한양행",
    "011200": "HMM", "030200": "KT", "010950": "S-Oil",
    "034220": "LG디스플레이", "086790": "하나금융지주", "055550": "신한지주"
}

def generate_html_report(data, timestamp):
    """리포트 HTML 생성"""
    
    # 모든 종목 합치기
    all_stocks = []
    for strategy, items in data.items():
        for stock in items.get('stocks', []):
            stock['strategy'] = strategy
            all_stocks.append(stock)
    
    # 점수 기준 정렬
    all_stocks.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 상위 30개만 표시
    display_stocks = all_stocks[:30]
    
    stocks_json = json.dumps(display_stocks, ensure_ascii=False)
    names_json = json.dumps(STOCK_NAMES, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통합 멀티 전략 리포트 - {timestamp}</title>
    <style>
        :root {{ --primary: #3b82f6; --success: #22c55e; --danger: #ef4444; --warning: #f59e0b; 
                 --purple: #8b5cf6; --gold: #fbbf24; --cyan: #06b6d4; --bg: #0f172a; 
                 --card: #1e293b; --text: #f1f5f9; --text-muted: #94a3b8; --border: #334155; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: "Segoe UI", "Noto Sans KR", sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%); 
                   border-radius: 16px; margin-bottom: 30px; border: 1px solid var(--border); }}
        .header h1 {{ font-size: 2.2rem; margin-bottom: 10px; }}
        .header .subtitle {{ color: var(--text-muted); font-size: 1.1rem; }}
        .header .timestamp {{ color: var(--warning); font-size: 1rem; margin-top: 5px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); text-align: center; }}
        .stat-card .label {{ color: var(--text-muted); font-size: 0.85rem; margin-bottom: 5px; }}
        .stat-card .value {{ font-size: 1.8rem; font-weight: 700; }}
        .filter-tabs {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; justify-content: center; }}
        .filter-tab {{ padding: 10px 20px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; 
                      cursor: pointer; transition: all 0.3s; font-weight: 600; }}
        .filter-tab:hover, .filter-tab.active {{ background: var(--primary); border-color: var(--primary); }}
        .stock-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stock-card {{ background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); 
                      transition: all 0.3s ease; cursor: pointer; position: relative; overflow: hidden; }}
        .stock-card:hover {{ transform: translateY(-3px); border-color: var(--primary); box-shadow: 0 8px 30px rgba(59,130,246,0.2); }}
        .stock-card.v {{ border-left: 4px solid var(--success); }}
        .stock-card.b01 {{ border-left: 4px solid var(--gold); }}
        .stock-card.nps {{ border-left: 4px solid var(--purple); }}
        .stock-card.multi {{ border-left: 4px solid var(--cyan); }}
        .stock-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .stock-name {{ font-size: 1.2rem; font-weight: 700; }}
        .stock-code {{ color: var(--text-muted); font-size: 0.85rem; }}
        .strategy-badge {{ padding: 3px 10px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; }}
        .strategy-badge.v {{ background: rgba(34,197,94,0.2); color: var(--success); }}
        .strategy-badge.b01 {{ background: rgba(251,191,36,0.2); color: var(--gold); }}
        .strategy-badge.nps {{ background: rgba(139,92,246,0.2); color: var(--purple); }}
        .strategy-badge.multi {{ background: rgba(6,182,212,0.2); color: var(--cyan); }}
        .score-badge {{ background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(59,130,246,0.1)); 
                       color: var(--primary); padding: 5px 12px; border-radius: 15px; font-size: 0.85rem; font-weight: 700; }}
        .price-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 12px 0; }}
        .price-box {{ background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; text-align: center; }}
        .price-box .label {{ font-size: 0.75rem; color: var(--text-muted); margin-bottom: 3px; }}
        .price-box .value {{ font-size: 1rem; font-weight: 600; }}
        .price-box.target {{ border-left: 2px solid var(--success); }}
        .price-box.stop {{ border-left: 2px solid var(--danger); }}
        .rr-info {{ display: flex; justify-content: space-between; font-size: 0.85rem; margin-top: 10px; padding-top: 10px; 
                   border-top: 1px solid var(--border); }}
        .rr-badge {{ color: var(--primary); font-weight: 600; }}
        
        /* Modal */
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; 
                  background: rgba(0,0,0,0.9); overflow: auto; }}
        .modal-content {{ background: var(--card); margin: 20px auto; padding: 25px; border-radius: 16px; 
                         width: 95%; max-width: 1100px; max-height: 95vh; overflow-y: auto; position: relative; 
                         border: 1px solid var(--border); }}
        .close {{ position: absolute; top: 15px; right: 20px; color: var(--text-muted); font-size: 32px; 
                 font-weight: bold; cursor: pointer; z-index: 1001; background: var(--bg); width: 40px; height: 40px; 
                 border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
        .close:hover {{ color: var(--text); }}
        .modal-header {{ margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid var(--border); }}
        .modal-title {{ font-size: 1.6rem; margin-bottom: 5px; }}
        .modal-subtitle {{ color: var(--text-muted); font-size: 0.95rem; }}
        .tradingview-container {{ height: 450px; margin: 15px 0; border-radius: 8px; overflow: hidden; 
                                border: 1px solid var(--border); }}
        .detail-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin: 15px 0; }}
        .detail-item {{ background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; text-align: center; }}
        .detail-item .label {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px; }}
        .detail-item .value {{ font-size: 1.1rem; font-weight: 700; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 통합 멀티 전략 리포트</h1>
            <p class="subtitle">V-Strategy + B01 + NPS + Multi-Strategy</p>
            <p class="timestamp">생성일시: {timestamp} (KST) | 데이터 기준: 2026-03-20</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">총 선정 종목</div>
                <div class="value">{len(all_stocks)}개</div>
            </div>
            <div class="stat-card">
                <div class="label">V-Strategy</div>
                <div class="value">{len(data.get('V', {}).get('stocks', []))}개</div>
            </div>
            <div class="stat-card">
                <div class="label">B01 Buffett</div>
                <div class="value">{len(data.get('B01', {}).get('stocks', []))}개</div>
            </div>
            <div class="stat-card">
                <div class="label">NPS</div>
                <div class="value">{len(data.get('NPS', {}).get('stocks', []))}개</div>
            </div>
            <div class="stat-card">
                <div class="label">Multi</div>
                <div class="value">{len(data.get('Multi', {}).get('stocks', []))}개</div>
            </div>
        </div>
        
        <div class="filter-tabs">
            <div class="filter-tab active" onclick="filterStocks('all')">전체</div>
            <div class="filter-tab" onclick="filterStocks('V')">V-Strategy</div>
            <div class="filter-tab" onclick="filterStocks('B01')">B01</div>
            <div class="filter-tab" onclick="filterStocks('NPS')">NPS</div>
            <div class="filter-tab" onclick="filterStocks('Multi')">Multi</div>
        </div>
        
        <div class="stock-grid" id="stockGrid"></div>
    </div>
    
    <div id="stockModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="modalBody"></div>
        </div>
    </div>

    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
        const stockData = {stocks_json};
        const stockNames = {names_json};
        let currentFilter = 'all';
        let tvWidget = null;
        
        function formatNumber(num) {{
            return "₩" + parseFloat(num).toLocaleString("ko-KR", {{maximumFractionDigits: 0}});
        }}
        
        function getStrategyClass(strategy) {{
            return strategy.toLowerCase();
        }}
        
        function getStrategyBadge(strategy) {{
            return strategy;
        }}
        
        function renderCards() {{
            const grid = document.getElementById("stockGrid");
            grid.innerHTML = "";
            
            let filtered = stockData;
            if (currentFilter !== 'all') {{
                filtered = stockData.filter(s => s.strategy === currentFilter);
            }}
            
            filtered.forEach((stock, i) => {{
                const name = stockNames[stock.symbol] || stock.symbol;
                const sClass = getStrategyClass(stock.strategy);
                
                const card = document.createElement("div");
                card.className = "stock-card " + sClass;
                card.onclick = () => openModal(stock);
                card.innerHTML = `
                    <div class="stock-header">
                        <div>
                            <div class="stock-name">${{i+1}}. ${{name}}</div>
                            <div class="stock-code">${{stock.symbol}}</div>
                        </div>
                        <div style="text-align: right;">
                            <span class="strategy-badge ${{sClass}}">${{getStrategyBadge(stock.strategy)}}</span>
                            <div class="score-badge" style="margin-top: 6px;">${{stock.score.toFixed(1)}}점</div>
                        </div>
                    </div>
                    <div class="price-row">
                        <div class="price-box current">
                            <div class="label">현재가</div>
                            <div class="value">${{formatNumber(stock.current_price)}}</div>
                        </div>
                        <div class="price-box target">
                            <div class="label">목표가</div>
                            <div class="value" style="color: var(--success)">${{formatNumber(stock.target_price)}}</div>
                        </div>
                        <div class="price-box stop">
                            <div class="label">손절가</div>
                            <div class="value" style="color: var(--danger)">${{formatNumber(stock.stop_loss)}}</div>
                        </div>
                    </div>
                    <div class="rr-info">
                        <span class="rr-badge">손익비 1:${{stock.rr_ratio.toFixed(2)}}</span>
                        <span style="color: var(--text-muted);">📊 클릭하여 차트 보기</span>
                    </div>
                `;
                grid.appendChild(card);
            }});
        }}
        
        function filterStocks(strategy) {{
            currentFilter = strategy;
            document.querySelectorAll('.filter-tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');
            renderCards();
        }}
        
        function openModal(stock) {{
            const modal = document.getElementById("stockModal");
            const body = document.getElementById("modalBody");
            const name = stockNames[stock.symbol] || stock.symbol;
            
            body.innerHTML = `
                <div class="modal-header">
                    <div class="modal-title">${{name}} (${{stock.symbol}})</div>
                    <div class="modal-subtitle">${{stock.strategy}} 전략 | 점수: ${{stock.score.toFixed(1)}}</div>
                </div>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="label">현재가</div>
                        <div class="value">${{formatNumber(stock.current_price)}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">목표가</div>
                        <div class="value" style="color: var(--success);">${{formatNumber(stock.target_price)}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">손절가</div>
                        <div class="value" style="color: var(--danger);">${{formatNumber(stock.stop_loss)}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">손익비</div>
                        <div class="value" style="color: var(--primary);">1:${{stock.rr_ratio.toFixed(2)}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">ATR</div>
                        <div class="value">${{formatNumber(stock.atr)}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">예상수익</div>
                        <div class="value" style="color: var(--success);">+${{((stock.target_price - stock.current_price) / stock.current_price * 100).toFixed(1)}}%</div>
                    </div>
                </div>
                <div class="tradingview-container" id="tv_chart"></div>
            `;
            
            modal.style.display = "block";
            
            // Destroy previous widget if exists
            if (tvWidget) {{
                tvWidget = null;
            }}
            
            // Create new TradingView widget
            setTimeout(() => {{
                try {{
                    tvWidget = new TradingView.widget({{
                        autosize: true,
                        symbol: "KRX:" + stock.symbol,
                        interval: "D",
                        timezone: "Asia/Seoul",
                        theme: "dark",
                        style: "1",
                        locale: "kr",
                        toolbar_bg: "#1e293b",
                        enable_publishing: false,
                        hide_top_toolbar: false,
                        hide_legend: false,
                        save_image: false,
                        container_id: "tv_chart",
                        studies: ["RSI@tv-basicstudies", "MACD@tv-basicstudies"],
                        show_popup_button: true,
                        popup_width: "1000",
                        popup_height: "650"
                    }});
                }} catch (e) {{
                    console.error("TradingView widget error:", e);
                    document.getElementById("tv_chart").innerHTML = 
                        '<div style="display: flex; justify-content: center; align-items: center; height: 100%; color: var(--text-muted);">' +
                        '차트를 불러올 수 없습니다. 직접 <a href="https://www.tradingview.com/chart/?symbol=KRX:' + stock.symbol + '" target="_blank" style="color: var(--primary); margin: 0 5px;">TradingView</a>에서 확인해주세요.</div>';
                }}
            }}, 200);
        }}
        
        function closeModal() {{
            document.getElementById("stockModal").style.display = "none";
            if (tvWidget) {{
                tvWidget = null;
            }}
        }}
        
        window.onclick = function(e) {{
            if (e.target === document.getElementById("stockModal")) closeModal();
        }};
        
        document.addEventListener("DOMContentLoaded", renderCards);
    </script>
    
    <footer style="text-align: center; padding: 30px; color: var(--text-muted); border-top: 1px solid var(--border); margin-top: 40px;">
        <p>Integrated Multi-Strategy Report with TradingView</p>
        <p style="font-size: 0.85rem; margin-top: 10px;">본 리포트는 투자 참고 자료입니다.</p>
    </footer>
</body>
</html>'''
    
    return html


def main():
    # 결과 파일 로드
    data = {}
    for strategy in ['V', 'B01', 'NPS', 'Multi']:
        try:
            with open(f'./reports/multi_strategy/{strategy.lower()}_scan_20260320.json', 'r', encoding='utf-8') as f:
                data[strategy] = json.load(f)
        except:
            data[strategy] = {'stocks': []}
    
    # 타임스탬프
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    timestamp = now.strftime('%Y%m%d_%H%M')
    display_time = now.strftime('%Y-%m-%d %H:%M')
    
    # HTML 생성
    html = generate_html_report(data, display_time)
    
    # 저장
    output_path = f'./reports/Integrated_Multi_Strategy_Report_{timestamp}.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # GitHub Pages용 복사
    shutil.copy(output_path, f'./docs/Integrated_Multi_Strategy_Report_{timestamp}.html')
    
    print(f"✅ 리포트 생성 완료: {output_path}")
    print(f"\n📊 결과 요약:")
    for strategy, items in data.items():
        print(f"   {strategy}: {len(items.get('stocks', []))}개 종목")
    
    print(f"\n🔗 URL: https://lubanana.github.io/kstock-dashboard/Integrated_Multi_Strategy_Report_{timestamp}.html")


if __name__ == '__main__':
    main()
