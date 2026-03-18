#!/usr/bin/env python3
"""
N01 Market Intelligence Report Generator
N01 선정 종목 시장조사 리포트 생성
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import pandas as pd


class N01MarketReportGenerator:
    """Generate market intelligence report for N01 selected stocks"""
    
    def __init__(self, json_path: str):
        with open(json_path, 'r', encoding='utf-8') as f:
            self.stocks = json.load(f)
        self.timestamp = datetime.now()
        
    def get_stock_details(self, symbol: str) -> Dict:
        """Get detailed stock info from DB"""
        try:
            conn = sqlite3.connect('./data/pivot_strategy.db')
            query = '''
                SELECT s.*, 
                       p.close as latest_price,
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
    
    def analyze_stock(self, stock: Dict) -> Dict:
        """Analyze individual stock"""
        symbol = stock['symbol']
        name = stock['name']
        
        # Get latest data
        details = self.get_stock_details(symbol)
        
        # Market Research Scores
        momentum_score = stock['score_momentum']
        stability_score = stock['score_stability']
        value_score = stock['score_value']
        nps_score = stock['score_nps']
        total_score = stock['total_score']
        
        # Calculate risk level
        volatility = stock['volatility']
        if volatility > 80:
            risk_level = 'HIGH'
            risk_color = 'red'
        elif volatility > 50:
            risk_level = 'MEDIUM'
            risk_color = 'yellow'
        else:
            risk_level = 'LOW'
            risk_color = 'green'
        
        # Calculate recommendation
        if total_score >= 70:
            recommendation = 'BUY'
            rec_color = 'green'
        elif total_score >= 55:
            recommendation = 'HOLD'
            rec_color = 'yellow'
        else:
            recommendation = 'WATCH'
            rec_color = 'gray'
        
        return {
            'symbol': symbol,
            'name': name,
            'current_price': stock['current_price'],
            'sector': details.get('sector', 'N/A'),
            'market': details.get('market', 'N/A'),
            'returns_1y': stock['returns_1y'],
            'volatility': volatility,
            'volume_avg': stock['volume_avg'],
            'disclosure_count': stock['disclosure_count'],
            'scores': {
                'momentum': momentum_score,
                'stability': stability_score,
                'value': value_score,
                'nps': nps_score,
                'total': total_score
            },
            'risk_level': risk_level,
            'risk_color': risk_color,
            'recommendation': recommendation,
            'rec_color': rec_color,
            'grade': stock['grade'],
            'rank': stock['rank']
        }
    
    def generate_html_report(self) -> str:
        """Generate HTML report"""
        
        # Analyze all stocks
        analyzed = [self.analyze_stock(s) for s in self.stocks[:5]]  # TOP 5 only
        
        timestamp_str = self.timestamp.strftime('%Y-%m-%d %H:%M')
        date_str = self.timestamp.strftime('%Y%m%d')
        
        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>N01 NPS Value Strategy - Market Intelligence Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ font-family: 'Noto Sans KR', sans-serif; }}
        body {{ background: linear-gradient(135deg, #1e3a8a 0%, #312e81 100%); min-height: 100vh; }}
        .glass {{ background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }}
        .gradient-text {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .score-ring {{ width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.2rem; border: 4px solid; }}
        .score-a {{ border-color: #10b981; color: #10b981; }}
        .score-b {{ border-color: #3b82f6; color: #3b82f6; }}
        .score-c {{ border-color: #f59e0b; color: #f59e0b; }}
        .score-d {{ border-color: #6b7280; color: #6b7280; }}
        .score-f {{ border-color: #ef4444; color: #ef4444; }}
        .stock-card {{ transition: all 0.3s ease; border-left: 4px solid transparent; }}
        .stock-card:hover {{ transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.15); }}
        .risk-high {{ border-left-color: #ef4444; }}
        .risk-medium {{ border-left-color: #f59e0b; }}
        .risk-low {{ border-left-color: #10b981; }}
    </style>
</head>
<body class="p-6">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="glass p-8 mb-8 text-center">
            <div class="inline-flex items-center gap-3 mb-4">
                <i class="fas fa-landmark text-4xl text-blue-600"></i>
                <h1 class="text-4xl font-black gradient-text">N01 NPS Value Strategy</h1>
            </div>
            <p class="text-gray-600 text-lg mb-2">🏛️ 국민연금 장기 가치 투자 패턴 분석 리포트</p>
            <p class="text-gray-500">생성일: {timestamp_str}</p>
            
            <div class="flex justify-center gap-4 mt-6">
                <span class="px-4 py-2 bg-blue-100 text-blue-700 rounded-full text-sm font-bold">
                    <i class="fas fa-chart-line mr-2"></i>선정 종목: {len(self.stocks)}개
                </span>
                <span class="px-4 py-2 bg-purple-100 text-purple-700 rounded-full text-sm font-bold">
                    <i class="fas fa-database mr-2"></i>데이터 소스: dart_focused.db
                </span>
                <span class="px-4 py-2 bg-green-100 text-green-700 rounded-full text-sm font-bold">
                    <i class="fas fa-bolt mr-2"></i>Ultra Fast Mode
                </span>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="glass p-6 text-center">
                <div class="text-3xl font-bold text-blue-600">{len(self.stocks)}</div>
                <div class="text-gray-500 text-sm">선정 종목</div>
            </div>
            <div class="glass p-6 text-center">
                <div class="text-3xl font-bold text-purple-600">{sum(1 for s in self.stocks if s['grade'] in ['A', 'B'])}</div>
                <div class="text-gray-500 text-sm">AB등급</div>
            </div>
            <div class="glass p-6 text-center">
                <div class="text-3xl font-bold text-green-600">{sum(s['returns_1y'] for s in self.stocks)/len(self.stocks):.1f}%</div>
                <div class="text-gray-500 text-sm">평균 1년 수익률</div>
            </div>
            <div class="glass p-6 text-center">
                <div class="text-3xl font-bold text-orange-600">{sum(s['disclosure_count'] for s in self.stocks)/len(self.stocks):.0f}</div>
                <div class="text-gray-500 text-sm">평균 공시 건수</div>
            </div>
        </div>

        <!-- TOP 5 Stocks -->
        <div class="glass p-8 mb-8">
            <h2 class="text-2xl font-bold mb-6 flex items-center gap-3">
                <i class="fas fa-trophy text-yellow-500"></i>
                TOP 5 선정 종목 상세 분석
            </h2>
'''
        
        # Add stock cards
        for stock in analyzed:
            risk_class = f"risk-{stock['risk_level'].lower()}"
            rec_bg = {
                'BUY': 'bg-green-100 text-green-700',
                'HOLD': 'bg-yellow-100 text-yellow-700',
                'WATCH': 'bg-gray-100 text-gray-700'
            }.get(stock['recommendation'], 'bg-gray-100')
            
            html += f'''
            <div class="stock-card {risk_class} glass p-6 mb-4">
                <div class="flex flex-col md:flex-row items-start md:items-center gap-6">
                    <!-- Rank & Grade -->
                    <div class="flex flex-col items-center gap-2">
                        <div class="score-ring score-{stock['grade'].lower()}">{stock['grade']}</div>
                        <div class="text-sm font-bold text-gray-500">#{stock['rank']}</div>
                    </div>
                    
                    <!-- Stock Info -->
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-2">
                            <h3 class="text-2xl font-bold text-gray-800">{stock['name']}</h3>
                            <span class="text-gray-500">({stock['symbol']})</span>
                            <span class="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">{stock['market']}</span>
                            <span class="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">{stock['sector'] or 'N/A'}</span>
                        </div>
                        
                        <div class="flex flex-wrap gap-4 text-sm text-gray-600 mb-4">
                            <span><i class="fas fa-won-sign mr-1"></i>현재가: {stock['current_price']:,.0f}원</span>
                            <span><i class="fas fa-chart-line mr-1 text-green-600"></i>1년 수익률: {stock['returns_1y']:+.1f}%</span>
                            <span><i class="fas fa-wave-square mr-1 text-orange-600"></i>변동성: {stock['volatility']:.1f}%</span>
                            <span><i class="fas fa-file-alt mr-1 text-blue-600"></i>공시: {stock['disclosure_count']}건</span>
                        </div>
                        
                        <!-- Score Breakdown -->
                        <div class="grid grid-cols-4 gap-2 mb-4">
                            <div class="bg-blue-50 p-3 rounded-lg text-center">
                                <div class="text-xs text-gray-500">모멘텀</div>
                                <div class="text-lg font-bold text-blue-600">{stock['scores']['momentum']}</div>
                            </div>
                            <div class="bg-purple-50 p-3 rounded-lg text-center">
                                <div class="text-xs text-gray-500">안정성</div>
                                <div class="text-lg font-bold text-purple-600">{stock['scores']['stability']}</div>
                            </div>
                            <div class="bg-orange-50 p-3 rounded-lg text-center">
                                <div class="text-xs text-gray-500">가치</div>
                                <div class="text-lg font-bold text-orange-600">{stock['scores']['value']}</div>
                            </div>
                            <div class="bg-green-50 p-3 rounded-lg text-center">
                                <div class="text-xs text-gray-500">NPS</div>
                                <div class="text-lg font-bold text-green-600">{stock['scores']['nps']}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recommendation -->
                    <div class="flex flex-col items-center gap-3">
                        <div class="text-center">
                            <div class="text-xs text-gray-500 mb-1">총점</div>
                            <div class="text-3xl font-black text-gray-800">{stock['scores']['total']:.1f}</div>
                        </div>
                        <span class="px-4 py-2 {rec_bg} rounded-full font-bold">{stock['recommendation']}</span>
                        <span class="px-3 py-1 text-xs rounded-full {'bg-red-100 text-red-700' if stock['risk_level'] == 'HIGH' else 'bg-yellow-100 text-yellow-700' if stock['risk_level'] == 'MEDIUM' else 'bg-green-100 text-green-700'}">
                            위험도: {stock['risk_level']}
                        </span>
                    </div>
                </div>
            </div>
'''
        
        # Close HTML
        html += f'''
        </div>

        <!-- Strategy Info -->
        <div class="glass p-8 mb-8">
            <h2 class="text-xl font-bold mb-4 flex items-center gap-3">
                <i class="fas fa-info-circle text-blue-600"></i>
                N01 전략 설명
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <h3 class="font-bold text-gray-700 mb-2">📊 평가 기준</h3>
                    <ul class="space-y-2 text-gray-600">
                        <li><i class="fas fa-check text-green-500 mr-2"></i>모멘텀 점수 (30%): 1년 수익률 기반</li>
                        <li><i class="fas fa-check text-green-500 mr-2"></i>안정성 점수 (25%): 변동성 기반</li>
                        <li><i class="fas fa-check text-green-500 mr-2"></i>가치 점수 (20%): 공시 투명도 기반</li>
                        <li><i class="fas fa-check text-green-500 mr-2"></i>NPS 점수 (25%): 국민연금 선호도</li>
                    </ul>
                </div>
                <div>
                    <h3 class="font-bold text-gray-700 mb-2">🎯 선정 필터</h3>
                    <ul class="space-y-2 text-gray-600">
                        <li><i class="fas fa-filter text-blue-500 mr-2"></i>최소 주가: 1,000원 이상</li>
                        <li><i class="fas fa-filter text-blue-500 mr-2"></i>최소 거래량: 1천만 이상</li>
                        <li><i class="fas fa-filter text-blue-500 mr-2"></i>금융업종 제외</li>
                        <li><i class="fas fa-filter text-blue-500 mr-2"></i>공시 데이터 보유 종목</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center text-white/70 text-sm py-6">
            <p>⚠️ 본 리포트는 정보 제공 목적으로 작성되었으며, 투자 결정의 책임은 투자자 본인에게 있습니다.</p>
            <p class="mt-1">Generated by K-Stock Strategy System | {timestamp_str}</p>
        </div>
    </div>
</body>
</html>
'''
        
        return html
    
    def save_report(self, output_dir: str = './reports/nps_value') -> str:
        """Save report to file"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = self.timestamp.strftime('%Y%m%d_%H%M')
        
        html = self.generate_html_report()
        html_path = f"{output_dir}/N01_market_report_{timestamp}.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 리포트 저장 완료: {html_path}")
        return html_path


def main():
    """Main execution"""
    import glob
    
    # Find latest N01 result
    json_files = glob.glob('./reports/nps_value/n01_ufast_*.json')
    if not json_files:
        print("❌ N01 결과 파일을 찾을 수 없습니다")
        return
    
    latest = max(json_files)
    print(f"📊 분석 파일: {latest}")
    
    generator = N01MarketReportGenerator(latest)
    report_path = generator.save_report()
    
    # Also copy to docs
    import shutil
    docs_path = f"./docs/N01_market_report_{generator.timestamp.strftime('%Y%m%d')}.html"
    shutil.copy(report_path, docs_path)
    print(f"✅ Docs 복사: {docs_path}")
    
    return report_path


if __name__ == '__main__':
    main()
