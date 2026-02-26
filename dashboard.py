#!/usr/bin/env python3
"""
KStock Dashboard - Web Server
한국 주식 스캔 결과 대시보드
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from datetime import datetime

BASE_PATH = '/home/programs/kstock_analyzer'
PORT = 8888


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        if self.path == '/':
            self.serve_dashboard()
        elif self.path == '/api/data':
            self.serve_api()
        else:
            self.send_error(404)
    
    def serve_dashboard(self):
        html = self.generate_html()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def serve_api(self):
        data = self.load_all_data()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def load_all_data(self):
        data = {
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'kospi': {},
            'kosdaq': {},
            'alerts': []
        }
        
        try:
            with open(f'{BASE_PATH}/data/kospi_analysis.csv', 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    headers = lines[0].strip().split(',')
                    values = lines[1].strip().split(',')
                    data['kospi']['summary'] = dict(zip(headers, values))
        except:
            pass
        
        try:
            with open(f'{BASE_PATH}/data/livermore_breakouts.json', 'r') as f:
                data['kospi']['livermore'] = json.load(f)
        except:
            data['kospi']['livermore'] = {'stocks': []}
        
        try:
            with open(f'{BASE_PATH}/data/oneil_volume_breakouts.json', 'r') as f:
                data['kospi']['oneil'] = json.load(f)
        except:
            data['kospi']['oneil'] = {'stocks': []}
        
        try:
            with open(f'{BASE_PATH}/data/minervini_vcp.json', 'r') as f:
                data['kospi']['minervini'] = json.load(f)
        except:
            data['kospi']['minervini'] = {'stocks': []}
        
        try:
            with open(f'{BASE_PATH}/data/kosdaq_scan_results.json', 'r') as f:
                data['kosdaq'] = json.load(f)
        except:
            data['kosdaq'] = {'results': {'livermore': [], 'oneil': [], 'minervini': []}}
        
        return data
    
    def generate_html(self):
        data = self.load_all_data()
        kospi = data['kospi'].get('summary', {})
        
        html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f7fa; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { text-align: center; margin-bottom: 30px; }
        h1 { font-size: 2.5em; margin-bottom: 10px; color: #2c3e50; }
        .timestamp { color: #95a5a6; font-size: 0.9em; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h3 { margin-bottom: 15px; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .stock-item { padding: 12px; border-bottom: 1px solid #ecf0f1; }
        .stock-item:last-child { border-bottom: none; }
        .stock-name { font-weight: bold; color: #2c3e50; }
        .stock-info { color: #7f8c8d; font-size: 0.9em; margin-top: 5px; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; }
        .badge-success { background: #d4edda; color: #155724; }
        .badge-warning { background: #fff3cd; color: #856404; }
        .kospi-summary { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 30px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin-top: 20px; }
        .metric { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 8px; }
        .metric-value { font-size: 1.5em; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; font-size: 0.85em; margin-top: 5px; }
        footer { text-align: center; padding: 20px; color: #95a5a6; font-size: 0.9em; }
        .empty { color: #95a5a6; text-align: center; padding: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 KStock Dashboard</h1>
            <p class="timestamp">최종 업데이트: """ + data['last_updated'] + """</p>
        </header>
        
        <div class="kospi-summary">
            <h2>KOSPI 요약</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">""" + str(kospi.get('close', '-')) + """</div>
                    <div class="metric-label">현재가</div>
                </div>
                <div class="metric">
                    <div class="metric-value">""" + str(kospi.get('change_pct', '-')) + """%</div>
                    <div class="metric-label">등락률</div>
                </div>
                <div class="metric">
                    <div class="metric-value">""" + str(kospi.get('rsi', '-')) + """</div>
                    <div class="metric-label">RSI</div>
                </div>
                <div class="metric">
                    <div class="metric-value">""" + str(kospi.get('trend', '-')) + """</div>
                    <div class="metric-label">추세</div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🎯 리버모어 (52주 신고가)</h3>
                """ + self.generate_stock_list(data['kospi'].get('livermore', {}).get('stocks', [])) + """
            </div>
            <div class="card">
                <h3>📊 오닐 (거래량 폭발)</h3>
                """ + self.generate_stock_list(data['kospi'].get('oneil', {}).get('stocks', [])) + """
            </div>
            <div class="card">
                <h3>📉 미너비니 (VCP)</h3>
                """ + self.generate_stock_list(data['kospi'].get('minervini', {}).get('stocks', [])) + """
            </div>
        </div>
        
        <footer>
            <p>📊 매일 오전 7:00 자동 갱신 | KOSPI & KOSDAQ</p>
        </footer>
    </div>
    <script>setTimeout(function(){location.reload();},60000);</script>
</body>
</html>"""
        return html
    
    def generate_stock_list(self, stocks):
        if not stocks:
            return '<div class="empty">발굴된 종목이 없습니다</div>'
        
        html = ''
        for s in stocks[:5]:
            html += f'<div class="stock-item">'
            html += f'<div class="stock-name">{s.get("name", s.get("symbol", ""))}</div>'
            html += f'<div class="stock-info">'
            html += f'<span class="badge badge-success">{s.get("price", 0):,.0f}원</span>'
            html += f'<span class="badge badge-warning">점수: {s.get("score", 0)}</span>'
            html += f'</div></div>'
        return html


def run_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"🚀 KStock Dashboard 서버 시작")
    print(f"📊 http://0.0.0.0:{port}")
    print(f"📊 http://localhost:{port}")
    print(f"\nCtrl+C로 종료\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ 서버 종료")
        server.shutdown()


if __name__ == "__main__":
    run_server()
