#!/usr/bin/env python3
"""
TradingView 차트 통합 리포트 생성기
===================================
기존 Chart.js 대신 TradingView Lightweight Charts 사용

Features:
- 캔들스틱 차트 (고성능)
- 목표가/손절가 수평선
- 이동평균선 오버레이
- 매수/매도 마커
- 다크/라이트 테마
"""

import json
from datetime import datetime
from typing import List, Dict


class TradingViewReportGenerator:
    """TradingView 차트를 사용하는 리포트 생성기"""
    
    CHART_JS_CDN = "https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"
    
    def __init__(self, theme='dark'):
        self.theme = theme
        self.colors = {
            'dark': {
                'bg': '#131722',
                'text': '#d1d4dc',
                'grid': '#2a2e39',
                'up': '#26a69a',
                'down': '#ef5350',
                'target': '#26a69a',
                'stop': '#ef5350',
                'entry': '#ffd700',
            },
            'light': {
                'bg': '#ffffff',
                'text': '#333333',
                'grid': '#e0e0e0',
                'up': '#26a69a',
                'down': '#ef5350',
                'target': '#22c55e',
                'stop': '#dc2626',
                'entry': '#f59e0b',
            }
        }
    
    def generate_chart_html(self, stock_code: str, stock_data: List[Dict],
                           entry_price: float = None,
                           target_price: float = None,
                           stop_price: float = None) -> str:
        """
        개별 종목 차트 HTML 생성
        
        Args:
            stock_code: 종목코드
            stock_data: OHLCV 데이터 리스트
            entry_price: 진입가 (선택)
            target_price: 목표가 (선택)
            stop_price: 손절가 (선택)
        """
        c = self.colors[self.theme]
        
        # 데이터 변환
        chart_data = json.dumps([
            {
                'time': d['date'].replace('-', ''),
                'open': d['open'],
                'high': d['high'],
                'low': d['low'],
                'close': d['close'],
            }
            for d in stock_data
        ])
        
        # 가격 라인 설정
        price_lines = []
        if entry_price:
            price_lines.append({
                'price': entry_price,
                'color': c['entry'],
                'title': f'Entry {entry_price:,.0f}',
            })
        if target_price:
            price_lines.append({
                'price': target_price,
                'color': c['target'],
                'title': f'Target {target_price:,.0f} (+{((target_price/entry_price-1)*100):.1f}%)',
            })
        if stop_price:
            price_lines.append({
                'price': stop_price,
                'color': c['stop'],
                'title': f'Stop {stop_price:,.0f} ({((stop_price/entry_price-1)*100):.1f}%)',
            })
        
        price_lines_js = json.dumps(price_lines)
        
        html = f'''
        <div id="chart-{stock_code}" class="tv-chart-container"></div>
        
        <script>
        (function() {{
            const chartData = {chart_data};
            const priceLines = {price_lines_js};
            
            const chart = LightweightCharts.createChart(
                document.getElementById('chart-{stock_code}'), 
                {{
                    layout: {{
                        background: {{ type: 'solid', color: '{c['bg']}' }},
                        textColor: '{c['text']}',
                    }},
                    grid: {{
                        vertLines: {{ color: '{c['grid']}' }},
                        horzLines: {{ color: '{c['grid']}' }},
                    }},
                    rightPriceScale: {{
                        borderColor: '{c['grid']}',
                    }},
                    timeScale: {{
                        borderColor: '{c['grid']}',
                        timeVisible: false,
                    }},
                    width: 700,
                    height: 400,
                }}
            );
            
            const candleSeries = chart.addCandlestickSeries({{
                upColor: '{c['up']}',
                downColor: '{c['down']}',
                borderVisible: false,
                wickUpColor: '{c['up']}',
                wickDownColor: '{c['down']}',
            }});
            
            candleSeries.setData(chartData);
            
            // 목표가/손절가 라인 추가
            priceLines.forEach(line => {{
                candleSeries.createPriceLine({{
                    price: line.price,
                    color: line.color,
                    lineWidth: 2,
                    lineStyle: LightweightCharts.LineStyle.Dashed,
                    axisLabelVisible: true,
                    title: line.title,
                }});
            }});
            
            // 차트 영역 자동 조정
            chart.timeScale().fitContent();
            
            // 리사이즈 핸들러
            window.addEventListener('resize', () => {{
                chart.applyOptions({{
                    width: document.getElementById('chart-{stock_code}').clientWidth,
                }});
            }});
        }})();
        </script>
        '''
        return html
    
    def generate_full_report(self, scan_results: List[Dict], title: str = "Stock Scan Report") -> str:
        """전체 리포트 HTML 생성"""
        c = self.colors[self.theme]
        
        # 샘플 데이터 (실제로는 DB에서 가져옴)
        sample_data = [
            {'date': '20260325', 'open': 65000, 'high': 66500, 'low': 64500, 'close': 66000},
            {'date': '20260326', 'open': 66000, 'high': 67800, 'low': 65500, 'close': 67500},
            {'date': '20260327', 'open': 67500, 'high': 68200, 'low': 66800, 'close': 67000},
            {'date': '20260328', 'open': 67000, 'high': 69500, 'low': 66500, 'close': 69000},
            {'date': '20260331', 'open': 69000, 'high': 71200, 'low': 68500, 'close': 70800},
            {'date': '20260401', 'open': 70800, 'high': 72500, 'low': 70200, 'close': 72000},
            {'date': '20260402', 'open': 72000, 'high': 73500, 'low': 71500, 'close': 73000},
            {'date': '20260403', 'open': 73000, 'high': 72800, 'low': 70500, 'close': 71000},
            {'date': '20260404', 'open': 71000, 'high': 71800, 'low': 69800, 'close': 70200},
            {'date': '20260407', 'open': 70200, 'high': 71100, 'low': 69500, 'close': 70800},
            {'date': '20260408', 'open': 70800, 'high': 72000, 'low': 70200, 'close': 71500},
            {'date': '20260409', 'open': 71500, 'high': 73000, 'low': 71000, 'close': 72800},
        ]
        
        # 종목별 차트 생성
        charts_html = ""
        for stock in scan_results[:3]:  # 상위 3개만 예시
            chart = self.generate_chart_html(
                stock['code'],
                sample_data,
                entry_price=stock.get('entry', 70200),
                target_price=stock.get('target'),
                stop_price=stock.get('stop'),
            )
            charts_html += f'''
            <div class="stock-card">
                <div class="stock-header">
                    <span class="stock-name">{stock.get('name', 'Unknown')}</span>
                    <span class="stock-code">{stock['code']}</span>
                    <span class="stock-score">Score: {stock.get('score', 0)}</span>
                </div>
                {chart}
                <div class="stock-levels">
                    <span class="level entry">Entry: {stock.get('entry', 70200):,}</span>
                    <span class="level target">Target: {stock.get('target', 85000):,} (+{(stock.get('target',85000)/stock.get('entry',70200)-1)*100:.1f}%)</span>
                    <span class="level stop">Stop: {stock.get('stop', 62000):,} ({(stock.get('stop',62000)/stock.get('entry',70200)-1)*100:.1f}%)</span>
                </div>
            </div>
            '''
        
        full_html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - TradingView Charts</title>
    <script src="{self.CHART_JS_CDN}"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {c['bg']};
            color: {c['text']};
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            padding: 20px;
            border-bottom: 1px solid {c['grid']};
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header .date {{
            color: #888;
            font-size: 14px;
        }}
        
        .stock-card {{
            background: {c['bg']};
            border: 1px solid {c['grid']};
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        
        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid {c['grid']};
        }}
        
        .stock-name {{
            font-size: 20px;
            font-weight: bold;
        }}
        
        .stock-code {{
            color: #888;
            font-size: 14px;
        }}
        
        .stock-score {{
            background: {c['up']};
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        .tv-chart-container {{
            width: 100%;
            height: 400px;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .stock-levels {{
            display: flex;
            gap: 20px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid {c['grid']};
        }}
        
        .level {{
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
        }}
        
        .level.entry {{
            background: rgba(255, 215, 0, 0.2);
            color: {c['entry']};
        }}
        
        .level.target {{
            background: rgba(38, 166, 154, 0.2);
            color: {c['target']};
        }}
        
        .level.stop {{
            background: rgba(239, 83, 80, 0.2);
            color: {c['stop']};
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 {title}</h1>
        <div class="date">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
    
    {charts_html}
    
    <script>
        // 모든 차트 초기화 완료 로그
        console.log('TradingView charts initialized');
    </script>
</body>
</html>'''
        
        return full_html


# 사용 예시
if __name__ == '__main__':
    # 샘플 데이터
    scan_results = [
        {
            'code': '005930',
            'name': '삼성전자',
            'score': 85,
            'entry': 70200,
            'target': 85000,
            'stop': 62000,
        },
        {
            'code': '000660',
            'name': 'SK하이닉스',
            'score': 78,
            'entry': 185000,
            'target': 220000,
            'stop': 165000,
        },
        {
            'code': '035720',
            'name': '카카오',
            'score': 72,
            'entry': 45000,
            'target': 55000,
            'stop': 39000,
        },
    ]
    
    # 다크 테마 리포트 생성
    generator = TradingViewReportGenerator(theme='dark')
    html_content = generator.generate_full_report(scan_results, "K-Stock Scanner Report")
    
    # 파일 저장
    output_file = 'tradingview_report_sample.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 리포트 생성 완료: {output_file}")
    print(f"📊 샘플 종목: {len(scan_results)}개")
