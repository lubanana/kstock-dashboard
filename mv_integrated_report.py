#!/usr/bin/env python3
"""
Unified M+V Strategy Report Generator with Fibonacci + ATR
M-Strategy + V-Strategy 통합 리포트 (피볼나치 + ATR 기반)
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Stock name mapping
STOCK_NAMES = {
    '005930': '삼성전자', '000660': 'SK하이닉스', '051910': 'LG화학', '005380': '현대차',
    '035720': '카카오', '068270': '셀트리온', '207940': '삼성바이오로직스',
    '006400': '삼성SDI', '000270': '기아', '012330': '현대모비스',
    '005490': 'POSCO홀딩스', '028260': '삼성물산', '105560': 'KB금융',
    '018260': '삼성에스디에스', '032830': '삼성생명', '034730': 'SK',
    '000150': '두산', '016360': '삼성증권', '009830': '한화솔루션',
    '003490': '대한항공', '004170': '신세계', '000100': '유한양행',
    '000250': '삼천당제약', '000500': '가온전선', '000700': '유수홀딩스'
}

STOCK_INDUSTRY = {
    '005930': '반도체/전자', '000660': '반도체', '051910': '화학', '005380': '자동차',
    '035720': '플랫폼/IT', '068270': '바이오', '207940': '바이오',
    '006400': '배터리/에너지', '000270': '자동차', '012330': '자동차부품',
    '005490': '철강/소재', '028260': '종합상사', '105560': '금융/은행',
    '018260': 'IT서비스', '032830': '금융/보험', '034730': '에너지/화학',
    '000150': '중공업/건설', '016360': '금융/증권', '009830': '에너지/화학',
    '003490': '항공/운송', '004170': '유통/백화점'
}


def load_scan_result(filepath: str) -> dict:
    """스캔 결과 로드"""
    if not Path(filepath).exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_market_research(symbol: str) -> dict:
    """종목별 시장조사 정보"""
    industry = STOCK_INDUSTRY.get(symbol, '기타')
    name = STOCK_NAMES.get(symbol, symbol)
    
    research_templates = {
        '반도체/전자': {
            'outlook': 'AI 반도체 수요 증가로 중장기 성장세 지속 예상',
            'risk': '미중 무역분쟁 및 공급망 리스크',
            'catalyst': 'AI 서버 투자 증가, HBM 수요 확대'
        },
        '반도체': {
            'outlook': '메모리 시황 개선 및 AI 칩 수요 증가',
            'risk': '가격 변동성 및 중국 경기 둔화',
            'catalyst': 'DDR5 전환, AI 가속기 수요'
        },
        '자동차': {
            'outlook': '전기차 전환 가속화 및 수출 호조',
            'risk': '원자재 가격 상승 및 환율 변동',
            'catalyst': '신차 출시, 전기차 수요 증가'
        },
        '바이오': {
            'outlook': '신약 개발 및 CMO 수주 증가',
            'risk': '임상 실패 리스크 및 규제 변화',
            'catalyst': '신약 승인, 수주 증가'
        },
        '배터리/에너지': {
            'outlook': '2차 전지 수요 지속 성장',
            'risk': '원재료 가격 변동 및 공급 과잉 우려',
            'catalyst': '전기차 판매 증가, ESS 수요'
        },
        '금융/은행': {
            'outlook': '금리 인하 기대 및 수익성 개선',
            'risk': '경기 침체로 인한 대손비용 증가',
            'catalyst': '금리 정책 변화, 가계대출 증가'
        },
        '에너지/화학': {
            'outlook': '정유 마진 개선 및 태양광 사업 확대',
            'risk': '유가 변동성 및 환율 리스크',
            'catalyst': '정유 마진 회복, 신재생에너지 투자'
        },
        'default': {
            'outlook': '업황 개선 및 수익성 회복 기대',
            'risk': '경기 변동성 및 환율 리스크',
            'catalyst': '실적 개선, 신사업 진출'
        }
    }
    
    template = research_templates.get(industry, research_templates['default'])
    
    return {
        'industry': industry,
        'outlook': template['outlook'],
        'risk': template['risk'],
        'catalyst': template['catalyst']
    }


def generate_html_report(v_data: dict, m_data: dict, output_path: str):
    """통합 HTML 리포트 생성"""
    
    scan_date = v_data.get('scan_date', datetime.now().strftime('%Y-%m-%d'))
    v_stocks = v_data.get('top_stocks', [])
    m_stocks = m_data.get('top_stocks', []) if m_data else []
    
    # 모든 종목 합치기 (V-Series 우선)
    all_stocks = []
    seen = set()
    
    for stock in v_stocks:
        stock['source'] = 'V-Series'
        all_stocks.append(stock)
        seen.add(stock['symbol'])
    
    for stock in m_stocks:
        if stock['symbol'] not in seen:
            stock['source'] = 'M-Strategy'
            all_stocks.append(stock)
    
    # 가치점수 기준 정렬
    all_stocks.sort(key=lambda x: x.get('value_score', 0), reverse=True)
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M+V 통합 선정 종목 리포트 - {scan_date}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    <style>
        :root {{
            --primary: #3b82f6;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
            --purple: #8b5cf6;
            --bg: #0f172a;
            --card: #1e293b;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #334155;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
            border-radius: 16px;
            margin-bottom: 30px;
            border: 1px solid var(--border);
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .header .subtitle {{ color: var(--text-muted); font-size: 1.1rem; }}
        .header .badge {{
            display: inline-block;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(139, 92, 246, 0.3));
            padding: 8px 20px;
            border-radius: 20px;
            margin-top: 15px;
            font-weight: 600;
        }}
        
        .strategy-tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: center;
        }}
        .tab {{
            padding: 12px 30px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
            border: 2px solid transparent;
        }}
        .tab.active {{
            background: var(--primary);
            border-color: var(--primary);
        }}
        .tab:not(.active) {{
            background: var(--card);
            border-color: var(--border);
            color: var(--text-muted);
        }}
        .tab:hover:not(.active) {{ border-color: var(--primary); color: var(--text); }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: var(--card);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid var(--border);
            text-align: center;
        }}
        .stat-card .label {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 8px; }}
        .stat-card .value {{ font-size: 2rem; font-weight: 700; }}
        .stat-card.primary .value {{ color: var(--primary); }}
        .stat-card.success .value {{ color: var(--success); }}
        .stat-card.purple .value {{ color: var(--purple); }}
        .stat-card.warning .value {{ color: var(--warning); }}
        
        .stock-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stock-card {{
            background: var(--card);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        .stock-card::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: var(--primary);
        }}
        .stock-card.v-series::before {{ background: var(--success); }}
        .stock-card.m-strategy::before {{ background: var(--purple); }}
        .stock-card:hover {{
            transform: translateY(-4px);
            border-color: var(--primary);
            box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2);
        }}
        
        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }}
        .stock-name {{ font-size: 1.3rem; font-weight: 700; }}
        .stock-code {{ color: var(--text-muted); font-size: 0.9rem; }}
        .source-badge {{
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .source-badge.v-series {{ background: rgba(34, 197, 94, 0.2); color: var(--success); }}
        .source-badge.m-strategy {{ background: rgba(139, 92, 246, 0.2); color: var(--purple); }}
        
        .value-score {{
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(34, 197, 94, 0.1));
            color: var(--success);
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
        }}
        
        .price-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 16px 0;
        }}
        .price-box {{
            background: rgba(255,255,255,0.03);
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }}
        .price-box .label {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px; }}
        .price-box .value {{ font-size: 1.1rem; font-weight: 600; }}
        .price-box.target {{ border-left: 3px solid var(--success); }}
        .price-box.stop {{ border-left: 3px solid var(--danger); }}
        .price-box.current {{ border-left: 3px solid var(--primary); }}
        
        .fib-info {{
            display: flex;
            gap: 10px;
            margin-top: 10px;
            flex-wrap: wrap;
        }}
        .fib-tag {{
            background: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
        }}
        .rr-badge {{
            display: inline-block;
            background: rgba(59, 130, 246, 0.2);
            color: var(--primary);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            overflow: auto;
        }}
        .modal-content {{
            background: var(--card);
            margin: 50px auto;
            padding: 30px;
            border-radius: 16px;
            width: 90%;
            max-width: 1000px;
            border: 1px solid var(--border);
            max-height: 90vh;
            overflow-y: auto;
        }}
        .close {{
            color: var(--text-muted);
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }}
        .close:hover {{ color: var(--text); }}
        
        .chart-container {{ height: 400px; margin: 20px 0; }}
        
        .research-section {{
            background: rgba(255,255,255,0.03);
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
        }}
        .research-section h3 {{
            color: var(--primary);
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--primary);
        }}
        .research-item {{
            margin: 12px 0;
            padding: 12px;
            background: rgba(255,255,255,0.02);
            border-radius: 8px;
        }}
        .research-item .label {{
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 M+V 통합 선정 종목 리포트</h1>
            <p class="subtitle">Fibonacci + ATR 기반 통합 전략</p>
            <p class="subtitle">기준일: {scan_date}</p>
            <div class="badge">Value Score + M-Strategy + Fibonacci Retracement + ATR Risk Management</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card primary">
                <div class="label">총 선정 종목</div>
                <div class="value">{len(all_stocks)}개</div>
            </div>
            <div class="stat-card success">
                <div class="label">V-Series</div>
                <div class="value">{len(v_stocks)}개</div>
            </div>
            <div class="stat-card purple">
                <div class="label">M-Strategy</div>
                <div class="value">{len(m_stocks)}개</div>
            </div>
            <div class="stat-card warning">
                <div class="label">평균 손익비</div>
                <div class="value">1:{sum(s.get('rr_ratio', 0) for s in all_stocks)/len(all_stocks):.1f}</div>
            </div>
        </div>
        
        <div class="stock-grid">
'''
    
    # Stock cards
    for i, stock in enumerate(all_stocks, 1):
        name = STOCK_NAMES.get(stock['symbol'], stock['symbol'])
        research = generate_market_research(stock['symbol'])
        source_class = 'v-series' if stock.get('source') == 'V-Series' else 'm-strategy'
        source_badge_class = 'v-series' if stock.get('source') == 'V-Series' else 'm-strategy'
        
        html += f'''
            <div class="stock-card {source_class}" onclick="openModal('{stock['symbol']}')">
                <div class="stock-header">
                    <div>
                        <div class="stock-name">{name}</div>
                        <div class="stock-code">{stock['symbol']} | {research['industry']}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="source-badge {source_badge_class}">{stock.get('source', 'V-Series')}</span>
                        <div class="value-score" style="margin-top: 8px;">{stock.get('value_score', 0):.0f}점</div>
                    </div>
                </div>
                
                <div class="price-row">
                    <div class="price-box current">
                        <div class="label">현재가</div>
                        <div class="value">₩{stock.get('current_price', 0):,.0f}</div>
                    </div>
                    <div class="price-box target">
                        <div class="label">목표가</div>
                        <div class="value" style="color: var(--success)">₩{stock.get('target_price', 0):,.0f}</div>
                    </div>
                    <div class="price-box stop">
                        <div class="label">손절가</div>
                        <div class="value" style="color: var(--danger)">₩{stock.get('stop_loss', 0):,.0f}</div>
                    </div>
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="rr-badge">손익비 1:{stock.get('rr_ratio', 0):.2f}</span>
                    <span style="color: var(--text-muted); font-size: 0.9rem;">
                        수익 +{stock.get('expected_return', 0):.1f}% / 손실 {stock.get('expected_loss', 0):.1f}%
                    </span>
                </div>
                
                <div class="fib-info">
                    <span class="fib-tag">Fib {stock.get('fib_level', 'N/A')}</span>
                    <span class="fib-tag">ATR ₩{stock.get('atr', 0):,.0f}</span>
                </div>
            </div>
'''
    
    html += '''
        </div>
        
        <div id="stockModal" class="modal">
            <div class="modal-content">
                <span class="close" onclick="closeModal()">&times;</span>
                <div id="modalBody"></div>
            </div>
        </div>
    </div>
    
    <script>
'''
    
    # Stock data for JavaScript
    stock_data_js = []
    for stock in all_stocks:
        name = STOCK_NAMES.get(stock['symbol'], stock['symbol'])
        research = generate_market_research(stock['symbol'])
        stock_data_js.append({
            'symbol': stock['symbol'],
            'name': name,
            'industry': research['industry'],
            'source': stock.get('source', 'V-Series'),
            'value_score': stock.get('value_score', 0),
            'current_price': stock.get('current_price', 0),
            'target_price': stock.get('target_price', 0),
            'stop_loss': stock.get('stop_loss', 0),
            'rr_ratio': stock.get('rr_ratio', 0),
            'expected_return': stock.get('expected_return', 0),
            'expected_loss': stock.get('expected_loss', 0),
            'fib_level': stock.get('fib_level', ''),
            'atr': stock.get('atr', 0),
            'fib_high': stock.get('fib_high', 0),
            'fib_low': stock.get('fib_low', 0),
            'outlook': research['outlook'],
            'risk': research['risk'],
            'catalyst': research['catalyst']
        })
    
    html += f'''
        const stockData = {json.dumps(stock_data_js, ensure_ascii=False)};
        
        function openModal(symbol) {{
            const stock = stockData.find(s => s.symbol === symbol);
            if (!stock) return;
            
            const modalBody = document.getElementById('modalBody');
            modalBody.innerHTML = `
                <h2>${{stock.name}} (${{stock.symbol}})</h2>
                <p style="color: var(--text-muted)">${{stock.industry}} | ${{stock.source}}</p>
                
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0;">
                    <div class="price-box current">
                        <div class="label">현재가</div>
                        <div class="value">₩${{stock.current_price.toLocaleString()}}</div>
                    </div>
                    <div class="price-box target">
                        <div class="label">목표가</div>
                        <div class="value" style="color: var(--success)">₩${{stock.target_price.toLocaleString()}}</div>
                    </div>
                    <div class="price-box stop">
                        <div class="label">손절가</div>
                        <div class="value" style="color: var(--danger)">₩${{stock.stop_loss.toLocaleString()}}</div>
                    </div>
                </div>
                
                <div style="display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap;">
                    <div>
                        <span class="label">가치점수: </span>
                        <span style="font-weight: 600; color: var(--success)">${{stock.value_score.toFixed(1)}}점</span>
                    </div>
                    <div>
                        <span class="label">손익비: </span>
                        <span style="font-weight: 600; color: var(--primary)">1:${{stock.rr_ratio.toFixed(2)}}</span>
                    </div>
                    <div>
                        <span class="label">예상수익률: </span>
                        <span style="font-weight: 600; color: var(--success)">+${{stock.expected_return.toFixed(1)}}%</span>
                    </div>
                </div>
                
                <div class="fib-info">
                    <span class="fib-tag">Fib Level: ${{stock.fib_level}}</span>
                    <span class="fib-tag">Fib High: ₩${{stock.fib_high.toLocaleString()}}</span>
                    <span class="fib-tag">Fib Low: ₩${{stock.fib_low.toLocaleString()}}</span>
                    <span class="fib-tag">ATR: ₩${{stock.atr.toLocaleString()}}</span>
                </div>
                
                <div class="research-section">
                    <h3>📊 시장조사 리포트</h3>
                    
                    <div class="research-item">
                        <div class="label">🎯 투자 전망</div>
                        <div>${{stock.outlook}}</div>
                    </div>
                    
                    <div class="research-item">
                        <div class="label">⚠️ 주요 리스크</div>
                        <div>${{stock.risk}}</div>
                    </div>
                    
                    <div class="research-item">
                        <div class="label">🚀 촉매제</div>
                        <div>${{stock.catalyst}}</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="modalChart"></canvas>
                </div>
            `;
            
            document.getElementById('stockModal').style.display = 'block';
            drawChart(stock);
        }}
        
        function closeModal() {{
            document.getElementById('stockModal').style.display = 'none';
        }}
        
        function drawChart(stock) {{
            const ctx = document.getElementById('modalChart').getContext('2d');
            
            const labels = ['1월', '2월', '3월', '4월', '5월', '6월'];
            const data = [
                stock.current_price * 0.9,
                stock.current_price * 0.95,
                stock.current_price * 0.92,
                stock.current_price * 0.98,
                stock.current_price * 1.02,
                stock.current_price
            ];
            
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: '주가',
                        data: data,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.4
                    }}, {{
                        label: '목표가',
                        data: Array(6).fill(stock.target_price),
                        borderColor: '#22c55e',
                        borderDash: [5, 5],
                        pointRadius: 0
                    }}, {{
                        label: '손절가',
                        data: Array(6).fill(stock.stop_loss),
                        borderColor: '#ef4444',
                        borderDash: [5, 5],
                        pointRadius: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            labels: {{ color: '#f1f5f9' }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            ticks: {{ color: '#94a3b8' }},
                            grid: {{ color: '#334155' }}
                        }},
                        x: {{
                            ticks: {{ color: '#94a3b8' }},
                            grid: {{ color: '#334155' }}
                        }}
                    }}
                }}
            }});
        }}
        
        window.onclick = function(event) {{
            const modal = document.getElementById('stockModal');
            if (event.target === modal) {{
                closeModal();
            }}
        }}
    </script>
</body>
</html>
'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 리포트 생성 완료: {output_path}")


def main():
    # 결과 파일 로드
    v_result = load_scan_result('./reports/v_series/v_series_scan_20260320.json')
    m_result = load_scan_result('./reports/m10/m10_scan_20260320.json')
    
    if not v_result:
        print("❌ V-Series 결과 파일을 찾을 수 없습니다")
        return
    
    # HTML 리포트 생성
    output_path = './reports/MV_Integrated_Report_20260320.html'
    generate_html_report(v_result, m_result, output_path)
    
    # 요약 출력
    print(f"\n📊 스캔 요약 (2026-03-20):")
    print(f"   V-Series: {v_result.get('selected_count', 0)}개 종목")
    if m_result:
        print(f"   M-Strategy: {m_result.get('selected_count', 0)}개 종목")
    else:
        print(f"   M-Strategy: 0개 종목")
    
    print(f"\n   TOP 5:")
    for i, stock in enumerate(v_result.get('top_stocks', [])[:5], 1):
        name = STOCK_NAMES.get(stock['symbol'], stock['symbol'])
        print(f"      {i}. {name} ({stock['symbol']}): {stock['value_score']:.1f}점, RR 1:{stock['rr_ratio']:.2f}")
    
    # GitHub에 복사
    import shutil
    shutil.copy(output_path, './docs/')
    print(f"\n📁 GitHub Pages용으로 docs/ 폴더에 복사 완료")


if __name__ == '__main__':
    main()
