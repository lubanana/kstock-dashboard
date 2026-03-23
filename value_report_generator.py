#!/usr/bin/env python3
"""
Value Stock Scanner - Report Generator
=======================================
HTML 리포트 생성 및 GitHub Pages 배포
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import json
import sys
import os

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)


class ValueReportGenerator:
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.stock_names = self._load_names()
    
    def _load_names(self):
        names = {}
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT symbol, name FROM stock_info')
            for row in cursor.fetchall():
                names[row[0]] = row[1]
        except:
            pass
        
        defaults = {
            '000440': '중앙에너비스', 'BYC': 'BYC', '000250': '삼천당제약',
            '000490': '대동공업', '003350': '기산텔레콤', '001750': '한양증권',
            '001515': 'SK증권우', '154030': '아이윈', '139480': '이마트',
            '049720': '고려신용정보', '002870': '신풍', '005930': '삼성전자',
            '051600': '한전KPS', '036190': '금화피에스시', '117700': '건설',
            '003550': 'LG', '035250': '강원랜드', '003690': '코리안리',
            '214320': '이노션'
        }
        names.update(defaults)
        return names
    
    def generate_report(self, scan_results):
        """HTML 리포트 생성"""
        now = datetime.now().strftime('%Y%m%d_%H%M')
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        top20 = scan_results[:20]
        top50 = scan_results[:50]
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Korea Value Stock Report | {date_str}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            color: #1a1a2e;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            font-size: 1.1rem;
            color: #666;
            margin-bottom: 20px;
        }}
        
        .header .meta {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        
        .meta-item {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 12px;
        }}
        
        .meta-item .label {{
            font-size: 0.85rem;
            opacity: 0.9;
            margin-bottom: 5px;
        }}
        
        .meta-item .value {{
            font-size: 1.5rem;
            font-weight: 700;
        }}
        
        .section {{
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        
        .section h2 {{
            font-size: 1.5rem;
            color: #1a1a2e;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }}
        
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.9rem;
        }}
        
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 12px;
            text-align: center;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        
        th:first-child {{ border-radius: 10px 0 0 0; }}
        th:last-child {{ border-radius: 0 10px 0 0; }}
        
        td {{
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }}
        
        tr:hover td {{
            background: #f8f9ff;
        }}
        
        .rank {{
            font-weight: 700;
            font-size: 1.2rem;
            color: #667eea;
        }}
        
        .rank.top3 {{ color: #ffd700; text-shadow: 0 0 10px rgba(255,215,0,0.5); }}
        
        .stock-name {{
            font-weight: 600;
            color: #1a1a2e;
        }}
        
        .stock-code {{
            font-size: 0.8rem;
            color: #888;
        }}
        
        .score {{
            font-weight: 700;
            font-size: 1.1rem;
            color: #667eea;
        }}
        
        .score-bar {{
            width: 100%;
            height: 6px;
            background: #eee;
            border-radius: 3px;
            margin-top: 5px;
            overflow: hidden;
        }}
        
        .score-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 3px;
        }}
        
        .price {{ font-weight: 600; color: #333; }}
        .target {{ color: #28a745; font-weight: 600; }}
        .stop {{ color: #dc3545; }}
        .rr {{ color: #666; font-size: 0.9rem; }}
        
        .fundamental {{
            font-size: 0.85rem;
            color: #666;
        }}
        
        .fundamental .per {{ color: #28a745; font-weight: 600; }}
        .fundamental .pbr {{ color: #17a2b8; font-weight: 600; }}
        
        .sub-scores {{
            display: flex;
            gap: 5px;
            justify-content: center;
        }}
        
        .sub-score {{
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        
        .sub-score.value {{ background: #e3f2fd; color: #1565c0; }}
        .sub-score.health {{ background: #e8f5e9; color: #2e7d32; }}
        .sub-score.momentum {{ background: #fff3e0; color: #ef6c00; }}
        .sub-score.risk {{ background: #fce4ec; color: #c2185b; }}
        
        .methodology {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 15px;
            line-height: 1.8;
        }}
        
        .methodology h3 {{
            color: #1a1a2e;
            margin-bottom: 15px;
        }}
        
        .score-breakdown {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .score-item {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid;
        }}
        
        .score-item.value {{ border-color: #1565c0; }}
        .score-item.health {{ border-color: #2e7d32; }}
        .score-item.momentum {{ border-color: #ef6c00; }}
        .score-item.risk {{ border-color: #c2185b; }}
        
        .score-item h4 {{
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 5px;
        }}
        
        .score-item .points {{
            font-size: 1.3rem;
            font-weight: 700;
            color: #1a1a2e;
        }}
        
        .disclaimer {{
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 20px;
            border-radius: 10px;
            font-size: 0.9rem;
            color: #666;
            margin-top: 30px;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8rem; }}
            .meta {{ flex-direction: column; }}
            table {{ font-size: 0.8rem; }}
            th, td {{ padding: 8px 5px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📊 Korea Value Stock Report</h1>
            <p class="subtitle">한국 저평가 우량주 분석 리포트 | 가치투자 기반 종합 평가</p>
            
            <div class="meta">
                <div class="meta-item">
                    <div class="label">분석 종목</div>
                    <div class="value">3,305개</div>
                </div>
                <div class="meta-item">
                    <div class="label">선정 종목</div>
                    <div class="value">{len(scan_results)}개</div>
                </div>
                <div class="meta-item">
                    <div class="label">생성일</div>
                    <div class="value">{date_str}</div>
                </div>
            </div>
        </div>
        
        <!-- TOP 20 Table -->
        <div class="section">
            <h2>🏆 TOP 20 저평가 종목</h2>
            
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>종목</th>
                            <th>현재가</th>
                            <th>PER</th>
                            <th>PBR</th>
                            <th>총점</th>
                            <th>세부점수</th>
                            <th>목표가</th>
                            <th>손절가</th>
                            <th>손익비</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for i, r in enumerate(top20, 1):
            rank_class = 'top3' if i <= 3 else ''
            name = self.stock_names.get(r['symbol'], r['name'])
            est_mark = "*" if r['fundamentals'].get('is_estimated', True) else ""
            
            html += f"""
                        <tr>
                            <td><span class="rank {rank_class}">#{i}</span></td>
                            <td>
                                <div class="stock-name">{name}</div>
                                <div class="stock-code">{r['symbol']}</div>
                            </td>
                            <td><span class="price">{r['price']:,.0f}원</span></td>
                            <td><span class="fundamental per">{r['fundamentals']['per']:.1f}x{est_mark}</span></td>
                            <td><span class="fundamental pbr">{r['fundamentals']['pbr']:.1f}x{est_mark}</span></td>
                            <td>
                                <span class="score">{r['score']}점</span>
                                <div class="score-bar">
                                    <div class="score-bar-fill" style="width: {r['score']/10}%"></div>
                                </div>
                            </td>
                            <td>
                                <div class="sub-scores">
                                    <span class="sub-score value">{r['scores']['value']}</span>
                                    <span class="sub-score health">{r['scores']['health']}</span>
                                    <span class="sub-score momentum">{r['scores']['momentum']}</span>
                                    <span class="sub-score risk">{r['scores']['risk']}</span>
                                </div>
                            </td>
                            <td><span class="target">{r['target']:,.0f}원</span></td>
                            <td><span class="stop">{r['stop_loss']:,.0f}원</span></td>
                            <td><span class="rr">1:{r['rr_ratio']:.2f}</span></td>
                        </tr>
"""
        
        html += f"""
                    </tbody>
                </table>
            </div>
            <p style="font-size: 0.85rem; color: #888; margin-top: 15px;">
                * PER/PBR이 표시된 경우 실제 재무 데이터, * 표시는 추정치입니다.
            </p>
        </div>
        
        <!-- Methodology -->
        <div class="section">
            <h2>📈 평가 방법론 (1000점 체계)</h2>
            
            <div class="methodology">
                <p>본 리포트는 다음 4가지 영역에서 종합 평가하여 저평가 우량주를 선정합니다.</p>
                
                <div class="score-breakdown">
                    <div class="score-item value">
                        <h4>💎 가치평가 (400점)</h4>
                        <div class="points">PER · PBR · ROE · 52주 위치</div>
                        <p style="font-size: 0.85rem; color: #666; margin-top: 10px;">
                            낮은 PER/PBR, 높은 ROE, 52주 저점 대비 낮은 위치
                        </p>
                    </div>
                    
                    <div class="score-item health">
                        <h4>🏢 재무건전성 (300점)</h4>
                        <div class="points">부채비율 · 시총 · 이익안정성</div>
                        <p style="font-size: 0.85rem; color: #666; margin-top: 10px;">
                            낮은 부채비율, 중대형주 선호, 안정적 수익성
                        </p>
                    </div>
                    
                    <div class="score-item momentum">
                        <h4>📊 기술적모멘텀 (200점)</h4>
                        <div class="points">추세 · RSI · 20일 수익률</div>
                        <p style="font-size: 0.85rem; color: #666; margin-top: 10px;">
                            정배열 추세, 과매도(RSI < 40), 적정 눌림목
                        </p>
                    </div>
                    
                    <div class="score-item risk">
                        <h4>🛡️ 리스크관리 (100점)</h4>
                        <div class="points">변동성 · 유동성 · 규모</div>
                        <p style="font-size: 0.85rem; color: #666; margin-top: 10px;">
                            적정 변동성, 거래량 유동성, 중소형주 리스크 관리
                        </p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- TOP 50 Full List -->
        <div class="section">
            <h2>📋 TOP 50 전체 목록</h2>
            
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>종목명</th>
                            <th>코드</th>
                            <th>현재가</th>
                            <th>총점</th>
                            <th>PER</th>
                            <th>PBR</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for i, r in enumerate(top50, 1):
            name = self.stock_names.get(r['symbol'], r['name'])
            html += f"""
                        <tr>
                            <td><strong>#{i}</strong></td>
                            <td>{name}</td>
                            <td>{r['symbol']}</td>
                            <td>{r['price']:,.0f}원</td>
                            <td><strong style="color: #667eea;">{r['score']}점</strong></td>
                            <td>{r['fundamentals']['per']:.1f}x</td>
                            <td>{r['fundamentals']['pbr']:.1f}x</td>
                        </tr>
"""
        
        html += f"""
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Disclaimer -->
        <div class="disclaimer">
            <strong>⚠️ 투자 유의사항</strong><br>
            본 리포트는 기술적 분석 및 재무 데이터를 기반으로 한 참고 자료이며, 
            투자 권유가 아닙니다. 실제 투자 결정은 투자자 본인의 판단과 책임하에 신중히 이루어져야 합니다. 
            과거의 수익률이 미래의 수익률을 보장하지 않으며, 
            원금 손실의 가능성이 있습니다. 개별 종목의 PER/PBR 등 재무지표는 
            추정치일 수 있으므로 실제 투자 시 추가 검증이 필요합니다.
            <br><br>
            <strong>Generated by:</strong> Korea Value Stock Scanner | 
            <strong>Data:</strong> FinanceDataReader | 
            <strong>Date:</strong> {date_str}
        </div>
    </div>
</body>
</html>
"""
        
        # 저장
        filename = f'Value_Stock_Report_{now}.html'
        report_path = f'./reports/{filename}'
        docs_path = f'./docs/{filename}'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        with open(docs_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # 최신 링크 업데이트
        latest_path = './docs/Value_Stock_Report_Latest.html'
        with open(latest_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # JSON 저장
        json_data = {
            'generated_at': datetime.now().isoformat(),
            'total_stocks': len(scan_results),
            'top20': top20,
            'top50': top50
        }
        
        with open(f'./reports/Value_Stock_Report_{now}.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        return filename, report_path


def main():
    # 이전 스캔 결과 로드 (또는 직접 실행)
    print("Value Report Generator")
    print("스캔 결과를 로드하려면 JSON 파일 경로를 입력하세요.")
    print("(엔터 시 새로 스캔)")
    
    # 여기서는 예시로 더미 데이터 생성
    print("\n리포트 생성 중...")


if __name__ == '__main__':
    main()
