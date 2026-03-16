#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monthly Report Generator - All Stocks View (Simplified)
=======================================================
날짜 선택 없이 전체 종목을 표시하는 월별 리포트 생성기
"""

import pandas as pd
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
from fdr_wrapper import FDRWrapper


class MonthlyReportGenerator:
    def __init__(self, scan_data_dir='./data/daily_scans', output_dir='./reports'):
        self.scan_data_dir = Path(scan_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.all_data = []
        self.dates = []
        
    def load_monthly_scans(self, year, month):
        pattern = f"scan_{year}-{month:02d}-*.csv"
        csv_files = sorted(self.scan_data_dir.glob(pattern))
        
        if not csv_files:
            print(f"⚠️ {year}년 {month}월 데이터 없음")
            return pd.DataFrame()
        
        for csv_file in csv_files:
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            date = csv_file.stem.replace('scan_', '')
            self.dates.append(date)
            self.all_data.append(df)
            print(f"📊 {date}: {len(df)}개")
        
        combined = pd.concat(self.all_data, ignore_index=True)
        combined = combined.sort_values('score', ascending=False)
        return combined
    
    def collect_price_data(self, df):
        print("\n📈 가격 데이터 수집 중...")
        unique_symbols = df[['symbol', 'name']].drop_duplicates()
        total = len(unique_symbols)
        price_data = {}
        
        with FDRWrapper() as fdr:
            for idx, row in unique_symbols.iterrows():
                symbol, name = row['symbol'], row['name']
                print(f"  [{idx+1}/{total}] {symbol}...", end=' ')
                
                try:
                    symbol_scans = df[df['symbol'] == symbol]
                    earliest_scan = symbol_scans['scan_date'].min()
                    latest_scan = symbol_scans['scan_date'].max()
                    
                    start_date = earliest_scan
                    end_date = (datetime.strptime(latest_scan, '%Y-%m-%d') + 
                               timedelta(days=60)).strftime('%Y-%m-%d')
                    
                    price_df = fdr.get_price(symbol, start_date, end_date)
                    
                    if not price_df.empty:
                        price_list = []
                        for date_idx, price_row in price_df.iterrows():
                            price_list.append({
                                'date': date_idx.strftime('%Y-%m-%d'),
                                'close': float(price_row['close']),
                                'open': float(price_row['open']),
                                'high': float(price_row['high']),
                                'low': float(price_row['low']),
                                'volume': int(price_row['volume'])
                            })
                        price_data[symbol] = price_list
                        print(f"✅ {len(price_list)}일")
                    else:
                        print("⚠️ 없음")
                except Exception as e:
                    print(f"❌ {e}")
        
        print(f"\n✅ 수집 완료: {len(price_data)}개 종목")
        return price_data
    
    def generate_html(self, year, month, title=None):
        df = self.load_monthly_scans(year, month)
        if df.empty:
            return "<h1>데이터 없음</h1>"
        
        price_data = self.collect_price_data(df)
        
        if title is None:
            title = f"{year}년 {month}월 피벗 돌파 신호"
        
        all_stocks = []
        for _, row in df.iterrows():
            all_stocks.append(row.to_dict())
        
        stocks_json = json.dumps(all_stocks, ensure_ascii=False)
        price_json = json.dumps(price_data, ensure_ascii=False)
        
        stocks_b64 = base64.b64encode(stocks_json.encode('utf-8')).decode('ascii')
        price_b64 = base64.b64encode(price_json.encode('utf-8')).decode('ascii')
        
        date_range = f"{min(self.dates)} ~ {max(self.dates)}" if self.dates else f"{year}-{month:02d}"
        
        return self._build_html(title, year, month, date_range, len(df), df['volume_ratio'].mean(), stocks_b64, price_b64)
    
    def _build_html(self, title, year, month, date_range, total_count, avg_volume, stocks_b64, price_b64):
        return f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{ font-family: 'Noto Sans KR', sans-serif; }}
        body {{ background: #f5f7fa; }}
        .stock-card {{ transition: all 0.2s; cursor: pointer; }}
        .stock-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
        .chart-modal {{ backdrop-filter: blur(5px); }}
        .fade-in {{ animation: fadeIn 0.3s ease-in; }}
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    </style>
</head>
<body class="min-h-screen">
    <header class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white sticky top-0 z-40 shadow-lg">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-xl font-bold">📅 {year}년 {month}월 피벗 돌파 신호</h1>
                    <p class="text-sm text-blue-100 mt-1">기간: {date_range} | 총 {total_count}개 신호</p>
                </div>
                <div class="text-right">
                    <div class="text-2xl font-bold">{total_count}</div>
                    <div class="text-xs text-blue-100">전체 신호</div>
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-4 pb-24" id="stockList">
        <div class="text-center py-12 text-gray-500">데이터 로딩 중...</div>
    </main>

    <div id="chartModal" class="chart-modal fixed inset-0 z-50 bg-black/50 hidden items-center justify-center p-4">
        <div class="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl">
            <div class="flex items-center justify-between p-4 border-b bg-gray-50">
                <div>
                    <h3 id="modalTitle" class="text-lg font-bold">종목명</h3>
                    <p id="modalCode" class="text-sm text-gray-500">종목코드</p>
                    <p id="modalScanDate" class="text-xs text-blue-600 mt-1">스캔일: -</p>
                </div>
                <button onclick="closeModal()" class="p-2 hover:bg-gray-200 rounded-full transition">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
                <div class="bg-blue-50 rounded-xl p-4 mb-4">
                    <div class="grid grid-cols-3 gap-4 text-center">
                        <div><div class="text-xs text-gray-500">스캔 당시 종가</div><div id="modalClose" class="text-lg font-bold text-blue-700">-</div></div>
                        <div><div class="text-xs text-gray-500">거래량 비율</div><div id="modalVolume" class="text-lg font-bold text-green-600">-</div></div>
                        <div><div class="text-xs text-gray-500">점수</div><div id="modalScore" class="text-lg font-bold text-orange-600">-</div></div>
                    </div>
                </div>
                <div class="bg-white rounded-xl border p-4 mb-4">
                    <h4 class="font-bold mb-3 text-gray-800">📈 실제 주가 추이 (스캔일부터)</h4>
                    <div id="chartContainer" class="w-full h-80"></div>
                </div>
                <div id="strategyContainer" class="bg-gray-50 rounded-xl p-4"></div>
            </div>
        </div>
    </div>

    <div class="fixed bottom-4 left-4 right-4 bg-white rounded-2xl shadow-xl border p-4 z-40">
        <div class="flex items-center justify-between">
            <div class="text-sm"><span class="text-gray-500">총 신호:</span><span class="font-bold text-blue-600"> {total_count}개</span></div>
            <div class="text-sm text-right"><span class="text-gray-500">평균 거래량:</span><span class="font-bold text-green-600"> {avg_volume:.1f}배</span></div>
        </div>
    </div>

    <script>
        const allStocks = JSON.parse(atob('{stocks_b64}'));
        const priceData = JSON.parse(atob('{price_b64}'));

        function renderStocks() {{
            const container = document.getElementById('stockList');
            if (allStocks.length === 0) {{
                container.innerHTML = '<div class="text-center py-12 text-gray-500">신호가 없습니다</div>';
                return;
            }}
            
            let html = '<div class="fade-in">';
            for (const stock of allStocks) {{
                const marketColor = stock.market === 'KOSPI' ? 'blue' : 'purple';
                const marketInitial = stock.market === 'KOSPI' ? 'P' : 'D';
                const changeColor = stock.price_change_pct >= 0 ? 'red' : 'blue';
                const changeArrow = stock.price_change_pct >= 0 ? '▲' : '▼';
                
                html += '<div class="stock-card bg-white rounded-xl p-4 mb-3 shadow-sm border" onclick="openChart(\'' + stock.symbol + '\', \'' + stock.name + '\', \'' + stock.scan_date + '\', ' + stock.close + ', ' + stock.volume_ratio + ', ' + stock.price_change_pct + ', ' + stock.score + ', \'' + stock.market + '\')">' +
                    '<div class="flex items-center justify-between">' +
                        '<div class="flex items-center gap-3">' +
                            '<div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold bg-' + marketColor + '-500">' + marketInitial + '</div>' +
                            '<div>' +
                                '<div class="flex items-center"><span class="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded mr-2">' + stock.scan_date + '</span><h3 class="font-bold text-gray-900">' + stock.name + '</h3></div>' +
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
                        '</div>' +
                        '<div class="bg-gradient-to-r from-orange-400 to-red-500 text-white px-3 py-1 rounded-full text-xs font-bold">점수: ' + Math.round(stock.score) + '</div>' +
                    '</div>' +
                '</div>';
            }}
            html += '</div>';
            container.innerHTML = html;
        }}

        function openChart(symbol, name, scanDate, close, volumeRatio, changePct, score, market) {{
            document.getElementById('modalTitle').textContent = name;
            document.getElementById('modalCode').textContent = symbol + ' | ' + market;
            document.getElementById('modalScanDate').textContent = '스캔일: ' + scanDate;
            document.getElementById('modalClose').textContent = close.toLocaleString() + '원';
            document.getElementById('modalVolume').textContent = volumeRatio.toFixed(1) + '배';
            document.getElementById('modalScore').textContent = Math.round(score);
            
            document.getElementById('chartModal').classList.remove('hidden');
            document.getElementById('chartModal').classList.add('flex');
            
            drawRealChart(symbol, name, scanDate, close);
            showStrategy(close, volumeRatio, changePct);
        }}

        function drawRealChart(symbol, name, scanDate, scanPrice) {{
            const prices = priceData[symbol];
            if (!prices || prices.length === 0) {{
                document.getElementById('chartContainer').innerHTML = '<div class="text-center py-12 text-gray-500">가격 데이터를 불러올 수 없습니다</div>';
                return;
            }}
            
            const scanIdx = prices.findIndex(p => p.date >= scanDate);
            const chartData = scanIdx >= 0 ? prices.slice(scanIdx) : prices;
            
            const dates = chartData.map(p => p.date);
            const closes = chartData.map(p => p.close);
            const finalPrice = closes[closes.length - 1];
            const returnPct = ((finalPrice - scanPrice) / scanPrice * 100).toFixed(2);
            const color = finalPrice >= scanPrice ? '#22c55e' : '#ef4444';
            
            const trace = {{
                x: dates,
                y: closes,
                type: 'scatter',
                mode: 'lines',
                line: {{ color: color, width: 2 }},
                fill: 'tozeroy',
                fillcolor: finalPrice >= scanPrice ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                name: '종가',
                hovertemplate: '%{{x}}<br>%{{y:,}}원<extra></extra>'
            }};
            
            const scanLine = {{
                x: [scanDate, scanDate],
                y: [Math.min(...closes) * 0.98, Math.max(...closes) * 1.02],
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#f97316', width: 2, dash: 'dash' }},
                name: '스캔일',
                hoverinfo: 'skip'
            }};
            
            const layout = {{
                title: {{ text: name + ' (' + symbol + ') - 실제 주가 추이', font: {{ size: 14 }} }},
                xaxis: {{ title: '', tickangle: -45, nticks: 8 }},
                yaxis: {{ title: '가격 (원)', tickformat: ',' }},
                margin: {{ t: 50, r: 50, b: 80, l: 80 }},
                showlegend: true,
                legend: {{ orientation: 'h', y: -0.15 }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                annotations: [{{
                    x: scanDate, y: scanPrice, xref: 'x', yref: 'y',
                    text: '스캔: ' + scanPrice.toLocaleString() + '원',
                    showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 2,
                    arrowcolor: '#f97316', ax: -50, ay: -40
                }}, {{
                    x: dates[dates.length - 1], y: finalPrice, xref: 'x', yref: 'y',
                    text: finalPrice.toLocaleString() + '원 (' + (returnPct >= 0 ? '+' : '') + returnPct + '%)',
                    showarrow: true, arrowhead: 2, arrowsize: 1, arrowwidth: 2,
                    arrowcolor: color, ax: 50, ay: returnPct >= 0 ? -40 : 40
                }}]
            }};
            
            Plotly.newPlot('chartContainer', [trace, scanLine], layout, {{responsive: true}});
        }}

        function showStrategy(close, volumeRatio, changePct) {{
            const entry1 = Math.round(close);
            const entry2 = Math.round(close * 1.05);
            const entry3 = Math.round(close * 1.10);
            const stopLoss = Math.round(close * 0.90);
            const takeProfit = Math.round(close * 1.15);
            
            document.getElementById('strategyContainer').innerHTML = 
                '<h4 class="font-bold text-lg mb-3">📈 매매 전략</h4>' +
                '<div class="grid grid-cols-2 gap-2 text-sm">' +
                    '<div class="bg-white p-2 rounded"><span class="text-gray-500">1차 진입:</span> <span class="font-bold text-green-600">' + entry1.toLocaleString() + '원</span></div>' +
                    '<div class="bg-white p-2 rounded"><span class="text-gray-500">2차 진입:</span> <span class="font-bold">' + entry2.toLocaleString() + '원 (+5%)</span></div>' +
                    '<div class="bg-white p-2 rounded"><span class="text-gray-500">3차 진입:</span> <span class="font-bold">' + entry3.toLocaleString() + '원 (+10%)</span></div>' +
                    '<div class="bg-red-50 p-2 rounded text-center"><span class="text-red-600 text-xs">손절</span><br><span class="font-bold text-red-700">' + stopLoss.toLocaleString() + '원</span></div>' +
                    '<div class="bg-green-50 p-2 rounded text-center"><span class="text-green-600 text-xs">익절</span><br><span class="font-bold text-green-700">' + takeProfit.toLocaleString() + '원</span></div>' +
                '</div>' +
                '<div class="mt-2 text-xs text-gray-500">거래량 ' + volumeRatio.toFixed(1) + '배 | 당일 상승률 ' + changePct.toFixed(2) + '%</div>';
        }}

        function closeModal() {{
            document.getElementById('chartModal').classList.add('hidden');
            document.getElementById('chartModal').classList.remove('flex');
        }}

        renderStocks();
        document.getElementById('chartModal').addEventListener('click', function(e) {{ if (e.target === this) closeModal(); }});
    </script>
</body>
</html>'''

    def save(self, year, month):
        filename = f"daily_{year}{month:02d}.html"
        output_path = self.output_dir / filename
        html_content = self.generate_html(year, month)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n📄 저장 완료: {output_path}")
        return str(output_path)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='월별 전체 종목 리포트 생성')
    parser.add_argument('--year', type=int, default=2026)
    parser.add_argument('--month', type=int, default=1)
    parser.add_argument('-o', '--output', default='./reports')
    args = parser.parse_args()
    
    print(f"🚀 {args.year}년 {args.month}월 리포트 생성...")
    generator = MonthlyReportGenerator(output_dir=args.output)
    generator.save(args.year, args.month)
    print("\n✅ 완료!")


if __name__ == "__main__":
    main()
