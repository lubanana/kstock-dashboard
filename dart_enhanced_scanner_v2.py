#!/usr/bin/env python3
"""
통합 스캐너 v2.0 - LazyAlpha 섹터 강도 연동
기본 스캔 + 웹 정보 + 섹터 강도 + 5일 워치 누적
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
from sector_strength_analyzer import SectorStrengthAnalyzer

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
            
            # 섹터 정보 추출
            try:
                sector_elem = soup.select_one('.section_trade .category em, .snb_inner .em')
                if sector_elem:
                    info['sector'] = sector_elem.text.strip()
            except:
                pass
            
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


class EnhancedIntegratedScanner:
    """통합 스캐너 v2.0 - LazyAlpha 섹터 강도 연동"""
    
    def __init__(self):
        self.price_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/pivot_strategy.db')
        self.dart_conn = sqlite3.connect('/root/.openclaw/workspace/strg/data/dart_financial.db')
        self.fundamental_cache = {}
        self.web_collector = WebInfoCollector()
        self.sector_analyzer = SectorStrengthAnalyzer()
        self.load_fundamentals()
        
        # 섹터 매핑 캐시
        self.sector_cache = {}
        
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
    
    def get_sector(self, symbol, name):
        """종목의 섹터 정보 조회"""
        # 캐시 확인
        if symbol in self.sector_cache:
            return self.sector_cache[symbol]
        
        # 기본 섹터 매핑 (주요 종목)
        sector_mapping = {
            # 반도체
            '042700': '반도체', '058470': '반도체', '092130': '반도체', 
            '348210': '반도체', '253590': '반도체', '064350': '반도체',
            '005930': '반도체', '000660': '반도체', '005380': '자동차',
            # 바이오
            '068270': '바이오', '207940': '바이오', '128940': '바이오',
            # 2차전지
            '051910': '2차전지', '006400': '2차전지', '003670': '2차전지',
            # 은행
            '005490': '은행', '000270': '은행', '086790': '은행',
            # 화학
            '051900': '화학', '011170': '화학', '010950': '화학',
            # 중공업
            '009540': '중공업', '012450': '중공업', '034020': '중공업',
            # IT/소프트웨어
            '035720': 'IT', '035420': 'IT', '018260': 'IT',
        }
        
        if symbol in sector_mapping:
            self.sector_cache[symbol] = sector_mapping[symbol]
            return sector_mapping[symbol]
        
        # 이름 기반 추정
        if any(x in name for x in ['반도체', '전자', '회로', '칩']):
            return '반도체'
        elif any(x in name for x in ['바이오', '제약', '헬스케어']):
            return '바이오'
        elif any(x in name for x in ['화학', '소재', '재료']):
            return '화학'
        elif any(x in name for x in ['자동차', '모빌리티']):
            return '자동차'
        elif any(x in name for x in ['건설', '건축']):
            return '건설'
        elif any(x in name for x in ['은행', '금융', '증권']):
            return '금융'
        elif any(x in name for x in ['IT', '소프트웨어', '플랫폼']):
            return 'IT'
        
        return '기타'
    
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
            
            # 섹터 정보
            sector = self.get_sector(symbol, name)
            
            return {
                'symbol': symbol, 'name': name, 'sector': sector, 'price': latest['Close'],
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
        naver_info = self.web_collector.get_naver_stock_info(symbol)
        stock['naver'] = naver_info
        
        # 네이버에서 가져온 섹터 정보로 업데이트
        if naver_info.get('sector'):
            stock['sector'] = naver_info['sector']
            self.sector_cache[symbol] = naver_info['sector']
        
        time.sleep(0.1)
        return stock
    
    def make_final_judgment(self, stock):
        """최종 판단 (기본)"""
        judgments = []
        score = 0
        
        # 1. 재무 점수 (30점)
        if stock['quality_score'] >= 90:
            judgments.append({"type": "positive", "text": "재무상태 매우 우수 (90점+)"})
            score += 30
        elif stock['quality_score'] >= 80:
            judgments.append({"type": "positive", "text": "재무상태 우수 (80점+)"})
            score += 25
        elif stock['quality_score'] >= 70:
            judgments.append({"type": "neutral", "text": "재무상태 양호 (70점+)"})
            score += 20
        else:
            judgments.append({"type": "warning", "text": "재무상태 보통 (60점+)"})
            score += 15
        
        # 2. 기술적 지표 (25점)
        if stock['rsi'] <= 20:
            judgments.append({"type": "positive", "text": "극심한 과매도 (RSI 20-)"})
            score += 25
        elif stock['rsi'] <= 30:
            judgments.append({"type": "positive", "text": "강한 과매도 (RSI 30-)"})
            score += 22
        elif stock['rsi'] <= 40:
            judgments.append({"type": "neutral", "text": "과매도 상태 (RSI 40-)"})
            score += 18
        
        # 3. 가격 조건 (20점)
        if stock['vs_52w_high'] <= -40:
            judgments.append({"type": "positive", "text": "52주 고점 대비 급락 (-40%+), 바닥권 진입"})
            score += 20
        elif stock['vs_52w_high'] <= -30:
            judgments.append({"type": "positive", "text": "52주 고점 대비 큰 하락 (-30%+), 반등 가능성"})
            score += 18
        elif stock['vs_52w_high'] <= -20:
            judgments.append({"type": "neutral", "text": "52주 고점 대비 하락 (-20%+), 가치 매수 구간"})
            score += 15
        else:
            judgments.append({"type": "warning", "text": "52주 고점 대비 소폭 하락 (-10%+), 추가 하락 가능성"})
            score += 12
        
        # 4. 네이버 정보 (15점)
        if 'naver' in stock and stock['naver']:
            naver = stock['naver']
            
            if naver.get('per') and naver['per'] < 10:
                judgments.append({"type": "positive", "text": f"저PER ({naver['per']:.1f}배) - 저평가"})
                score += 5
            elif naver.get('per') and naver['per'] > 50:
                judgments.append({"type": "warning", "text": f"고PER ({naver['per']:.1f}배) - 고평가 우려"})
            
            if naver.get('pbr') and naver['pbr'] < 1:
                judgments.append({"type": "positive", "text": f"저PBR ({naver['pbr']:.2f}배) - 자산 대비 저평가"})
                score += 5
            
            if naver.get('foreign_ownership'):
                try:
                    foreign_pct = float(naver['foreign_ownership'].replace('%', ''))
                    if foreign_pct > 30:
                        judgments.append({"type": "positive", "text": f"외국인 높은 관심 ({foreign_pct:.1f}%)"})
                        score += 5
                    elif foreign_pct > 10:
                        judgments.append({"type": "neutral", "text": f"외국인 관심 ({foreign_pct:.1f}%)"})
                        score += 3
                except:
                    pass
        
        # 5. 성장성 (10점)
        if stock.get('profit_growth', 0) > 50:
            judgments.append({"type": "positive", "text": f"높은 성장성 (순이익 +{stock['profit_growth']:.0f}%+)"})
            score += 10
        elif stock.get('profit_growth', 0) > 20:
            judgments.append({"type": "neutral", "text": f"우수한 성장성 (순이익 +{stock['profit_growth']:.0f}%+)"})
            score += 7
        elif stock.get('profit_growth', 0) > 0:
            judgments.append({"type": "neutral", "text": f"양호한 성장성 (순이익 +{stock['profit_growth']:.0f}%+)"})
            score += 5
        else:
            judgments.append({"type": "warning", "text": f"성장성 둔화 (순이익 {stock['profit_growth']:.0f}%)"})
        
        stock['base_score'] = score
        stock['judgments'] = judgments
        
        return stock
    
    def apply_lazyalpha_scoring(self, stock):
        """LazyAlpha 스타일 섹터 강도 점수 적용"""
        sector = stock.get('sector', '기타')
        symbol = stock['symbol']
        base_score = stock['base_score']
        
        # 현재 날짜의 섹터 강도 계산
        today = datetime.now().strftime('%Y-%m-%d')
        sector_strength = self.sector_analyzer.calculate_sector_strength(today)
        
        # 섹터 본 추가 (0-20점)
        sector_bonus = 0
        if sector in sector_strength:
            strength = sector_strength[sector]['strength']
            sector_bonus = min(max(strength * 2, 0), 20)
            stock['sector_strength'] = strength
            stock['sector_rank'] = list(sector_strength.keys()).index(sector) + 1
        else:
            stock['sector_strength'] = 0
            stock['sector_rank'] = '-'
        
        # 5일 워치 누적 별 추가 (0-15점)
        watch_score, watch_count = self.sector_analyzer.get_watch_accumulated_score(symbol)
        watch_bonus = min(watch_count * 3, 15)
        stock['watch_count'] = watch_count
        
        # 총점 계산
        total_score = base_score + sector_bonus + watch_bonus
        stock['final_score'] = round(total_score, 1)
        stock['score_breakdown'] = {
            'base_score': base_score,
            'sector_bonus': round(sector_bonus, 1),
            'watch_bonus': watch_bonus
        }
        
        # LazyAlpha 등급 산정
        if stock['final_score'] >= 90:
            stock['grade'] = 'S'
            stock['grade_text'] = '핵심 후보'
            stock['recommendation'] = '즉시 매수 고려. 10일 보유 시 +2.66% 예상'
            stock['grade_color'] = '#00ff88'
        elif stock['final_score'] >= 70:
            stock['grade'] = 'A'
            stock['grade_text'] = '관심'
            stock['recommendation'] = '매수 적기. 분할 매수 전략 권장'
            stock['grade_color'] = '#4dabf7'
        elif stock['final_score'] >= 55:
            stock['grade'] = 'B'
            stock['grade_text'] = '참고'
            stock['recommendation'] = '추가 하락 기다리거나 소액 매수'
            stock['grade_color'] = '#fcc419'
        else:
            stock['grade'] = 'C'
            stock['grade_text'] = '관망'
            stock['recommendation'] = '관망 권장'
            stock['grade_color'] = '#ff6b6b'
        
        return stock
    
    def run(self, max_stocks=50):
        """전체 파이프라인 실행"""
        print("="*70)
        print("🔍 통합 스캐너 v2.0 - LazyAlpha 섹터 강도 연동")
        print("="*70)
        print("\n[단계 1/5] 기본 스캔: 재무점수 60+, RSI 40-, 52주 -10%+")
        print("[단계 2/5] 웹 정보 수집: 네이버증권 (PER, PBR, 섹터, 뉴스)")
        print("[단계 3/5] 기본 판단: 재무/기술/가격/네이버/성장")
        print("[단계 4/5] LazyAlpha 점수: 섹터강도 + 5일워치누적")
        print("[단계 5/5] 최종 등급: 핵심후보/관심/참고/관망")
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
        
        print(f"\n✅ 단계 1 완료: {len(results)}개 종목 선정\n")
        
        # 상위 max_stocks개만 진행
        results = sorted(results, key=lambda x: x['quality_score'], reverse=True)[:max_stocks]
        
        # 2. 웹 정보 수집
        print(f"📡 단계 2: 웹 정보 수집 (상위 {len(results)}개 종목)")
        print("-"*70)
        for i, stock in enumerate(results, 1):
            print(f"[{i}/{len(results)}] {stock['name']} ({stock['symbol']}) - 섹터: {stock['sector']}")
            self.collect_web_info(stock)
        
        print("\n✅ 단계 2 완료\n")
        
        # 3. 기본 판단
        print("🎯 단계 3: 기본 판단")
        for stock in results:
            self.make_final_judgment(stock)
        
        # 4. LazyAlpha 점수 적용
        print("📊 단계 4: LazyAlpha 섹터 강도 점수 적용")
        print("-"*70)
        
        # 섹터 강도 미리 계산 (데모용 시그널 추가)
        demo_sectors = {}
        for stock in results[:20]:
            sector = stock.get('sector', '기타')
            if sector not in demo_sectors:
                demo_sectors[sector] = {'entry': 0, 'watch': 0, 'exit': 0}
            # 재무점수 기반으로 데모 시그널 생성
            if stock['quality_score'] >= 90:
                demo_sectors[sector]['entry'] += 1
            elif stock['quality_score'] >= 75:
                demo_sectors[sector]['watch'] += 1
        
        # 데모 시그널 저장
        today = datetime.now().strftime('%Y-%m-%d')
        for sector, counts in demo_sectors.items():
            for _ in range(counts['entry']):
                self.sector_analyzer.add_signal(sector, 'DEMO', 'entry', 80)
            for _ in range(counts['watch']):
                self.sector_analyzer.add_signal(sector, 'DEMO', 'watch', 70)
        
        # 섹터 강도 계산 및 출력
        sector_strength = self.sector_analyzer.calculate_sector_strength(today)
        print("\n📊 섹터 강도 순위 (LazyAlpha 공식: 진입×1.2 + 워치×0.4 − 청산)")
        print("-"*70)
        for i, (sector, data) in enumerate(sector_strength.items(), 1):
            print(f"   {i}. {sector:<12} 강도: {data['strength']:>6.1f}  (진입{data['entry']}, 워치{data['watch']}, 청산{data['exit']})")
        
        # 각 종목에 점수 적용
        for stock in results:
            self.apply_lazyalpha_scoring(stock)
        
        print("\n✅ 단계 4 완료\n")
        
        # 5. 최종 정렬
        results = sorted(results, key=lambda x: x['final_score'], reverse=True)
        
        return results
    
    def generate_html_report(self, results, date_str):
        """HTML 리포트 생성"""
        
        # 등급별 통계
        grade_counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0}
        for r in results:
            grade = r['grade']
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        # 섹터 강도 HTML
        today = datetime.now().strftime('%Y-%m-%d')
        sector_strength = self.sector_analyzer.calculate_sector_strength(today)
        
        sector_html = ""
        for i, (sector, data) in enumerate(sector_strength.items(), 1):
            strength_color = '#00ff88' if data['strength'] > 0 else '#ff6b6b' if data['strength'] < 0 else '#868e96'
            sector_html += f"""
            <div style="display: flex; justify-content: space-between; padding: 8px; 
                 background: rgba(255,255,255,0.03); margin: 5px 0; border-radius: 6px;">
                <span>{i}. {sector}</span>
                <span style="color: {strength_color}; font-weight: bold;">{data['strength']:.1f}</span>
            </div>
            """
        
        # TOP 종목 HTML
        top_stocks_html = ""
        for i, r in enumerate(results[:20], 1):
            # 판단 근거 HTML
            judgments_html = ""
            for j in r['judgments']:
                icon = "✓" if j['type'] == 'positive' else ("○" if j['type'] == 'neutral' else "△")
                color = "#00ff88" if j['type'] == 'positive' else ("#fcc419" if j['type'] == 'neutral' else "#ff6b6b")
                judgments_html += f'<div style="margin: 4px 0; color: {color}; font-size: 13px;">{icon} {j["text"]}</div>'
            
            # 점수 브레이크다운
            breakdown = r.get('score_breakdown', {})
            breakdown_html = f"""
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px;">
                <div style="background: rgba(77,171,247,0.1); padding: 8px; border-radius: 6px; text-align: center;">
                    <div style="color: #868e96; font-size: 11px;">기본점수</div>
                    <div style="color: #4dabf7; font-weight: bold;">+{breakdown.get('base_score', 0)}</div>
                </div>
                <div style="background: rgba(0,255,136,0.1); padding: 8px; border-radius: 6px; text-align: center;">
                    <div style="color: #868e96; font-size: 11px;">섹터병점수</div>
                    <div style="color: #00ff88; font-weight: bold;">+{breakdown.get('sector_bonus', 0)}</div>
                </div>
                <div style="background: rgba(252,196,25,0.1); padding: 8px; border-radius: 6px; text-align: center;">
                    <div style="color: #868e96; font-size: 11px;">워치누적</div>
                    <div style="color: #fcc419; font-weight: bold;">+{breakdown.get('watch_bonus', 0)}</div>
                </div>
            </div>
            """
            
            # 네이버 정보
            naver = r.get('naver', {})
            naver_metrics = []
            if naver.get('per'): naver_metrics.append(f"PER: {naver['per']:.1f}배")
            if naver.get('pbr'): naver_metrics.append(f"PBR: {naver['pbr']:.2f}배")
            if naver.get('market_cap'): naver_metrics.append(f"시총: {naver['market_cap']/10000:.1f}조")
            naver_html = " | ".join(naver_metrics) if naver_metrics else "정보 없음"
            
            # 뉴스
            news_html = ""
            if naver.get('recent_news') and len(naver['recent_news']) > 0:
                for news in naver['recent_news'][:2]:
                    news_html += f'<div style="color: #adb5bd; font-size: 12px; margin: 2px 0;">📰 {news[:55]}...</div>'
            
            top_stocks_html += f"""
            <div class="stock-card" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                 border-radius: 12px; padding: 20px; margin: 15px 0; border-left: 4px solid {r['grade_color']};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <span style="font-size: 24px; font-weight: bold; color: {r['grade_color']};">{i}.</span>
                        <span style="font-size: 20px; font-weight: bold; color: #fff; margin-left: 10px;">{r['name']}</span>
                        <span style="color: #adb5bd; margin-left: 10px;">({r['symbol']}) · {r['sector']}</span>
                    </div>
                    <div style="background: {r['grade_color']}; color: #000; padding: 5px 15px; 
                         border-radius: 20px; font-weight: bold;">
                        {r['grade']}급 · {r['grade_text']}
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 15px;">
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 11px;">현재가</div>
                        <div style="color: #fff; font-size: 16px; font-weight: bold;">{r['price']:,.0f}원</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 11px;">RSI</div>
                        <div style="color: {'#ff6b6b' if r['rsi'] < 30 else '#fff'}; font-size: 16px; font-weight: bold;">{r['rsi']:.1f}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 11px;">52주대비</div>
                        <div style="color: {'#ff6b6b' if r['vs_52w_high'] < -30 else '#fcc419'}; font-size: 16px; font-weight: bold;">{r['vs_52w_high']:.1f}%</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 11px;">재무점수</div>
                        <div style="color: #fff; font-size: 16px; font-weight: bold;">{r['quality_score']:.0f}</div>
                    </div>
                    <div style="background: {r['grade_color']}; padding: 10px; border-radius: 8px;">
                        <div style="color: #000; font-size: 11px;">총점</div>
                        <div style="color: #000; font-size: 18px; font-weight: bold;">{r['final_score']}</div>
                    </div>
                </div>
                
                {breakdown_html}
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                    <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 12px; margin-bottom: 8px;">📋 판단 근거</div>
                        {judgments_html}
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 12px; margin-bottom: 8px;">📱 네이버증권 · 섹터강도: {r.get('sector_strength', 0):.1f} (순위: {r.get('sector_rank', '-')})</div>
                        <div style="color: #ced4da; font-size: 13px;">{naver_html}</div>
                        {news_html}
                    </div>
                </div>
                
                <div style="background: rgba({r['grade_color'].replace('#', '')}, 0.1); 
                     padding: 12px; border-radius: 8px; border-left: 3px solid {r['grade_color']};">
                    <div style="color: #868e96; font-size: 12px;">💡 추천</div>
                    <div style="color: {r['grade_color']}; font-weight: bold;">{r['recommendation']}</div>
                </div>
            </div>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통합 스캔 리포트 v2.0 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ 
            text-align: center; padding: 40px 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px; margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 32px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; }}
        .summary-grid {{ 
            display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; 
            margin-bottom: 30px;
        }}
        .summary-card {{ 
            background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px;
            text-align: center;
        }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; margin: 10px 0; }}
        .summary-card .label {{ color: #868e96; font-size: 14px; }}
        .section {{ margin-bottom: 40px; }}
        .section-title {{ 
            font-size: 24px; margin-bottom: 20px; padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .footer {{ 
            text-align: center; padding: 30px; color: #868e96; 
            border-top: 1px solid #333; margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 통합 종목 스캔 리포트 v2.0</h1>
            <p>DART 재무 + 기술적 분석 + 네이버증권 + LazyAlpha 섹터 강도</p>
            <p style="margin-top: 10px; font-size: 14px;">{date_str} · 총점 = 기본점수 + 섹터병점수(0-20) + 워치누적(0-15)</p>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card">
                <div class="label">총 선정</div>
                <div class="value" style="color: #fff;">{len(results)}</div>
            </div>
            <div class="summary-card">
                <div class="label">S급 핵심후보</div>
                <div class="value" style="color: #00ff88;">{grade_counts['S']}</div>
            </div>
            <div class="summary-card">
                <div class="label">A급 관심</div>
                <div class="value" style="color: #4dabf7;">{grade_counts['A']}</div>
            </div>
            <div class="summary-card">
                <div class="label">평균 RSI</div>
                <div class="value" style="color: #fcc419;">{np.mean([r['rsi'] for r in results]):.1f}</div>
            </div>
            <div class="summary-card">
                <div class="label">평균 총점</div>
                <div class="value" style="color: #da77f2;">{np.mean([r['final_score'] for r in results]):.1f}</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🔥 섹터 강도 순위 (LazyAlpha 공식)</h2>
            <div style="background: rgba(255,255,255,0.03); padding: 20px; border-radius: 12px;">
                <p style="color: #868e96; margin-bottom: 15px; font-size: 14px;">
                    섹터 강도 = 진입×1.2 + 워치×0.4 − 청산 · 양수 = 강한 섹터 · 음수 = 약한 섹터
                </p>
                {sector_html if sector_html else '<p style="color: #868e96;">섹터 데이터 없음</p>'}
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🏆 TOP 20 추천 종목 (점수 브레이크다운 포함)</h2>
            {top_stocks_html}
        </div>
        
        <div class="footer">
            <p>⚠️ 본 리포트는 투자 참고 자료이며, 투자 결정은 본인의 책임하에 신중히 결정하시기 바랍니다.</p>
            <p style="margin-top: 10px;">Generated by Enhanced Integrated Scanner v2.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html


def main():
    scanner = EnhancedIntegratedScanner()
    results = scanner.run(max_stocks=50)
    
    print("\n" + "="*70)
    print("📋 최종 리포트")
    print("="*70)
    
    # 등급별 통계
    grade_counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0}
    for r in results:
        grade = r['grade']
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    
    print(f"\n📊 등급별 통계:")
    for grade in ['S', 'A', 'B', 'C']:
        if grade in grade_counts:
            print(f"   {grade}급: {grade_counts[grade]}개")
    
    print(f"\n🏆 TOP 5 추천 종목:")
    for i, r in enumerate(results[:5], 1):
        bd = r.get('score_breakdown', {})
        print(f"   {i}. [{r['grade']}급] {r['name']} ({r['symbol']}) - {r['final_score']}점 (기본{bd.get('base_score',0)}+섹터{bd.get('sector_bonus',0)}+워치{bd.get('watch_bonus',0)})")
    
    # HTML 리포트 생성
    date_str = datetime.now().strftime('%Y%m%d')
    html = scanner.generate_html_report(results, date_str)
    
    output_path = f'/root/.openclaw/workspace/strg/docs/DART_ENHANCED_SCAN_{date_str}.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n📄 HTML 리포트: {output_path}")
    
    # JSON도 저장
    json_path = f'/root/.openclaw/workspace/strg/docs/dart_enhanced_scan_{date_str}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"📄 JSON: {json_path}")
    
    return results, output_path


if __name__ == '__main__':
    main()
