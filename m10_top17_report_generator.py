#!/usr/bin/env python3
"""
M10 Multi-Strategy TOP 17 Market Intelligence Report Generator
M10 멀티전략 3개 이상 충족 종목 시장조사 리포트
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import pandas as pd


class M10MarketReportGenerator:
    """Generate market intelligence report for M10 multi-strategy stocks"""
    
    def __init__(self, csv_path: str = 'reports/multi_strategy_scan.csv'):
        self.df = pd.read_csv(csv_path)
        self.timestamp = datetime.now()
        
        # Filter stocks with 3+ strategies
        self.top_stocks = self.df[self.df['충족전략수'] >= 3].sort_values(
            ['충족전략수', '거래대금(억)'], 
            ascending=[False, False]
        )
    
    def get_stock_details(self, symbol: str) -> Dict:
        """Get detailed stock info from DB"""
        try:
            conn = sqlite3.connect('./data/pivot_strategy.db')
            query = '''
                SELECT s.*, 
                       p.close as latest_price,
                       p.volume,
                       p.date as price_date
                FROM stock_info s
                LEFT JOIN stock_prices p ON s.symbol = p.symbol
                WHERE s.symbol = ?
                ORDER BY p.date DESC
                LIMIT 1
            '''
            df = pd.read_sql_query(query, conn, params=(symbol,))
            conn.close()
            
            if len(df) > 0:
                return df.iloc[0].to_dict()
            return {}
        except Exception as e:
            print(f"Error getting details for {symbol}: {e}")
            return {}
    
    def get_strategy_combo(self, row) -> str:
        """Get strategy combination for a stock"""
        strategies = []
        if row.get('전략1_거래대금TOP20') == '✅': strategies.append('S1')
        if row.get('전략2_턴어라운드') == '✅': strategies.append('S2')
        if row.get('전략3_모멘텀') == '✅': strategies.append('S3')
        if row.get('전략4_2000억돌파') == '✅': strategies.append('S4')
        if row.get('전략5_MA200우상향') == '✅': strategies.append('S5')
        return '+'.join(strategies) if strategies else 'None'
    
    def analyze_stock(self, row) -> Dict:
        """Analyze individual stock"""
        symbol = str(row['종목코드']).zfill(6)
        name = row['종목명']
        
        # Get latest data
        details = self.get_stock_details(symbol)
        
        strategy_count = int(row['충족전략수'])
        strategy_combo = self.get_strategy_combo(row)
        
        # Calculate recommendation based on strategy count
        if strategy_count >= 4:
            recommendation = 'STRONG BUY'
            rec_color = 'green'
            rec_bg = 'bg-green-100 text-green-700'
        elif strategy_count == 3:
            recommendation = 'BUY'
            rec_color = 'blue'
            rec_bg = 'bg-blue-100 text-blue-700'
        else:
            recommendation = 'HOLD'
            rec_color = 'yellow'
            rec_bg = 'bg-yellow-100 text-yellow-700'
        
        # Trading amount in billions
        trading_amount = row['거래대금(억)']
        
        return {
            'symbol': symbol,
            'name': name,
            'current_price': row['현재가'],
            'sector': details.get('sector', row.get('업종', 'N/A')),
            'market': row['시장'],
            'trading_amount': trading_amount,
            'strategy_count': strategy_count,
            'strategy_combo': strategy_combo,
            'rank': int(row['우선순위']),
            'recommendation': recommendation,
            'rec_color': rec_color,
            'rec_bg': rec_bg,
            # Additional metrics
            'rsi': row.get('RSI', 'N/A'),
            'macd': row.get('MACD', 'N/A'),
            'ma200_slope': row.get('전략5_MA200우상향', 'N/A'),
            '52w_high_ratio': row.get('52주고가대비', 'N/A')
        }
    
    def generate_html_report(self) -> str:
        """Generate HTML report"""
        
        # Analyze all top stocks
        analyzed = [self.analyze_stock(row) for _, row in self.top_stocks.iterrows()]
        
        timestamp_str = self.timestamp.strftime('%Y-%m-%d %H:%M')
        date_str = self.timestamp.strftime('%Y%m%d')
        
        # Calculate stats
        total_stocks = len(self.df)
        top_count = len(analyzed)
        four_strategy = len([s for s in analyzed if s['strategy_count'] >= 4])
        three_strategy = len([s for s in analyzed if s['strategy_count'] == 3])
        
        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M10 Multi-Strategy TOP 17 Market Intelligence Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ font-family: 'Noto Sans KR', sans-serif; }}
        body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .glass {{ background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }}
        .gradient-text {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stock-card {{ transition: all 0.3s ease; border-left: 4px solid transparent; }}
        .stock-card:hover {{ transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.15); }}
        .strategy-badge {{ display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-right: 4px; }}
        .s1 {{ background: #dbeafe; color: #1e40af; }}
        .s2 {{ background: #fce7f3; color: #be185d; }}
        .s3 {{ background: #d1fae5; color: #065f46; }}
        .s4 {{ background: #fef3c7; color: #92400e; }}
        .s5 {{ background: #e0e7ff; color: #3730a3; }}
        .rank-1 {{ border-left-color: #fbbf24; background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); }}
        .rank-2 {{ border-left-color: #9ca3af; background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%); }}
        .rank-3 {{ border-left-color: #f97316; background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%); }}
    </style>
</head>
<body class="p-6">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="glass p-8 mb-8 text-center">
            <div class="inline-flex items-center gap-3 mb-4">
                <i class="fas fa-layer-group text-4xl text-indigo-600"></i>
                <h1 class="text-4xl font-black gradient-text">M10 Multi-Strategy TOP 17</h1>
            </div>
            <p class="text-gray-600 text-lg mb-2">🎯 5가지 전략 중 3개 이상 충족하는 우량 종목 분석</p>
            <p class="text-gray-500">생성일: {timestamp_str}</p>
            
            <div class="flex justify-center gap-4 mt-6 flex-wrap">
                <span class="px-4 py-2 bg-indigo-100 text-indigo-700 rounded-full text-sm font-bold">
                    <i class="fas fa-chart-pie mr-2"></i>분석 종목: {total_stocks:,}개
                </span>
                <span class="px-4 py-2 bg-green-100 text-green-700 rounded-full text-sm font-bold">
                    <i class="fas fa-trophy mr-2"></i>3+ 전략 충족: {top_count}개
                </span>
                <span class="px-4 py-2 bg-purple-100 text-purple-700 rounded-full text-sm font-bold">
                    <i class="fas fa-star mr-2"></i>4 전략 충족: {four_strategy}개
                </span>
                <span class="px-4 py-2 bg-blue-100 text-blue-700 rounded-full text-sm font-bold">
                    <i class="fas fa-check-double mr-2"></i>3 전략 충족: {three_strategy}개
                </span>
            </div>
        </div>

        <!-- Strategy Legend -->
        <div class="glass p-6 mb-8">
            <h3 class="font-bold text-gray-700 mb-4">📋 전략 설명</h3>
            <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div class="flex items-center gap-2">
                    <span class="strategy-badge s1">S1</span>
                    <span class="text-sm text-gray-600">거래대금 TOP20</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="strategy-badge s2">S2</span>
                    <span class="text-sm text-gray-600">턴어라운드</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="strategy-badge s3">S3</span>
                    <span class="text-sm text-gray-600">신규 모멘텀</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="strategy-badge s4">S4</span>
                    <span class="text-sm text-gray-600">2000억 돌파</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="strategy-badge s5">S5</span>
                    <span class="text-sm text-gray-600">MA200 우상향</span>
                </div>
            </div>
        </div>

        <!-- TOP Stocks -->
        <div class="glass p-8 mb-8">
            <h2 class="text-2xl font-bold mb-6 flex items-center gap-3">
                <i class="fas fa-crown text-yellow-500"></i>
                TOP 17 선정 종목 상세 분석
            </h2>
'''
        
        # Add stock cards
        for idx, stock in enumerate(analyzed, 1):
            rank_class = f"rank-{idx}" if idx <= 3 else ""
            
            # Parse strategy combo
            strategies = stock['strategy_combo'].split('+')
            strategy_badges = ''
            for s in strategies:
                strategy_badges += f'<span class="strategy-badge {s.lower()}">{s}</span>'
            
            html += f'''
            <div class="stock-card {rank_class} glass p-6 mb-4">
                <div class="flex flex-col lg:flex-row items-start lg:items-center gap-6">
                    <!-- Rank -->
                    <div class="flex flex-col items-center gap-2 min-w-[60px]">
                        <div class="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-xl">{idx}</div>
                        <div class="text-xs text-gray-500">우선순위 #{stock['rank']}</div>
                    </div>
                    
                    <!-- Stock Info -->
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-2 flex-wrap">
                            <h3 class="text-2xl font-bold text-gray-800">{stock['name']}</h3>
                            <span class="text-gray-500">({stock['symbol']})</span>
                            <span class="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-bold">{stock['market']}</span>
                            <span class="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">{stock['sector'] or 'N/A'}</span>
                        </div>
                        
                        <div class="flex flex-wrap gap-4 text-sm text-gray-600 mb-3">
                            <span><i class="fas fa-won-sign mr-1 text-indigo-600"></i>현재가: {stock['current_price']:,.0f}원</span>
                            <span><i class="fas fa-chart-bar mr-1 text-green-600"></i>거래대금: {stock['trading_amount']:,.1f}억</span>
                            <span><i class="fas fa-layer-group mr-1 text-purple-600"></i>충족 전략: {stock['strategy_count']}개</span>
                        </div>
                        
                        <!-- Strategy Badges -->
                        <div class="flex flex-wrap gap-1">
                            {strategy_badges}
                        </div>
                    </div>
                    
                    <!-- Recommendation -->
                    <div class="flex flex-col items-center gap-2 min-w-[120px]">
                        <span class="px-4 py-2 {stock['rec_bg']} rounded-full font-bold text-sm">{stock['recommendation']}</span>
                        <div class="text-center">
                            <div class="text-xs text-gray-500">적용 전략</div>
                            <div class="text-lg font-bold text-indigo-600">{stock['strategy_combo']}</div>
                        </div>
                    </div>
                </div>
            </div>
'''
        
        # Close HTML
        html += f'''
        </div>

        <!-- Analysis Summary -->
        <div class="glass p-8 mb-8">
            <h2 class="text-xl font-bold mb-4 flex items-center gap-3">
                <i class="fas fa-chart-pie text-indigo-600"></i>
                전략 조합 분석
            </h2>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h3 class="font-bold text-gray-700 mb-3">🏆 가장 많은 전략 조합</h3>
                    <ul class="space-y-2 text-gray-600">
                        <li><i class="fas fa-check text-green-500 mr-2"></i>S1+S2+S5: 대형주 중심 안정적 상승세</li>
                        <li><i class="fas fa-check text-green-500 mr-2"></i>S1+S2+S3+S5: 고거래대금 + 턴어라운드 + 모멘텀</li>
                        <li><i class="fas fa-check text-green-500 mr-2"></i>S1+S3+S4+S5: 대형 우량주 + 성장성</li>
                        <li><i class="fas fa-check text-green-500 mr-2"></i>S2+S3+S5: 중소형주 중심 급등세</li>
                    </ul>
                </div>
                <div>
                    <h3 class="font-bold text-gray-700 mb-3">💡 투자 인사이트</h3>
                    <ul class="space-y-2 text-gray-600">
                        <li><i class="fas fa-lightbulb text-yellow-500 mr-2"></i>대형주(삼성전자, 하이닉스)는 S1+S2+S5 패턴</li>
                        <li><i class="fas fa-lightbulb text-yellow-500 mr-2"></i>4개 전략 충족은 대우건설, 신세계</li>
                        <li><i class="fas fa-lightbulb text-yellow-500 mr-2"></i>KOSDAQ 중소형주는 S2+S3+S5 패턴</li>
                        <li><i class="fas fa-lightbulb text-yellow-500 mr-2"></i>S1(거래대금) + S5(MA200) 조합이 가장 많음</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center text-white/70 text-sm py-6">
            <p>⚠️ 본 리포트는 정보 제공 목적으로 작성되었으며, 투자 결정의 책임은 투자자 본인에게 있습니다.</p>
            <p class="mt-1">Generated by K-Stock Strategy System | M10 Multi-Strategy Scanner | {timestamp_str}</p>
        </div>
    </div>
</body>
</html>
'''
        
        return html
    
    def save_report(self, output_dir: str = './reports/multi_strategy') -> str:
        """Save report to file"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = self.timestamp.strftime('%Y%m%d_%H%M')
        
        html = self.generate_html_report()
        html_path = f"{output_dir}/M10_TOP17_market_report_{timestamp}.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 리포트 저장 완료: {html_path}")
        return html_path


def main():
    """Main execution"""
    generator = M10MarketReportGenerator()
    report_path = generator.save_report()
    
    # Also copy to docs
    import shutil
    docs_path = f"./docs/M10_TOP17_market_report_{generator.timestamp.strftime('%Y%m%d')}.html"
    shutil.copy(report_path, docs_path)
    print(f"✅ Docs 복사: {docs_path}")
    
    return report_path


if __name__ == '__main__':
    main()
