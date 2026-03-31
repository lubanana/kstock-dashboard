#!/usr/bin/env python3
"""
실시간 DART Quality Oversold 스캐너 (웹 검색 + 네이버증권 연동)
오늘 기준 과매도 + 재무우수 종목 발굴 + 추가 정보 수집
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
                'market_cap': None,
                'per': None,
                'pbr': None,
                'dividend_yield': None,
                'foreign_ownership': None,
                'institutional_ownership': None,
                'trading_volume': None,
                'sector': None,
                'industry': None,
                'recent_news': [],
                'opinion': None,
                'target_price': None
            }
            
            # 시가총액 - 새로운 방식으로 파싱
            try:
                # 투자정보 테이블에서 시총 찾기
                invest_info = soup.select('.first td em')
                for em in invest_info:
                    text = em.text.strip()
                    if '조' in text or '억' in text:
                        # 시총 추출
                        cap_match = re.search(r'(\d+[\d,]*)\s*(조|억)', text)
                        if cap_match:
                            value = int(cap_match.group(1).replace(',', ''))
                            unit = cap_match.group(2)
                            if unit == '조':
                                info['market_cap'] = value * 10000  # 조를 억으로 변환
                            else:
                                info['market_cap'] = value
                        break
            except:
                pass
            
            # PER, PBR - 기업실적분석 테이블에서 추출 (최신 데이터)
            try:
                # 모든 테이블 검색
                tables = soup.find_all('table')
                for table in tables:
                    # PER 찾기
                    per_th = table.find('th', string=lambda x: x and 'PER' in x and 'EPS' not in x)
                    if per_th:
                        per_row = per_th.find_parent('tr')
                        if per_row:
                            tds = per_row.find_all('td')
                            if len(tds) >= 2:
                                # 최근 분기 데이터 (마지막 열)
                                per_text = tds[-1].text.strip().replace(',', '')
                                try:
                                    per_val = float(per_text)
                                    if 0 < per_val < 1000:  # 정상 범위
                                        info['per'] = per_val
                                except:
                                    pass
                    
                    # PBR 찾기
                    pbr_th = table.find('th', string=lambda x: x and 'PBR' in x)
                    if pbr_th:
                        pbr_row = pbr_th.find_parent('tr')
                        if pbr_row:
                            tds = pbr_row.find_all('td')
                            if len(tds) >= 2:
                                pbr_text = tds[-1].text.strip().replace(',', '')
                                try:
                                    pbr_val = float(pbr_text)
                                    if 0 < pbr_val < 100:  # 정상 범위
                                        info['pbr'] = pbr_val
                                except:
                                    pass
            except Exception as e:
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
            
            # 투자의견, 목표주가
            try:
                opinion_section = soup.select('.first td')
                for td in opinion_section:
                    text = td.text.strip()
                    if '매수' in text or '중립' in text or '매도' in text:
                        info['opinion'] = text[:10]
                    if '목표주가' in text:
                        target_match = re.search(r'(\d+[\d,]*)', text)
                        if target_match:
                            info['target_price'] = int(target_match.group(1).replace(',', ''))
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
            
            # 거래대금
            try:
                amount = soup.select_one('#_amount')
                if amount:
                    info['trading_volume'] = amount.text.strip()
            except:
                pass
            
            self.cache[symbol] = info
            return info
            
        except Exception as e:
            return {
                'market_cap': None, 'per': None, 'pbr': None,
                'dividend_yield': None, 'foreign_ownership': None,
                'institutional_ownership': None, 'trading_volume': None,
                'sector': None, 'industry': None, 'recent_news': [],
                'opinion': None, 'target_price': None
            }
    
    def search_stock_info(self, name, symbol):
        """웹 검색을 통한 종목 정보 수집 (kimi_search 활용)"""
        try:
            info = {
                'investment_opinion': None,
                'target_price': None,
                'analyst_count': None,
                'recent_themes': [],
                'risk_factors': [],
                'catalysts': [],
                'search_summary': None
            }
            
            # 실제 사용 시 kimi_search 도구를 호출하도록 구조만 마련
            # 현재는 빈 구조 반환 (실제 구현은 외부에서 처리)
            
            return info
            
        except Exception as e:
            return {
                'investment_opinion': None, 'target_price': None,
                'analyst_count': None, 'recent_themes': [],
                'risk_factors': [], 'catalysts': [],
                'search_summary': None
            }


# 웹 검색 기능을 위한 외부 함수
def collect_web_search_info(stock_name, stock_symbol):
    """
    종목에 대한 웹 검색 정보 수집
    실제 사용 시 이 함수를 호출하여 추가 정보 수집
    """
    search_query = f"{stock_name} {stock_symbol} 주식 투자 의견 목표주가"
    
    # 여기서 kimi_search 도구를 사용할 수 있음
    # 결과를 파싱하여 투자의견, 목표주가 등 추출
    
    return {
        'query': search_query,
        'collected_at': datetime.now().isoformat()
    }


class DARTRealtimeScanner:
    """실시간 스캐너 (웹 정보 포함)"""
    
    def __init__(self, collect_web_info=True):
        self.price_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
        self.dart_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/dart_financial.db')
        self.fundamental_cache = {}
        self.web_collector = WebInfoCollector() if collect_web_info else None
        self.collect_web_info = collect_web_info
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
        """최신 재무 점수 계산"""
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
        
        # 성장성
        revenue_growth = 0
        profit_growth = 0
        if prev and prev[1] > 0 and prev[3] > 0:
            revenue_growth = ((latest[1] - prev[1]) / prev[1]) * 100
            profit_growth = ((latest[3] - prev[3]) / prev[3]) * 100
        
        # 퀄리티 점수
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
            # 재무 데이터
            fund = self.get_fundamental_score(symbol)
            if not fund or fund['quality_score'] < 60:
                return None
            
            # 가격 데이터 (최근 400일)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=400)
            df = get_price(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 100:
                return None
            
            latest = df.iloc[-1]
            if latest['Close'] < 1000:
                return None
            
            # RSI 계산
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_val = rsi.iloc[-1]
            
            if rsi_val > 40:
                return None
            
            # 52주 고점 대비
            high_52w = df['High'].tail(252).max()
            vs_high = (latest['Close'] - high_52w) / high_52w * 100
            
            if vs_high > -10:
                return None
            
            # 종목명 조회
            name = self.price_conn.execute(
                'SELECT name FROM stock_info WHERE symbol = ?', (symbol,)
            ).fetchone()
            name = name[0] if name else 'Unknown'
            
            result = {
                'symbol': symbol,
                'name': name,
                'price': latest['Close'],
                'rsi': rsi_val,
                'vs_52w_high': vs_high,
                'quality_score': fund['quality_score'],
                'roe': fund['roe'],
                'debt_ratio': fund['debt_ratio'],
                'op_margin': fund['op_margin'],
                'revenue_growth': fund['revenue_growth'],
                'profit_growth': fund['profit_growth'],
                'year': fund['year']
            }
            
            # 웹 정보 수집
            if self.collect_web_info and self.web_collector:
                try:
                    # 네이버 증권 정보
                    naver_info = self.web_collector.get_naver_stock_info(symbol)
                    result['naver'] = naver_info
                    
                    # 웹 검색 정보
                    web_info = self.web_collector.search_stock_info(name, symbol)
                    result['web_search'] = web_info
                    
                    # API 호출 간격 조절
                    time.sleep(0.1)
                    
                except Exception as e:
                    result['naver'] = {}
                    result['web_search'] = {}
            
            return result
            
        except Exception as e:
            return None
    
    def run(self):
        """전체 종목 스캔"""
        print("="*70)
        print(f"📊 실시간 DART Quality Oversold 스캐너")
        print(f"기준일: {datetime.now().strftime('%Y-%m-%d')}")
        if self.collect_web_info:
            print(f"🌐 웹 정보 수집: 활성화 (네이버증권 + 웹검색)")
        print("="*70)
        print("\n선정 기준:")
        print("  • 재무점수 60점+")
        print("  • RSI 40 이하")
        print("  • 52주 고점 대비 -10%+")
        print("  • 주가 1,000원 이상")
        print()
        
        # 전체 종목 로드
        symbols = [r[0] for r in self.price_conn.execute('SELECT symbol FROM stock_info').fetchall()]
        print(f"대상: {len(symbols)}개 종목\n")
        
        results = []
        for i, symbol in enumerate(symbols, 1):
            if i % 200 == 0:
                print(f"  [{i}/{len(symbols)}] 스캔 중... (선정: {len(results)}개)", end='\r')
            
            result = self.scan_stock(symbol)
            if result:
                results.append(result)
                web_status = "🌐" if self.collect_web_info and 'naver' in result else ""
                print(f"  ✓ {symbol} ({result['name']}) {web_status} - 재무:{result['quality_score']:.0f} RSI:{result['rsi']:.1f}")
        
        print(f"\n\n✅ 선정 완료: {len(results)}개 종목")
        return sorted(results, key=lambda x: x['quality_score'], reverse=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='DART Quality Oversold Scanner')
    parser.add_argument('--no-web', action='store_true', help='웹 정보 수집 비활성화')
    parser.add_argument('--top', type=int, default=20, help='표시할 상위 종목 수')
    args = parser.parse_args()
    
    scanner = DARTRealtimeScanner(collect_web_info=not args.no_web)
    results = scanner.run()
    
    if results:
        print("\n" + "="*70)
        print("📈 오늘의 선정 종목")
        print("="*70)
        print(f"{'순위':<4} {'종목':<8} {'이름':<12} {'현재가':<10} {'RSI':<6} {'52주대비':<10} {'재무점수':<8}")
        print("-"*70)
        
        for i, r in enumerate(results[:args.top], 1):
            name_short = r['name'][:10] if len(r['name']) > 10 else r['name']
            print(f"{i:<4} {r['symbol']:<8} {name_short:<12} {r['price']:>8,.0f} {r['rsi']:>5.1f} {r['vs_52w_high']:>8.1f}% {r['quality_score']:>7.0f}")
        
        # 상세 정보 (웹 정보 포함)
        print("\n" + "="*70)
        print("📊 상세 재무 및 웹 정보")
        print("="*70)
        for i, r in enumerate(results[:10], 1):
            print(f"\n{i}. {r['symbol']} {r['name']} ({r['year']}년 기준)")
            print(f"   현재가: {r['price']:,.0f}원 | RSI: {r['rsi']:.1f} | 52주대비: {r['vs_52w_high']:.1f}%")
            print(f"   재무점수: {r['quality_score']:.0f}/100")
            print(f"   ROE: {r['roe']:.1f}% | 부채비율: {r['debt_ratio']:.1f}% | 영업익률: {r['op_margin']:.1f}%")
            
            # 네이버 정보 표시
            if 'naver' in r and r['naver']:
                naver = r['naver']
                print(f"   📱 네이버증권:")
                if naver.get('market_cap'):
                    print(f"      시총: {naver['market_cap']:,.0f}억원", end='')
                if naver.get('per'):
                    print(f" | PER: {naver['per']:.2f}", end='')
                if naver.get('pbr'):
                    print(f" | PBR: {naver['pbr']:.2f}", end='')
                if naver.get('dividend_yield'):
                    print(f" | 배당율: {naver['dividend_yield']:.2f}%", end='')
                print()
                
                if naver.get('sector'):
                    print(f"      업종: {naver['sector']}")
                
                if naver.get('recent_news') and len(naver['recent_news']) > 0:
                    print(f"      📰 최신 뉴스:")
                    for news in naver['recent_news'][:2]:
                        print(f"         • {news[:50]}...")
    
    # 저장
    date_str = datetime.now().strftime('%Y%m%d')
    output = f'/root/.openclaw/workspace/strg/docs/dart_realtime_scan_{date_str}.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 결과 저장: {output}")
    
    # 요약 저장
    summary = {
        'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_selected': len(results),
        'criteria': {
            'quality_score_min': 60,
            'rsi_max': 40,
            'vs_52w_high_max': -10,
            'price_min': 1000
        },
        'top_picks': results[:10] if len(results) >= 10 else results
    }
    summary_output = f'/root/.openclaw/workspace/strg/docs/dart_scan_summary_{date_str}.json'
    with open(summary_output, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"📄 요약 저장: {summary_output}")


if __name__ == '__main__':
    main()
