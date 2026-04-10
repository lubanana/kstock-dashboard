#!/usr/bin/env python3
"""
TradingView 차트 통합 리포트 생성기 v3
======================================
- TP1, TP2, TP3 라벨 사용
- TradingView 날짜 형식 수정
- 네이버증권 링크
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class TVChartReportGenerator:
    """TradingView 차트 리포트 생성기"""
    
    CDN_URL = "https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"
    
    def __init__(self, db_path: str = 'data/level1_prices.db', theme: str = 'dark'):
        self.db_path = db_path
        self.theme = theme
        self.colors = self._get_theme_colors()
    
    def _get_theme_colors(self) -> Dict:
        themes = {
            'dark': {
                'bg': '#131722',
                'card_bg': '#1a1d29',
                'text': '#d1d4dc',
                'grid': '#2a2e39',
                'up': '#26a69a',
                'down': '#ef5350',
                'entry': '#ffd700',
                'tp1': '#4ade80',
                'tp2': '#22c55e', 
                'tp3': '#16a34a',
                'stop': '#ef5350',
                'accent': '#feca57',
            },
        }
        return themes.get(self.theme, themes['dark'])
    
    def get_stock_data(self, code: str, days: int = 90) -> List[Dict]:
        """DB에서 종목 데이터 조회 - TradingView 형식으로 반환"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                """
                SELECT date, open, high, low, close, volume 
                FROM price_data 
                WHERE code = ? AND date <= date('now')
                ORDER BY date DESC 
                LIMIT ?
                """,
                (code, days)
            )
            rows = cursor.fetchall()
            conn.close()
            
            # TradingView format: 'YYYY-MM-DD'
            data = []
            for row in reversed(rows):
                # 날짜가 YYYY-MM-DD 형식인지 확인
                date_str = row[0]
                if len(date_str) == 8 and date_str.isdigit():
                    # YYYYMMDD -> YYYY-MM-DD
                    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                
                data.append({
                    'time': date_str,  # '2026-04-09' 형식
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                })
            return data
        except Exception as e:
            print(f"⚠️ {code} 데이터 조회 실패: {e}")
            return []
    
    def generate_chart_js(self, stock: Dict, container_id: str) -> str:
        """차트 JavaScript 생성"""
        c = self.colors
        code = stock['code']
        
        chart_data = self.get_stock_data(code)
        if not chart_data:
            return f"<div class='no-data'>📊 차트 데이터 준비 중 ({code})</div>"
        
        # 데이터를 JSON으로 직렬화
        data_json = json.dumps(chart_data, ensure_ascii=False)
        
        # 목표가
        targets = stock.get('targets', {})
        entry = targets.get('entry', stock.get('price'))
        stop = targets.get('stop_loss')
        tp1 = targets.get('tp1')
        tp2 = targets.get('tp2')
        tp3 = targets.get('tp3')
        
        # 가격 라인
        price_lines = []
        if entry:
            price_lines.append({'price': entry, 'color': c['entry'], 'title': f'Entry {entry:,.0f}'})
        if tp1:
            price_lines.append({'price': tp1, 'color': c['tp1'], 'title': f'TP1 {tp1:,.0f}'})
        if tp2:
            price_lines.append({'price': tp2, 'color': c['tp2'], 'title': f'TP2 {tp2:,.0f}'})
        if tp3:
            price_lines.append({'price': tp3, 'color': c['tp3'], 'title': f'TP3 {tp3:,.0f}'})
        if stop:
            price_lines.append({'price': stop, 'color': c['stop'], 'title': f'Stop {stop:,.0f}'})
        
        price_lines_js = json.dumps(price_lines, ensure_ascii=False)
        
        return f'''
        <div id="{container_id}" class="chart-wrapper"></div>
        <script>
        (function() {{
            try {{
                const chartData = {data_json};
                const priceLines = {price_lines_js};
                
                const container = document.getElementById('{container_id}');
                if (!container) {{
                    console.error('Chart container not found: {container_id}');
                    return;
                }}
                
                const chart = LightweightCharts.createChart(container, {{
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
                        scaleMargins: {{ top: 0.15, bottom: 0.15 }},
                    }},
                    timeScale: {{
                        borderColor: '{c['grid']}',
                        timeVisible: false,
                        fixLeftEdge: true,
                        fixRightEdge: true,
                    }},
                    crosshair: {{
                        mode: LightweightCharts.CrosshairMode.Normal,
                    }},
                }});
                
                const candleSeries = chart.addCandlestickSeries({{
                    upColor: '{c['up']}',
                    downColor: '{c['down']}',
                    borderVisible: false,
                    wickUpColor: '{c['up']}',
                    wickDownColor: '{c['down']}',
                }});
                
                candleSeries.setData(chartData);
                
                // 가격 라인
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
                
                // 초기 크기
                chart.applyOptions({{
                    width: container.clientWidth || 800,
                    height: 350,
                }});
                
                chart.timeScale().fitContent();
                
                // 리사이즈
                if (typeof ResizeObserver !== 'undefined') {{
                    const resizeObserver = new ResizeObserver(function(entries) {{
                        for (let entry of entries) {{
                            const width = entry.contentRect.width;
                            if (width > 0) {{
                                chart.applyOptions({{ width: width }});
                            }}
                        }}
                    }});
                    resizeObserver.observe(container);
                }}
                
                console.log('✅ Chart loaded: {code}');
            }} catch (e) {{
                console.error('Chart error ({code}):', e);
                document.getElementById('{container_id}').innerHTML = 
                    '<div class="no-data">⚠️ 차트 로딩 오류</div>';
            }}
        }})();
        </script>
        '''
    
    def generate_report(self, scan_data: List[Dict], scan_date: str, 
                       output_dir: str = 'docs') -> str:
        """전체 리포트 HTML 생성"""
        c = self.colors
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M')
        
        total_signals = len(scan_data)
        avg_score = sum(s.get('score', 0) for s in scan_data) / total_signals if total_signals > 0 else 0
        avg_rr = sum(s.get('targets', {}).get('risk_reward_tp2', 0) for s in scan_data) / total_signals if total_signals > 0 else 0
        
        cards_html = ""
        for i, stock in enumerate(scan_data):
            targets = stock.get('targets', {})
            entry = targets.get('entry', stock.get('price', 0))
            stop = targets.get('stop_loss', 0)
            tp1 = targets.get('tp1', 0)
            tp2 = targets.get('tp2', 0)
            tp3 = targets.get('tp3', 0)
            rr = targets.get('risk_reward_tp2', 0)
            stop_pct = targets.get('stop_pct', 0)
            tp2_pct = targets.get('tp2_pct', 0)
            
            naver_link = f"https://finance.naver.com/item/main.naver?code={stock['code']}"
            chart_js = self.generate_chart_js(stock, f"chart-{i}")
            
            cards_html += f'''
            <div class="signal-card">
                <div class="signal-header">
                    <div class="stock-info">
                        <a href="{naver_link}" target="_blank" class="stock-name-link">
                            <span class="stock-name">{stock.get('name', 'Unknown')}</span>
                            <span class="external-link">↗</span>
                        </a>
                        <span class="stock-code">{stock['code']}</span>
                    </div>
                    <div class="stock-score">{stock.get('score', 0)}점</div>
                </div>
                
                <div class="signal-levels">
                    <div class="level-box entry">
                        <span class="level-label">진입가</span>
                        <span class="level-value">{entry:,.0f}</span>
                    </div>
                    <div class="level-box stop">
                        <span class="level-label">손절가</span>
                        <span class="level-value">{stop:,.0f}</span>
                        <span class="level-pct">{stop_pct:.1f}%</span>
                    </div>
                    <div class="level-box tp1">
                        <span class="level-label">TP1</span>
                        <span class="level-value">{tp1:,.0f}</span>
                    </div>
                    <div class="level-box tp2">
                        <span class="level-label">TP2</span>
                        <span class="level-value">{tp2:,.0f}</span>
                        <span class="level-pct">+{tp2_pct:.1f}%</span>
                    </div>
                    <div class="level-box tp3">
                        <span class="level-label">TP3</span>
                        <span class="level-value">{tp3:,.0f}</span>
                    </div>
                    <div class="level-box rr">
                        <span class="level-label">손익비</span>
                        <span class="level-value">1:{rr:.1f}</span>
                    </div>
                </div>
                
                {chart_js}
                
                <div class="signal-reasons">
                    <h4>📋 선정 사유</h4>
                    <div class="reason-tags">
                        {''.join(f'<span class="reason-tag">{reason}</span>' for reason in stock.get('reasons', []))}
                    </div>
                </div>
                
                <div class="signal-actions">
                    <a href="{naver_link}" target="_blank" class="naver-btn">
                        네이버증권에서 보기 ↗
                    </a>
                </div>
            </div>
            '''
        
        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2604+V7 스캔 리포트 - {scan_date}</title>
    <script src="{self.CDN_URL}"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {c['bg']};
            color: {c['text']};
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid {c['grid']};
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 2rem; margin-bottom: 10px; color: {c['accent']}; }}
        .header .date {{ color: #888; font-size: 1rem; }}
        .header .timestamp {{ color: #666; font-size: 0.85rem; margin-top: 5px; }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: {c['card_bg']};
            border: 1px solid {c['grid']};
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        .stat-card h3 {{ color: #888; font-size: 0.8rem; margin-bottom: 8px; }}
        .stat-card .value {{ font-size: 1.6rem; font-weight: bold; color: {c['accent']}; }}
        
        .signal-card {{
            background: {c['card_bg']};
            border: 1px solid {c['grid']};
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        .signal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid {c['grid']};
        }}
        .stock-info {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
        .stock-name-link {{
            text-decoration: none;
            color: inherit;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .stock-name {{ font-size: 1.4rem; font-weight: bold; color: {c['accent']}; }}
        .stock-name-link:hover .stock-name {{ text-decoration: underline; }}
        .external-link {{ font-size: 0.9rem; color: #888; }}
        .stock-code {{ color: #888; font-size: 0.9rem; }}
        .stock-score {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.1rem;
        }}
        
        .signal-levels {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
            margin-bottom: 20px;
        }}
        .level-box {{
            background: rgba(255,255,255,0.05);
            padding: 12px 8px;
            border-radius: 8px;
            text-align: center;
            border-left: 3px solid transparent;
        }}
        .level-box.entry {{ border-left-color: {c['entry']}; }}
        .level-box.stop {{ border-left-color: {c['stop']}; }}
        .level-box.tp1 {{ border-left-color: {c['tp1']}; }}
        .level-box.tp2 {{ border-left-color: {c['tp2']}; }}
        .level-box.tp3 {{ border-left-color: {c['tp3']}; }}
        .level-box.rr {{ border-left-color: {c['accent']}; }}
        .level-label {{ display: block; color: #888; font-size: 0.7rem; margin-bottom: 4px; }}
        .level-value {{ display: block; font-size: 0.95rem; font-weight: bold; }}
        .level-pct {{ display: block; font-size: 0.75rem; margin-top: 2px; }}
        .level-box.stop .level-pct {{ color: {c['stop']}; }}
        .level-box.tp1 .level-pct, .level-box.tp2 .level-pct, .level-box.tp3 .level-pct {{ color: {c['tp2']}; }}
        
        .chart-wrapper {{
            width: 100%;
            height: 350px;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 20px;
            background: {c['bg']};
            min-height: 350px;
        }}
        .no-data {{
            padding: 40px;
            text-align: center;
            color: #888;
            background: rgba(255,255,255,0.02);
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        
        .signal-reasons h4 {{ font-size: 0.9rem; margin-bottom: 12px; color: {c['accent']}; }}
        .reason-tags {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .reason-tag {{
            background: rgba(255,255,255,0.08);
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 0.85rem;
        }}
        
        .signal-actions {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid {c['grid']};
            text-align: right;
        }}
        .naver-btn {{
            display: inline-block;
            background: #03c75a;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        .naver-btn:hover {{ background: #02b350; }}
        
        @media (max-width: 768px) {{
            .signal-levels {{ grid-template-columns: repeat(3, 1fr); }}
            .stats {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        @media (max-width: 480px) {{
            .signal-levels {{ grid-template-columns: repeat(2, 1fr); }}
            .stats {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 2604+V7 통합 스캔 리포트</h1>
            <div class="date">스캔일: {scan_date}</div>
            <div class="timestamp">생성시간: {now.strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>신호 종목</h3>
                <div class="value">{total_signals}개</div>
            </div>
            <div class="stat-card">
                <h3>평균 점수</h3>
                <div class="value">{avg_score:.0f}점</div>
            </div>
            <div class="stat-card">
                <h3>평균 손익비</h3>
                <div class="value">1:{avg_rr:.1f}</div>
            </div>
            <div class="stat-card">
                <h3>데이터 기준</h3>
                <div class="value">{scan_date}</div>
            </div>
        </div>
        
        {cards_html}
    </div>
</body>
</html>'''
        
        filename = f"2604_v7_hybrid_{timestamp}.html"
        filepath = os.path.join(output_dir, filename)
        
        os.makedirs(output_dir, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 리포트 생성: {filepath}")
        return filepath


def main():
    import sys
    
    json_file = 'reports/2604_v7_hybrid_20260409.json'
    if not os.path.exists(json_file):
        print(f"❌ 파일 없음: {json_file}")
        sys.exit(1)
    
    with open(json_file, 'r', encoding='utf-8') as f:
        scan_data = json.load(f)
    
    print(f"📊 {len(scan_data)}개 종목 로드")
    
    generator = TVChartReportGenerator(theme='dark')
    filepath = generator.generate_report(
        scan_data=scan_data,
        scan_date='2026-04-09',
        output_dir='docs'
    )
    
    print(f"\n📁 파일: {filepath}")
    print(f"🔗 https://lubanana.github.io/kstock-dashboard/{os.path.basename(filepath)}")


if __name__ == '__main__':
    main()
