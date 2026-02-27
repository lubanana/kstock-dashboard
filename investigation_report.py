#!/usr/bin/env python3
"""
KStock Investigation Report Generator
주식 조사 결과 보고 페이지 생성기
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = '/home/programs/kstock_analyzer/docs'


class InvestigationReport:
    """조사 결과 보고서 생성기"""
    
    def __init__(self):
        self.data = self.load_investigation_data()
        os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    def load_investigation_data(self) -> Dict:
        """모든 조사 데이터 로드"""
        data = {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'kospi': {},
            'investigations': []
        }
        
        # KOSPI 데이터
        try:
            with open(f'{BASE_PATH}/data/kospi_analysis.csv', 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    headers = lines[0].strip().split(',')
                    values = lines[1].strip().split(',')
                    data['kospi'] = dict(zip(headers, values))
        except:
            pass
        
        # 리버모어 조사 결과
        try:
            with open(f'{BASE_PATH}/data/livermore_breakouts.json', 'r') as f:
                result = json.load(f)
                for stock in result.get('stocks', []):
                    self.add_investigation(data['investigations'], stock, '리버모어 52주 신고가 돌파')
        except:
            pass
        
        # 오닐 조사 결과
        try:
            with open(f'{BASE_PATH}/data/oneil_volume_breakouts.json', 'r') as f:
                result = json.load(f)
                for stock in result.get('stocks', []):
                    self.add_investigation(data['investigations'], stock, "오닐 거래량 폭발")
        except:
            pass
        
        # 미너비니 조사 결과
        try:
            with open(f'{BASE_PATH}/data/minervini_vcp.json', 'r') as f:
                result = json.load(f)
                for stock in result.get('stocks', []):
                    self.add_investigation(data['investigations'], stock, '미너비니 VCP 패턴')
        except:
            pass
        
        # KOSDAQ 조사 결과
        try:
            with open(f'{BASE_PATH}/data/kosdaq_scan_results.json', 'r') as f:
                result = json.load(f)
                for strategy, stocks in result.get('results', {}).items():
                    strategy_name = {
                        'livermore': '리버모어',
                        'oneil': '오닐',
                        'minervini': '미너비니'
                    }.get(strategy, strategy)
                    for stock in stocks:
                        self.add_investigation(data['investigations'], stock, f'KOSDAQ {strategy_name}')
        except:
            pass
        
        # 2가지 이상 신호 종목
        try:
            with open(f'{BASE_PATH}/data/double_signal_results.json', 'r') as f:
                result = json.load(f)
                for stock in result.get('results', []):
                    signals = []
                    if stock.get('livermore_count', 0) > 0:
                        signals.append('리버모어')
                    if stock.get('oneil_count', 0) > 0:
                        signals.append('오닐')
                    if stock.get('minervini_count', 0) > 0:
                        signals.append('미너비니')
                    
                    if len(signals) >= 2:
                        self.add_investigation(
                            data['investigations'], 
                            stock, 
                            f"복합 신호: {' + '.join(signals)}",
                            priority='high'
                        )
        except:
            pass
        
        # 우선순위 정렬
        data['investigations'].sort(key=lambda x: (
            0 if x['priority'] == 'high' else 1,
            -x['score']
        ))
        
        return data
    
    def add_investigation(self, investigations: List[Dict], stock: Dict, 
                          investigation_type: str, priority: str = 'normal'):
        """조사 결과 추가"""
        symbol = stock.get('symbol', '')
        name = stock.get('name', '')
        
        # 중복 확인
        for inv in investigations:
            if inv['symbol'] == symbol and inv['type'] == investigation_type:
                return
        
        investigations.append({
            'symbol': symbol,
            'name': name,
            'type': investigation_type,
            'price': stock.get('price', 0),
            'change': stock.get('change_pct', stock.get('price_change', 0)),
            'score': stock.get('score', 0),
            'priority': priority,
            'details': stock
        })
    
    def generate_report(self) -> str:
        """HTML 보고서 생성"""
        kospi = self.data['kospi']
        investigations = self.data['investigations']
        
        # 통계
        high_priority = len([i for i in investigations if i['priority'] == 'high'])
        normal_priority = len([i for i in investigations if i['priority'] == 'normal'])
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Investigation Report - {self.data['generated_at']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            color: #333;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        /* 헤더 */
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 20px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ font-size: 1.2em; opacity: 0.9; }}
        .header .timestamp {{ margin-top: 15px; font-size: 0.9em; opacity: 0.8; }}
        
        /* 요약 카드 */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: rgba(255,255,255,0.95);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .summary-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .summary-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .summary-card.high {{ border-top: 4px solid #e74c3c; }}
        .summary-card.normal {{ border-top: 4px solid #3498db; }}
        .summary-card.total {{ border-top: 4px solid #27ae60; }}
        .summary-card.market {{ border-top: 4px solid #f39c12; }}
        
        /* 섹션 */
        .section {{
            background: rgba(255,255,255,0.95);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
            font-size: 1.5em;
        }}
        
        /* 시장 상태 */
        .market-status {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        .market-item {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        .market-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .market-label {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        /* 조사 결과 테이블 */
        .investigation-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95em;
        }}
        .investigation-table th {{
            background: linear-gradient(135deg, #34495e, #2c3e50);
            color: white;
            padding: 15px;
            text-align: left;
        }}
        .investigation-table td {{
            padding: 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        .investigation-table tr:hover {{
            background: #f8f9fa;
        }}
        .investigation-table tr.high-priority {{
            background: linear-gradient(90deg, #fff5f5 0%, #ffffff 100%);
            border-left: 4px solid #e74c3c;
        }}
        
        /* 배지 */
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        .badge-livermore {{ background: #ffebee; color: #c62828; }}
        .badge-oneil {{ background: #e3f2fd; color: #1565c0; }}
        .badge-minervini {{ background: #f3e5f5; color: #7b1fa2; }}
        .badge-composite {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-kosdaq {{ background: #fff3e0; color: #ef6c00; }}
        
        .priority-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: bold;
        }}
        .priority-high {{
            background: #e74c3c;
            color: white;
        }}
        .priority-normal {{
            background: #95a5a6;
            color: white;
        }}
        
        /* 차트 컨테이너 */
        .chart-container {{
            position: relative;
            height: 300px;
            margin: 20px 0;
        }}
        
        /* 푸터 */
        .footer {{
            text-align: center;
            padding: 30px;
            color: rgba(255,255,255,0.8);
        }}
        
        /* 반응형 */
        @media (max-width: 768px) {{
            .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .market-status {{ grid-template-columns: repeat(2, 1fr); }}
            .investigation-table {{ font-size: 0.85em; }}
            .investigation-table th,
            .investigation-table td {{ padding: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 KStock Investigation Report</h1>
            <div class="subtitle">주식 조사 결과 종합 보고서</div>
            <div class="timestamp">생성일시: {self.data['generated_at']}</div>
        </div>
        
        <!-- 요약 -->
        <div class="summary-grid">
            <div class="summary-card high">
                <div class="summary-value">{high_priority}</div>
                <div class="summary-label">고우선순위 종목</div>
            </div>
            <div class="summary-card normal">
                <div class="summary-value">{normal_priority}</div>
                <div class="summary-label">일반 종목</div>
            </div>
            <div class="summary-card total">
                <div class="summary-value">{len(investigations)}</div>
                <div class="summary-label">총 조사 종목</div>
            </div>
            <div class="summary-card market">
                <div class="summary-value">{kospi.get('close', '0')}</div>
                <div class="summary-label">KOSPI</div>
            </div>
        </div>
        
        <!-- 시장 상태 -->
        <div class="section">
            <h2>📈 시장 상태</h2>
            <div class="market-status">
                <div class="market-item">
                    <div class="market-value">{kospi.get('close', '0')}</div>
                    <div class="market-label">KOSPI 현재가</div>
                </div>
                <div class="market-item">
                    <div class="market-value" style="color: {'#27ae60' if float(kospi.get('change_pct', 0)) > 0 else '#e74c3c'}">
                        {kospi.get('change_pct', '-')}%
                    </div>
                    <div class="market-label">등락률</div>
                </div>
                <div class="market-item">
                    <div class="market-value">{kospi.get('rsi', '-')}</div>
                    <div class="market-label">RSI(14)</div>
                </div>
                <div class="market-item">
                    <div class="market-value">{kospi.get('trend', '-')}</div>
                    <div class="market-label">추세</div>
                </div>
            </div>
        </div>
        
        <!-- 조사 결과 -->
        <div class="section">
            <h2>🔍 조사 결과 상세</h2>
            <table class="investigation-table">
                <thead>
                    <tr>
                        <th>우선순위</th>
                        <th>종목명</th>
                        <th>현재가</th>
                        <th>등락률</th>
                        <th>조사 유형</th>
                        <th>점수</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # 조사 결과 행 추가
        for inv in investigations[:50]:  # 상위 50개만
            priority_class = 'high-priority' if inv['priority'] == 'high' else ''
            priority_badge = '<span class="priority-badge priority-high">HIGH</span>' if inv['priority'] == 'high' else '<span class="priority-badge priority-normal">NORMAL</span>'
            
            # 배지 결정
            if '복합' in inv['type']:
                badge_class = 'badge-composite'
            elif '리버모어' in inv['type']:
                badge_class = 'badge-livermore'
            elif '오닐' in inv['type']:
                badge_class = 'badge-oneil'
            elif '미너비니' in inv['type']:
                badge_class = 'badge-minervini'
            else:
                badge_class = 'badge-kosdaq'
            
            change_color = '#27ae60' if inv['change'] > 0 else '#e74c3c' if inv['change'] < 0 else '#7f8c8d'
            
            html += f"""
                    <tr class="{priority_class}">
                        <td>{priority_badge}</td>
                        <td>
                            <strong>{inv['name']}</strong><br>
                            <small style="color: #95a5a6;">{inv['symbol']}</small>
                        </td>
                        <td>{inv['price']:,.0f}원</td>
                        <td style="color: {change_color}; font-weight: bold;">{inv['change']:+.2f}%</td>
                        <td><span class="badge {badge_class}">{inv['type']}</span></td>
                        <td>{inv['score']}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <!-- 조사 방법론 -->
        <div class="section">
            <h2>📋 조사 방법론</h2>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                <div style="padding: 20px; background: #fff5f5; border-radius: 10px; border-left: 4px solid #e74c3c;">
                    <h3 style="color: #c62828; margin-bottom: 10px;">리버모어 전략</h3>
                    <p style="font-size: 0.9em; color: #666;">52주 신고가 돌파 + 거래량 확인</p>
                </div>
                <div style="padding: 20px; background: #f0f7ff; border-radius: 10px; border-left: 4px solid #3498db;">
                    <h3 style="color: #1565c0; margin-bottom: 10px;">오닐 전략</h3>
                    <p style="font-size: 0.9em; color: #666;">거래량 2배 이상 + 3% 이상 상승</p>
                </div>
                <div style="padding: 20px; background: #faf5ff; border-radius: 10px; border-left: 4px solid #9b59b6;">
                    <h3 style="color: #7b1fa2; margin-bottom: 10px;">미너비니 전략</h3>
                    <p style="font-size: 0.9em; color: #666;">VCP 패턴 + 변동성 축소</p>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>KStock Analyzer - Automated Investigation System</p>
            <p style="font-size: 0.85em; margin-top: 10px;">Data source: Yahoo Finance | Analysis period: Last 1 year</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def save_report(self):
        """보고서 저장"""
        html = self.generate_report()
        
        output_file = f'{OUTPUT_PATH}/investigation_report.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Investigation report saved: {output_file}")
        print(f"   Total investigations: {len(self.data['investigations'])}")
        
        return output_file


def main():
    """메인 함수"""
    print("=" * 60)
    print("KStock Investigation Report Generator")
    print("=" * 60)
    
    report = InvestigationReport()
    output_file = report.save_report()
    
    print(f"\n📄 Report generated successfully!")
    print(f"   File: {output_file}")
    print(f"   URL: https://lubanana.github.io/kstock-dashboard/investigation_report.html")


if __name__ == '__main__':
    main()
