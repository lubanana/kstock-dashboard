#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEPA + VCP Multi-Stock Scanner
==============================
Mark Minervini SEPA 전략 + VCP 패턴 다중 종목 스캐너

- 한국 주식 시장 전 종목 스캔
- RS (Relative Strength) 순위 계산
- 결과 CSV/HTML 리포트 생성
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json

from sepa_vcp_strategy import SEPA_VCP_Strategy, SEPASignal
from sepa_vcp_visualizer import SEPA_VCP_Visualizer
from local_db import LocalDatabase
from fdr_wrapper import FDRWrapper


class SEPAVCPScanner:
    """SEPA + VCP 패턴 멀티 스캐너"""
    
    def __init__(self, 
                 db_path: str = './data/pivot_strategy.db',
                 output_dir: str = './reports/sepa',
                 max_workers: int = 4):
        
        self.db = LocalDatabase(db_path)
        self.fdr = FDRWrapper(db_path)
        self.strategy = SEPA_VCP_Strategy()
        self.visualizer = SEPA_VCP_Visualizer()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        
        # 시장 데이터 캐시
        self.market_data_cache = {}
        
    def get_market_data(self, market: str = 'KOSPI', days: int = 300) -> pd.DataFrame:
        """시장 데이터 로드 (RS 계산용)"""
        cache_key = f"{market}_{days}"
        if cache_key in self.market_data_cache:
            return self.market_data_cache[cache_key]
        
        # KOSPI/KOSDAQ 지수 데이터
        if market == 'KOSPI':
            df = self.fdr.get_price('^KS11', days=days)
        else:  # KOSDAQ
            df = self.fdr.get_price('^KQ11', days=days)
        
        if df is not None and not df.empty:
            self.market_data_cache[cache_key] = df
            return df
        return None
    
    def scan_symbol(self, symbol: str, market: str = 'KOSPI', days: int = 300) -> Optional[SEPASignal]:
        """
        단일 종목 스캔
        
        Args:
            symbol: 종목코드
            market: 시장 구분
            days: 분석 기간
        
        Returns:
            SEPASignal 또는 None
        """
        try:
            # 주가 데이터 로드
            df = self.fdr.get_price(symbol, days=days)
            if df is None or df.empty or len(df) < 252:
                return None
            
            # 컬럼명 통일
            df.columns = [c.lower() for c in df.columns]
            if 'date' not in df.columns:
                df.reset_index(inplace=True)
                if 'index' in df.columns:
                    df.rename(columns={'index': 'date'}, inplace=True)
            
            # 시장 데이터 로드 (RS 계산용)
            market_df = self.get_market_data(market, days)
            
            # 분석 실행
            signal = self.strategy.analyze_symbol(symbol, df, market_df)
            
            # 시장 정보 추가
            if signal:
                signal.market = market
            
            return signal
            
        except Exception as e:
            print(f"❌ Error scanning {symbol}: {e}")
            return None
    
    def scan_all(self, market: str = 'ALL', limit: Optional[int] = None,
                 min_score: int = 50) -> pd.DataFrame:
        """
        전 종목 스캔
        
        Args:
            market: 'KOSPI', 'KOSDAQ', 또는 'ALL'
            limit: 최대 스캔 종목 수
            min_score: 최소 점수
        
        Returns:
            결과 DataFrame
        """
        # 종목 리스트 로드
        if market == 'ALL':
            stocks = self.db.get_all_stocks()
        else:
            stocks = self.db.get_stocks_by_market(market)
        
        if limit:
            stocks = stocks.head(limit)
        
        print(f"🔍 Scanning {len(stocks)} stocks for SEPA + VCP patterns...")
        
        results = []
        valid_signals = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.scan_symbol, row['symbol'], row['market']): row 
                for _, row in stocks.iterrows()
            }
            
            for future in as_completed(future_to_symbol):
                row = future_to_symbol[future]
                try:
                    signal = future.result()
                    if signal and signal.score >= min_score:
                        results.append({
                            'symbol': signal.symbol,
                            'market': row['market'],
                            'name': row['name'],
                            'date': signal.date,
                            'close': signal.current_price,
                            'score': signal.score,
                            'trend_template': signal.trend_template_passed,
                            'vcp_passed': signal.vcp_passed,
                            'contraction_count': signal.contraction_count,
                            'depth_narrowing': signal.depth_narrowing,
                            'duration_shortening': signal.duration_shortening,
                            'volume_dry_up': signal.volume_dry_up,
                            'volume_surge': signal.volume_surge,
                            'volume_ratio': signal.volume_ratio,
                            'pivot_line': signal.pivot_line,
                            'pivot_breakout': signal.pivot_breakout,
                            'relative_strength': signal.relative_strength,
                            'rs_top25': signal.rs_top25,
                            'is_valid': signal.is_valid
                        })
                        valid_signals.append(signal)
                        print(f"✅ {signal.symbol}: Score {signal.score}")
                except Exception as e:
                    print(f"❌ Error processing {row['symbol']}: {e}")
        
        # 결과 정렬
        if results:
            df_results = pd.DataFrame(results)
            df_results = df_results.sort_values('score', ascending=False)
            
            # RS 순위 계산
            if len(df_results) > 0:
                df_results['rs_rank'] = df_results['relative_strength'].rank(pct=True)
                df_results['rs_top25'] = df_results['rs_rank'] >= 0.75
            
            print(f"\n📊 Found {len(df_results)} stocks with score >= {min_score}")
            print(f"📈 Valid SEPA + VCP signals: {df_results['is_valid'].sum()}")
            
            return df_results, valid_signals
        
        return pd.DataFrame(), []
    
    def save_results(self, df: pd.DataFrame, filename_prefix: str = 'sepa_scan'):
        """결과 저장"""
        if df.empty:
            print("⚠️ No results to save")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d')
        
        # CSV 저장
        csv_path = self.output_dir / f"{filename_prefix}_{timestamp}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"💾 CSV saved: {csv_path}")
        
        # Excel 저장
        excel_path = self.output_dir / f"{filename_prefix}_{timestamp}.xlsx"
        df.to_excel(excel_path, index=False, sheet_name='SEPA_VCP')
        print(f"💾 Excel saved: {excel_path}")
        
        return csv_path, excel_path
    
    def generate_charts(self, valid_signals: List[SEPASignal], top_n: int = 10):
        """상위 종목 차트 생성"""
        print(f"\n📈 Generating charts for top {top_n} stocks...")
        
        chart_paths = []
        for signal in valid_signals[:top_n]:
            try:
                # 데이터 로드
                df = self.fdr.get_price(signal.symbol, days=300)
                if df is not None and not df.empty:
                    df.columns = [c.lower() for c in df.columns]
                    if 'date' not in df.columns:
                        df.reset_index(inplace=True)
                        if 'index' in df.columns:
                            df.rename(columns={'index': 'date'}, inplace=True)
                    
                    # 차트 생성
                    chart_path = self.output_dir / f"{signal.symbol}_sepa_{signal.date.strftime('%Y%m%d')}.png"
                    self.visualizer.plot_matplotlib(df, signal, str(chart_path))
                    chart_paths.append(chart_path)
                    
                    # 인터랙티브 차트
                    html_path = self.output_dir / f"{signal.symbol}_sepa_{signal.date.strftime('%Y%m%d')}.html"
                    self.visualizer.plot_plotly(df, signal, str(html_path))
                    chart_paths.append(html_path)
                    
            except Exception as e:
                print(f"❌ Error generating chart for {signal.symbol}: {e}")
        
        print(f"✅ Generated {len(chart_paths)} charts")
        return chart_paths
    
    def generate_report(self, df: pd.DataFrame, valid_signals: List[SEPASignal]):
        """HTML 리포트 생성"""
        from sepa_vcp_visualizer import SEPA_VCP_Visualizer
        
        timestamp = datetime.now().strftime('%Y%m%d')
        report_path = self.output_dir / f"sepa_report_{timestamp}.html"
        
        # HTML 템플릿
        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEPA + VCP Scan Report - {timestamp}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{ font-family: 'Noto Sans KR', sans-serif; }}
        .stock-card {{ transition: all 0.2s; cursor: pointer; }}
        .stock-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
    </style>
</head>
<body class="bg-gray-100 min-h-screen">
    <header class="bg-gradient-to-r from-purple-600 to-indigo-700 text-white py-6">
        <div class="max-w-7xl mx-auto px-4">
            <h1 class="text-3xl font-bold">📊 SEPA + VCP Scan Report</h1>
            <p class="text-purple-100 mt-2">Mark Minervini Strategy | {timestamp}</p>
        </div>
    </header>
    
    <main class="max-w-7xl mx-auto px-4 py-6">
        <!-- Summary -->
        <div class="bg-white rounded-xl shadow-lg p-6 mb-6">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="text-center p-4 bg-blue-50 rounded-lg">
                    <div class="text-3xl font-bold text-blue-600">{len(df)}</div>
                    <div class="text-sm text-gray-600">Total Signals</div>
                </div>
                <div class="text-center p-4 bg-green-50 rounded-lg">
                    <div class="text-3xl font-bold text-green-600">{df['is_valid'].sum() if not df.empty else 0}</div>
                    <div class="text-sm text-gray-600">Valid Signals</div>
                </div>
                <div class="text-center p-4 bg-purple-50 rounded-lg">
                    <div class="text-3xl font-bold text-purple-600">{df['vcp_passed'].sum() if not df.empty else 0}</div>
                    <div class="text-sm text-gray-600">VCP Patterns</div>
                </div>
                <div class="text-center p-4 bg-orange-50 rounded-lg">
                    <div class="text-3xl font-bold text-orange-600">{df['volume_surge'].sum() if not df.empty else 0}</div>
                    <div class="text-sm text-gray-600">Volume Surge</div>
                </div>
            </div>
        </div>
        
        <!-- Stock List -->
        <div class="bg-white rounded-xl shadow-lg p-6">
            <h2 class="text-xl font-bold mb-4">🎯 Top Signals</h2>
            
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-4 py-2 text-left">Rank</th>
                            <th class="px-4 py-2 text-left">Symbol</th>
                            <th class="px-4 py-2 text-left">Name</th>
                            <th class="px-4 py-2 text-right">Price</th>
                            <th class="px-4 py-2 text-center">Score</th>
                            <th class="px-4 py-2 text-center">VCP</th>
                            <th class="px-4 py-2 text-center">Volume</th>
                            <th class="px-4 py-2 text-right">RS</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for i, row in df.head(20).iterrows():
            vcp_badge = '✅' if row['vcp_passed'] else '❌'
            vol_badge = f"{row['volume_ratio']:.1f}x" if row['volume_surge'] else '-'
            
            html_content += f"""
                        <tr class="border-b hover:bg-gray-50">
                            <td class="px-4 py-3">{i+1}</td>
                            <td class="px-4 py-3 font-bold">{row['symbol']}</td>
                            <td class="px-4 py-3">{row['name']}</td>
                            <td class="px-4 py-3 text-right">{row['close']:,.0f}</td>
                            <td class="px-4 py-3 text-center">
                                <span class="px-2 py-1 rounded text-white {'bg-green-500' if row['score'] >= 80 else 'bg-yellow-500' if row['score'] >= 60 else 'bg-gray-500'}">
                                    {row['score']}
                                </span>
                            </td>
                            <td class="px-4 py-3 text-center">{vcp_badge}</td>
                            <td class="px-4 py-3 text-center">{vol_badge}</td>
                            <td class="px-4 py-3 text-right">{row['relative_strength']:.1f}%</td>
                        </tr>
"""
        
        html_content += """
                    </tbody>
                </table>
            </div>
        </div>
    </main>
</body>
</html>
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTML report saved: {report_path}")
        return report_path


# 실행 예시
if __name__ == "__main__":
    scanner = SEPAVCPScanner()
    
    print("🔥 SEPA + VCP Multi-Stock Scanner")
    print("=" * 50)
    
    # 전 종목 스캔
    results, valid_signals = scanner.scan_all(market='ALL', min_score=50)
    
    if not results.empty:
        # 결과 저장
        scanner.save_results(results)
        
        # 상위 10개 차트 생성
        scanner.generate_charts(valid_signals, top_n=10)
        
        # HTML 리포트 생성
        scanner.generate_report(results, valid_signals)
        
        print("\n✅ Scan complete!")
        print(f"📊 Top 5 results:")
        print(results.head()[['symbol', 'name', 'close', 'score', 'vcp_passed']].to_string(index=False))
    else:
        print("⚠️ No signals found")
