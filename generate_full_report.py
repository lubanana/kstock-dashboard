#!/usr/bin/env python3
"""
V-Series 전체 종목 통합 리포트 생성기
"""

import json
import sqlite3
from datetime import datetime
import os

# 종목명 매핑 (확장)
STOCK_NAMES = {
    '000660': 'SK하이닉스',
    '005930': '삼성전자',
    '051910': 'LG화학',
    '005380': '현대차',
    '035720': '카카오',
    '068270': '셀트리온',
    '207940': '삼성바이오로직스',
    '006400': '삼성SDI',
    '000270': '기아',
    '012330': '현대모비스',
    '009150': '삼성전기',
    '236200': '제이앤티씨',
    '023530': '롯데쇼핑',
    '092870': '엔씨소프트',
    '001120': 'LX인터내셔널',
    '267270': '현대중공업지주',
    '388210': 'IBKS제21호스팩',
    '091700': '파트론',
    '027410': 'BGF',
    '237690': '클리오',
    '099320': '쎄트렉아이',
    '039030': '이니텍',
    '009420': '한올바이오파마',
    '006260': 'LS',
    '271560': '오리온',
    '064760': '덕산테코피아',
    '001800': '오리엔탈정공',
    '357870': '현대퓨처넷',
    '381180': '케이프이에스제4호',
}

def get_stock_name(symbol):
    """종목명 가져오기"""
    return STOCK_NAMES.get(symbol, symbol)

def generate_full_report():
    """전체 리포트 생성"""
    
    # 스캔 결과 로드
    with open('./reports/v_series/v_series_scan_20260325_full.json', 'r') as f:
        data = json.load(f)
    
    # ETF/일반주 분리
    stocks_only = [s for s in data['top_stocks'] if not s['symbol'].startswith(('4', '5'))]
    etfs = [s for s in data['top_stocks'] if s['symbol'].startswith(('4', '5'))]
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V-Series 전체 종목 리포트 - 2026-03-25</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #0f3460 0%, #533483 100%);
            border-radius: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .subtitle {{ font-size: 1.3em; color: #aaa; margin-top: 10px; }}
        .header .date {{ font-size: 1em; color: #888; margin-top: 5px; }}
        
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .section h2 {{
            color: #e94560;
            font-size: 1.8em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
        }}
        .summary-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #4ecca3;
        }}
        .summary-card .label {{ color: #aaa; font-size: 0.9em; }}
        
        .tab-buttons {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .tab-btn {{
            padding: 12px 30px;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
        }}
        .tab-btn.active {{
            background: linear-gradient(135deg, #e94560 0%, #ff6b6b 100%);
        }}
        .tab-btn:hover {{ background: rgba(233,69,96,0.5); }}
        
        .stock-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95em;
        }}
        .stock-table th {{
            background: rgba(233,69,96,0.2);
            padding: 15px 10px;
            text-align: center;
            font-weight: bold;
            position: sticky;
            top: 0;
        }}
        .stock-table td {{
            padding: 12px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            text-align: center;
        }}
        .stock-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        .rank {{ font-weight: bold; color: #e94560; font-size: 1.1em; }}
        .stock-name {{ font-weight: bold; text-align: left !important; }}
        .stock-code {{ color: #888; font-size: 0.85em; }}
        .value-score {{
            background: #4ecca3;
            color: #1a1a2e;
            padding: 5px 12px;
            border-radius: 15px;
            font-weight: bold;
        }}
        .price {{ font-family: 'Courier New', monospace; }}
        .positive {{ color: #ff6b6b; }}
        .negative {{ color: #4ecdc4; }}
        .rr-ratio {{ font-weight: bold; color: #4ecca3; }}
        
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .badge-quality {{ background: #4ecca3; color: #1a1a2e; }}
        .badge-netnet {{ background: #ffd93d; color: #1a1a2e; }}
        .badge-dividend {{ background: #6bcf7f; color: #1a1a2e; }}
        
        .strategy-box {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: #1a1a2e;
            padding: 25px;
            border-radius: 15px;
            margin-top: 20px;
        }}
        .strategy-box h3 {{ margin-bottom: 15px; font-size: 1.3em; }}
        .strategy-box ul {{ margin-left: 20px; }}
        .strategy-box li {{ margin: 8px 0; }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: #888;
            font-size: 0.9em;
        }}
        
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔮 V-Series 전체 종목 리포트</h1>
            <div class="subtitle">Value + Fibonacci + ATR 전략 | 전체 3,299개 종목 대상</div>
            <div class="date">2026년 3월 25일 (수)</div>
        </div>
        
        <div class="section">
            <h2>📊 스캔 개요</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="number">{data['total_symbols']:,}</div>
                    <div class="label">스캔 종목</div>
                </div>
                <div class="summary-card">
                    <div class="number">{data['selected_count']}</div>
                    <div class="label">선정 종목</div>
                </div>
                <div class="summary-card">
                    <div class="number">{data['selected_count']/data['total_symbols']*100:.1f}%</div>
                    <div class="label">선정률</div>
                </div>
                <div class="summary-card">
                    <div class="number">{len(stocks_only)}</div>
                    <div class="label">일반주</div>
                </div>
                <div class="summary-card">
                    <div class="number">{len(etfs)}</div>
                    <div class="label">ETF/ETN</div>
                </div>
            </div>
            
            <div class="strategy-box">
                <h3>📋 선정 기준</h3>
                <ul>
                    <li><strong>Value Score 65점 이상</strong>: Graham Net-Net 또는 Quality Fair Price 전략 충족</li>
                    <li><strong>Fibonacci 38.2%~50% 구간</strong>: 눌림목 진입 구간 확인</li>
                    <li><strong>ATR 기반 리스크 관리</strong>: 손절가 = 진입가 - (ATR × 1.5)</li>
                    <li><strong>최소 손익비 1:1.5</strong>: 목표가 = Fibonacci 1.618 확장</li>
                    <li><strong>최소 거래대금 10억원</strong>: 유동성 확보</li>
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 선정 종목 상세</h2>
            
            <div class="tab-buttons">
                <button class="tab-btn active" onclick="showTab('stocks')">일반주 TOP 50</button>
                <button class="tab-btn" onclick="showTab('etfs')">ETF/ETN TOP 30</button>
            </div>
            
            <div id="stocks" class="tab-content active">
                <table class="stock-table">
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>종목</th>
                            <th>가치점수</th>
                            <th>전략</th>
                            <th>현재가</th>
                            <th>목표가</th>
                            <th>수익률</th>
                            <th>손절가</th>
                            <th>손익비</th>
                        </tr>
                    </thead>
                    <tbody>
'''
    
    # 일반주 TOP 50
    for i, s in enumerate(stocks_only[:50], 1):
        name = get_stock_name(s['symbol'])
        strategy_badge = 'badge-quality'
        if 'NetNet' in s.get('strategy_type', ''):
            strategy_badge = 'badge-netnet'
        elif 'Dividend' in s.get('strategy_type', ''):
            strategy_badge = 'badge-dividend'
        
        html += f'''
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="stock-name">
                                {name}
                                <br><span class="stock-code">{s['symbol']}</span>
                            </td>
                            <td><span class="value-score">{s['value_score']:.1f}</span></td>
                            <td><span class="badge {strategy_badge}">{s.get('strategy_type', 'Quality')[:10]}</span></td>
                            <td class="price">₩{s['current_price']:,.0f}</td>
                            <td class="price positive">₩{s['target_price']:,.0f}</td>
                            <td class="positive">+{s['expected_return']:.1f}%</td>
                            <td class="price negative">₩{s['stop_loss']:,.0f}</td>
                            <td class="rr-ratio">1:{s['rr_ratio']:.2f}</td>
                        </tr>
'''
    
    html += '''
                    </tbody>
                </table>
            </div>
            
            <div id="etfs" class="tab-content">
                <table class="stock-table">
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>종목코드</th>
                            <th>가치점수</th>
                            <th>현재가</th>
                            <th>목표가</th>
                            <th>수익률</th>
                            <th>손익비</th>
                        </tr>
                    </thead>
                    <tbody>
'''
    
    # ETF TOP 30
    for i, s in enumerate(etfs[:30], 1):
        html += f'''
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="stock-name">{s['symbol']}</td>
                            <td><span class="value-score">{s['value_score']:.1f}</span></td>
                            <td class="price">₩{s['current_price']:,.0f}</td>
                            <td class="price positive">₩{s['target_price']:,.0f}</td>
                            <td class="positive">+{s['expected_return']:.1f}%</td>
                            <td class="rr-ratio">1:{s['rr_ratio']:.2f}</td>
                        </tr>
'''
    
    html += '''
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="section">
            <h2>⚠️ 리스크 관리</h2>
            <div class="strategy-box" style="background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);">
                <h3>투자 유의사항</h3>
                <ul>
                    <li><strong>분할 매수:</strong> 목표가 진입 시 50% → 저점 확인 시 50% 추가</li>
                    <li><strong>손절 준수:</strong> ATR 기반 손절가(-7~10%) 반드시 설정</li>
                    <li><strong>익절 전략:</strong> 목표가 도달 시 50% 부분 익절, 나머지 추세 추종</li>
                    <li><strong>최대 보유:</strong> 20일 이상 보유 시 리밸런싱 검토</li>
                    <li><strong>시장 상황:</strong> 코스피/코스닥 3% 이상 급락 시 전량 손절 검토</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>📊 V-Series Strategy: Value + Fibonacci + ATR</p>
            <p>생성일: 2026-03-25 | 데이터 출처: FinanceDataReader | DB 기반 스캔</p>
            <p style="margin-top: 10px; color: #666;">※ 본 리포트는 투자 참고용이며, 투자 결정은 투자자 본인의 책임입니다.</p>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // 모든 탭 버튼 비활성화
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            // 모든 탭 콘텐츠 숨기기
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            // 선택한 탭 활성화
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }
    </script>
</body>
</html>
'''
    
    return html

def main():
    print("📄 V-Series 전체 종목 리포트 생성 중...")
    
    html_content = generate_full_report()
    
    # 저장
    output_path = './reports/V_Series_Full_Report_20260325.html'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 리포트 저장: {output_path}")
    
    # docs에도 복사
    docs_path = './docs/V_Series_Full_Report_20260325.html'
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ GitHub Pages용 복사: {docs_path}")

if __name__ == "__main__":
    main()
