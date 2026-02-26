#!/usr/bin/env python3
"""
KStock Dashboard Generator
정적 HTML 대시보드 자동 생성기
"""

import json
import os
from datetime import datetime

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = '/home/programs/kstock_analyzer/docs'


class DashboardGenerator:
    """대시보드 HTML 생성기"""
    
    def __init__(self):
        self.data = self.load_all_data()
        os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    def load_all_data(self):
        """모든 데이터 로드"""
        data = {
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'kospi': {},
            'kosdaq': {}
        }
        
        # KOSPI 데이터
        try:
            with open(f'{BASE_PATH}/data/kospi_analysis.csv', 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    headers = lines[0].strip().split(',')
                    values = lines[1].strip().split(',')
                    data['kospi']['summary'] = dict(zip(headers, values))
        except:
            pass
        
        # 리버모어
        try:
            with open(f'{BASE_PATH}/data/livermore_breakouts.json', 'r') as f:
                data['kospi']['livermore'] = json.load(f)
        except:
            data['kospi']['livermore'] = {'stocks': []}
        
        # 오닐
        try:
            with open(f'{BASE_PATH}/data/oneil_volume_breakouts.json', 'r') as f:
                data['kospi']['oneil'] = json.load(f)
        except:
            data['kospi']['oneil'] = {'stocks': []}
        
        # 미너비니
        try:
            with open(f'{BASE_PATH}/data/minervini_vcp.json', 'r') as f:
                data['kospi']['minervini'] = json.load(f)
        except:
            data['kospi']['minervini'] = {'stocks': []}
        
        # KOSDAQ
        try:
            with open(f'{BASE_PATH}/data/kosdaq_scan_results.json', 'r') as f:
                data['kosdaq'] = json.load(f)
        except:
            data['kosdaq'] = {'results': {'livermore': [], 'oneil': [], 'minervini': []}}
        
        return data
    
    def format_number(self, value):
        """숫자 포맷팅"""
        try:
            return f"{int(float(value)):,}"
        except:
            return str(value)
    
    def generate_html(self):
        """HTML 생성"""
        kospi = self.data['kospi'].get('summary', {})
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Dashboard - 한국 주식 스캔 결과</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        header {{ text-align: center; margin-bottom: 40px; padding: 30px; background: rgba(255,255,255,0.95); border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }}
        h1 {{ font-size: 3em; margin-bottom: 10px; color: #2c3e50; }}
        .subtitle {{ color: #7f8c8d; font-size: 1.2em; }}
        .timestamp {{ color: #95a5a6; font-size: 0.9em; margin-top: 10px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 25px; margin-bottom: 40px; }}
        .card {{ background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); transition: transform 0.3s; }}
        .card:hover {{ transform: translateY(-5px); }}
        .card h3 {{ margin-bottom: 20px; color: #2c3e50; font-size: 1.4em; border-left: 4px solid #3498db; padding-left: 15px; }}
        .stock-item {{ padding: 15px; border-bottom: 1px solid #ecf0f1; transition: background 0.2s; }}
        .stock-item:hover {{ background: #f8f9fa; }}
        .stock-item:last-child {{ border-bottom: none; }}
        .stock-name {{ font-weight: bold; color: #2c3e50; font-size: 1.1em; }}
        .stock-info {{ color: #7f8c8d; font-size: 0.9em; margin-top: 8px; display: flex; gap: 10px; flex-wrap: wrap; }}
        .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 500; }}
        .badge-price {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-score {{ background: #fff3e0; color: #ef6c00; }}
        .badge-change-up {{ background: #e3f2fd; color: #1565c0; }}
        .badge-change-down {{ background: #ffebee; color: #c62828; }}
        .kospi-summary {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); margin-bottom: 40px; }}
        .kospi-summary h2 {{ margin-bottom: 20px; color: #2c3e50; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 20px; margin-top: 20px; }}
        .metric {{ text-align: center; padding: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-radius: 12px; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ color: #7f8c8d; font-size: 0.9em; margin-top: 8px; }}
        .empty {{ color: #95a5a6; text-align: center; padding: 30px; font-style: italic; }}
        .refresh-btn {{ display: inline-block; padding: 12px 30px; background: #3498db; color: white; border: none; border-radius: 25px; cursor: pointer; font-size: 1em; margin-top: 20px; transition: background 0.3s; text-decoration: none; }}
        .refresh-btn:hover {{ background: #2980b9; }}
        footer {{ text-align: center; padding: 30px; color: rgba(255,255,255,0.8); font-size: 0.9em; }}
        .alert {{ padding: 15px; border-radius: 8px; margin-bottom: 20px; background: #fff3cd; border: 1px solid #ffc107; color: #856404; }}
        @media (max-width: 768px) {{ h1 {{ font-size: 2em; }} .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📈 KStock Dashboard</h1>
            <p class="subtitle">한국 주식 전략별 스캔 결과</p>
            <p class="timestamp">최종 업데이트: {self.data['last_updated']}</p>
            <a href="https://github.com/username/kstock-dashboard" class="refresh-btn" target="_blank">📊 GitHub에서 보기</a>
        </header>
        
        {self.generate_alerts()}
        
        <div class="kospi-summary">
            <h2>📊 KOSPI 요약</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{self.format_number(kospi.get('close', '-'))}</div>
                    <div class="metric-label">현재가</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: {'#27ae60' if float(kospi.get('change_pct', 0)) > 0 else '#e74c3c'};">
                        {kospi.get('change_pct', '-')}%
                    </div>
                    <div class="metric-label">등락률</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: {'#e74c3c' if float(kospi.get('rsi', 50)) > 70 else '#3498db'};">
                        {kospi.get('rsi', '-')}
                    </div>
                    <div class="metric-label">RSI</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: {'#27ae60' if kospi.get('trend') == 'BULLISH' else '#e74c3c'};">
                        {kospi.get('trend', '-')}
                    </div>
                    <div class="metric-label">추세</div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            {self.generate_strategy_card('🎯 리버모어', '52주 신고가 돌파', self.data['kospi'].get('livermore', {}).get('stocks', []))}
            {self.generate_strategy_card('📊 오닐', '거래량 폭발', self.data['kospi'].get('oneil', {}).get('stocks', []))}
            {self.generate_strategy_card('📉 미너비니', 'VCP 변동성 축소', self.data['kospi'].get('minervini', {}).get('stocks', []))}
        </div>
        
        {self.generate_kosdaq_section()}
        
        <footer>
            <p>📊 매일 오전 7:00 자동 갱신 | 전략: Livermore / O'Neil / Minervini</p>
            <p>⚠️ 이 정보는 투자 참고용이며, 투자 결정은 본인의 책임입니다</p>
        </footer>
    </div>
    
    <script>
        setTimeout(function(){{ location.reload(); }}, 60000);
    </script>
</body>
</html>"""
        return html
    
    def generate_alerts(self):
        """알림 섹션 생성"""
        alerts = []
        kospi = self.data['kospi'].get('summary', {})
        
        try:
            rsi = float(kospi.get('rsi', 50))
            if rsi > 80:
                alerts.append(f'<div class="alert">⚠️ KOSPI RSI 과매수 구간: {rsi:.1f} (주의 필요)</div>')
            elif rsi < 30:
                alerts.append(f'<div class="alert">✅ KOSPI RSI 과매도 구간: {rsi:.1f} (기회일 수 있음)</div>')
        except:
            pass
        
        total_breakouts = (
            len(self.data['kospi'].get('livermore', {}).get('stocks', [])) +
            len(self.data['kospi'].get('oneil', {}).get('stocks', [])) +
            len(self.data['kosdaq'].get('results', {}).get('oneil', []))
        )
        
        if total_breakouts > 0:
            alerts.append(f'<div class="alert" style="background: #d4edda; border-color: #28a745; color: #155724;">🚀 오늘 총 {total_breakouts}개 돌파 신호 감지!</div>')
        
        return '\n'.join(alerts) if alerts else ''
    
    def generate_strategy_card(self, title, subtitle, stocks):
        """전략별 카드 생성"""
        if not stocks:
            return f'''<div class="card">
                <h3>{title}</h3>
                <p style="color: #7f8c8d; margin-bottom: 15px;">{subtitle}</p>
                <div class="empty">발굴된 종목이 없습니다</div>
            </div>'''
        
        items = ''
        for s in stocks[:5]:
            change = s.get('change_pct', s.get('price_change', 0))
            items += f'''
            <div class="stock-item">
                <div class="stock-name">{s.get('name', s.get('symbol', ''))}</div>
                <div class="stock-info">
                    <span class="badge badge-price">{s.get('price', 0):,.0f}원</span>
                    <span class="badge badge-score">점수: {s.get('score', 0)}</span>
                    <span class="badge {'badge-change-up' if change > 0 else 'badge-change-down'}">{change:+.2f}%</span>
                </div>
            </div>'''
        
        return f'''<div class="card">
            <h3>{title}</h3>
            <p style="color: #7f8c8d; margin-bottom: 15px;">{subtitle}</p>
            {items}
        </div>'''
    
    def generate_kosdaq_section(self):
        """KOSDAQ 섹션 생성"""
        kosdaq = self.data['kosdaq'].get('results', {})
        oneil_stocks = kosdaq.get('oneil', [])
        
        if not oneil_stocks:
            return ''
        
        items = ''
        for s in oneil_stocks[:5]:
            items += f'''
            <div class="stock-item">
                <div class="stock-name">{s.get('name', '')}</div>
                <div class="stock-info">
                    <span class="badge badge-price">{s.get('price', 0):,.0f}원</span>
                    <span class="badge badge-score">점수: {s.get('score', 0)}</span>
                </div>
            </div>'''
        
        return f'''
        <div class="kospi-summary">
            <h2>📈 KOSDAQ</h2>
            <div class="grid" style="margin-top: 20px;">
                <div class="card">
                    <h3>오닐 (거래량 폭발)</h3>
                    {items}
                </div>
            </div>
        </div>'''
    
    def save(self):
        """HTML 파일 저장"""
        html = self.generate_html()
        filepath = f'{OUTPUT_PATH}/index.html'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 대시보드 생성 완료: {filepath}")
        return filepath


def main():
    """메인 실행"""
    print("🚀 KStock Dashboard Generator")
    print("=" * 50)
    
    generator = DashboardGenerator()
    filepath = generator.save()
    
    print(f"\n📁 출력 위치: {filepath}")
    print(f"\n🌐 GitHub Pages 설정 방법:")
    print("  1. GitHub 저장소 생성: kstock-dashboard")
    print("  2. docs 폴더 push")
    print("  3. Settings → Pages → Source: Deploy from a branch")
    print("  4. Branch: main /docs folder")
    print("  5. https://username.github.io/kstock-dashboard")
    
    return filepath


if __name__ == "__main__":
    main()
