#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
버핏 3전략 종합 리포트 생성기
"""

import json
import pandas as pd
from datetime import datetime
import os

class BuffettReportGenerator:
    """
    버핏 전략 종합 HTML 리포트 생성
    """
    
    def __init__(self, scan_file: str, backtest_file: str = None):
        self.scan_file = scan_file
        self.backtest_file = backtest_file
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
    def load_scan_results(self) -> dict:
        """스캔 결과 로드"""
        with open(self.scan_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_backtest_results(self) -> dict:
        """백테스트 결과 로드"""
        if self.backtest_file and os.path.exists(self.backtest_file):
            with open(self.backtest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def generate_html(self, output_path: str = None):
        """HTML 리포트 생성"""
        scan_data = self.load_scan_results()
        backtest_data = self.load_backtest_results()
        
        if output_path is None:
            output_path = f'./docs/buffett_comprehensive_report_{self.timestamp}.html'
        
        # 상위 종목 추출
        top_s1 = scan_data.get('strategy1', [])[:10]
        top_s2 = scan_data.get('strategy2', [])[:10]
        top_s3 = scan_data.get('strategy3', [])[:10]
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>버핏 3전략 종합 리포트 - {self.timestamp}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{ font-family: 'Noto Sans KR', sans-serif; }}
        body {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; }}
        .glass {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); }}
        .stock-card {{ transition: all 0.3s ease; }}
        .stock-card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
        .strategy-badge {{ display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .strategy-1 {{ background: #10b981; color: white; }}
        .strategy-2 {{ background: #3b82f6; color: white; }}
        .strategy-3 {{ background: #f59e0b; color: white; }}
        .score-circle {{ width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white; }}
    </style>
</head>
<body class="py-8 px-4">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="text-center mb-10">
            <div class="inline-flex items-center gap-3 bg-white/10 rounded-full px-6 py-3 mb-4">
                <span class="text-3xl">📊</span>
                <span class="text-white font-bold text-lg">Buffett Value Investing</span>
            </div>
            <h1 class="text-4xl font-bold text-white mb-3">버핏 3전략 종합 리포트</h1>
            <p class="text-white/60 text-lg">KOSPI/KOSDAQ 3,286종목 대상 스캔 및 분석</p>
            
            <div class="mt-6 flex justify-center gap-4 flex-wrap">
                <div class="bg-white/10 rounded-xl px-6 py-3">
                    <div class="text-3xl font-bold text-green-400">{len(scan_data.get('strategy1', [])) + len(scan_data.get('strategy2', [])) + len(scan_data.get('strategy3', []))}</div>
                    <div class="text-white/60 text-sm">총 선정 종목</div>
                </div>
                <div class="bg-white/10 rounded-xl px-6 py-3">
                    <div class="text-3xl font-bold text-blue-400">3</div>
                    <div class="text-white/60 text-sm">전략</div>
                </div>
                <div class="bg-white/10 rounded-xl px-6 py-3">
                    <div class="text-3xl font-bold text-yellow-400">3,286</div>
                    <div class="text-white/60 text-sm">분석 종목</div>
                </div>
            </div>
        </div>

        <!-- Strategy Overview -->
        <div class="glass rounded-2xl p-6 mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-6">🎯 3가지 전략 개요</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-5 text-white">
                    <div class="text-3xl font-bold mb-2">전략 1</div>
                    <div class="text-xl font-semibold mb-3">그레이엄 순유동자산</div>
                    <div class="text-sm opacity-90 mb-4">"10센트에 1달러짜리 사기"</div>
                    <div class="space-y-2 text-sm">
                        <div>📊 선정: {len(scan_data.get('strategy1', []))}개</div>
                        <div>🎯 핵심: 저평가 + 거래량</div>
                        <div>⏰ 보유: 2-3년</div>
                    </div>
                </div>

                <div class="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-5 text-white">
                    <div class="text-3xl font-bold mb-2">전략 2</div>
                    <div class="text-xl font-semibold mb-3">퀄리티 적정가</div>
                    <div class="text-sm opacity-90 mb-4">"해자 있는 좋은 회사를 싸게"</div>
                    <div class="space-y-2 text-sm">
                        <div>📊 선정: {len(scan_data.get('strategy2', []))}개</div>
                        <div>🎯 핵심: ROE + Moat</div>
                        <div>⏰ 보유: 5-10년</div>
                    </div>
                </div>

                <div class="bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl p-5 text-white">
                    <div class="text-3xl font-bold mb-2">전략 3</div>
                    <div class="text-xl font-semibold mb-3">배당성장</div>
                    <div class="text-sm opacity-90 mb-4">"현금창출 머신 모으기"</div>
                    <div class="space-y-2 text-sm">
                        <div>📊 선정: {len(scan_data.get('strategy3', []))}개</div>
                        <div>🎯 핵심: 안정성 + 배당</div>
                        <div>⏰ 보유: 10년+</div>
                    </div>
                </div>
            </div>
        </div>
"""
        
        # 전략 1 상위 종목
        html += self._generate_strategy_section("전략 1: 그레이엄 순유동자산", top_s1, "strategy-1", "green")
        
        # 전략 2 상위 종목
        html += self._generate_strategy_section("전략 2: 퀄리티 적정가", top_s2, "strategy-2", "blue")
        
        # 전략 3 상위 종목
        html += self._generate_strategy_section("전략 3: 배당성장", top_s3, "strategy-3", "amber")
        
        # 백테스트 결과 (있는 경우)
        if backtest_data:
            html += self._generate_backtest_section(backtest_data)
        
        # Footer
        html += f"""
        <!-- Footer -->
        <div class="mt-8 text-center text-white/60 text-sm">
            <p>* 본 리포트는 기술적 분석 기반의 버핏 전략 근사치입니다</p>
            <p class="mt-2">스캔 일시: {self.timestamp} | 분석 종목: KOSPI/KOSDAQ 3,286개</p>
            <p class="mt-1">⚠️ 투자의 책임은 투자자 본인에게 있습니다</p>
        </div>
    </div>
</body>
</html>
"""
        
        # 저장
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML 리포트 생성 완료: {output_path}")
        return output_path
    
    def _generate_strategy_section(self, title: str, stocks: list, badge_class: str, color: str) -> str:
        """전략별 섹션 생성"""
        if not stocks:
            return ""
        
        html = f"""
        <!-- {title} -->
        <div class="glass rounded-2xl p-6 mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-6">🎯 {title} TOP 10</h2>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
"""
        
        for i, stock in enumerate(stocks, 1):
            score = stock.get('score', 0)
            name = stock.get('name', '')
            symbol = stock.get('symbol', '')
            market = stock.get('market', '')
            price = stock.get('price', 0)
            
            html += f"""
                <div class="stock-card bg-white rounded-xl p-4 border-l-4 border-{color}-500">
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="strategy-badge {badge_class}">{i}위</span>
                                <span class="text-xs text-gray-500">{symbol} | {market}</span>
                            </div>
                            <div class="text-lg font-bold text-gray-800">{name}</div>
                            <div class="text-sm text-gray-600 mt-1">현재가: {price:,}원</div>
                        </div>
                        
                        <div class="score-circle bg-gradient-to-br from-{color}-400 to-{color}-600">
                            {score}
                        </div>
                    </div>
                </div>
"""
        
        html += """
            </div>
        </div>
"""
        return html
    
    def _generate_backtest_section(self, backtest_data: dict) -> str:
        """백테스트 섹션 생성"""
        # 간략화된 백테스트 결과 표시
        html = """
        <!-- Backtest Results -->
        <div class="glass rounded-2xl p-6 mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-6">📈 백테스트 결과 (2024.01 ~ 2026.03)</h2>
            
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="bg-gray-100">
                            <th class="p-3 text-left">전략</th>
                            <th class="p-3 text-right">총수익률</th>
                            <th class="p-3 text-right">CAGR</th>
                            <th class="p-3 text-right">MDD</th>
                            <th class="p-3 text-right">승률</th>
                            <th class="p-3 text-right">거래횟수</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        strategy_names = {
            'graham': '그레이엄 순유동자산',
            'quality': '퀄리티 적정가',
            'dividend': '배당성장'
        }
        
        for key, name in strategy_names.items():
            if key in backtest_data:
                r = backtest_data[key]
                html += f"""
                        <tr class="border-b">
                            <td class="p-3 font-semibold">{name}</td>
                            <td class="p-3 text-right text-green-600 font-bold">{r.get('total_return_pct', 0):.1f}%</td>
                            <td class="p-3 text-right">{r.get('cagr_pct', 0):.1f}%</td>
                            <td class="p-3 text-right text-red-500">{r.get('mdd_pct', 0):.1f}%</td>
                            <td class="p-3 text-right">{r.get('win_rate_pct', 0):.1f}%</td>
                            <td class="p-3 text-right">{r.get('total_trades', 0)}회</td>
                        </tr>
"""
        
        html += """
                    </tbody>
                </table>
            </div>
        </div>
"""
        return html


def main():
    """메인 실행"""
    import glob
    
    # 최신 스캔 파일 찾기
    scan_files = glob.glob('./reports/buffett_scan_*.json')
    if not scan_files:
        print("❌ 스캔 결과 파일을 찾을 수 없습니다.")
        return
    
    latest_scan = max(scan_files)
    print(f"📂 스캔 파일: {latest_scan}")
    
    # 백테스트 파일 찾기 (있는 경우)
    backtest_files = glob.glob('./reports/buffett_backtest/backtest_results_*.json')
    latest_backtest = max(backtest_files) if backtest_files else None
    
    if latest_backtest:
        print(f"📂 백테스트 파일: {latest_backtest}")
    
    # 리포트 생성
    generator = BuffettReportGenerator(latest_scan, latest_backtest)
    output_path = generator.generate_html()
    
    print(f"\n✅ 리포트 생성 완료!")
    print(f"   파일: {output_path}")


if __name__ == '__main__':
    main()
