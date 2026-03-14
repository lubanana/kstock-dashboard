#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
February 2026 Monthly Buy Strength Report Generator
====================================================
2026년 2월 한 달간 매일 Buy Strength 스캔 수행 및 월간 리포트 생성

- 2026-02-01 ~ 2026-02-28 기간 매일 스캔
- 누적 데이터 분석
- 월간 집계 리포트 (HTML) 생성
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import sqlite3

from buy_strength_scanner import BuyStrengthScanner


def get_trading_days(year: int, month: int) -> list:
    """해당 연월의 영업일 목록 반환"""
    trading_days = []
    start_date = datetime(year, month, 1)
    
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    current = start_date
    while current < end_date:
        if current.weekday() < 5:  # 월~금
            trading_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return trading_days


def scan_single_day(scan_date: str, db_path: str = './data/pivot_strategy.db') -> list:
    """
    단일 일자 스캔 수행
    
    Returns:
        list of dict: 해당 일자의 신호 종목들
    """
    print(f"📅 {scan_date} 스캔 중...")
    
    scanner = BuyStrengthScanner(
        db_path=db_path,
        min_amount=1e9,
        min_price=1000
    )
    
    # 종목 리스트 로드
    with open('./data/stock_list.json', 'r') as f:
        stocks_data = json.load(f)
    stocks = pd.DataFrame(stocks_data['stocks'])
    
    results = []
    
    for _, row in stocks.iterrows():
        try:
            symbol = row['symbol']
            
            # 해당 날짜 기준 데이터 조회
            conn = sqlite3.connect(db_path)
            query = """
                SELECT * FROM stock_prices 
                WHERE symbol = ? AND date <= ?
                ORDER BY date
            """
            df = pd.read_sql_query(query, conn, params=(symbol, scan_date))
            conn.close()
            
            if len(df) < 60:
                continue
            
            # 분석
            df.columns = [c.lower() for c in df.columns]
            current = df.iloc[-1]
            current_price = current['close']
            current_volume = current['volume']
            amount = current_price * current_volume
            
            if amount < 1e9 or current_price < 1000:
                continue
            
            # 점수 계산
            trend_score, _ = scanner.calculate_trend_score(df)
            momentum_score, momentum_metrics = scanner.calculate_momentum_score(df)
            volume_score, volume_metrics = scanner.calculate_volume_score(df)
            
            total_score = trend_score + momentum_score + volume_score
            
            if total_score >= 60:  # 60점 이상만 기록
                results.append({
                    'scan_date': scan_date,
                    'symbol': symbol,
                    'name': row['name'],
                    'market': row['market'],
                    'price': current_price,
                    'amount': amount / 1e8,
                    'total_score': total_score,
                    'trend_score': trend_score,
                    'momentum_score': momentum_score,
                    'volume_score': volume_score,
                    'rsi': momentum_metrics.get('rsi14', 0),
                    'volume_ratio': volume_metrics.get('volume_ratio', 0),
                    'grade': 'A' if total_score >= 80 else 'B' if total_score >= 60 else 'C'
                })
                
        except Exception as e:
            continue
    
    print(f"   ✅ {len(results)}개 신호 발견")
    return results


def generate_february_2026_report():
    """2026년 2월 월간 리포트 생성"""
    print("=" * 70)
    print("📊 2026년 2월 Buy Strength 월간 리포트 생성")
    print("=" * 70)
    
    # 2월 영업일 목록
    trading_days = get_trading_days(2026, 2)
    print(f"📅 총 {len(trading_days)}개 영업일")
    print(f"   기간: {trading_days[0]} ~ {trading_days[-1]}\n")
    
    # 매일 스캔 수행
    all_signals = []
    daily_stats = []
    
    for scan_date in trading_days:
        signals = scan_single_day(scan_date)
        all_signals.extend(signals)
        
        daily_stats.append({
            'date': scan_date,
            'total_signals': len(signals),
            'a_grade': len([s for s in signals if s['grade'] == 'A']),
            'b_grade': len([s for s in signals if s['grade'] == 'B']),
            'avg_score': np.mean([s['total_score'] for s in signals]) if signals else 0
        })
    
    # DataFrame 변환
    df_all = pd.DataFrame(all_signals)
    df_daily = pd.DataFrame(daily_stats)
    
    # 종목별 집계
    symbol_stats = df_all.groupby(['symbol', 'name', 'market']).agg({
        'scan_date': 'count',  # 발굴 횟수
        'total_score': ['mean', 'max', 'min'],  # 평균/최고/최저 점수
        'price': ['first', 'last'],  # 기간 초/종가
        'amount': 'mean'  # 평균 거래대금
    }).reset_index()
    
    symbol_stats.columns = ['종목코드', '종목명', '시장', '발굴횟수', '평균점수', '최고점수', '최저점수', '시작가', '종료가', '평균거래대금']
    symbol_stats['수익률'] = ((symbol_stats['종료가'] / symbol_stats['시작가']) - 1) * 100
    symbol_stats = symbol_stats.sort_values(['발굴횟수', '평균점수'], ascending=[False, False])
    
    # 저장
    output_dir = Path('./reports/buy_strength_monthly')
    output_dir.mkdir(exist_ok=True)
    
    df_all.to_csv(output_dir / 'feb2026_all_signals.csv', index=False, encoding='utf-8-sig')
    df_daily.to_csv(output_dir / 'feb2026_daily_stats.csv', index=False, encoding='utf-8-sig')
    symbol_stats.to_csv(output_dir / 'feb2026_symbol_summary.csv', index=False, encoding='utf-8-sig')
    
    # 결과 출력
    print("\n" + "=" * 70)
    print("📈 월간 집계 결과")
    print("=" * 70)
    print(f"총 신호 수: {len(df_all):,}건")
    print(f"발굴 종목 수: {len(symbol_stats)}개")
    print(f"일 평균 신호: {len(df_all)/len(trading_days):.1f}개")
    print(f"\nA등급 빈도: {len(df_all[df_all['grade']=='A'])}회")
    print(f"B등급 빈도: {len(df_all[df_all['grade']=='B'])}회")
    
    print("\n📊 발굴 빈도 TOP 10:")
    print(symbol_stats.head(10)[['종목코드', '종목명', '발굴횟수', '평균점수', '수익률']].to_string(index=False))
    
    print("\n💰 수익률 TOP 5:")
    top_return = symbol_stats.nlargest(5, '수익률')
    print(top_return[['종목코드', '종목명', '발굴횟수', '수익률']].to_string(index=False))
    
    # HTML 리포트 생성
    generate_monthly_html(df_all, df_daily, symbol_stats, trading_days, output_dir)
    
    return df_all, df_daily, symbol_stats


def generate_monthly_html(df_all, df_daily, symbol_stats, trading_days, output_dir):
    """월간 HTML 리포트 생성"""
    
    # 차트용 데이터 준비
    top_symbols = symbol_stats.head(20)
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Buy Strength 월간 리포트 - 2026년 2월</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{ font-family: 'Noto Sans KR', sans-serif; }}
        body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .glass {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }}
        .grade-a {{ background: linear-gradient(135deg, #10b981, #059669); }}
    </style>
</head>
<body class="py-8 px-4">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-10">
            <h1 class="text-4xl font-bold text-white mb-3">📊 Buy Strength 월간 리포트</h1>
            <p class="text-white/80 text-lg">2026년 2월 ({len(trading_days)}거래일)</p>
        </div>

        <!-- Summary Cards -->
        <div class="glass rounded-2xl p-6 mb-8 shadow-2xl">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="text-center p-4 bg-blue-50 rounded-lg">
                    <div class="text-3xl font-bold text-blue-600">{len(df_all)}</div>
                    <div class="text-sm text-gray-600">총 신호</div>
                </div>
                <div class="text-center p-4 bg-green-50 rounded-lg">
                    <div class="text-3xl font-bold text-green-600">{len(symbol_stats)}</div>
                    <div class="text-sm text-gray-600">발굴 종목</div>
                </div>
                <div class="text-center p-4 bg-purple-50 rounded-lg">
                    <div class="text-3xl font-bold text-purple-600">{len(df_all[df_all['grade']=='A'])}</div>
                    <div class="text-sm text-gray-600">A등급</div>
                </div>
                <div class="text-center p-4 bg-orange-50 rounded-lg">
                    <div class="text-3xl font-bold text-orange-600">{len(df_all)/len(trading_days):.1f}</div>
                    <div class="text-sm text-gray-600">일평균 신호</div>
                </div>
            </div>
        </div>

        <!-- Daily Trend Chart -->
        <div class="glass rounded-2xl p-6 mb-8 shadow-2xl">
            <h2 class="text-xl font-bold mb-4">📈 일별 신호 추이</h2>
            <canvas id="dailyChart" height="100"></canvas>
        </div>

        <!-- Top Symbols Table -->
        <div class="glass rounded-2xl p-6 mb-8 shadow-2xl">
            <h2 class="text-xl font-bold mb-4">🏆 발굴 빈도 TOP 20</h2>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-3 py-2 text-left text-sm">순위</th>
                            <th class="px-3 py-2 text-left text-sm">종목코드</th>
                            <th class="px-3 py-2 text-left text-sm">종목명</th>
                            <th class="px-3 py-2 text-center text-sm">발굴횟수</th>
                            <th class="px-3 py-2 text-center text-sm">평균점수</th>
                            <th class="px-3 py-2 text-center text-sm">수익률</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for idx, (_, row) in enumerate(top_symbols.iterrows(), 1):
        return_class = 'text-green-600' if row['수익률'] > 0 else 'text-red-600'
        html += f"""
                        <tr class="border-b hover:bg-gray-50">
                            <td class="px-3 py-3">{idx}</td>
                            <td class="px-3 py-3 font-bold">{row['종목코드']}</td>
                            <td class="px-3 py-3">{row['종목명']}</td>
                            <td class="px-3 py-3 text-center">
                                <span class="px-2 py-1 rounded text-white grade-a text-sm font-bold">{int(row['발굴횟수'])}</span>
                            </td>
                            <td class="px-3 py-3 text-center">{row['평균점수']:.1f}</td>
                            <td class="px-3 py-3 text-center font-bold {return_class}">{row['수익률']:+.1f}%</td>
                        </tr>
"""
    
    html += """
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            // Daily Chart
            const ctx = document.getElementById('dailyChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: """ + str(list(df_daily['date'])) + """,
                    datasets: [{
                        label: '총 신호',
                        data: """ + str(list(df_daily['total_signals'])) + """,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'A등급',
                        data: """ + str(list(df_daily['a_grade'])) + """,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    interaction: { intersect: false, mode: 'index' },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#f0f0f0' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        </script>
    </div>
</body>
</html>
"""
    
    # HTML 저장
    with open(output_dir / 'feb2026_monthly_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n📄 HTML 리포트 저장: {output_dir / 'feb2026_monthly_report.html'}")


if __name__ == "__main__":
    generate_february_2026_report()
    print("\n✅ 월간 리포트 생성 완료!")
