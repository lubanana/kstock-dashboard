#!/usr/bin/env python3
"""
Combined Strategy Report Generator
오닐 CANSLIM + 미니버니 SEPA 통합 리포트 생성기

Features:
- 두 전략 결과 병합
- 중복 종목 강조
- 종합 점수 계산
- HTML 리포트 생성
"""

import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple


class CombinedStrategyReport:
    """통합 전략 리포트 생성기"""
    
    def __init__(self):
        self.oneil_data = None
        self.minervini_data = None
        self.combined_data = None
    
    def load_oneil_data(self) -> pd.DataFrame:
        """오닐 데이터 로드 (병렬 결과 우선)"""
        try:
            # 병렬 결과 먼저 시도
            try:
                with open('data/oneil_parallel_results.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stocks = data.get('stocks', [])
                    df = pd.DataFrame(stocks)
                    df['strategy'] = 'ONeil'
                    print(f"✅ 오닐 데이터 (병렬): {len(df)}개 종목")
                    return df
            except:
                with open('data/oneil_scan_results.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stocks = data.get('stocks', [])
                    df = pd.DataFrame(stocks)
                    df['strategy'] = 'ONeil'
                    print(f"✅ 오닐 데이터: {len(df)}개 종목")
                    return df
        except Exception as e:
            print(f"❌ 오닐 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def load_minervini_data(self) -> pd.DataFrame:
        """미니버니 데이터 로드 (병렬 결과 우선)"""
        try:
            # 병렬 결과 먼저 시도
            try:
                with open('data/minervini_parallel_results.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stocks = data.get('stocks', [])
                    df = pd.DataFrame(stocks)
                    df['strategy'] = 'Minervini'
                    print(f"✅ 미니버니 데이터 (병렬): {len(df)}개 종목")
                    return df
            except:
                with open('data/minervini_scan_results.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stocks = data.get('stocks', [])
                    df = pd.DataFrame(stocks)
                    df['strategy'] = 'Minervini'
                    print(f"✅ 미니버니 데이터: {len(df)}개 종목")
                    return df
        except Exception as e:
            print(f"❌ 미니버니 데이터 로드 실패: {e}")
            return pd.DataFrame()
    
    def combine_data(self, oneil_df: pd.DataFrame, minervini_df: pd.DataFrame) -> pd.DataFrame:
        """데이터 병합 및 중복 처리"""
        if oneil_df.empty and minervini_df.empty:
            return pd.DataFrame()
        
        # 컬럼명 통일
        column_mapping = {
            'setup_quality': 'score',
            'composite_score': 'score',
            'signal_type': 'signal',
            'entry_price': 'entry',
            'stop_loss': 'stop',
            'target_price': 'target'
        }
        
        for old, new in column_mapping.items():
            if old in oneil_df.columns:
                oneil_df = oneil_df.rename(columns={old: new})
            if old in minervini_df.columns:
                minervini_df = minervini_df.rename(columns={old: new})
        
        # 병합
        combined = pd.concat([oneil_df, minervini_df], ignore_index=True)
        
        # 코드별 그룹화 (중복 종목 처리)
        grouped = combined.groupby('code').agg({
            'name': 'first',
            'market': 'first',
            'score': 'max',
            'strategy': lambda x: ', '.join(sorted(set(x))),
            'signal': lambda x: ', '.join(sorted(set(x))),
            'entry': 'first',
            'stop': 'first',
            'target': 'first'
        }).reset_index()
        
        # 복합 전략 여부
        grouped['is_combo'] = grouped['strategy'].str.contains(',')
        
        # 종합 점수 (복합 전략 볼너스)
        grouped['final_score'] = grouped.apply(
            lambda x: x['score'] * 1.1 if x['is_combo'] else x['score'], axis=1
        )
        
        # 정렬
        grouped = grouped.sort_values('final_score', ascending=False)
        
        return grouped
    
    def generate_html(self, df: pd.DataFrame) -> str:
        """HTML 리포트 생성"""
        
        # 통계 계산
        total = len(df)
        combo_count = len(df[df['is_combo'] == True])
        oneil_only = len(df[df['strategy'] == 'ONeil'])
        minervini_only = len(df[df['strategy'] == 'Minervini'])
        
        # 상위 50개
        top50 = df.head(50)
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>O'Neil + Minervini Combined Strategy Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', -apple-system, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.2em; opacity: 0.9; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{ color: #667eea; font-size: 2.5em; margin-bottom: 5px; }}
        .stat-card p {{ color: #666; }}
        .highlight {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }}
        .highlight h3 {{ color: white; }}
        .section {{ padding: 30px; }}
        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .combo-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 0.75em;
            font-weight: bold;
            margin-left: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 0.95em;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 10px;
            text-align: left;
            font-weight: 600;
        }}
        td {{ padding: 12px 10px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f5f5f5; }}
        tr.combo {{ background: #fff3f3; }}
        .score-high {{ color: #e74c3c; font-weight: bold; }}
        .score-medium {{ color: #f39c12; font-weight: bold; }}
        .strategy-oneil {{ color: #3498db; }}
        .strategy-minervini {{ color: #9b59b6; }}
        .strategy-combo {{ color: #e74c3c; font-weight: bold; }}
        .methodology {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 15px;
            margin: 20px 0;
        }}
        .methodology h3 {{ color: #667eea; margin-bottom: 15px; }}
        .methodology ul {{ margin-left: 20px; line-height: 1.8; }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Combined Strategy Report</h1>
            <p>O'Neil CANSLIM + Minervini SEPA Integration</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{total}</h3>
                <p>총 신호 종목</p>
            </div>
            <div class="stat-card highlight">
                <h3>{combo_count}</h3>
                <p>🔥 복합 전략 (중복)</p>
            </div>
            <div class="stat-card">
                <h3>{oneil_only}</h3>
                <p>오닐 전용</p>
            </div>
            <div class="stat-card">
                <h3>{minervini_only}</h3>
                <p>미니버니 전용</p>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 전략 비교</h2>
            <div class="methodology">
                <h3>O'Neil CANSLIM</h3>
                <ul>
                    <li>52주 신고가 근접 + 거래량 급증</li>
                    <li>이동평균선 정렬 확인</li>
                    <li>강력한 추세 확인</li>
                    <li>감지 신호: {oneil_only + combo_count}개</li>
                </ul>
            </div>
            
            <div class="methodology">
                <h3>Minervini SEPA</h3>
                <ul>
                    <li>Trend Template 통과 (150>200일선)</li>
                    <li>VCP (변동성 수축 패턴)</li>
                    <li>박스권 수축 후 돌파</li>
                    <li>감지 신호: {minervini_only + combo_count}개</li>
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 TOP 50 Combined Signals</h2>
            <div style="margin-bottom: 15px;">
                <span style="color: #e74c3c; font-weight: bold;">★ 복합 전략 (양쪽 모두 감지)</span>
                <span style="margin-left: 20px; color: #3498db;">오닐 전용</span>
                <span style="margin-left: 20px; color: #9b59b6;">미니버니 전용</span>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>종목코드</th>
                        <th>종목명</th>
                        <th>전략</th>
                        <th>기본점수</th>
                        <th>최종점수</th>
                        <th>신호</th>
                        <th>진입가</th>
                        <th>목표가</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # 테이블 행 생성
        for i, (_, row) in enumerate(top50.iterrows(), 1):
            combo_class = 'combo' if row['is_combo'] else ''
            combo_badge = '<span class="combo-badge">COMBO</span>' if row['is_combo'] else ''
            
            # 전략에 따른 색상
            if row['is_combo']:
                strategy_class = 'strategy-combo'
            elif 'ONeil' in row['strategy']:
                strategy_class = 'strategy-oneil'
            else:
                strategy_class = 'strategy-minervini'
            
            # 점수 색상
            if row['final_score'] >= 80:
                score_class = 'score-high'
            elif row['final_score'] >= 65:
                score_class = 'score-medium'
            else:
                score_class = ''
            
            entry_val = row.get('entry', 0)
            target_val = row.get('target', 0)
            
            try:
                entry = f"{float(entry_val):,.0f}" if pd.notna(entry_val) and entry_val != '' else '-'
            except:
                entry = '-'
            
            try:
                target = f"{float(target_val):,.0f}" if pd.notna(target_val) and target_val != '' else '-'
            except:
                target = '-'
            
            html += f"""
                    <tr class="{combo_class}">
                        <td>{i}</td>
                        <td>{row['code']}</td>
                        <td><strong>{row['name']}</strong>{combo_badge}</td>
                        <td class="{strategy_class}">{row['strategy']}</td>
                        <td>{row['score']:.1f}</td>
                        <td class="{score_class}">{row['final_score']:.1f}</td>
                        <td>{row.get('signal', '-')}</td>
                        <td>{entry}</td>
                        <td>{target}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>© 2026 KStock Analyzer | O'Neil CANSLIM + Minervini SEPA Integration</p>
            <p>⚠️ 본 리포트는 투자 참고용이며, 실제 투자는 본인의 판단과 책임하에 진행하시기 바랍니다.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_report(self):
        """리포트 생성 메인"""
        print("\n" + "="*70)
        print("🚀 Combined Strategy Report Generator")
        print("="*70)
        
        # 데이터 로드
        print("\n📊 데이터 로드 중...")
        oneil_df = self.load_oneil_data()
        minervini_df = self.load_minervini_data()
        
        if oneil_df.empty and minervini_df.empty:
            print("❌ 데이터가 없습니다. 먼저 스캔을 실행해주세요.")
            return False
        
        # 데이터 병합
        print("\n🔗 데이터 병합 중...")
        combined_df = self.combine_data(oneil_df, minervini_df)
        
        if combined_df.empty:
            print("❌ 병합된 데이터가 없습니다.")
            return False
        
        # 통계 출력
        combo_count = len(combined_df[combined_df['is_combo'] == True])
        print(f"\n📈 병합 결과:")
        print(f"   총 종목: {len(combined_df)}")
        print(f"   복합 전략: {combo_count}개")
        print(f"   오닐 전용: {len(combined_df[combined_df['strategy'] == 'ONeil'])}개")
        print(f"   미니버니 전용: {len(combined_df[combined_df['strategy'] == 'Minervini'])}개")
        
        # HTML 생성
        print("\n📝 HTML 리포트 생성 중...")
        html = self.generate_html(combined_df)
        
        # 파일 저장
        output_file = 'docs/combined_strategy_report.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ 리포트 생성 완료!")
        print(f"   파일: {output_file}")
        
        # JSON 저장
        combined_df.to_json('data/combined_strategy_results.json', 
                           orient='records', force_ascii=False, indent=2)
        print(f"   데이터: data/combined_strategy_results.json")
        
        return True


if __name__ == '__main__':
    generator = CombinedStrategyReport()
    success = generator.generate_report()
    
    if success:
        print("\n" + "="*70)
        print("🌐 리포트 URL:")
        print("   https://lubanana.github.io/kstock-dashboard/combined_strategy_report.html")
        print("="*70)
