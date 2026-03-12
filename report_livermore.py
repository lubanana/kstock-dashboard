#!/usr/bin/env python3
"""
Jesse Livermore Strategy Report Generator
제시 리버모어 전략 리포트 생성기

HTML 리포트 + 시각화
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import FinanceDataReader as fdr


class LivermoreReportGenerator:
    """리버모어 전략 리포트 생성기"""
    
    def __init__(self, db_path: str = 'data/livermore_signals.db'):
        self.db_path = db_path
        self.results = []
        self.scan_date = None
    
    def load_data(self) -> pd.DataFrame:
        """스캔 결과 로드"""
        try:
            with open('data/livermore_scan_results.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.scan_date = data.get('scan_date', datetime.now().strftime('%Y-%m-%d'))
                self.results = data.get('stocks', [])
                
            df = pd.DataFrame(self.results)
            print(f"✅ 데이터 로드: {len(df)}개 신호")
            return df
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def generate_html(self, df: pd.DataFrame) -> str:
        """HTML 리포트 생성"""
        
        # 통계 계산
        total = len(df)
        strong_buy = len(df[df['signal_grade'] == 'STRONG_BUY'])
        buy = len(df[df['signal_grade'] == 'BUY'])
        watch = len(df[df['signal_grade'] == 'WATCH'])
        
        # 시장별 분포
        kospi_count = len(df[df['market'] == 'KOSPI'])
        kosdaq_count = len(df[df['market'] == 'KOSDAQ'])
        
        # TOP 50
        top50 = df.head(50)
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Jesse Livermore Pivot Point Strategy Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        html {{ font-size: 16px; }}
        @media (max-width: 480px) {{ html {{ font-size: 14px; }} }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 0;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
        }}
        @media (min-width: 768px) {{
            .container {{
                max-width: 1400px;
                border-radius: 20px;
                margin: 20px auto;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 2.5rem 1rem;
            text-align: center;
        }}
        .header h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; font-weight: 700; }}
        .header p {{ font-size: 1rem; opacity: 0.9; margin-bottom: 0.3rem; }}
        .header .subtitle {{ font-size: 0.85rem; opacity: 0.8; }}
        @media (min-width: 768px) {{
            .header h1 {{ font-size: 2.5rem; }}
            .header p {{ font-size: 1.2rem; }}
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.8rem;
            padding: 1.2rem;
            background: #f8f9fa;
        }}
        @media (min-width: 768px) {{
            .stats-grid {{
                grid-template-columns: repeat(4, 1fr);
                gap: 1.2rem;
                padding: 1.5rem;
            }}
        }}
        
        .stat-card {{
            background: white;
            padding: 1.2rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{ 
            color: #2a5298; 
            font-size: 2rem; 
            margin-bottom: 0.3rem;
            font-weight: 700;
        }}
        .stat-card p {{ color: #666; font-size: 0.85rem; }}
        .stat-card.strong {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; }}
        .stat-card.strong h3 {{ color: white; }}
        .stat-card.strong p {{ color: rgba(255,255,255,0.9); }}
        
        .section {{ padding: 1.5rem; }}
        @media (min-width: 768px) {{ .section {{ padding: 2rem; }} }}
        
        .section h2 {{
            color: #333;
            margin-bottom: 1.2rem;
            padding-bottom: 0.5rem;
            border-bottom: 3px solid #2a5298;
            font-size: 1.3rem;
        }}
        
        .strategy-box {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            border-left: 4px solid #2a5298;
        }}
        .strategy-box h3 {{ color: #2a5298; margin-bottom: 1rem; font-size: 1.1rem; }}
        .strategy-box ul {{ margin-left: 1.2rem; }}
        .strategy-box li {{ margin: 0.6rem 0; font-size: 0.95rem; color: #555; }}
        
        .badge {{
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-strong {{ background: #ff6b6b; color: white; }}
        .badge-buy {{ background: #2ed573; color: white; }}
        .badge-watch {{ background: #ffa502; color: white; }}
        
        .table-container {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin: 1rem 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        table {{
            width: 100%;
            min-width: 800px;
            border-collapse: collapse;
            font-size: 0.85rem;
            background: white;
        }}
        @media (min-width: 768px) {{ table {{ font-size: 0.9rem; }} }}
        
        th {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 1rem 0.5rem;
            text-align: left;
            font-weight: 600;
            white-space: nowrap;
            position: sticky;
            top: 0;
        }}
        td {{ padding: 0.8rem 0.5rem; border-bottom: 1px solid #eee; white-space: nowrap; }}
        tr:hover {{ background: #f8f9fa; }}
        
        .price {{ text-align: right; font-family: 'Courier New', monospace; }}
        .score-high {{ color: #ff6b6b; font-weight: bold; }}
        .score-medium {{ color: #2ed573; font-weight: bold; }}
        .score-low {{ color: #ffa502; font-weight: bold; }}
        
        .pyramid-info {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }}
        .pyramid-step {{
            background: #e3f2fd;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            color: #1976d2;
        }}
        
        .scroll-hint {{
            text-align: center;
            padding: 0.5rem;
            color: #999;
            font-size: 0.8rem;
            display: block;
        }}
        @media (min-width: 768px) {{ .scroll-hint {{ display: none; }} }}
        
        .footer {{
            background: #f8f9fa;
            padding: 1.5rem;
            text-align: center;
            color: #666;
            font-size: 0.85rem;
        }}
        
        .disclaimer {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            font-size: 0.85rem;
            color: #856404;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 Livermore Strategy Report</h1>
            <p>Jesse Livermore Pivot Point Analysis</p>
            <p class="subtitle">Scan Date: {self.scan_date or datetime.now().strftime('%Y-%m-%d')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{total}</h3>
                <p>총 신호</p>
            </div>
            <div class="stat-card strong">
                <h3>{strong_buy}</h3>
                <p>강력매수</p>
            </div>
            <div class="stat-card">
                <h3>{kospi_count}</h3>
                <p>KOSPI</p>
            </div>
            <div class="stat-card">
                <h3>{kosdaq_count}</h3>
                <p>KOSDAQ</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 전략 설명</h2>
            
            <div class="strategy-box">
                <h3>📊 진입 조건 (Pivot Point Breakout)</h3>
                <ul>
                    <li><strong>전환점 돌파:</strong> 20일 또는 60일 신고가 돌파</li>
                    <li><strong>거래량 확인:</strong> 당일 거래량 > 20일 평균의 150%</li>
                    <li><strong>가격 돌파 강도:</strong> 신고가 대비 돌파 폭 측정</li>
                    <li><strong>추세 확인:</strong> 20일 이동평균선 상회</li>
                </ul>
            </div>
            
            <div class="strategy-box">
                <h3>🏗️ 피라미딩 (Pyramiding) 전략</h3>
                <ul>
                    <li><strong>1차 진입:</strong> 신호 발생 시 30% 매수</li>
                    <li><strong>2차 진입:</strong> 1차 진입가 대비 +5% 상승 시 30% 추가</li>
                    <li><strong>3차 진입:</strong> 2차 진입가 대비 +5% 상승 시 40% 추가</li>
                </ul>
            </div>
            
            <div class="strategy-box">
                <h3>🛡️ 리스크 관리 (Exit Strategy)</h3>
                <ul>
                    <li><strong>손절 (Stop Loss):</strong> 평균단가 대비 -10% 하띂 시 전량 매도</li>
                    <li><strong>익절 (Trailing Stop):</strong> 최고점 대비 -15% 하락 시 수익 실현</li>
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 TOP 50 Signals</h2>
            
            <div class="disclaimer">
                ⚠️ <strong>투자 유의사항:</strong> 본 리포트는 기술적 분석 기반 참고자료이며, 
                실제 투자는 본인의 판단과 책임하에 진행하시기 바랍니다. 과거 수익률이 미래 수익률을 보장하지 않습니다.
            </div>
            
            <p class="scroll-hint">← 좌우로 스와이프하여 더 보기 →</p>
            
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>순위</th>
                            <th>종목</th>
                            <th>등급</th>
                            <th>점수</th>
                            <th>현재가</th>
                            <th>거래량</th>
                            <th>1차진입</th>
                            <th>손절가</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        # 테이블 행 생성
        for i, (_, row) in enumerate(top50.iterrows(), 1):
            # 등급에 따른 배지
            if row['signal_grade'] == 'STRONG_BUY':
                badge = '<span class="badge badge-strong">강력매수</span>'
                score_class = 'score-high'
            elif row['signal_grade'] == 'BUY':
                badge = '<span class="badge badge-buy">매수</span>'
                score_class = 'score-medium'
            else:
                badge = '<span class="badge badge-watch">관망</span>'
                score_class = 'score-low'
            
            html += f"""
                        <tr>
                            <td>{i}</td>
                            <td><strong>{row['name']}</strong><br><small>{row['code']}</small></td>
                            <td>{badge}</td>
                            <td class="{score_class}">{row['score']:.1f}</td>
                            <td class="price">{row['current_price']:,.0f}</td>
                            <td>{row['volume_ratio']:.1f}x</td>
                            <td class="price">{row['entry_1']:,.0f}</td>
                            <td class="price" style="color:#ff6b6b">{row['stop_loss']:,.0f}</td>
                        </tr>
"""
        
        html += """
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 KStock Analyzer | Jesse Livermore Strategy</p>
            <p>⚠️ 본 리포트는 투자 참고용이며, 실제 투자는 본인의 판단과 책임하에 진행하시기 바랍니다.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_visualization(self, df: pd.DataFrame):
        """시각화 생성"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 점수 분포
        ax1 = axes[0, 0]
        score_counts = df['signal_grade'].value_counts()
        colors = {'STRONG_BUY': '#ff6b6b', 'BUY': '#2ed573', 'WATCH': '#ffa502'}
        ax1.pie(score_counts.values, labels=score_counts.index, autopct='%1.1f%%',
                colors=[colors.get(x, '#999') for x in score_counts.index])
        ax1.set_title('Signal Grade Distribution', fontsize=12, fontweight='bold')
        
        # 2. 시장별 분포
        ax2 = axes[0, 1]
        market_counts = df['market'].value_counts()
        ax2.bar(market_counts.index, market_counts.values, color=['#2a5298', '#1e3c72'])
        ax2.set_title('Market Distribution', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Count')
        
        # 3. 거래량 vs 점수
        ax3 = axes[1, 0]
        scatter = ax3.scatter(df['volume_ratio'], df['score'], 
                            c=df['score'], cmap='RdYlGn', alpha=0.6, s=50)
        ax3.set_xlabel('Volume Ratio')
        ax3.set_ylabel('Score')
        ax3.set_title('Volume Ratio vs Score', fontsize=12, fontweight='bold')
        plt.colorbar(scatter, ax=ax3)
        
        # 4. 돌파 강도 분포
        ax4 = axes[1, 1]
        ax4.hist(df['break_strength'], bins=20, color='#2a5298', alpha=0.7, edgecolor='black')
        ax4.set_xlabel('Break Strength (%)')
        ax4.set_ylabel('Count')
        ax4.set_title('Break Strength Distribution', fontsize=12, fontweight='bold')
        ax4.axvline(df['break_strength'].mean(), color='red', linestyle='--', 
                   label=f'Mean: {df["break_strength"].mean():.1f}%')
        ax4.legend()
        
        plt.tight_layout()
        
        # 저장
        os.makedirs('reports', exist_ok=True)
        output_path = 'reports/livermore_analysis.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📊 시각화 저장됨: {output_path}")
        return output_path
    
    def generate_report(self):
        """리포트 생성 메인"""
        print("\n" + "="*70)
        print("📝 Jesse Livermore Strategy Report Generator")
        print("="*70)
        
        # 데이터 로드
        df = self.load_data()
        if df.empty:
            print("❌ 스캔 데이터가 없습니다. 먼저 scanner_livermore.py를 실행하세요.")
            return False
        
        # HTML 생성
        print("\n🌐 HTML 리포트 생성 중...")
        html = self.generate_html(df)
        
        output_file = 'docs/livermore_report.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML 리포트: {output_file}")
        
        # 시각화 생성
        print("\n📊 시각화 생성 중...")
        viz_path = self.generate_visualization(df)
        
        # 요약 출력
        print("\n" + "="*70)
        print("📈 리포트 요약")
        print("="*70)
        print(f"총 신호: {len(df)}개")
        print(f"강력매수: {len(df[df['signal_grade']=='STRONG_BUY'])}개")
        print(f"매수: {len(df[df['signal_grade']=='BUY'])}개")
        print(f"관망: {len(df[df['signal_grade']=='WATCH'])}개")
        print(f"KOSPI: {len(df[df['market']=='KOSPI'])}개")
        print(f"KOSDAQ: {len(df[df['market']=='KOSDAQ'])}개")
        print("="*70)
        
        return True


if __name__ == '__main__':
    generator = LivermoreReportGenerator()
    success = generator.generate_report()
    
    if success:
        print("\n🌐 리포트 URL:")
        print("   https://lubanana.github.io/kstock-dashboard/livermore_report.html")
