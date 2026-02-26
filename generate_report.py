#!/usr/bin/env python3
"""
KStock Daily Report Generator
일일 조사 결과 통합 리포트 생성기
"""

import json
import os
from datetime import datetime

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = '/home/programs/kstock_analyzer/docs'


class DailyReportGenerator:
    """일일 리포트 생성기"""
    
    def __init__(self):
        self.data = self.load_all_data()
        os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    def load_all_data(self):
        """모든 데이터 로드"""
        data = {
            'date': datetime.now().strftime('%Y년 %m월 %d일'),
            'kospi': {},
            'kosdaq': {},
            'summary': {}
        }
        
        # KOSPI 데이터
        try:
            with open(f'{BASE_PATH}/data/kospi_analysis.csv', 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    headers = lines[0].strip().split(',')
                    values = lines[1].strip().split(',')
                    data['kospi']['summary'] = dict(zip(headers, values))
        except Exception as e:
            print(f"KOSPI 데이터 로드 실패: {e}")
        
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
        
        # 요약 계산
        data['summary']['total_breakouts'] = (
            len(data['kospi'].get('livermore', {}).get('stocks', [])) +
            len(data['kospi'].get('oneil', {}).get('stocks', [])) +
            len(data['kosdaq'].get('results', {}).get('oneil', []))
        )
        
        data['summary']['kospi_status'] = data['kospi'].get('summary', {})
        
        return data
    
    def format_number(self, value):
        """숫자 포맷팅"""
        try:
            return f"{int(float(value)):,}"
        except:
            return str(value)
    
    def generate_html(self):
        """HTML 리포트 생성"""
        kospi_summary = self.data['kospi'].get('summary', {})
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Daily Report - {self.data['date']}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            color: #333; 
            line-height: 1.6;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        
        /* 헤더 */
        .header {{ 
            text-align: center; 
            margin-bottom: 30px; 
            padding: 40px 30px; 
            background: rgba(255,255,255,0.95); 
            border-radius: 20px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.2); 
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; color: #2c3e50; }}
        .header .date {{ color: #7f8c8d; font-size: 1.2em; margin-bottom: 15px; }}
        .header .summary {{ 
            display: inline-block; 
            padding: 10px 25px; 
            background: #3498db; 
            color: white; 
            border-radius: 25px; 
            font-size: 1.1em;
        }}
        
        /* 섹션 */
        .section {{ 
            background: rgba(255,255,255,0.95); 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
            margin-bottom: 25px;
        }}
        .section h2 {{ 
            color: #2c3e50; 
            margin-bottom: 20px; 
            padding-bottom: 10px; 
            border-bottom: 3px solid #3498db;
            font-size: 1.5em;
        }}
        
        /* KOSPI 요약 */
        .kospi-grid {{ 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 15px; 
            margin-bottom: 20px;
        }}
        .kospi-item {{ 
            text-align: center; 
            padding: 20px; 
            background: #f8f9fa; 
            border-radius: 12px;
        }}
        .kospi-value {{ font-size: 1.8em; font-weight: bold; color: #2c3e50; }}
        .kospi-label {{ color: #7f8c8d; font-size: 0.9em; margin-top: 5px; }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .warning {{ color: #f39c12; }}
        
        /* 종목 리스트 */
        .stock-list {{ margin-top: 15px; }}
        .stock-item {{ 
            display: flex; 
            justify-content: space-between; 
            align-items: center;
            padding: 15px; 
            border-bottom: 1px solid #ecf0f1; 
            transition: background 0.2s;
        }}
        .stock-item:hover {{ background: #f8f9fa; }}
        .stock-item:last-child {{ border-bottom: none; }}
        
        .stock-info {{ flex: 1; }}
        .stock-name {{ font-size: 1.2em; font-weight: bold; color: #2c3e50; }}
        .stock-code {{ color: #95a5a6; font-size: 0.85em; }}
        
        .stock-metrics {{ display: flex; gap: 10px; align-items: center; }}
        .metric-box {{ 
            padding: 8px 15px; 
            border-radius: 8px; 
            font-size: 0.9em; 
            font-weight: 500;
        }}
        .box-price {{ background: #e8f5e9; color: #2e7d32; }}
        .box-change-up {{ background: #e3f2fd; color: #1565c0; }}
        .box-change-down {{ background: #ffebee; color: #c62828; }}
        .box-score {{ background: #fff3e0; color: #ef6c00; }}
        
        .stock-signals {{ margin-top: 8px; }}
        .signal-tag {{ 
            display: inline-block; 
            padding: 4px 10px; 
            border-radius: 15px; 
            font-size: 0.8em; 
            background: #e3f2fd; 
            color: #1565c0; 
            margin-right: 5px;
        }}
        
        /* 알림 */
        .alert {{ 
            padding: 15px 20px; 
            border-radius: 10px; 
            margin-bottom: 20px;
        }}
        .alert-warning {{ background: #fff3cd; border-left: 4px solid #ffc107; color: #856404; }}
        .alert-success {{ background: #d4edda; border-left: 4px solid #28a745; color: #155724; }}
        .alert-info {{ background: #d1ecf1; border-left: 4px solid #17a2b8; color: #0c5460; }}
        
        /* 전략 설명 */
        .strategy-desc {{ 
            color: #7f8c8d; 
            font-size: 0.95em; 
            margin-bottom: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        /* 빈 상태 */
        .empty {{ 
            text-align: center; 
            padding: 40px; 
            color: #95a5a6; 
            font-style: italic;
        }}
        
        /* 푸터 */
        .footer {{ 
            text-align: center; 
            padding: 30px; 
            color: rgba(255,255,255,0.8); 
            font-size: 0.9em;
        }}
        
        /* 반응형 */
        @media (max-width: 768px) {{
            .kospi-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .stock-item {{ flex-direction: column; align-items: flex-start; }}
            .stock-metrics {{ margin-top: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 헤더 -->
        <div class="header">
            <h1>📈 KStock Daily Report</h1>
            <div class="date">{self.data['date']}</div>
            <div class="summary">총 {self.data['summary']['total_breakouts']}개 돌파 신호 감지</div>
        </div>
        
        <!-- 알림 -->
        {self.generate_alerts()}
        
        <!-- KOSPI 시장 요약 -->
        <div class="section">
            <h2>📊 KOSPI 시장 요약</h2>
            <div class="kospi-grid">
                <div class="kospi-item">
                    <div class="kospi-value">{self.format_number(kospi_summary.get('close', '-'))}</div>
                    <div class="kospi-label">현재가</div>
                </div>
                <div class="kospi-item">
                    <div class="kospi-value {'positive' if float(kospi_summary.get('change_pct', 0)) > 0 else 'negative'}">{kospi_summary.get('change_pct', '-')}%</div>
                    <div class="kospi-label">등락률</div>
                </div>
                <div class="kospi-item">
                    <div class="kospi-value {'warning' if float(kospi_summary.get('rsi', 50)) > 70 else ''}">{kospi_summary.get('rsi', '-')}</div>
                    <div class="kospi-label">RSI(14)</div>
                </div>
                <div class="kospi-item">
                    <div class="kospi-value {'positive' if kospi_summary.get('trend') == 'BULLISH' else 'negative'}">{kospi_summary.get('trend', '-')}</div>
                    <div class="kospi-label">추세</div>
                </div>
            </div>
        </div>
        
        <!-- 리버모어 전략 -->
        <div class="section">
            <h2>🎯 리버모어 전략 - 52주 신고가 돌파</h2>
            <div class="strategy-desc">
                제시 리버모어의 핵심 전략: 52주 최고가를 돌파하는 종목은 강한 상승세를 보일 가능성이 높습니다.
            </div>
            {self.generate_stock_list(self.data['kospi'].get('livermore', {}).get('stocks', []))}
        </div>
        
        <!-- 오닐 전략 -->
        <div class="section">
            <h2>📈 오닐 전략 - 거래량 폭발</h2>
            <div class="strategy-desc">
                윌리엄 오닐의 CAN SLIM 전략: 거래량이 50일 평균의 2배 이상 증가하며 가격이 상승하는 종목.
            </div>
            {self.generate_stock_list(self.data['kospi'].get('oneil', {}).get('stocks', []))}
        </div>
        
        <!-- 미너비니 전략 -->
        <div class="section">
            <h2>📉 미너비니 전략 - VCP 변동성 축소</h2>
            <div class="strategy-desc">
                마크 미너비니의 SEPA 전략: 변동성이 A>B>C 순으로 축소되며 가격이 압축되는 패턴.
            </div>
            {self.generate_stock_list(self.data['kospi'].get('minervini', {}).get('stocks', []))}
        </div>
        
        <!-- KOSDAQ -->
        <div class="section">
            <h2>📊 KOSDAQ - 성장주 스캔</h2>
            <div class="strategy-desc">
                KOSDAQ 대표 종목 대상으로 동일한 3가지 전략을 적용한 결과입니다.
            </div>
            {self.generate_kosdaq_section()}
        </div>
        
        <!-- 푸터 -->
        <div class="footer">
            <p>📊 매일 오전 7:00 자동 갱신 | 전략: Livermore / O'Neil / Minervini</p>
            <p>⚠️ 이 리포트는 투자 참고용이며, 투자 결정은 본인의 책임입니다.</p>
            <p style="margin-top: 10px; font-size: 0.85em;">Generated by KStock Analyzer</p>
        </div>
    </div>
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
                alerts.append(f'<div class="alert alert-warning">⚠️ <strong>과매수 경고:</strong> KOSPI RSI가 {rsi:.1f}로 과매수 구간입니다. 조정에 주의하세요.</div>')
            elif rsi < 30:
                alerts.append(f'<div class="alert alert-success">✅ <strong>과매도 기회:</strong> KOSPI RSI가 {rsi:.1f}로 과매도 구간입니다. 매수 기회일 수 있습니다.</div>')
        except:
            pass
        
        if self.data['summary']['total_breakouts'] > 0:
            alerts.append(f'<div class="alert alert-success">🚀 <strong>돌파 신호:</strong> 오늘 총 {self.data["summary"]["total_breakouts"]}개 종목에서 매수 신호가 감지되었습니다.</div>')
        
        return '\n'.join(alerts) if alerts else ''
    
    def generate_stock_list(self, stocks):
        """종목 리스트 HTML 생성"""
        if not stocks:
            return '<div class="empty">오늘은 해당 전략에 맞는 종목이 발굴되지 않았습니다.</div>'
        
        html = '<div class="stock-list">'
        
        for stock in stocks:
            name = stock.get('name', '')
            symbol = stock.get('symbol', '')
            price = stock.get('price', 0)
            score = stock.get('score', 0)
            
            # 등락률 (리버모어/오닐 다름)
            change = stock.get('change_pct', stock.get('price_change', stock.get('price_change', 0)))
            
            # 신호 태그
            signals = stock.get('signals', [])
            signals_html = ''.join([f'<span class="signal-tag">{s}</span>' for s in signals[:3]])
            
            change_class = 'box-change-up' if change > 0 else 'box-change-down'
            
            html += f"""
            <div class="stock-item">
                <div class="stock-info">
                    <div class="stock-name">{name}</div>
                    <div class="stock-code">{symbol}</div>
                    <div class="stock-signals">{signals_html}</div>
                </div>
                <div class="stock-metrics">
                    <span class="metric-box box-price">{price:,.0f}원</span>
                    <span class="metric-box {change_class}">{change:+.2f}%</span>
                    <span class="metric-box box-score">점수 {score}</span>
                </div>
            </div>"""
        
        html += '</div>'
        return html
    
    def generate_kosdaq_section(self):
        """KOSDAQ 섹션 생성"""
        kosdaq = self.data['kosdaq'].get('results', {})
        
        # 오닐 전략 결과만 표시 (가장 많이 나옴)
        oneil_stocks = kosdaq.get('oneil', [])
        
        if not oneil_stocks:
            return '<div class="empty">오늘은 KOSDAQ에서 해당 전략에 맞는 종목이 발굴되지 않았습니다.</div>'
        
        html = '<div class="stock-list">'
        
        for stock in oneil_stocks:
            name = stock.get('name', '')
            symbol = stock.get('symbol', '')
            price = stock.get('price', 0)
            score = stock.get('score', 0)
            change = stock.get('price_change', 0)
            volume_ratio = stock.get('volume_ratio_50d', 0)
            
            change_class = 'box-change-up' if change > 0 else 'box-change-down'
            
            html += f"""
            <div class="stock-item">
                <div class="stock-info">
                    <div class="stock-name">{name}</div>
                    <div class="stock-code">{symbol} | 거래량 {volume_ratio:.1f}x</div>
                </div>
                <div class="stock-metrics">
                    <span class="metric-box box-price">{price:,.0f}원</span>
                    <span class="metric-box {change_class}">{change:+.2f}%</span>
                    <span class="metric-box box-score">점수 {score}</span>
                </div>
            </div>"""
        
        html += '</div>'
        return html
    
    def save(self):
        """리포트 저장"""
        html = self.generate_html()
        filepath = f'{OUTPUT_PATH}/daily_report.html'
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 일일 리포트 생성 완료: {filepath}")
        return filepath


def main():
    """메인 실행"""
    print("=" * 60)
    print("📄 KStock Daily Report Generator")
    print("=" * 60)
    
    generator = DailyReportGenerator()
    filepath = generator.save()
    
    print(f"\n📁 리포트 위치: {filepath}")
    print(f"\n🌐 GitHub Pages URL:")
    print(f"   https://lubanana.github.io/kstock-dashboard/daily_report.html")
    
    return filepath


if __name__ == "__main__":
    main()
