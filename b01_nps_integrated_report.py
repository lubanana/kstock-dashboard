#!/usr/bin/env python3
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

def main():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    timestamp = now.strftime("%Y%m%d_%H%M")
    display_time = now.strftime("%Y-%m-%d %H:%M")
    
    with open("./reports/b01_buffett/b01_buffett_scan_20260320.json", "r", encoding="utf-8") as f:
        b01_data = json.load(f)
    with open("./reports/nps/nps_scan_20260320.json", "r", encoding="utf-8") as f:
        nps_data = json.load(f)
    
    all_stocks = []
    for s in b01_data.get("stocks", []):
        s["source"] = "B01_Buffett"
        s["score"] = s.get("buffett_score", 0)
        all_stocks.append(s)
    for s in nps_data.get("stocks", []):
        s["source"] = "NPS"
        s["score"] = s.get("nps_score", 0)
        all_stocks.append(s)
    all_stocks.sort(key=lambda x: x["score"], reverse=True)
    
    html = generate_html(all_stocks, b01_data, nps_data, display_time)
    
    output_path = f"./reports/B01_NPS_Integrated_Report_{timestamp}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    shutil.copy(output_path, f"./docs/B01_NPS_Integrated_Report_{timestamp}.html")
    print(f"✅ 리포트 생성 완료: {output_path}")

def generate_html(stocks, b01, nps, time_str):
    stocks_json = json.dumps(stocks, ensure_ascii=False)
    names_json = json.dumps(STOCK_NAMES, ensure_ascii=False)
    
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B01 + NPS 통합 리포트 - {time_str}</title>
    <style>
        :root {{ --primary: #3b82f6; --success: #22c55e; --danger: #ef4444; --warning: #f59e0b; --purple: #8b5cf6; --gold: #fbbf24; --bg: #0f172a; --card: #1e293b; --text: #f1f5f9; --text-muted: #94a3b8; --border: #334155; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: "Segoe UI", "Noto Sans KR", sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
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
        .stock-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stock-card {{ background: var(--card); border-radius: 16px; padding: 24px; border: 1px solid var(--border); transition: all 0.3s ease; position: relative; overflow: hidden; cursor: pointer; }}
        .stock-card.b01::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--gold); }}
        .stock-card.nps::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--purple); }}
        .stock-card:hover {{ border-color: var(--primary); box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2); transform: translateY(-4px); }}
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
        .modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.85); overflow: auto; }}
        .modal-content {{ background: var(--card); margin: 30px auto; padding: 30px; border-radius: 16px; width: 95%; max-width: 1200px; border: 1px solid var(--border); max-height: 90vh; overflow-y: auto; position: relative; }}
        .close {{ position: absolute; top: 15px; right: 25px; color: var(--text-muted); font-size: 36px; font-weight: bold; cursor: pointer; z-index: 1001; }}
        .close:hover {{ color: var(--text); }}
        .modal-header {{ margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid var(--border); }}
        .modal-title {{ font-size: 1.8rem; margin-bottom: 5px; }}
        .modal-subtitle {{ color: var(--text-muted); }}
        .tradingview-widget-container {{ height: 500px; margin: 20px 0; border-radius: 8px; overflow: hidden; }}
        .detail-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
        .detail-item {{ background: rgba(255,255,255,0.03); padding: 15px; border-radius: 8px; text-align: center; }}
        .detail-item .label {{ font-size: 0.85rem; color: var(--text-muted); margin-bottom: 5px; }}
        .detail-item .value {{ font-size: 1.2rem; font-weight: 600; }}
        .research-section {{ background: rgba(255,255,255,0.03); padding: 20px; border-radius: 12px; margin-top: 20px; }}
        .research-section h3 {{ color: var(--primary); margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid var(--primary); }}
        .research-item {{ margin: 12px 0; padding: 12px; background: rgba(255,255,255,0.02); border-radius: 8px; }}
        .research-item .label {{ font-weight: 600; color: var(--text-muted); margin-bottom: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 B01 + NPS 통합 선정 종목 리포트</h1>
            <p class="subtitle">Buffett Value + Net Purchase Strength with Fibonacci + ATR</p>
            <p class="timestamp">생성일시: {time_str} (KST)</p>
            <div class="badge">B01 버핏 가치전략 + NPS 수급 강도 + Fibonacci + ATR</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card primary">
                <div class="label">총 선정 종목</div>
                <div class="value">{len(stocks)}개</div>
            </div>
            <div class="stat-card warning">
                <div class="label">B01 Buffett</div>
                <div class="value">{b01.get("selected_count", 0)}개</div>
            </div>
            <div class="stat-card purple">
                <div class="label">NPS</div>
                <div class="value">{nps.get("selected_count", 0)}개</div>
            </div>
            <div class="stat-card success">
                <div class="label">평균 손익비</div>
                <div class="value">1:{sum(float(s.get("rr_ratio", 0)) for s in stocks)/max(len(stocks),1):.1f}</div>
            </div>
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
        
        function formatNumber(num) {{
            return "₩" + parseFloat(num).toLocaleString("ko-KR", {{maximumFractionDigits: 0}});
        }}
        
        function renderCards() {{
            const grid = document.getElementById("stockGrid");
            stockData.forEach((stock, i) => {{
                const name = stockNames[stock.symbol] || stock.symbol;
                const srcClass = stock.source === "B01_Buffett" ? "b01" : "nps";
                const badge = stock.source === "B01_Buffett" ? "B01" : "NPS";
                
                const card = document.createElement("div");
                card.className = "stock-card " + srcClass;
                card.onclick = () => openModal(stock);
                card.innerHTML = `
                    <div class="stock-header">
                        <div>
                            <div class="stock-name">${{i+1}}. ${{name}}</div>
                            <div class="stock-code">${{stock.symbol}}</div>
                        </div>
                        <div style="text-align: right;">
                            <span class="source-badge ${{srcClass}}">${{badge}}</span>
                            <div class="value-score" style="margin-top: 8px;">${{stock.score}}점</div>
                        </div>
                    </div>
                    <div class="price-row">
                        <div class="price-box current"><div class="label">현재가</div><div class="value">${{formatNumber(stock.current_price)}}</div></div>
                        <div class="price-box target"><div class="label">목표가</div><div class="value" style="color: var(--success)">${{formatNumber(stock.target_price)}}</div></div>
                        <div class="price-box stop"><div class="label">손절가</div><div class="value" style="color: var(--danger)">${{formatNumber(stock.stop_loss)}}</div></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="rr-badge">손익비 1:${{parseFloat(stock.rr_ratio).toFixed(2)}}</span>
                        <span style="color: var(--text-muted); font-size: 0.9rem;">수익 +${{parseFloat(stock.expected_return).toFixed(1)}}%</span>
                    </div>
                    <div class="fib-info">
                        <span class="fib-tag">Fib ${{stock.fib_level}}</span>
                        <span class="fib-tag">ATR ${{formatNumber(stock.atr)}}</span>
                    </div>
                    <div style="text-align: center; margin-top: 15px; color: var(--text-muted); font-size: 0.85rem;">📊 클릭하여 상세 정보 및 차트 보기</div>
                `;
                grid.appendChild(card);
            }});
        }}
        
        function openModal(stock) {{
            const modal = document.getElementById("stockModal");
            const body = document.getElementById("modalBody");
            const name = stockNames[stock.symbol] || stock.symbol;
            const src = stock.source === "B01_Buffett" ? "B01 Buffett" : "NPS";
            
            body.innerHTML = `
                <div class="modal-header">
                    <div class="modal-title">${{name}} (${{stock.symbol}})</div>
                    <div class="modal-subtitle">${{src}} | 점수: ${{stock.score}}</div>
                </div>
                <div class="detail-grid">
                    <div class="detail-item"><div class="label">현재가</div><div class="value">${{formatNumber(stock.current_price)}}</div></div>
                    <div class="detail-item"><div class="label">목표가</div><div class="value" style="color: var(--success);">${{formatNumber(stock.target_price)}}</div></div>
                    <div class="detail-item"><div class="label">손절가</div><div class="value" style="color: var(--danger);">${{formatNumber(stock.stop_loss)}}</div></div>
                    <div class="detail-item"><div class="label">손익비</div><div class="value" style="color: var(--primary);">1:${{parseFloat(stock.rr_ratio).toFixed(2)}}</div></div>
                    <div class="detail-item"><div class="label">예상수익</div><div class="value" style="color: var(--success);">+${{parseFloat(stock.expected_return).toFixed(1)}}%</div></div>
                    <div class="detail-item"><div class="label">Fibonacci</div><div class="value">${{stock.fib_level}}</div></div>
                    <div class="detail-item"><div class="label">ATR</div><div class="value">${{formatNumber(stock.atr)}}</div></div>
                </div>
                <div class="tradingview-widget-container">
                    <div id="tv_chart"></div>
                </div>
            `;
            
            modal.style.display = "block";
            
            setTimeout(() => {{
                new TradingView.widget({{
                    "width": "100%", "height": 500, "symbol": "KRX:" + stock.symbol,
                    "interval": "D", "timezone": "Asia/Seoul", "theme": "dark",
                    "style": "1", "locale": "kr", "toolbar_bg": "#f1f3f6",
                    "enable_publishing": false, "hide_top_toolbar": false,
                    "hide_legend": false, "save_image": false,
                    "container_id": "tv_chart",
                    "studies": ["RSI@tv-basicstudies", "MACD@tv-basicstudies"],
                    "show_popup_button": true, "popup_width": "1000", "popup_height": "650"
                }});
            }}, 100);
        }}
        
        function closeModal() {{
            document.getElementById("stockModal").style.display = "none";
        }}
        
        window.onclick = function(e) {{
            if (e.target === document.getElementById("stockModal")) closeModal();
        }};
        
        document.addEventListener("DOMContentLoaded", renderCards);
    </script>
    
    <footer style="text-align: center; padding: 40px; color: var(--text-muted); border-top: 1px solid var(--border); margin-top: 40px;">
        <p>B01 + NPS Integrated Strategy Report | TradingView Charts</p>
        <p style="font-size: 0.9rem;">본 리포트는 투자 참고 자료입니다.</p>
    </footer>
</body>
</html>"""

if __name__ == "__main__":
    main()
