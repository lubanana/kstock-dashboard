#!/usr/bin/env python3
"""
Jesse Livermore Strategy Report Generator with Interactive Charts
제시 리버모어 전략 리포트 생성기 - 종목 클릭 시 차트 보기 기능
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import FinanceDataReader as fdr


class LivermoreReportGenerator:
    """리버모어 전략 리포트 생성기 (차트 기능 포함)"""
    
    def __init__(self):
        self.results = []
        self.scan_date = None
    
    def load_data(self):
        """스캔 결과 로드"""
        try:
            with open('data/livermore_scan_results.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.scan_date = data.get('scan_date', datetime.now().strftime('%Y-%m-%d'))
                self.results = data.get('stocks', [])
                
            df = pd.DataFrame(self.results)
            print(f"✅ 데이터 로드: {len(df)}개 신호")
            return df
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def generate_chart_data_js(self, df):
        """차트 데이터 JavaScript 생성"""
        js_entries = []
        
        for _, row in df.iterrows():
            code = row['code']
            name = row['name']
            
            try:
                # 데이터 수집 (최근 60일)
                end = datetime.now()
                start = end - timedelta(days=60)
                data_df = fdr.DataReader(code, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
                
                if data_df is None or len(data_df) < 20:
                    continue
                
                # OHLCV 데이터 변환
                dates = [d.strftime('%Y-%m-%d') for d in data_df.index]
                closes = [round(p, 0) for p in data_df['Close'].tolist()]
                high_20 = data_df['High'].rolling(20).max().tolist()
                high_20_clean = [round(h, 0) if pd.notna(h) else None for h in high_20]
                
                entry = float(row['entry_1'])
                stop = float(row['stop_loss'])
                
                entry_js = {
                    'name': name,
                    'code': code,
                    'dates': dates,
                    'prices': closes,
                    'high20': high_20_clean,
                    'entry': entry,
                    'stop': stop,
                    'score': float(row['score']),
                    'signal': row['signal_grade']
                }
                js_entries.append(f"'{code}': {json.dumps(entry_js, ensure_ascii=False)}")
            except Exception as e:
                continue
        
        return ',\n        '.join(js_entries)
    
    def generate_html(self, df):
        """HTML 리포트 생성"""
        
        total = len(df)
        strong_buy = len(df[df['signal_grade'] == 'STRONG_BUY'])
        buy = len(df[df['signal_grade'] == 'BUY'])
        kospi_count = len(df[df['market'] == 'KOSPI'])
        kosdaq_count = len(df[df['market'] == 'KOSDAQ'])
        
        top50 = df.head(50)
        scan_date = self.scan_date or datetime.now().strftime('%Y-%m-%d')
        
        # 테이블 행 생성
        table_rows = []
        for i, (_, row) in enumerate(top50.iterrows(), 1):
            if row['signal_grade'] == 'STRONG_BUY':
                badge = '<span class="badge badge-strong">강력매수</span>'
                score_class = 'score-high'
            else:
                badge = '<span class="badge badge-buy">매수</span>'
                score_class = 'score-medium'
            
            row_html = f"""<tr class="clickable" onclick="openChart('{row['code']}')">
                            <td>{i}</td>
                            <td><strong>{row['name']}</strong><br><small>{row['code']}</small></td>
                            <td>{badge}</td>
                            <td class="{score_class}">{row['score']:.1f}</td>
                            <td class="price">{row['current_price']:,.0f}</td>
                            <td>{row['volume_ratio']:.1f}x</td>
                            <td class="price">{row['entry_1']:,.0f}</td>
                            <td class="price" style="color:#ff6b6b">{row['stop_loss']:,.0f}</td>
                        </tr>"""
            table_rows.append(row_html)
        
        table_html = '\n'.join(table_rows)
        chart_data_js = self.generate_chart_data_js(df)
        
        html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jesse Livermore Strategy Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            color: #333;
        }}
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
        }}
        @media (min-width: 768px) {{
            .container {{
                max-width: 1400px;
                border-radius: 20px;
                margin: 20px auto;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 2rem 1rem;
            text-align: center;
        }}
        .header h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
        .header p {{ font-size: 1rem; opacity: 0.9; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.8rem;
            padding: 1.2rem;
            background: #f8f9fa;
        }}
        @media (min-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(4, 1fr); gap: 1.2rem; padding: 1.5rem; }}
        }}
        .stat-card {{
            background: white;
            padding: 1.2rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{ color: #2a5298; font-size: 2rem; margin-bottom: 0.3rem; }}
        .stat-card.strong {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; }}
        .stat-card.strong h3 {{ color: white; }}
        .section {{ padding: 1.5rem; }}
        .badge {{
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-strong {{ background: #ff6b6b; color: white; }}
        .badge-buy {{ background: #2ed573; color: white; }}
        .table-container {{
            overflow-x: auto;
            margin: 1rem 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            min-width: 800px;
            border-collapse: collapse;
            font-size: 0.85rem;
            background: white;
        }}
        th {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 1rem 0.5rem;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        td {{ padding: 0.8rem 0.5rem; border-bottom: 1px solid #eee; }}
        tr.clickable {{ cursor: pointer; transition: background 0.2s; }}
        tr.clickable:hover {{ background: #e3f2fd; }}
        .price {{ text-align: right; font-family: monospace; }}
        .score-high {{ color: #ff6b6b; font-weight: bold; }}
        .score-medium {{ color: #2ed573; font-weight: bold; }}
        
        /* 모달 */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.7);
        }}
        .modal-content {{
            background-color: white;
            margin: 3% auto;
            padding: 20px;
            border-radius: 15px;
            width: 95%;
            max-width: 900px;
            max-height: 90vh;
            overflow-y: auto;
        }}
        @media (max-width: 768px) {{
            .modal-content {{ margin: 0; width: 100%; height: 100%; max-height: 100vh; border-radius: 0; }}
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }}
        .modal-title {{ font-size: 1.5rem; font-weight: 700; color: #1e3c72; }}
        .close {{ color: #aaa; font-size: 28px; font-weight: bold; cursor: pointer; }}
        .close:hover {{ color: #ff6b6b; }}
        .chart-container {{ position: relative; height: 400px; margin: 20px 0; }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        .info-item {{ text-align: center; }}
        .info-label {{ font-size: 0.8rem; color: #666; margin-bottom: 5px; }}
        .info-value {{ font-size: 1.2rem; font-weight: 700; color: #1e3c72; }}
        .footer {{ background: #f8f9fa; padding: 1.5rem; text-align: center; color: #666; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 Livermore Strategy Report</h1>
            <p>Jesse Livermore Pivot Point Analysis</p>
            <p style="opacity:0.8;font-size:0.9rem">Scan Date: {scan_date}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{total}</h3>
                <p>총 신호</p>
            </div>
            <div class="stat-card strong">
                <h3>{strong_buy}</h3>
                <p>강력매수</p>
            </div>
            <div class="stat-card">
                <h3>{kospi_count}</h3>
                <p>KOSPI</p>
            </div>
            <div class="stat-card">
                <h3>{kosdaq_count}</h3>
                <p>KOSDAQ</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 TOP 50 Signals (클릭하여 차트 보기)</h2>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>종목</th>
                            <th>등급</th>
                            <th>점수</th>
                            <th>현재가</th>
                            <th>거래량</th>
                            <th>1차진입</th>
                            <th>손절가</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_html}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div id="chartModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title" id="modalTitle">종목 차트</div>
                    <span class="close" onclick="closeModal()">&times;</span>
                </div>
                
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">현재가</div>
                        <div class="info-value" id="infoPrice">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">점수</div>
                        <div class="info-value" id="infoScore">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">등급</div>
                        <div class="info-value" id="infoSignal">-</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="stockChart"></canvas>
                </div>
                
                <div style="background:#f0f4f8;padding:15px;border-radius:10px;margin-top:15px;">
                    <h4 style="color:#1e3c72;margin-bottom:10px;">📊 전략 정보</h4>
                    <ul style="margin-left:20px;line-height:1.8;">
                        <li><strong>1차 진입가:</strong> <span id="infoEntry">-</span></li>
                        <li><strong>손절가 (-10%):</strong> <span id="infoStop" style="color:#ff6b6b">-</span></li>
                        <li><strong>2차 진입가 (+5%):</strong> <span id="infoEntry2">-</span></li>
                        <li><strong>3차 진입가 (+10%):</strong> <span id="infoEntry3">-</span></li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 KStock Analyzer | Jesse Livermore Strategy</p>
            <p>⚠️ 본 리포트는 투자 참고용입니다.</p>
        </div>
    </div>
    
    <script>
        const chartData = {{
        {chart_data_js}
        }};
        
        let currentChart = null;
        
        function openChart(code) {{
            const data = chartData[code];
            if (!data) {{
                alert('차트 데이터를 불러올 수 없습니다.');
                return;
            }}
            
            document.getElementById('modalTitle').textContent = data.name + ' (' + code + ')';
            document.getElementById('infoPrice').textContent = data.entry.toLocaleString() + '원';
            document.getElementById('infoScore').textContent = data.score.toFixed(1);
            document.getElementById('infoSignal').textContent = data.signal;
            document.getElementById('infoEntry').textContent = data.entry.toLocaleString() + '원';
            document.getElementById('infoStop').textContent = data.stop.toLocaleString() + '원';
            document.getElementById('infoEntry2').textContent = Math.round(data.entry * 1.05).toLocaleString() + '원';
            document.getElementById('infoEntry3').textContent = Math.round(data.entry * 1.1025).toLocaleString() + '원';
            
            document.getElementById('chartModal').style.display = 'block';
            document.body.style.overflow = 'hidden';
            
            drawChart(data);
        }}
        
        function closeModal() {{
            document.getElementById('chartModal').style.display = 'none';
            document.body.style.overflow = 'auto';
            if (currentChart) {{ currentChart.destroy(); }}
        }}
        
        function drawChart(data) {{
            const ctx = document.getElementById('stockChart').getContext('2d');
            if (currentChart) {{ currentChart.destroy(); }}
            
            const entryLine = new Array(data.dates.length).fill(data.entry);
            const stopLine = new Array(data.dates.length).fill(data.stop);
            
            currentChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: data.dates,
                    datasets: [{{
                        label: '종가',
                        data: data.prices,
                        borderColor: '#2a5298',
                        backgroundColor: 'rgba(42, 82, 152, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1,
                        pointRadius: 0
                    }}, {{
                        label: '20일 최고가',
                        data: data.high20,
                        borderColor: '#ffa502',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false
                    }}, {{
                        label: '1차 진입가',
                        data: entryLine,
                        borderColor: '#2ed573',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    }}, {{
                        label: '손절가',
                        data: stopLine,
                        borderColor: '#ff6b6b',
                        borderWidth: 2,
                        borderDash: [10, 5],
                        pointRadius: 0,
                        fill: false
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ intersect: false, mode: 'index' }},
                    plugins: {{
                        legend: {{ position: 'top' }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.parsed.y.toLocaleString() + '원';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 8 }} }},
                        y: {{
                            ticks: {{ callback: function(value) {{ return value.toLocaleString(); }} }}
                        }}
                    }}
                }}
            }});
        }}
        
        window.onclick = function(event) {{
            if (event.target == document.getElementById('chartModal')) closeModal();
        }}
        document.addEventListener('keydown', function(e) {{ if (e.key === 'Escape') closeModal(); }});
    </script>
</body>
</html>'''
        
        return html_content
    
    def generate_report(self):
        """리포트 생성"""
        print("="*70)
        print("📝 Livermore Strategy Report Generator (with Charts)")
        print("="*70)
        
        df = self.load_data()
        if df.empty:
            print("❌ 스캔 데이터가 없습니다.")
            return False
        
        print("\n🌐 HTML 리포트 생성 중...")
        html = self.generate_html(df)
        
        output_file = 'docs/livermore_report.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 리포트: {output_file}")
        
        print("\n" + "="*70)
        print(f"총 신호: {len(df)}개")
        print(f"강력매수: {len(df[df['signal_grade']=='STRONG_BUY'])}개")
        print(f"매수: {len(df[df['signal_grade']=='BUY'])}개")
        print("="*70)
        
        return True


if __name__ == '__main__':
    generator = LivermoreReportGenerator()
    success = generator.generate_report()
    if success:
        print("\n🌐 https://lubanana.github.io/kstock-dashboard/livermore_report.html")
