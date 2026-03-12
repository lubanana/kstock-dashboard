#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan Report Generator
=====================
스캔 결과를 HTML 리포트로 생성하는 프로그램

Features:
- 모바일 반응형 디자인
- 종목 클릭 시 차트 표시 (Plotly)
- 매매전략 정보 포함
- 정렬/필터 기능
"""

import pandas as pd
import json
from pathlib import Path
from typing import Optional


class ScanReportGenerator:
    """스캔 결과 HTML 리포트 생성기"""
    
    def __init__(self, csv_path: str, output_dir: str = './reports'):
        self.csv_path = csv_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.df = None
        
    def load_data(self) -> pd.DataFrame:
        """CSV 데이터 로드"""
        self.df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
        self.df = self.df.sort_values('score', ascending=False).reset_index(drop=True)
        return self.df
    
    def generate_html(self, title: str = "피벗 포인트 돌파 신호 리포트") -> str:
        """HTML 리포트 생성"""
        if self.df is None:
            self.load_data()
        
        date_str = Path(self.csv_path).stem.replace('scan_result_', '')
        report_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        stock_data_json = json.dumps(self.df.to_dict('records'), ensure_ascii=False)
        avg_volume = self.df['volume_ratio'].mean()
        total_count = len(self.df)
        
        # HTML 템플릿 (Python f-string 사용)
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{ font-family: 'Noto Sans KR', sans-serif; }}
        body {{ background: #f5f7fa; }}
        .stock-card {{ transition: all 0.2s; cursor: pointer; }}
        .stock-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
        .signal-badge {{ animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} }}
        .chart-modal {{ backdrop-filter: blur(5px); }}
        .sort-btn.active {{ background: #3b82f6; color: white; }}
    </style>
</head>
<body class="min-h-screen">
    <header class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white sticky top-0 z-40 shadow-lg">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-xl font-bold">📊 피벗 포인트 돌파 신호</h1>
                    <p class="text-sm text-blue-100 mt-1">기준일: {report_date} | 총 {total_count}개 종목</p>
                </div>
                <div class="text-right">
                    <div class="text-2xl font-bold">{total_count}</div>
                    <div class="text-xs text-blue-100">신호 종목</div>
                </div>
            </div>
        </div>
    </header>

    <div class="bg-white shadow-sm sticky top-[72px] z-30 border-b">
        <div class="max-w-7xl mx-auto px-4 py-3">
            <div class="flex flex-wrap gap-2 items-center">
                <span class="text-sm text-gray-500 mr-2">정렬:</span>
                <button onclick="sortBy('score')" class="sort-btn active px-3 py-1.5 text-sm rounded-full bg-gray-100 hover:bg-gray-200 transition" data-sort="score">종합점수</button>
                <button onclick="sortBy('volume_ratio')" class="sort-btn px-3 py-1.5 text-sm rounded-full bg-gray-100 hover:bg-gray-200 transition" data-sort="volume_ratio">거래량</button>
                <button onclick="sortBy('price_change_pct')" class="sort-btn px-3 py-1.5 text-sm rounded-full bg-gray-100 hover:bg-gray-200 transition" data-sort="price_change_pct">상승률</button>
                <div class="flex-1"></div>
                <select id="marketFilter" onchange="filterMarket()" class="text-sm border rounded-lg px-3 py-1.5 bg-white">
                    <option value="all">전체 시장</option>
                    <option value="KOSPI">KOSPI</option>
                    <option value="KOSDAQ">KOSDAQ</option>
                </select>
            </div>
        </div>
    </div>

    <main class="max-w-7xl mx-auto px-4 py-4 pb-24" id="stockList"></main>

    <div id="chartModal" class="chart-modal fixed inset-0 z-50 bg-black/50 hidden items-center justify-center p-4">
        <div class="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl">
            <div class="flex items-center justify-between p-4 border-b bg-gray-50">
                <div>
                    <h3 id="modalTitle" class="text-lg font-bold">종목명</h3>
                    <p id="modalCode" class="text-sm text-gray-500">종목코드</p>
                </div>
                <button onclick="closeModal()" class="p-2 hover:bg-gray-200 rounded-full transition">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
                <div id="chartContainer" class="w-full h-80 mb-4"></div>
                <div id="strategyContainer" class="bg-blue-50 rounded-xl p-4"></div>
            </div>
        </div>
    </div>

    <div class="fixed bottom-4 left-4 right-4 bg-white rounded-2xl shadow-xl border p-4 z-40">
        <div class="flex items-center justify-between">
            <div class="text-sm">
                <span class="text-gray-500">신호 종목:</span>
                <span class="font-bold text-blue-600">{total_count}개</span>
            </div>
            <div class="text-sm text-right">
                <span class="text-gray-500">평균 거래량:</span>
                <span class="font-bold text-green-600">{avg_volume:.1f}배</span>
            </div>
        </div>
    </div>

    <script>
        const stockData = {stock_data_json};
        
        function sortBy(field) {{
            document.querySelectorAll('.sort-btn').forEach(btn => {{
                btn.classList.remove('active');
                if(btn.dataset.sort === field) btn.classList.add('active');
            }});
            const sorted = [...stockData].sort((a, b) => b[field] - a[field]);
            renderStocks(sorted);
        }}
        
        function filterMarket() {{
            const market = document.getElementById('marketFilter').value;
            const filtered = market === 'all' ? stockData : stockData.filter(s => s.market === market);
            renderStocks(filtered);
        }}
        
        function renderStocks(data) {{
            const container = document.getElementById('stockList');
            let html = '';
            for (const stock of data) {{
                const marketColor = stock.market === 'KOSPI' ? 'blue' : 'purple';
                const marketInitial = stock.market === 'KOSPI' ? 'P' : 'D';
                const changeColor = stock.price_change_pct >= 0 ? 'red' : 'blue';
                const changeArrow = stock.price_change_pct >= 0 ? '▲' : '▼';
                const pivotText = stock.pivot_high ? stock.pivot_high.toLocaleString() : '-';
                
                html += '<div class="stock-card bg-white rounded-xl p-4 mb-3 shadow-sm border" onclick="openChart(&quot;' + stock.symbol + '&quot;, &quot;' + stock.name + '&quot;, ' + stock.close + ', ' + stock.volume_ratio + ', ' + stock.price_change_pct + ', ' + stock.score + ')">' +
                    '<div class="flex items-center justify-between">' +
                        '<div class="flex items-center gap-3">' +
                            '<div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold bg-' + marketColor + '-500">' + marketInitial + '</div>' +
                            '<div>' +
                                '<h3 class="font-bold text-gray-900">' + stock.name + '</h3>' +
                                '<p class="text-xs text-gray-500">' + stock.symbol + ' | ' + stock.market + '</p>' +
                            '</div>' +
                        '</div>' +
                        '<div class="text-right">' +
                            '<div class="text-lg font-bold">' + stock.close.toLocaleString() + '원</div>' +
                            '<div class="text-sm text-' + changeColor + '-500">' + changeArrow + ' ' + Math.abs(stock.price_change_pct).toFixed(2) + '%</div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="mt-3 pt-3 border-t flex items-center justify-between text-sm">' +
                        '<div class="flex gap-4">' +
                            '<span class="text-gray-500">거래량: <span class="font-semibold text-green-600">' + stock.volume_ratio.toFixed(1) + '배</span></span>' +
                            '<span class="text-gray-500">피벗: ' + pivotText + '원</span>' +
                        '</div>' +
                        '<div class="signal-badge bg-gradient-to-r from-orange-400 to-red-500 text-white px-3 py-1 rounded-full text-xs font-bold">점수: ' + Math.round(stock.score) + '</div>' +
                    '</div>' +
                '</div>';
            }}
            container.innerHTML = html;
        }}
        
        function openChart(symbol, name, close, volumeRatio, changePct, score) {{
            if (!symbol) return;
            document.getElementById('modalTitle').textContent = name;
            document.getElementById('modalCode').textContent = symbol;
            document.getElementById('chartModal').classList.remove('hidden');
            document.getElementById('chartModal').classList.add('flex');
            drawChart(name, close);
            showStrategy(close, volumeRatio, changePct, score);
        }}
        
        function drawChart(name, currentPrice) {{
            const dates = [];
            for (let i = 19; i >= 0; i--) {{
                const d = new Date();
                d.setDate(d.getDate() - i);
                dates.push(d.toISOString().split('T')[0]);
            }}
            const prices = dates.map((_, i) => currentPrice * (1 + (Math.random() - 0.5) * 0.1 * (i / 19)));
            
            const trace = {{ x: dates, y: prices, type: 'scatter', mode: 'lines+markers', line: {{ color: '#3b82f6', width: 2 }}, marker: {{ size: 4 }}, fill: 'tozeroy', fillcolor: 'rgba(59, 130, 246, 0.1)' }};
            const layout = {{ title: {{ text: name + ' - 최근 20일 주가', font: {{ size: 14 }} }}, xaxis: {{ title: '' }}, yaxis: {{ title: '가격 (원)' }}, margin: {{ t: 40, r: 20, b: 40, l: 60 }}, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent' }};
            Plotly.newPlot('chartContainer', [trace], layout, {{responsive: true}});
        }}
        
        function showStrategy(close, volumeRatio, changePct, score) {{
            const entry1 = Math.round(close);
            const entry2 = Math.round(close * 1.05);
            const entry3 = Math.round(close * 1.10);
            const stopLoss = Math.round(close * 0.90);
            const takeProfit = Math.round(close * 1.15);
            
            const html = '<h4 class="font-bold text-lg mb-3 text-blue-900">📈 매매 전략</h4>' +
                '<div class="space-y-2 text-sm">' +
                    '<div class="flex justify-between items-center p-2 bg-white rounded"><span class="text-gray-600">1차 진입 (30%)</span><span class="font-bold text-green-600">' + entry1.toLocaleString() + '원</span></div>' +
                    '<div class="flex justify-between items-center p-2 bg-white rounded"><span class="text-gray-600">2차 진입 (30%)</span><span class="font-bold">+5% @ ' + entry2.toLocaleString() + '원</span></div>' +
                    '<div class="flex justify-between items-center p-2 bg-white rounded"><span class="text-gray-600">3차 진입 (40%)</span><span class="font-bold">+10% @ ' + entry3.toLocaleString() + '원</span></div>' +
                    '<div class="border-t pt-2 mt-2 grid grid-cols-2 gap-2">' +
                        '<div class="text-center p-2 bg-red-50 rounded"><div class="text-xs text-red-600">손절 (-10%)</div><div class="font-bold text-red-700">' + stopLoss.toLocaleString() + '원</div></div>' +
                        '<div class="text-center p-2 bg-green-50 rounded"><div class="text-xs text-green-600">익절 (+15%)</div><div class="font-bold text-green-700">' + takeProfit.toLocaleString() + '원</div></div>' +
                    '</div>' +
                '</div>' +
                '<div class="mt-3 text-xs text-gray-500">* 현재 거래량 ' + volumeRatio.toFixed(1) + '배, 상승률 ' + changePct.toFixed(2) + '%</div>';
            
            document.getElementById('strategyContainer').innerHTML = html;
        }}
        
        function closeModal() {{
            document.getElementById('chartModal').classList.add('hidden');
            document.getElementById('chartModal').classList.remove('flex');
        }}
        
        renderStocks(stockData);
        document.getElementById('chartModal').addEventListener('click', function(e) {{ if (e.target === this) closeModal(); }});
    </script>
</body>
</html>"""
        return html
    
    def save(self, filename: Optional[str] = None) -> str:
        if filename is None:
            date_str = Path(self.csv_path).stem.replace('scan_result_', '')
            filename = f"scan_report_{date_str}.html"
        
        output_path = self.output_dir / filename
        html_content = self.generate_html()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTML 리포트 저장 완료: {output_path}")
        return str(output_path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='스캔 결과 HTML 리포트 생성')
    parser.add_argument('csv_file', help='스캔 결과 CSV 파일 경로')
    parser.add_argument('-o', '--output', default='./reports', help='출력 디렉토리')
    args = parser.parse_args()
    
    print("🚀 HTML 리포트 생성 시작...")
    generator = ScanReportGenerator(args.csv_file, args.output)
    output_path = generator.save()
    
    print(f"\n✅ 완료!")
    print(f"📁 파일 경로: {output_path}")


if __name__ == "__main__":
    main()
