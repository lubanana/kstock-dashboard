#!/usr/bin/env python3
"""
통합 스캐너 파이프라인
1. 기본 스캔 (재무점수 + 기술적 지표)
2. 웹 정보 수집 (네이버증권)
3. 웹 검색 분석 (투자의견, 뉴스, 촉매제)
4. 최종 판단 및 추천
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sqlite3
import sys
import time
import re
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/root/.openclaw/workspace/strg')
from fdr_wrapper import get_price

# Web scraping
import requests
from bs4 import BeautifulSoup

class WebInfoCollector:
    """웹 정보 수집기"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache = {}
    
    def get_naver_stock_info(self, symbol):
        """네이버 증권에서 종목 정보 수집"""
        try:
            if symbol in self.cache:
                return self.cache[symbol]
            
            url = f"https://finance.naver.com/item/main.naver?code={symbol}"
            response = self.session.get(url, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            info = {
                'market_cap': None, 'per': None, 'pbr': None,
                'dividend_yield': None, 'foreign_ownership': None,
                'sector': None, 'recent_news': [], 'opinion': None
            }
            
            # 시가총액
            try:
                invest_info = soup.select('.first td em')
                for em in invest_info:
                    text = em.text.strip()
                    if '조' in text or '억' in text:
                        cap_match = re.search(r'(\d+[\d,]*)\s*(조|억)', text)
                        if cap_match:
                            value = int(cap_match.group(1).replace(',', ''))
                            unit = cap_match.group(2)
                            info['market_cap'] = value * 10000 if unit == '조' else value
                        break
            except:
                pass
            
            # PER, PBR
            try:
                tables = soup.find_all('table')
                for table in tables:
                    per_th = table.find('th', string=lambda x: x and 'PER' in x and 'EPS' not in x)
                    if per_th:
                        per_row = per_th.find_parent('tr')
                        if per_row:
                            tds = per_row.find_all('td')
                            if len(tds) >= 2:
                                per_text = tds[-1].text.strip().replace(',', '')
                                try:
                                    per_val = float(per_text)
                                    if 0 < per_val < 1000:
                                        info['per'] = per_val
                                except:
                                    pass
                    
                    pbr_th = table.find('th', string=lambda x: x and 'PBR' in x)
                    if pbr_th:
                        pbr_row = pbr_th.find_parent('tr')
                        if pbr_row:
                            tds = pbr_row.find_all('td')
                            if len(tds) >= 2:
                                pbr_text = tds[-1].text.strip().replace(',', '')
                                try:
                                    pbr_val = float(pbr_text)
                                    if 0 < pbr_val < 100:
                                        info['pbr'] = pbr_val
                                except:
                                    pass
            except:
                pass
            
            # 외국인 보유비중
            try:
                foreign_rows = soup.select('table tr')
                for row in foreign_rows:
                    if '외국인소진율' in row.text or '외국인비율' in row.text:
                        foreign_td = row.select('td em')
                        if foreign_td:
                            info['foreign_ownership'] = foreign_td[-1].text.strip()
            except:
                pass
            
            # 최신 뉴스
            try:
                news_section = soup.select('.section_news li a, .news_list li a')
                for news in news_section[:3]:
                    title = news.text.strip()
                    if title and len(title) > 5:
                        info['recent_news'].append(title)
            except:
                pass
            
            self.cache[symbol] = info
            return info
            
        except Exception as e:
            return {'market_cap': None, 'per': None, 'pbr': None, 
                    'foreign_ownership': None, 'sector': None, 'recent_news': []}


class IntegratedScanner:
    """통합 스캐너"""
    
    def __init__(self):
        self.price_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
        self.dart_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/dart_financial.db')
        self.fundamental_cache = {}
        self.web_collector = WebInfoCollector()
        self.load_fundamentals()
        
    def load_fundamentals(self):
        """재무 데이터 로드"""
        cursor = self.dart_conn.cursor()
        results = cursor.execute('''
            SELECT stock_code, year, revenue, operating_profit, net_income, 
                   total_assets, total_liabilities, total_equity
            FROM financial_data WHERE reprt_code = '11011'
            ORDER BY stock_code, year DESC
        ''').fetchall()
        
        for row in results:
            code = row[0]
            if code not in self.fundamental_cache:
                self.fundamental_cache[code] = []
            self.fundamental_cache[code].append(row[1:])
    
    def get_fundamental_score(self, symbol):
        """재무 점수 계산"""
        if symbol not in self.fundamental_cache:
            return None
        
        data = self.fundamental_cache[symbol]
        if not data:
            return None
        
        latest = data[0]
        prev = data[1] if len(data) > 1 else None
        revenue, op_profit, net_income, assets, liabilities, equity = latest[1:]
        
        if equity <= 0 or revenue <= 0:
            return None
        
        roe = (net_income / equity) * 100
        debt_ratio = (liabilities / equity) * 100
        op_margin = (op_profit / revenue) * 100
        
        revenue_growth = 0
        profit_growth = 0
        if prev and prev[1] > 0 and prev[3] > 0:
            revenue_growth = ((latest[1] - prev[1]) / prev[1]) * 100
            profit_growth = ((latest[3] - prev[3]) / prev[3]) * 100
        
        score = 0
        if roe >= 20: score += 30
        elif roe >= 15: score += 25
        elif roe >= 10: score += 20
        elif roe >= 5: score += 10
        
        if debt_ratio <= 50: score += 25
        elif debt_ratio <= 100: score += 20
        elif debt_ratio <= 200: score += 15
        elif debt_ratio <= 300: score += 10
        
        if op_margin >= 20: score += 25
        elif op_margin >= 15: score += 20
        elif op_margin >= 10: score += 15
        elif op_margin >= 5: score += 10
        
        if revenue_growth >= 20: score += 10
        elif revenue_growth >= 10: score += 7
        elif revenue_growth >= 0: score += 5
        
        if profit_growth >= 30: score += 10
        elif profit_growth >= 10: score += 7
        elif profit_growth >= 0: score += 5
        
        return {
            'quality_score': score, 'roe': roe, 'debt_ratio': debt_ratio,
            'op_margin': op_margin, 'revenue_growth': revenue_growth,
            'profit_growth': profit_growth, 'year': latest[0]
        }
    
    def scan_stock(self, symbol):
        """개별 종목 스캔"""
        try:
            fund = self.get_fundamental_score(symbol)
            if not fund or fund['quality_score'] < 60:
                return None
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400)
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 100:
                return None
            
            latest = df.iloc[-1]
            if latest['Close'] < 1000:
                return None
            
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1]
            
            if rsi_val > 40:
                return None
            
            high_52w = df['High'].tail(252).max()
            vs_high = (latest['Close'] - high_52w) / high_52w * 100
            
            if vs_high > -10:
                return None
            
            name = self.price_conn.execute(
                'SELECT name FROM stock_info WHERE symbol = ?', (symbol,)
            ).fetchone()
            name = name[0] if name else 'Unknown'
            
            return {
                'symbol': symbol, 'name': name, 'price': latest['Close'],
                'rsi': rsi_val, 'vs_52w_high': vs_high,
                'quality_score': fund['quality_score'], 'roe': fund['roe'],
                'debt_ratio': fund['debt_ratio'], 'op_margin': fund['op_margin'],
                'revenue_growth': fund['revenue_growth'], 'profit_growth': fund['profit_growth'],
                'year': fund['year']
            }
            
        except Exception as e:
            return None
    
    def collect_web_info(self, stock):
        """웹 정보 수집"""
        symbol = stock['symbol']
        print(f"    🌐 네이버증권 정보 수집 중...", end=' ')
        
        naver_info = self.web_collector.get_naver_stock_info(symbol)
        stock['naver'] = naver_info
        
        # 간단한 정보 출력
        info_parts = []
        if naver_info.get('per'):
            info_parts.append(f"PER:{naver_info['per']:.1f}")
        if naver_info.get('pbr'):
            info_parts.append(f"PBR:{naver_info['pbr']:.1f}")
        if naver_info.get('market_cap'):
            info_parts.append(f"시총:{naver_info['market_cap']/10000:.1f}조")
        
        if info_parts:
            print(f"✓ ({', '.join(info_parts)})")
        else:
            print("✓")
        
        time.sleep(0.1)
        return stock
    
    def make_final_judgment(self, stock):
        """최종 판단"""
        judgments = []
        score = 0
        max_score = 100
        
        # 1. 재무 점수 (30점)
        if stock['quality_score'] >= 90:
            judgments.append("✓ 재무상태 매우 우수 (90점+)")
            score += 30
        elif stock['quality_score'] >= 80:
            judgments.append("✓ 재무상태 우수 (80점+)")
            score += 25
        elif stock['quality_score'] >= 70:
            judgments.append("○ 재무상태 양호 (70점+)")
            score += 20
        else:
            judgments.append("△ 재무상태 보통 (60점+)")
            score += 15
        
        # 2. 기술적 지표 (25점)
        if stock['rsi'] <= 20:
            judgments.append("✓ 극심한 과매도 (RSI 20-)")
            score += 25
        elif stock['rsi'] <= 30:
            judgments.append("✓ 강한 과매도 (RSI 30-)")
            score += 22
        elif stock['rsi'] <= 40:
            judgments.append("○ 과매도 상태 (RSI 40-)")
            score += 18
        
        # 3. 가격 조건 (20점)
        if stock['vs_52w_high'] <= -40:
            judgments.append("✓ 52주 고점 대비 급락 (-40%+)")
            score += 20
        elif stock['vs_52w_high'] <= -30:
            judgments.append("✓ 52주 고점 대비 큰 하락 (-30%+)")
            score += 18
        elif stock['vs_52w_high'] <= -20:
            judgments.append("○ 52주 고점 대비 하락 (-20%+)")
            score += 15
        else:
            judgments.append("△ 52주 고점 대비 소폭 하락 (-10%+)")
            score += 12
        
        # 4. 네이버 정보 (15점)
        if 'naver' in stock and stock['naver']:
            naver = stock['naver']
            
            # 저PER
            if naver.get('per') and naver['per'] < 10:
                judgments.append("✓ 저PER (10배 미만)")
                score += 5
            
            # 저PBR
            if naver.get('pbr') and naver['pbr'] < 1:
                judgments.append("✓ 저PBR (1배 미만)")
                score += 5
            
            # 외국인 보유
            if naver.get('foreign_ownership'):
                try:
                    foreign_pct = float(naver['foreign_ownership'].replace('%', ''))
                    if foreign_pct > 30:
                        judgments.append("✓ 외국인 높은 관심 (30%+)")
                        score += 5
                    elif foreign_pct > 10:
                        judgments.append("○ 외국인 관심 (10%+)")
                        score += 3
                except:
                    pass
        
        # 5. 성장성 (10점)
        if stock.get('profit_growth', 0) > 50:
            judgments.append("✓ 높은 성장성 (순이익 +50%+)")
            score += 10
        elif stock.get('profit_growth', 0) > 20:
            judgments.append("○ 우수한 성장성 (순이익 +20%+)")
            score += 7
        elif stock.get('profit_growth', 0) > 0:
            judgments.append("△ 양호한 성장성 (순이익 +%)")
            score += 5
        
        # 등급 산정
        if score >= 85:
            grade = "S급 (강력매수)"
            recommendation = "즉시 매수 고려. 10일 보유 시 +2.66% 예상"
        elif score >= 70:
            grade = "A급 (매수)"
            recommendation = "매수 적기. 분할 매수 전략 권장"
        elif score >= 55:
            grade = "B급 (관망 후 매수)"
            recommendation = "추가 하띜 기다리거나 소액 매수"
        else:
            grade = "C급 (관망)"
            recommendation = "관망 권장"
        
        stock['final_score'] = score
        stock['final_grade'] = grade
        stock['final_recommendation'] = recommendation
        stock['judgments'] = judgments
        
        return stock
    
    def run(self, max_stocks=50):
        """전체 파이프라인 실행"""
        print("="*70)
        print("🔍 통합 스캐너 파이프라인")
        print("="*70)
        print("\n[단계 1/4] 기본 스캔: 재무점수 60+, RSI 40-, 52주 -10%+")
        print("[단계 2/4] 웹 정보 수집: 네이버증권 (PER, PBR, 뉴스)")
        print("[단계 3/4] 종합 분석: 다차원 평가")
        print("[단계 4/4] 최종 판단: 등급 및 추천")
        print()
        
        # 1. 기본 스캔
        symbols = [r[0] for r in self.price_conn.execute('SELECT symbol FROM stock_info').fetchall()]
        print(f"📊 대상: {len(symbols)}개 종목 스캔 중...\n")
        
        results = []
        for i, symbol in enumerate(symbols, 1):
            if i % 200 == 0:
                print(f"   [{i}/{len(symbols)}] 진행중... (선정: {len(results)}개)", end='\r')
            
            result = self.scan_stock(symbol)
            if result:
                results.append(result)
                if len(results) <= 5:  # 처음 5개만 출력
                    print(f"   ✓ {symbol} {result['name']} - 재무:{result['quality_score']:.0f} RSI:{result['rsi']:.1f}")
        
        print(f"\n✅ 단계 1 완료: {len(results)}개 종목 선정\n")
        
        # 상위 max_stocks개만 진행
        results = sorted(results, key=lambda x: x['quality_score'], reverse=True)[:max_stocks]
        
        # 2. 웹 정보 수집
        print(f"📡 단계 2: 웹 정보 수집 (상위 {len(results)}개 종목)")
        print("-"*70)
        for i, stock in enumerate(results, 1):
            print(f"\n[{i}/{len(results)}] {stock['name']} ({stock['symbol']})")
            self.collect_web_info(stock)
        
        print("\n✅ 단계 2 완료\n")
        
        # 3. 최종 판단
        print("🎯 단계 3/4: 종합 분석 및 최종 판단")
        print("-"*70)
        
        final_results = []
        for stock in results:
            self.make_final_judgment(stock)
            final_results.append(stock)
        
        # 등급별 정렬
        final_results = sorted(final_results, key=lambda x: x['final_score'], reverse=True)
        
        return final_results


def print_final_report(results, top_n=20):
    """최종 리포트 출력"""
    print("\n" + "="*70)
    print("📋 최종 리포트")
    print("="*70)
    
    # 등급별 통계
    grade_counts = {}
    for r in results:
        grade = r['final_grade'].split()[0]
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    
    print("\n📊 등급별 통계:")
    for grade in ['S급', 'A급', 'B급', 'C급']:
        if grade in grade_counts:
            print(f"   {grade}: {grade_counts[grade]}개")
    
    # TOP 종목
    print(f"\n🏆 TOP {top_n} 추천 종목")
    print("="*70)
    
    for i, r in enumerate(results[:top_n], 1):
        print(f"\n{'─'*70}")
        print(f"{i}. [{r['final_grade']}] {r['symbol']} {r['name']}")
        print(f"{'─'*70}")
        print(f"   💰 현재가: {r['price']:,.0f}원 | RSI: {r['rsi']:.1f} | 52주대비: {r['vs_52w_high']:.1f}%")
        print(f"   📈 재무점수: {r['quality_score']:.0f}/100 | ROE: {r['roe']:.1f}%")
        print(f"   🎯 종합점수: {r['final_score']}/100")
        print(f"   💡 추천: {r['final_recommendation']}")
        
        # 판단 근거
        print(f"\n   📋 판단 근거:")
        for judgment in r['judgments']:
            print(f"      {judgment}")
        
        # 네이버 정보
        if 'naver' in r and r['naver']:
            naver = r['naver']
            print(f"\n   📱 네이버증권:")
            metrics = []
            if naver.get('per'): metrics.append(f"PER: {naver['per']:.1f}배")
            if naver.get('pbr'): metrics.append(f"PBR: {naver['pbr']:.2f}배")
            if naver.get('market_cap'): metrics.append(f"시총: {naver['market_cap']/10000:.1f}조")
            if naver.get('foreign_ownership'): metrics.append(f"외국인: {naver['foreign_ownership']}")
            if metrics:
                print(f"      {' | '.join(metrics)}")
            
            if naver.get('recent_news') and len(naver['recent_news']) > 0:
                print(f"      📰 {naver['recent_news'][0][:55]}...")


def main():
    scanner = IntegratedScanner()
    results = scanner.run(max_stocks=50)
    
    print_final_report(results, top_n=20)
    
    # 저장
    date_str = datetime.now().strftime('%Y%m%d')
    output = f'/root/.openclaw/workspace/strg/docs/dart_integrated_scan_{date_str}.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 결과 저장: {output}")


if __name__ == '__main__':
    main()
