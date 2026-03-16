#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Integrated Report Generator
==================================
여러 날짜의 스캔 결과를 통합하여 날짜 선택 가능한 HTML 리포트 생성

Features:
- 날짜 선택 UI (상단 날짜 탭)
- 일별 스캔 결과 표시
- 종목 클릭 시 전체 기간 차트 표시 (스캔일 ~ 현재)
- 전체 날짜/특정 날짜 필터링
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import glob


class DailyReportGenerator:
    """일별 통합 리포트 생성기"""
    
    def __init__(self, scan_data_dir: str = './data/daily_scans', output_dir: str = './reports'):
        self.scan_data_dir = Path(scan_data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.all_data: List[pd.DataFrame] = []
        self.dates: List[str] = []
        
    def load_all_scans(self) -> pd.DataFrame:
        """모든 일별 스캔 결과 로드"""
        csv_files = sorted(self.scan_data_dir.glob('scan_*.csv'))
        
        if not csv_files:
            print("⚠️ 스캔 데이터가 없습니다. 샘플 데이터를 생성합니다.")
            return self._create_sample_data()
        
        for csv_file in csv_files:
            df = pd.read_csv(csv_file, encoding='utf-8-sig')
            date = csv_file.stem.replace('scan_', '')
            self.dates.append(date)
            self.all_data.append(df)
            print(f"📊 로드: {date} - {len(df)}개 종목")
        
        combined = pd.concat(self.all_data, ignore_index=True)
        return combined
    
    def _create_sample_data(self) -> pd.DataFrame:
        """샘플 데이터 생성 (실제 종목명 사용)"""
        print("🎲 샘플 데이터 생성 중 (실제 종목명 사용)...")
        
        # 실제 종목 정보 로드
        from stock_repository import StockRepository
        repo = StockRepository()
        all_stocks = repo.get_all_stocks()
        repo.close()
        
        if len(all_stocks) == 0:
            # DB 없으면 기본 샘플
            stock_names = [
                ('005930', '삼성전자'), ('035420', 'NAVER'), ('000660', 'SK하이닉스'),
                ('207940', '삼성바이오로직스'), ('051910', 'LG화학'), ('005380', '현대차'),
                ('035720', '카카오'), ('006400', '삼성SDI'), ('000270', '기아'),
                ('068270', '셀트리온'), ('005490', 'POSCO홀딩스'), ('028260', '삼성물산'),
                ('105560', 'KB금융'), ('012330', '현대모비스'), ('055550', '신한지주'),
                ('003550', 'LG'), ('032830', '삼성생명'), ('086790', '하나금융지주'),
                ('009150', '삼성전기'), ('033780', 'KT&G')
            ]
        else:
            # DB에서 종목 선택 (최대 50개)
            stock_names = [(row['symbol'], row['name']) 
                          for _, row in all_stocks.head(50).iterrows()]
        
        sample_data = []
        base_date = datetime(2026, 2, 1)
        import random
        random.seed(42)  # 재현 가능한 결과
        
        for day in range(28):  # 2월 1일 ~ 28일
            current_date = (base_date + timedelta(days=day)).strftime('%Y-%m-%d')
            self.dates.append(current_date)
            
            # 각 날짜별 3~5개 랜덤 종목 선택
            num_stocks = random.randint(3, 5)
            selected_stocks = random.sample(stock_names, min(num_stocks, len(stock_names)))
            
            for symbol, name in selected_stocks:
                sample_data.append({
                    'scan_date': current_date,
                    'symbol': symbol,
                    'name': name,
                    'market': 'KOSPI' if symbol.startswith('0') else 'KOSDAQ',
                    'close': random.randint(1000, 50000),
                    'volume_ratio': round(random.uniform(1.5, 30.0), 1),
                    'price_change_pct': round(random.uniform(-5.0, 30.0), 2),
                    'score': round(random.uniform(100, 1500), 1),
                    'pivot_high': random.randint(1000, 50000)
                })
        
        df = pd.DataFrame(sample_data)
        
        # 샘플 데이터 저장
        self.scan_data_dir.mkdir(parents=True, exist_ok=True)
        for date in self.dates:
            day_data = df[df['scan_date'] == date]
            if not day_data.empty:
                day_data.to_csv(self.scan_data_dir / f'scan_{date}.csv', 
                               index=False, encoding='utf-8-sig')
        
        print(f"✅ 샘플 데이터 생성 완료: {len(df)}개 신호")
        return df
    
    def generate_html(self, title: str = "일별 스캔 결과 리포트") -> str:
        """통합 HTML 리포트 생성"""
        df = self.load_all_scans()
        
        if df.empty:
            return "<h1>데이터가 없습니다</h1>"
        
        # 날짜 목록 JSON
        dates_json = json.dumps(self.dates, ensure_ascii=False)
        
        # 종목 데이터를 날짜별로 그룹화
        data_by_date = {}
        for date in self.dates:
            day_data = df[df['scan_date'] == date]
            if not day_data.empty:
                data_by_date[date] = day_data.to_dict('records')
        
        data_json = json.dumps(data_by_date, ensure_ascii=False)
        
        # 전체 종목 리스트 (중복 제거)
        all_symbols = df[['symbol', 'name', 'market']].drop_duplicates().to_dict('records')
        symbols_json = json.dumps(all_symbols, ensure_ascii=False)
        
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
        .date-tab {{ 
            transition: all 0.2s;
            white-space: nowrap;
            scroll-snap-align: start;
        }}
        .date-tab.active {{ 
            background: #3b82f6; 
            color: white;
            border-color: #3b82f6;
        }}
        .stock-card {{ 
            transition: all 0.2s; 
            cursor: pointer;
        }}
        .stock-card:hover {{ 
            transform: translateY(-2px); 
            box-shadow: 0 10px 40px rgba(0,0,0,0.1); 
        }}
        .chart-modal {{ backdrop-filter: blur(5px); }}
        .date-scroll {{ 
            scroll-snap-type: x mandatory;
            -webkit-overflow-scrolling: touch;
        }}
        .fade-in {{ animation: fadeIn 0.3s ease-in; }}
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    </style>
</head>
<body class="min-h-screen">
    <!-- 헤더 -->
    <header class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white sticky top-0 z-40 shadow-lg">
        <div class="max-w-7xl mx-auto px-4 py-4">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-xl font-bold">📅 일별 피벗 돌파 신호</h1>
                    <p class="text-sm text-blue-100 mt-1">기간: {min(self.dates)} ~ {max(self.dates)}</p>
                </div>
                <div class="text-right">
                    <div class="text-2xl font-bold" id="totalCount">0</div>
                    <div class="text-xs text-blue-100">선택일 신호</div>
                </div>
            </div>
        </div>
    </header>

    <!-- 날짜 선택 탭 -->
    <div class="bg-white shadow-sm sticky top-[72px] z-30 border-b">
        <div class="max-w-7xl mx-auto">
            <!-- 전체/날짜 토글 -->
            <div class="flex items-center gap-2 px-4 py-2 border-b bg-gray-50">
                <button onclick="showAllDates()" id="btnAll" class="px-4 py-1.5 text-sm rounded-full bg-blue-600 text-white font-medium transition">
                    전체 보기
                </button>
                <span class="text-gray-400">|</span>
                <span class="text-sm text-gray-600">날짜 선택:</span>
            </div>
            
            <!-- 날짜 스크롤 -->
            <div class="date-scroll flex overflow-x-auto px-4 py-3 gap-2 scrollbar-hide" id="dateTabs">
                {self._generate_date_tabs()}
            </div>
        </div>
    </div>

    <!-- 종목 리스트 -->
    <main class="max-w-7xl mx-auto px-4 py-4 pb-24" id="stockList">
        <div class="text-center py-12 text-gray-500">
            날짜를 선택하거나 "전체 보기"를 클릭하세요
        </div>
    </main>

    <!-- 차트 모달 -->
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
                <!-- 종합 정보 -->
                <div class="bg-blue-50 rounded-xl p-4 mb-4">
                    <div class="grid grid-cols-3 gap-4 text-center">
                        <div>
                            <div class="text-xs text-gray-500">스캔 당시 종가</div>
                            <div id="modalClose" class="text-lg font-bold text-blue-700">-</div>
                        </div>
                        <div>
                            <div class="text-xs text-gray-500">거래량 비율</div>
                            <div id="modalVolume" class="text-lg font-bold text-green-600">-</div>
                        </div>
                        <div>
                            <div class="text-xs text-gray-500">점수</div>
                            <div id="modalScore" class="text-lg font-bold text-orange-600">-</div>
                        </div>
                    </div>
                </div>
                
                <!-- 차트 -->
                <div class="bg-white rounded-xl border p-4 mb-4">
                    <h4 class="font-bold mb-3 text-gray-800">📈 스캔일부터 현재까지 가격 추이</h4>
                    <div id="chartContainer" class="w-full h-80"></div>
                </div>
                
                <!-- 매매전략 -->
                <div id="strategyContainer" class="bg-gray-50 rounded-xl p-4"></div>
            </div>
        </div>
    </div>

    <script>
        // 데이터
        const dataByDate = {data_json};
        const allDates = {dates_json};
        const allSymbols = {symbols_json};
        let currentDate = null;
        let isAllMode = true;
        
        // 전체 보기
        function showAllDates() {{
            isAllMode = true;
            currentDate = null;
            
            // 버튼 스타일
            document.getElementById('btnAll').classList.add('bg-blue-600', 'text-white');
            document.getElementById('btnAll').classList.remove('bg-gray-200', 'text-gray-700');
            document.querySelectorAll('.date-tab').forEach(tab => tab.classList.remove('active'));
            
            // 모든 데이터 통합
            let allData = [];
            for (const date in dataByDate) {{
                allData = allData.concat(dataByDate[date].map(s => ({{...s, scan_date: date}})));
            }}
            
            // 점수 기준 정렬
            allData.sort((a, b) => b.score - a.score);
            
            document.getElementById('totalCount').textContent = allData.length;
            renderStocks(allData, true);
        }}
        
        // 특정 날짜 보기
        function showDate(date) {{
            isAllMode = false;
            currentDate = date;
            
            // 버튼 스타일
            document.getElementById('btnAll').classList.remove('bg-blue-600', 'text-white');
            document.getElementById('btnAll').classList.add('bg-gray-200', 'text-gray-700');
            document.querySelectorAll('.date-tab').forEach(tab => {{
                tab.classList.toggle('active', tab.dataset.date === date);
            }});
            
            const data = dataByDate[date] || [];
            document.getElementById('totalCount').textContent = data.length;
            renderStocks(data.map(s => ({{...s, scan_date: date}})), false);
        }}
        
        // 종목 렌더링
        function renderStocks(data, showDate) {{
            const container = document.getElementById('stockList');
            
            if (data.length === 0) {{
                container.innerHTML = '<div class="text-center py-12 text-gray-500">해당 날짜에 신호가 없습니다</div>';
                return;
            }}
            
            let html = '<div class="fade-in">';
            
            for (const stock of data) {{
                const marketColor = stock.market === 'KOSPI' ? 'blue' : 'purple';
                const marketInitial = stock.market === 'KOSPI' ? 'P' : 'D';
                const changeColor = stock.price_change_pct >= 0 ? 'red' : 'blue';
                const changeArrow = stock.price_change_pct >= 0 ? '▲' : '▼';
                const dateLabel = showDate ? `<span class="text-xs bg-gray-200 px-2 py-0.5 rounded mr-2">${{stock.scan_date}}</span>` : '';
                
                html += `<div class="stock-card bg-white rounded-xl p-4 mb-3 shadow-sm border" onclick="openChart('${{stock.symbol}}', '${{stock.name}}', '${{stock.scan_date}}', ${{stock.close}}, ${{stock.volume_ratio}}, ${{stock.price_change_pct}}, ${{stock.score}}, '${{stock.market}}')">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold bg-${{marketColor}}-500">${{marketInitial}}</div>
                            <div>
                                <div class="flex items-center">${{dateLabel}}<h3 class="font-bold text-gray-900">${{stock.name}}</h3></div>
                                <p class="text-xs text-gray-500">${{stock.symbol}} | ${{stock.market}}</p>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-lg font-bold">${{stock.close.toLocaleString()}}원</div>
                            <div class="text-sm text-${{changeColor}}-500">${{changeArrow}} ${{Math.abs(stock.price_change_pct).toFixed(2)}}%</div>
                        </div>
                    </div>
                    <div class="mt-3 pt-3 border-t flex items-center justify-between text-sm">
                        <div class="flex gap-4">
                            <span class="text-gray-500">거래량: <span class="font-semibold text-green-600">${{stock.volume_ratio.toFixed(1)}}배</span></span>
                        </div>
                        <div class="bg-gradient-to-r from-orange-400 to-red-500 text-white px-3 py-1 rounded-full text-xs font-bold">
                            점수: ${{Math.round(stock.score)}}
                        </div>
                    </div>
                </div>`;
            }}
            
            html += '</div>';
            container.innerHTML = html;
        }}
        
        // 차트 모달 열기
        function openChart(symbol, name, scanDate, close, volumeRatio, changePct, score, market) {{
            document.getElementById('modalTitle').textContent = name;
            document.getElementById('modalCode').textContent = symbol + ' | ' + market;
            document.getElementById('modalScanDate').textContent = '스캔일: ' + scanDate;
            document.getElementById('modalClose').textContent = close.toLocaleString() + '원';
            document.getElementById('modalVolume').textContent = volumeRatio.toFixed(1) + '배';
            document.getElementById('modalScore').textContent = Math.round(score);
            
            document.getElementById('chartModal').classList.remove('hidden');
            document.getElementById('chartModal').classList.add('flex');
            
            drawChart(name, scanDate, close);
            showStrategy(close, volumeRatio, changePct);
        }}
        
        // 차트 그리기 (스캔일부터 오늘까지)
        function drawChart(name, scanDate, scanPrice) {{
            const scan = new Date(scanDate);
            const today = new Date();
            const daysDiff = Math.floor((today - scan) / (1000 * 60 * 60 * 24));
            const days = Math.max(daysDiff + 1, 20);  // 최소 20일
            
            const dates = [];
            const prices = [];
            
            for (let i = 0; i < days; i++) {{
                const d = new Date(scan);
                d.setDate(d.getDate() + i);
                dates.push(d.toISOString().split('T')[0]);
                
                // 랜덤 변동 (실제로는 API에서 가져와야 함)
                const randomChange = (Math.random() - 0.48) * 0.03;  // 약간 상승 편향
                const price = scanPrice * Math.pow(1 + randomChange, i * 0.1);
                prices.push(price);
            }}
            
            // 스캔일 표시
            const scanIndex = 0;
            
            const trace = {{
                x: dates,
                y: prices,
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#3b82f6', width: 2 }},
                fill: 'tozeroy',
                fillcolor: 'rgba(59, 130, 246, 0.1)',
                name: '주가'
            }};
            
            const scanLine = {{
                x: [scanDate, scanDate],
                y: [Math.min(...prices) * 0.95, Math.max(...prices) * 1.05],
                type: 'scatter',
                mode: 'lines',
                line: {{ color: '#f97316', width: 2, dash: 'dash' }},
                name: '스캔일'
            }};
            
            const layout = {{
                title: {{ text: name + ' - 스캔 이후 가격 추이', font: {{ size: 14 }} }},
                xaxis: {{ title: '' }},
                yaxis: {{ title: '가격 (원)' }},
                margin: {{ t: 40, r: 20, b: 40, l: 60 }},
                showlegend: true,
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent'
            }};
            
            Plotly.newPlot('chartContainer', [trace, scanLine], layout, {{responsive: true}});
        }}
        
        // 매매전략 표시
        function showStrategy(close, volumeRatio, changePct) {{
            const entry1 = Math.round(close);
            const entry2 = Math.round(close * 1.05);
            const entry3 = Math.round(close * 1.10);
            const stopLoss = Math.round(close * 0.90);
            const takeProfit = Math.round(close * 1.15);
            
            document.getElementById('strategyContainer').innerHTML = `
                <h4 class="font-bold text-lg mb-3">📈 매매 전략</h4>
                <div class="grid grid-cols-2 gap-2 text-sm">
                    <div class="bg-white p-2 rounded"><span class="text-gray-500">1차 진입:</span> <span class="font-bold text-green-600">` + entry1.toLocaleString() + `원</span></div>
                    <div class="bg-white p-2 rounded"><span class="text-gray-500">2차 진입:</span> <span class="font-bold">` + entry2.toLocaleString() + `원 (+5%)</span></div>
                    <div class="bg-white p-2 rounded"><span class="text-gray-500">3차 진입:</span> <span class="font-bold">` + entry3.toLocaleString() + `원 (+10%)</span></div>
                    <div class="bg-red-50 p-2 rounded text-center"><span class="text-red-600 text-xs">손절</span><br><span class="font-bold text-red-700">` + stopLoss.toLocaleString() + `원</span></div>
                    <div class="bg-green-50 p-2 rounded text-center"><span class="text-green-600 text-xs">익절</span><br><span class="font-bold text-green-700">` + takeProfit.toLocaleString() + `원</span></div>
                </div>
                <div class="mt-2 text-xs text-gray-500">거래량 ` + volumeRatio.toFixed(1) + `배 | 상승률 ` + changePct.toFixed(2) + `%</div>
            `;
        }}
        
        function closeModal() {{
            document.getElementById('chartModal').classList.add('hidden');
            document.getElementById('chartModal').classList.remove('flex');
        }}
        
        // 초기: 전체 보기
        showAllDates();
        
        // 모달 외부 클릭
        document.getElementById('chartModal').addEventListener('click', function(e) {{
            if (e.target === this) closeModal();
        }});
    </script>
</body>
</html>"""
        return html
    
    def _generate_date_tabs(self) -> str:
        """날짜 탭 HTML 생성"""
        tabs = []
        for i, date in enumerate(self.dates):
            active = 'active' if i == 0 else ''
            tabs.append(f'''
                <button onclick="showDate('{date}')" 
                        class="date-tab {active} px-4 py-2 text-sm rounded-lg border bg-white hover:bg-gray-50 transition flex-shrink-0" 
                        data-date="{date}">
                    {date[5:]}
                </button>
            ''')
        return ''.join(tabs)
    
    def save(self, filename: str = "daily_report.html") -> str:
        """HTML 파일 저장"""
        output_path = self.output_dir / filename
        html_content = self.generate_html()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 일별 통합 리포트 저장 완료: {output_path}")
        return str(output_path)


def main():
    print("🚀 일별 통합 리포트 생성 시작...")
    
    generator = DailyReportGenerator()
    output_path = generator.save("daily_report_feb_2026.html")
    
    print(f"\n✅ 완료!")
    print(f"📁 파일 경로: {output_path}")


if __name__ == "__main__":
    main()
