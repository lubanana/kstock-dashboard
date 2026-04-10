#!/usr/bin/env python3
"""
TradingView 차트 - Python 통합 모듈
====================================
Python에서 TV 차트를 생성하고 HTML 리포트로 출력

사용법:
    from tv_charts_integration import TVChartGenerator
    
    generator = TVChartGenerator()
    html = generator.create_chart(stock_data)
    generator.save_report(html, 'report.html')
"""

import json
from datetime import datetime
from typing import List, Dict, Optional


class TVChartGenerator:
    """TradingView 차트 생성기"""
    
    CDN_URL = "https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"
    
    def __init__(self, theme='dark', width=800, height=400):
        self.theme = theme
        self.width = width
        self.height = height
        self.colors = self._get_theme_colors()
    
    def _get_theme_colors(self) -> Dict:
        """테마 색상 가져오기"""
        themes = {
            'dark': {
                'bg': '#131722',
                'text': '#d1d4dc',
                'grid': '#2a2e39',
                'up': '#26a69a',
                'down': '#ef5350',
            },
            'light': {
                'bg': '#ffffff',
                'text': '#333333',
                'grid': '#e0e0e0',
                'up': '#26a69a',
                'down': '#ef5350',
            }
        }
        return themes.get(self.theme, themes['dark'])
    
    def convert_krx_data(self, df_records: List[Dict]) -> List[Dict]:
        """
        KRX 데이터를 TV 차트 형식으로 변환
        
        Args:
            df_records: [{'date': '2026-04-09', 'open': 100, 'high': 105, ...}, ...]
        
        Returns:
            TV 차트 형식: [{'time': '20260409', 'open': 100, ...}, ...]
        """
        converted = []
        for record in df_records:
            converted.append({
                'time': record['date'].replace('-', ''),
                'open': float(record['open']),
                'high': float(record['high']),
                'low': float(record['low']),
                'close': float(record['close']),
            })
        return converted
    
    def create_chart(self, 
                     data: List[Dict],
                     container_id: str = 'chart',
                     entry_price: Optional[float] = None,
                     target_price: Optional[float] = None,
                     stop_price: Optional[float] = None) -> str:
        """
        차트 HTML/JS 생성
        
        Args:
            data: OHLCV 데이터 리스트
            container_id: 차트 컨테이너 ID
            entry_price: 진입가 (선택)
            target_price: 목표가 (선택)
            stop_price: 손절가 (선택)
        
        Returns:
            HTML + JavaScript 코드
        """
        c = self.colors
        chart_data = json.dumps(data)
        
        # 가격 라인 설정
        price_lines = []
        if entry_price:
            price_lines.append({
                'price': entry_price,
                'color': '#ffd700',
                'title': f'Entry {entry_price:,.0f}',
            })
        if target_price:
            change = ((target_price / entry_price - 1) * 100) if entry_price else 0
            price_lines.append({
                'price': target_price,
                'color': '#26a69a',
                'title': f'Target {target_price:,.0f} (+{change:.1f}%)',
            })
        if stop_price:
            change = ((stop_price / entry_price - 1) * 100) if entry_price else 0
            price_lines.append({
                'price': stop_price,
                'color': '#ef5350',
                'title': f'Stop {stop_price:,.0f} ({change:.1f}%)',
            })
        
        price_lines_js = json.dumps(price_lines)
        
        html = f'''
<div id="{container_id}" style="width: {self.width}px; height: {self.height}px;"></div>

<script>
(function() {{
    const chartData = {chart_data};
    const priceLines = {price_lines_js};
    
    const chart = LightweightCharts.createChart(
        document.getElementById('{container_id}'),
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
            width: {self.width},
            height: {self.height},
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
    
    // 가격 라인 추가
    priceLines.forEach(function(line) {{
        candleSeries.createPriceLine({{
            price: line.price,
            color: line.color,
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: line.title,
        }});
    }});
    
    chart.timeScale().fitContent();
}})();
</script>
'''
        return html
    
    def create_full_html(self,
                        charts_data: List[Dict],
                        title: str = "Stock Charts") -> str:
        """
        전체 HTML 문서 생성
        
        Args:
            charts_data: [{'code': '005930', 'name': '삼성전자', 'data': [...], 'entry': 70200}, ...]
            title: 페이지 제목
        
        Returns:
            완전한 HTML 문서
        """
        c = self.colors
        
        charts_html = ""
        for i, stock in enumerate(charts_data):
            chart_js = self.create_chart(
                data=stock['data'],
                container_id=f"chart-{i}",
                entry_price=stock.get('entry'),
                target_price=stock.get('target'),
                stop_price=stock.get('stop'),
            )
            
            charts_html += f'''
            <div class="stock-card">
                <div class="stock-header">
                    <span class="stock-name">{stock.get('name', 'Unknown')}</span>
                    <span class="stock-code">{stock['code']}</span>
                </div>
                {chart_js}
            </div>
            '''
        
        full_html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="{self.CDN_URL}"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {c['bg']};
            color: {c['text']};
            padding: 20px;
            margin: 0;
        }}
        .header {{
            text-align: center;
            padding: 20px;
            border-bottom: 1px solid {c['grid']};
            margin-bottom: 30px;
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
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid {c['grid']};
        }}
        .stock-name {{
            font-size: 18px;
            font-weight: bold;
        }}
        .stock-code {{
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    {charts_html}
</body>
</html>'''
        
        return full_html
    
    def save_report(self, html_content: str, filename: str):
        """HTML 리포트 저장"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ 리포트 저장 완료: {filename}")


# 사용 예시
if __name__ == '__main__':
    # 샘플 데이터
    sample_data = [
        {'time': '20260401', 'open': 65000, 'high': 66500, 'low': 64500, 'close': 66000},
        {'time': '20260402', 'open': 66000, 'high': 67800, 'low': 65500, 'close': 67500},
        {'time': '20260403', 'open': 67500, 'high': 68200, 'low': 66800, 'close': 67000},
        {'time': '20260404', 'open': 67000, 'high': 69500, 'low': 66500, 'close': 69000},
        {'time': '20260407', 'open': 69000, 'high': 71200, 'low': 68500, 'close': 70800},
        {'time': '20260408', 'open': 70800, 'high': 72500, 'low': 70200, 'close': 72000},
        {'time': '20260409', 'open': 72000, 'high': 73500, 'low': 71500, 'close': 73000},
    ]
    
    # 차트 생성기 초기화
    generator = TVChartGenerator(theme='dark', width=700, height=350)
    
    # 개별 차트 HTML 생성
    chart_html = generator.create_chart(
        data=sample_data,
        container_id='my-chart',
        entry_price=70200,
        target_price=85000,
        stop_price=62000,
    )
    
    # 전체 리포트 생성
    full_html = generator.create_full_html(
        charts_data=[{
            'code': '005930',
            'name': '삼성전자',
            'data': sample_data,
            'entry': 70200,
            'target': 85000,
            'stop': 62000,
        }],
        title='Sample Chart Report'
    )
    
    # 저장
    generator.save_report(full_html, 'tv_chart_sample.html')
