#!/usr/bin/env python3
"""
V-Series 통합 리포트 생성기
기술적 분석 + 뉴스/시장 상황 통합 리포트
"""

import json
from datetime import datetime
import os

def generate_html_report():
    """통합 HTML 리포트 생성"""
    
    # V-Series 결과 로드
    with open('./reports/v_series/v_series_scan_20260325.json', 'r') as f:
        v_data = json.load(f)
    
    # 뉴스 데이터 로드
    try:
        with open('./reports/v_series/v_series_news_20260325.json', 'r') as f:
            news_data = json.load(f)
    except:
        news_data = {'stocks': {}}
    
    # 스캔 요약 데이터
    total_scanned = v_data.get('total_symbols', 50)
    selected_count = v_data.get('selected_count', len(v_data['top_stocks']))
    selection_rate = (selected_count / total_scanned) * 100 if total_scanned > 0 else 0
    avg_rr = sum(s['rr_ratio'] for s in v_data['top_stocks']) / len(v_data['top_stocks']) if v_data['top_stocks'] else 0
    
    # 종목명 매핑
    stock_names = {
        '000660': 'SK하이닉스',
        '032830': '삼성생명',
        '004800': '현대해상',
        '006400': '삼성SDI',
        '005070': '코스모신소재',
        '001740': 'SK네트웍스',
        '003490': '대한항공'
    }
    
    # 시장 상황 분석
    if avg_rr >= 3.0 and selection_rate < 20:
        market_condition = "강한 매수 타이밍"
        market_desc = "고품질 종목 중심으로 선별적 매수 권장"
    elif avg_rr >= 2.5:
        market_condition = "매수 타이밍"
        market_desc = "분할 매수로 접근 권장"
    elif avg_rr >= 2.0:
        market_condition = "중립"
        market_desc = "소규모 분할 매수 또는 관망"
    else:
        market_condition = "관망 권장"
        market_desc = "시장 상황 개선 시까지 대기"
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V-Series 통합 리포트 - 2026-03-25</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
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
        .header .date {{ font-size: 1.2em; color: #aaa; }}
        
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
        }}
        
        .market-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
        }}
        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #4ecca3;
        }}
        .stat-card .label {{ color: #aaa; font-size: 0.9em; }}
        
        .market-condition {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: #1a1a2e;
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
        }}
        .market-condition h3 {{ margin-bottom: 10px; }}
        
        .stock-grid {{ display: grid; gap: 20px; }}
        .stock-card {{
            background: linear-gradient(135deg, rgba(233,69,96,0.1) 0%, rgba(83,52,131,0.1) 100%);
            border-radius: 15px;
            padding: 25px;
            border-left: 4px solid #e94560;
        }}
        
        .stock-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .stock-name {{ font-size: 1.5em; font-weight: bold; color: #fff; }}
        .stock-code {{ color: #aaa; font-size: 0.9em; margin-left: 10px; }}
        .value-score {{
            background: #4ecca3;
            color: #1a1a2e;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.2em;
        }}
        
        .price-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .price-item {{
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}
        .price-item .label {{ font-size: 0.8em; color: #888; }}
        .price-item .value {{ font-size: 1.3em; font-weight: bold; }}
        .positive {{ color: #ff6b6b; }}
        .negative {{ color: #4ecdc4; }}
        
        .news-section {{
            margin-top: 20px;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
        }}
        .news-item {{
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .news-item:last-child {{ border-bottom: none; }}
        .news-title {{ color: #ddd; font-size: 0.95em; }}
        .news-meta {{ font-size: 0.8em; color: #888; margin-top: 5px; }}
        
        .portfolio-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .portfolio-table th {{
            background: rgba(233,69,96,0.2);
            padding: 15px;
            text-align: center;
        }}
        .portfolio-table td {{
            padding: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            text-align: center;
        }}
        
        .risk-box {{
            background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
            color: #fff;
            padding: 25px;
            border-radius: 15px;
            margin-top: 30px;
        }}
        .risk-box h3 {{ margin-bottom: 15px; }}
        .risk-box ul {{ margin-left: 20px; }}
        .risk-box li {{ margin: 8px 0; }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: #888;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔮 V-Series 통합 리포트</h1>
            <p class="date">2026년 3월 25일 (수) | Value + Fibonacci + ATR 전략</p>
        </div>
        
        <div class="section">
            <h2>📊 시장 요약</h2>
            <div class="market-summary">
                <div class="stat-card">
                    <div class="number">{total_scanned}</div>
                    <div class="label">스캔 종목</div>
                </div>
                <div class="stat-card">
                    <div class="number">{selected_count}</div>
                    <div class="label">선정 종목</div>
                </div>
                <div class="stat-card">
                    <div class="number">{selection_rate:.1f}%</div>
                    <div class="label">선정률</div>
                </div>
                <div class="stat-card">
                    <div class="number">{avg_rr:.2f}</div>
                    <div class="label">평균 손익비</div>
                </div>
            </div>
            
            <div class="market-condition">
                <h3>📈 현재 시장 상황: {market_condition}</h3>
                <p>{market_desc}</p>
                <p style="margin-top: 10px;">
                    평균 손익비 {avg_rr:.2f}로 우량 종목 위주의 선별적 매수가 유리한 구간입니다.
                </p>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 선정 종목 상세 ({len(v_data['top_stocks'])}개)</h2>
            <div class="stock-grid">
'''
    
    # 각 종목 카드
    for i, stock in enumerate(v_data['top_stocks'], 1):
        symbol = stock['symbol']
        name = stock_names.get(symbol, symbol)
        news_list = news_data.get('stocks', {}).get(symbol, {}).get('news', [])
        
        expected_return = stock.get('expected_return', (stock['target_price'] - stock['entry_price']) / stock['entry_price'] * 100)
        expected_loss = stock.get('expected_loss', (stock['stop_loss'] - stock['entry_price']) / stock['entry_price'] * 100)
        
        html += f'''
                <div class="stock-card">
                    <div class="stock-header">
                        <div>
                            <span class="stock-name">{i}. {name}</span>
                            <span class="stock-code">({symbol})</span>
                        </div>
                        <div class="value-score">{stock['value_score']:.1f}점</div>
                    </div>
                    
                    <div class="price-grid">
                        <div class="price-item">
                            <div class="label">현재가</div>
                            <div class="value">₩{stock['current_price']:,.0f}</div>
                        </div>
                        <div class="price-item">
                            <div class="label">진입가</div>
                            <div class="value">₩{stock['entry_price']:,.0f}</div>
                        </div>
                        <div class="price-item">
                            <div class="label">목표가</div>
                            <div class="value positive">₩{stock['target_price']:,.0f}</div>
                            <div style="color: #ff6b6b; font-size: 0.9em;">+{expected_return:.1f}%</div>
                        </div>
                        <div class="price-item">
                            <div class="label">손절가</div>
                            <div class="value negative">₩{stock['stop_loss']:,.0f}</div>
                            <div style="color: #4ecdc4; font-size: 0.9em;">{expected_loss:.1f}%</div>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 15px 0; font-size: 0.9em;">
                        <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                            <span style="color: #888;">손익비:</span> 
                            <span style="color: #4ecca3; font-weight: bold;">1:{stock['rr_ratio']:.2f}</span>
                        </div>
                        <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                            <span style="color: #888;">ATR:</span> 
                            <span>₩{stock['atr']:,.0f}</span>
                        </div>
                        <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                            <span style="color: #888;">Fib:</span> 
                            <span>{stock.get('fib_level', 'N/A')}</span>
                        </div>
                    </div>
                    
                    <div style="background: rgba(78,204,163,0.1); padding: 15px; border-radius: 10px; margin-top: 15px;">
                        <div style="color: #4ecca3; font-weight: bold; margin-bottom: 5px;">
                            📈 추천 전략: {stock.get('strategy_type', 'Quality_FairPrice')}
                        </div>
                        <div style="font-size: 0.9em; color: #aaa;">
                            고점: ₩{stock.get('fib_high', 0):,.0f} / 저점: ₩{stock.get('fib_low', 0):,.0f}
                        </div>
                    </div>
'''
        
        # 뉴스
        if news_list and 'error' not in news_list[0]:
            html += '''
                    <div class="news-section">
                        <div style="color: #e94560; font-weight: bold; margin-bottom: 10px;">📰 관련 뉴스</div>
'''
            for news in news_list[:3]:
                html += f'''
                        <div class="news-item">
                            <div class="news-title">{news.get('title', '')}</div>
                            <div class="news-meta">{news.get('source', '')} | {news.get('date', '')}</div>
                        </div>
'''
            html += '</div>'
        
        html += '</div>'
    
    # 포트폴리오 테이블
    html += '''
            </div>
        </div>
        
        <div class="section">
            <h2>💼 추천 포트폴리오 구성</h2>
            <table class="portfolio-table">
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>종목</th>
                        <th>비중</th>
                        <th>진입가</th>
                        <th>목표가</th>
                        <th>손절가</th>
                        <th>손익비</th>
                    </tr>
                </thead>
                <tbody>
'''
    
    allocations = [25, 20, 15, 15, 10, 10, 5]
    for i, stock in enumerate(v_data['top_stocks'][:7], 1):
        symbol = stock['symbol']
        name = stock_names.get(symbol, symbol)
        alloc = allocations[i-1] if i <= len(allocations) else 0
        
        html += f'''
                    <tr>
                        <td>{i}</td>
                        <td><strong>{name}</strong><br><span style="color: #888; font-size: 0.85em;">{symbol}</span></td>
                        <td>{alloc}%</td>
                        <td>₩{stock['entry_price']:,.0f}</td>
                        <td style="color: #4ecca3;">₩{stock['target_price']:,.0f}</td>
                        <td style="color: #ff6b6b;">₩{stock['stop_loss']:,.0f}</td>
                        <td style="font-weight: bold;">1:{stock['rr_ratio']:.2f}</td>
                    </tr>
'''
    
    html += '''
                </tbody>
            </table>
            
            <div class="risk-box">
                <h3>⚠️ 리스크 관리 가이드</h3>
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
            <p>생성일: 2026-03-25 | 데이터 출처: FinanceDataReader, Naver Finance</p>
            <p style="margin-top: 10px; color: #666;">※ 본 리포트는 투자 참고용이며, 투자 결정은 투자자 본인의 책임입니다.</p>
        </div>
    </div>
</body>
</html>
'''
    
    return html

def main():
    print("📄 V-Series 통합 리포트 생성 중...")
    
    html_content = generate_html_report()
    
    # 저장
    output_path = './reports/V_Series_Integrated_Report_20260325.html'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 리포트 저장 완료: {output_path}")
    
    # 요약
    with open('./reports/v_series/v_series_scan_20260325.json', 'r') as f:
        data = json.load(f)
    
    avg_rr = sum(s['rr_ratio'] for s in data['top_stocks']) / len(data['top_stocks'])
    
    print(f"\n📊 리포트 요약:")
    print(f"  • 스캔 종목: {data.get('total_symbols', 50)}개")
    print(f"  • 선정 종목: {len(data['top_stocks'])}개")
    print(f"  • 평균 손익비: {avg_rr:.2f}")
    print(f"  • TOP 종목: {data['top_stocks'][0]['symbol']} ({data['top_stocks'][0]['value_score']:.1f}점)")

if __name__ == "__main__":
    main()
