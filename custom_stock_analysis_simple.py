#!/usr/bin/env python3
"""
Custom Stock Analysis Report - Simplified
특정 종목 커스텀 분석 리포트 (간소화 버전)

Target: 현대제철, 로보티즈, SK텔레콤, SK오션플랜트
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List

# 경로 설정
sys.path.insert(0, '/home/programs/kstock_analyzer')
sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from agents.technical_agent import TechnicalAnalysisAgent
from agents.quant_agent import QuantAnalysisAgent


class CustomStockAnalyzer:
    """커스텀 종목 분석기"""
    
    def __init__(self):
        self.results = []
    
    def analyze_stock(self, symbol: str, name: str, market: str = 'KOSPI') -> Dict:
        """개별 종목 분석 (간소화)"""
        print(f"\n{'='*60}")
        print(f"📊 Analyzing {name} ({symbol})")
        print('='*60)
        
        result = {
            'symbol': symbol,
            'name': name,
            'market': market,
            'analysis_date': datetime.now().isoformat(),
            'agents': {}
        }
        
        # 1. Technical Analysis
        print("\n   🔧 Technical Analysis...")
        try:
            tech_agent = TechnicalAnalysisAgent(symbol, name)
            tech_result = tech_agent.analyze()
            result['agents']['technical'] = {
                'score': tech_result.get('total_score', 0),
                'recommendation': tech_result.get('recommendation', 'HOLD'),
                'signals': tech_result.get('key_signals', []),
                'risks': tech_result.get('key_risks', [])
            }
            print(f"      ✅ Score: {tech_result.get('total_score', 0)}/100")
        except Exception as e:
            print(f"      ⚠️  Error: {e}")
            result['agents']['technical'] = {'error': str(e), 'score': 0}
        
        # 2. Quant Analysis
        print("\n   📊 Quant Analysis...")
        try:
            quant_agent = QuantAnalysisAgent(symbol, name)
            quant_result = quant_agent.analyze()
            result['agents']['quant'] = {
                'score': quant_result.get('total_score', 0),
                'recommendation': quant_result.get('recommendation', 'HOLD'),
                'signals': quant_result.get('key_signals', []),
                'risks': quant_result.get('key_risks', [])
            }
            print(f"      ✅ Score: {quant_result.get('total_score', 0)}/100")
        except Exception as e:
            print(f"      ⚠️  Error: {e}")
            result['agents']['quant'] = {'error': str(e), 'score': 0}
        
        # 종합 점수 계산 (2개 에이전트만)
        scores = []
        weights = {'technical': 0.5, 'quant': 0.5}
        
        for agent_type, weight in weights.items():
            if agent_type in result['agents'] and 'score' in result['agents'][agent_type]:
                scores.append(result['agents'][agent_type]['score'] * weight)
        
        result['avg_score'] = round(sum(scores), 2) if scores else 0
        
        # 종합 추천
        if result['avg_score'] >= 70:
            result['final_recommendation'] = 'BUY'
        elif result['avg_score'] >= 50:
            result['final_recommendation'] = 'HOLD'
        else:
            result['final_recommendation'] = 'SELL'
        
        print(f"\n   📊 FINAL: {result['avg_score']:.1f}pts - {result['final_recommendation']}")
        
        return result
    
    def analyze_all(self, stocks: List[Dict]) -> List[Dict]:
        """모든 종목 분석"""
        for stock in stocks:
            result = self.analyze_stock(stock['symbol'], stock['name'], stock.get('market', 'KOSPI'))
            self.results.append(result)
        
        # 점수 순 정렬
        self.results.sort(key=lambda x: x['avg_score'], reverse=True)
        return self.results


def generate_html_report(results: List[Dict]) -> str:
    """HTML 리포트 생성"""
    date = datetime.now().isoformat()
    
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Custom Stock Analysis Report - {date[:10]}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ opacity: 0.9; font-size: 1.2em; }}
        
        .summary {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; margin-bottom: 25px; }}
        .summary h2 {{ color: #2c3e50; margin-bottom: 20px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }}
        .summary-card {{ background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); padding: 20px; border-radius: 15px; text-align: center; }}
        .summary-card .rank {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .summary-card .name {{ font-size: 1.3em; font-weight: bold; margin: 10px 0; }}
        .summary-card .score {{ font-size: 1.5em; font-weight: bold; }}
        .summary-card .recommendation {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; margin-top: 10px; }}
        .rec-buy {{ background: #d4edda; color: #155724; }}
        .rec-hold {{ background: #fff3cd; color: #856404; }}
        .rec-sell {{ background: #f8d7da; color: #721c24; }}
        
        .stock-section {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 20px; margin-bottom: 25px; }}
        .stock-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 3px solid #3498db; }}
        .stock-header h2 {{ color: #2c3e50; }}
        .stock-score {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        
        .agents-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
        .agent-card {{ background: #f8f9fa; padding: 20px; border-radius: 15px; }}
        .agent-card h4 {{ color: #2c3e50; margin-bottom: 10px; }}
        .agent-card .score {{ font-size: 1.5em; font-weight: bold; color: #667eea; margin-bottom: 10px; }}
        .agent-card .signals {{ font-size: 0.9em; color: #27ae60; }}
        .agent-card .risks {{ font-size: 0.9em; color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Custom Stock Analysis</h1>
            <div class="subtitle">현대제철 · 로보티즈 · SK텔레콤 · SK오션플랜트</div>
            <div style="margin-top: 10px; opacity: 0.8;">{date[:10]} {date[11:16]}</div>
        </div>
        
        <div class="summary">
            <h2>🏆 종합 순위</h2>
            <div class="summary-grid">
"""
    
    # 종합 순위
    for i, result in enumerate(results[:4], 1):
        rec_class = 'rec-buy' if result['final_recommendation'] == 'BUY' else 'rec-hold' if result['final_recommendation'] == 'HOLD' else 'rec-sell'
        html += f"""
                <div class="summary-card">
                    <div class="rank">#{i}</div>
                    <div class="name">{result['name']}</div>
                    <div class="score">{result['avg_score']:.1f}pts</div>
                    <div class="recommendation {rec_class}">{result['final_recommendation']}</div>
                </div>
"""
    
    html += """
            </div>
        </div>
"""
    
    # 개별 종목 상세
    for result in results:
        html += f"""
        <div class="stock-section">
            <div class="stock-header">
                <div>
                    <h2>{result['name']} ({result['symbol']})</h2>
                    <div style="color: #7f8c8d;">{result['market']}</div>
                </div>
                <div class="stock-score">{result['avg_score']:.1f}pts</div>
            </div>
            
            <div class="agents-grid">
"""
        
        # 에이전트별 결과
        agent_names = {
            'technical': '🔧 기술적 분석',
            'quant': '📊 재무 분석'
        }
        
        for agent_type, agent_name in agent_names.items():
            if agent_type in result['agents'] and 'score' in result['agents'][agent_type]:
                agent_data = result['agents'][agent_type]
                signals = agent_data.get('signals', [])[:2]
                risks = agent_data.get('risks', [])[:2]
                
                html += f"""
                <div class="agent-card">
                    <h4>{agent_name}</h4>
                    <div class="score">{agent_data['score']}/100</div>
                    <div style="margin-bottom: 10px;">추천: <strong>{agent_data['recommendation']}</strong></div>
"""
                if signals:
                    html += f"""
                    <div class="signals">✅ {', '.join(signals)}</div>
"""
                if risks:
                    html += f"""
                    <div class="risks">⚠️ {', '.join(risks)}</div>
"""
                html += """
                </div>
"""
        
        html += """
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    return html


def main():
    """메인 실행"""
    print("=" * 60)
    print("📊 Custom Stock Analysis Report (Simplified)")
    print("=" * 60)
    
    # 분석 대상 종목
    target_stocks = [
        {'symbol': '004020.KS', 'name': '현대제철', 'market': 'KOSPI'},
        {'symbol': '454910.KS', 'name': '로보티즈', 'market': 'KOSPI'},
        {'symbol': '017670.KS', 'name': 'SK텔레콤', 'market': 'KOSPI'},
        {'symbol': '100090.KS', 'name': 'SK오션플랜트', 'market': 'KOSPI'}
    ]
    
    print(f"\n📈 분석 종목: {len(target_stocks)}개")
    for stock in target_stocks:
        print(f"   • {stock['name']} ({stock['symbol']})")
    
    # 분석 실행
    analyzer = CustomStockAnalyzer()
    results = analyzer.analyze_all(target_stocks)
    
    # 결과 저장
    output_data = {
        'report_type': 'custom_analysis',
        'generated_at': datetime.now().isoformat(),
        'stocks': results
    }
    
    # JSON 저장
    json_file = f'/home/programs/kstock_analyzer/data/custom_report_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # HTML 리포트 생성
    html = generate_html_report(results)
    html_file = f'/home/programs/kstock_analyzer/docs/custom_report.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # 콘솔 출력
    print("\n" + "=" * 60)
    print("📊 ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\n🏆 종합 순위:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. {result['name']}: {result['avg_score']:.1f}pts ({result['final_recommendation']})")
    
    print(f"\n💾 Files saved:")
    print(f"   • JSON: {json_file}")
    print(f"   • HTML: {html_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()
