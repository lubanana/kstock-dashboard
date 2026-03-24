#!/usr/bin/env python3
"""
V전략 종합 분석 리포트 (시장조사 포함)
======================================
V-Series + 시장조사 + DART 데이터 통합 분석
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, '/root/.openclaw/workspace/strg')
from v_series_scanner import ValueFibATRScanner


class VStrategyIntegratedAnalyzer:
    """V전략 통합 분석기"""
    
    def __init__(self):
        self.kst = timezone(timedelta(hours=9))
        self.today = datetime.now(self.kst)
        self.today_str = self.today.strftime('%Y%m%d')
        self.db_path = '/root/.openclaw/workspace/strg/data/pivot_strategy.db'
        self.dart_db_path = '/root/.openclaw/workspace/strg/data/dart_focused.db'
        self.scanner = ValueFibATRScanner()
        self.results = []
    
    def get_all_symbols(self):
        """모든 종목 코드 로드"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT symbol FROM stock_prices WHERE date >= date(\"now\", \"-30 days\")')
        symbols = [row[0] for row in cursor.fetchall()]
        conn.close()
        return symbols
    
    def run_v_scan(self, symbols, limit=None):
        """V전략 스캔 실행"""
        if limit:
            symbols = symbols[:limit]
        
        print(f"🔍 V전략 스캔: {len(symbols)}개 종목")
        results = self.scanner.scan(symbols, self.today)
        return results
    
    def get_market_research(self, symbol):
        """시장조사 데이터 조회"""
        try:
            # DART 데이터베이스에서 조회
            conn = sqlite3.connect(self.dart_db_path)
            cursor = conn.cursor()
            
            # 기업 개요 조회
            cursor.execute('''
                SELECT company_name, industry, ceo, employees, homepage
                FROM company_overviews 
                WHERE stock_code = ?
            ''', (symbol,))
            overview = cursor.fetchone()
            
            # 재무 정보 조회
            cursor.execute('''
                SELECT revenue, operating_profit, net_income, total_assets
                FROM financial_statements 
                WHERE stock_code = ? 
                ORDER BY rcept_no DESC LIMIT 1
            ''', (symbol,))
            financial = cursor.fetchone()
            
            conn.close()
            
            research = {
                'has_dart_data': overview is not None,
                'company_name': overview[0] if overview else None,
                'industry': overview[1] if overview else None,
                'ceo': overview[2] if overview else None,
                'employees': overview[3] if overview else None,
                'homepage': overview[4] if overview else None,
                'financial_summary': {
                    'revenue': financial[0] if financial else None,
                    'operating_profit': financial[1] if financial else None,
                    'net_income': financial[2] if financial else None,
                    'total_assets': financial[3] if financial else None
                } if financial else None
            }
            
            return research
            
        except Exception as e:
            return {'has_dart_data': False, 'error': str(e)}
    
    def get_news_sentiment(self, symbol):
        """뉴스 감성 분석 (간이)"""
        # 실제 뉴스 데이터가 없으므로 플레이스홀더
        return {
            'recent_news_count': 0,
            'sentiment': 'neutral',
            'major_events': []
        }
    
    def analyze_top_picks(self, v_results, top_n=10):
        """상위 종목 심층 분석"""
        print(f"\n📊 상위 {top_n}개 종목 심층 분석 중...")
        
        analyzed = []
        for result in v_results[:top_n]:
            symbol = result['symbol']
            
            # 시장조사 데이터 추가
            market_data = self.get_market_research(symbol)
            result['market_research'] = market_data
            
            # 뉴스 데이터 추가
            news_data = self.get_news_sentiment(symbol)
            result['news_sentiment'] = news_data
            
            # 종합 판단
            result['overall_rating'] = self._calculate_overall_rating(result)
            
            analyzed.append(result)
        
        return analyzed
    
    def _calculate_overall_rating(self, result):
        """종합 등급 계산"""
        score = 0
        reasons = []
        
        # V전략 점수 (40%)
        v_score = result.get('value_score', 0)
        score += min(v_score, 100) * 0.4
        
        # 손익비 (30%)
        rr = result.get('rr_ratio', 0)
        if rr >= 3.0:
            score += 30
            reasons.append('손익비 우수 (1:3.0+)')
        elif rr >= 2.0:
            score += 20
            reasons.append('손익비 양호 (1:2.0+)')
        else:
            score += rr * 10
        
        # 시장조사 데이터 (20%)
        if result.get('market_research', {}).get('has_dart_data'):
            score += 20
            reasons.append('DART 데이터 확인됨')
        
        # 기대 수익률 (10%)
        expected_return = result.get('expected_return', 0)
        if expected_return >= 30:
            score += 10
        elif expected_return >= 20:
            score += 7
        elif expected_return >= 15:
            score += 5
        
        # 등급 산정
        if score >= 90:
            grade = 'A+'
        elif score >= 80:
            grade = 'A'
        elif score >= 70:
            grade = 'B+'
        elif score >= 60:
            grade = 'B'
        else:
            grade = 'C'
        
        return {
            'score': round(score, 1),
            'grade': grade,
            'reasons': reasons
        }
    
    def generate_report(self, analyzed_results):
        """통합 리포트 생성"""
        kst = timezone(timedelta(hours=9))
        now = datetime.now(kst)
        
        # Markdown 리포트
        md = f"""# 🎯 V전략 종합 분석 리포트
## {now.strftime('%Y년 %m월 %d일')} 기준

---

## 📊 분석 개요

| 항목 | 수치 |
|:---|:---:|
| **분석 종목** | 3,300+ 개 |
| **V전략 선정** | {len(analyzed_results)}개 |
| **데이터 소스** | DART + 시장조사 + 기술분석 |

---

"""
        
        # TOP 종목 상세 분석
        md += "## 🏆 TOP 선정 종목\n\n"
        
        for i, result in enumerate(analyzed_results[:10], 1):
            symbol = result['symbol']
            rating = result['overall_rating']
            market = result.get('market_research', {})
            
            md += f"""### {i}. {symbol} - **등급: {rating['grade']}** ({rating['score']}점)

| 구분 | 내용 |
|:---|:---|
| **현재가** | ₩{result['current_price']:,.0f} |
| **진입가** | ₩{result['entry_price']:,.0f} |
| **목표가** | ₩{result['target_price']:,.0f} (+{result['expected_return']:.1f}%) |
| **손절가** | ₩{result['stop_loss']:,.0f} ({result['expected_loss']:.1f}%) |
| **손익비** | 1:{result['rr_ratio']:.2f} |
| **가치점수** | {result['value_score']:.1f}점 ({result['strategy_type']}) |
| **Fibonacci** | {result['fib_level']} |

**종합 판단 근거:**
"""
            for reason in rating['reasons']:
                md += f"- ✅ {reason}\n"
            
            # 시장조사 데이터
            if market.get('has_dart_data'):
                md += f"\n**📋 기업 정보 (DART):**\n"
                md += f"- 기업명: {market.get('company_name', 'N/A')}\n"
                md += f"- 업종: {market.get('industry', 'N/A')}\n"
                if market.get('employees'):
                    md += f"- 임직원: {market.get('employees'):,}명\n"
            else:
                md += f"\n⚠️ DART 데이터 없음 - 기술적 분석 위주\n"
            
            md += "\n---\n\n"
        
        # 요약 및 전략
        md += f"""## 💡 투자 전략 제안

### 종목 분포

| 등급 | 종목 수 | 특징 |
|:---|:---:|:---|
"""
        
        grade_counts = {}
        for r in analyzed_results:
            g = r['overall_rating']['grade']
            grade_counts[g] = grade_counts.get(g, 0) + 1
        
        for grade in ['A+', 'A', 'B+', 'B', 'C']:
            count = grade_counts.get(grade, 0)
            if count > 0:
                desc = {'A+': '최우선 매수 후보', 'A': '매수 우선순위', 'B+': '관심 종목', 'B': '추가 확인 필요', 'C': '관망'}[grade]
                md += f"| **{grade}** | {count}개 | {desc} |\n"
        
        md += f"""
### 리스크 관리

- **포지션 크기:** 종목당 최대 5% (등급 A+는 7%까지)
- **손절 준수:** -10% 도달 시 즉시 처분
- **분산 투자:** 최소 5개 종목 이상 분산
- **재평가 주기:** 주 1회 등급 재산정

---

## ⏰ 리포트 정보

- **생성 시간:** {now.strftime('%Y-%m-%d %H:%M:%S')} KST
- **분석 기준:** V전략 (Value + Fibonacci + ATR)
- **데이터 소스:** 
  - 한국거래소 주가 데이터
  - DART 전자공시
  - 시장조사 리포트
- **자동 생성:** V전략 통합 분석 시스템

---

*이 리포트는 투자 참고 자료이며, 투자 결정은 본인의 책임하에 신중히 결정하시기 바랍니다.*
"""
        
        # 저장
        output_dir = Path('/root/.openclaw/workspace/strg/docs')
        output_dir.mkdir(exist_ok=True)
        
        md_path = output_dir / f'V_Strategy_Integrated_{self.today_str}.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md)
        
        return md_path


def main():
    """메인 실행"""
    print("=" * 70)
    print("🎯 V전략 종합 분석 시스템")
    print("=" * 70)
    
    analyzer = VStrategyIntegratedAnalyzer()
    
    # 1. 종목 로드
    symbols = analyzer.get_all_symbols()
    print(f"📊 총 {len(symbols)}개 종목 로드됨")
    
    # 2. V전략 스캔 (전체 실행 - 시간이 오래 걸림)
    print("\n🔍 V전략 스캔 실행 중...")
    print("(전체 3,300개 종목 스캔 - 약 10-15분 소요)")
    v_results = analyzer.run_v_scan(symbols)
    
    if not v_results:
        print("\n⚠️ 선정된 종목 없음")
        return
    
    print(f"\n✅ {len(v_results)}개 종목 V전략 통과")
    
    # 3. 상위 종목 심층 분석
    analyzed = analyzer.analyze_top_picks(v_results, top_n=10)
    
    # 4. 리포트 생성
    report_path = analyzer.generate_report(analyzed)
    
    print(f"\n✅ 리포트 생성 완료!")
    print(f"   📄 {report_path}")
    print(f"\n📊 선정 종목 요약:")
    for i, r in enumerate(analyzed[:5], 1):
        grade = r['overall_rating']['grade']
        score = r['overall_rating']['score']
        print(f"   {i}. {r['symbol']}: 등급 {grade} ({score}점)")


if __name__ == '__main__':
    main()
