#!/usr/bin/env python3
"""
통합 스캐너 + 웹 검색 + HTML 리포트 생성기
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


class IntegratedReportGenerator:
    """통합 리포트 생성기"""
    
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
        naver_info = self.web_collector.get_naver_stock_info(symbol)
        stock['naver'] = naver_info
        time.sleep(0.1)
        return stock
    
    def make_final_judgment(self, stock):
        """최종 판단"""
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
            elif naver.get('pbr') and naver['pbr'] < 3:
                judgments.append({"type": "neutral", "text": f"적정PBR ({naver['pbr']:.2f}배)"})
            
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
        
        # 등급 산정
        if score >= 85:
            grade = "S"
            grade_text = "S급 (강력매수)"
            recommendation = "즉시 매수 고려. 10일 보유 시 +2.66% 예상"
            color = "#00ff88"
        elif score >= 70:
            grade = "A"
            grade_text = "A급 (매수)"
            recommendation = "매수 적기. 분할 매수 전략 권장"
            color = "#4dabf7"
        elif score >= 55:
            grade = "B"
            grade_text = "B급 (관망 후 매수)"
            recommendation = "추가 하락 기다리거나 소액 매수"
            color = "#fcc419"
        else:
            grade = "C"
            grade_text = "C급 (관망)"
            recommendation = "관망 권장"
            color = "#ff6b6b"
        
        stock['final_score'] = score
        stock['final_grade'] = grade
        stock['final_grade_text'] = grade_text
        stock['final_recommendation'] = recommendation
        stock['grade_color'] = color
        stock['judgments'] = judgments
        
        return stock
    
    def generate_html_report(self, results, date_str):
        """HTML 리포트 생성"""
        
        # 등급별 통계
        grade_counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0}
        for r in results:
            grade_counts[r['final_grade']] = grade_counts.get(r['final_grade'], 0) + 1
        
        # TOP 종목 HTML
        top_stocks_html = ""
        for i, r in enumerate(results[:20], 1):
            # 판단 근거 HTML
            judgments_html = ""
            for j in r['judgments']:
                icon = "✓" if j['type'] == 'positive' else ("○" if j['type'] == 'neutral' else "△")
                color = "#00ff88" if j['type'] == 'positive' else ("#fcc419" if j['type'] == 'neutral' else "#ff6b6b")
                judgments_html += f'<div style="margin: 4px 0; color: {color};">{icon} {j["text"]}</div>'
            
            # 네이버 정보
            naver = r.get('naver', {})
            naver_metrics = []
            if naver.get('per'): naver_metrics.append(f"PER: {naver['per']:.1f}배")
            if naver.get('pbr'): naver_metrics.append(f"PBR: {naver['pbr']:.2f}배")
            if naver.get('market_cap'): naver_metrics.append(f"시총: {naver['market_cap']/10000:.1f}조")
            if naver.get('foreign_ownership'): naver_metrics.append(f"외국인: {naver['foreign_ownership']}")
            naver_html = " | ".join(naver_metrics) if naver_metrics else "정보 없음"
            
            # 뉴스
            news_html = ""
            if naver.get('recent_news') and len(naver['recent_news']) > 0:
                for news in naver['recent_news'][:2]:
                    news_html += f'<div style="color: #adb5bd; font-size: 12px; margin: 2px 0;">📰 {news[:60]}...</div>'
            
            top_stocks_html += f"""
            <div class="stock-card" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                 border-radius: 12px; padding: 20px; margin: 15px 0; border-left: 4px solid {r['grade_color']};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <span style="font-size: 24px; font-weight: bold; color: {r['grade_color']};">{i}.</span>
                        <span style="font-size: 20px; font-weight: bold; color: #fff; margin-left: 10px;">{r['name']}</span>
                        <span style="color: #adb5bd; margin-left: 10px;">({r['symbol']})</span>
                    </div>
                    <div style="background: {r['grade_color']}; color: #000; padding: 5px 15px; 
                         border-radius: 20px; font-weight: bold;">
                        {r['final_grade_text']}
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 15px;">
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 12px;">현재가</div>
                        <div style="color: #fff; font-size: 18px; font-weight: bold;">{r['price']:,.0f}원</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 12px;">RSI</div>
                        <div style="color: {'#ff6b6b' if r['rsi'] < 30 else '#fcc419'}; font-size: 18px; font-weight: bold;">{r['rsi']:.1f}</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 12px;">52주대비</div>
                        <div style="color: {'#ff6b6b' if r['vs_52w_high'] < -30 else '#fcc419'}; font-size: 18px; font-weight: bold;">{r['vs_52w_high']:.1f}%</div>
                    </div>
                    <div style="background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 12px;">종합점수</div>
                        <div style="color: {r['grade_color']}; font-size: 18px; font-weight: bold;">{r['final_score']}/100</div>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                    <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 12px; margin-bottom: 8px;">📋 판단 근거</div>
                        {judgments_html}
                    </div>
                    <div style="background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px;">
                        <div style="color: #868e96; font-size: 12px; margin-bottom: 8px;">📱 네이버증권</div>
                        <div style="color: #ced4da; font-size: 13px;">{naver_html}</div>
                        {news_html}
                    </div>
                </div>
                
                <div style="background: rgba({r['grade_color'].replace('#', '').replace('ff6b6b', '255,107,107').replace('fcc419', '252,196,25').replace('4dabf7', '77,171,247').replace('00ff88', '0,255,136')}, 0.1); 
                     padding: 12px; border-radius: 8px; border-left: 3px solid {r['grade_color']};">
                    <div style="color: #868e96; font-size: 12px;">💡 추천</div>
                    <div style="color: {r['grade_color']}; font-weight: bold;">{r['final_recommendation']}</div>
                </div>
            </div>
            """
        
        # 전체 테이블 행
        table_rows = ""
        for i, r in enumerate(results, 1):
            naver = r.get('naver', {})
            table_rows += f"""
            <tr style="border-bottom: 1px solid #333;">
                <td style="padding: 10px; text-align: center;">{i}</td>
                <td style="padding: 10px;"><span style="color: {r['grade_color']}; font-weight: bold;">{r['final_grade']}</span></td>
                <td style="padding: 10px;">{r['symbol']}</td>
                <td style="padding: 10px; font-weight: bold;">{r['name']}</td>
                <td style="padding: 10px; text-align: right;">{r['price']:,.0f}</td>
                <td style="padding: 10px; text-align: right; color: {'#ff6b6b' if r['rsi'] < 30 else '#fff'};">{r['rsi']:.1f}</td>
                <td style="padding: 10px; text-align: right; color: {'#ff6b6b' if r['vs_52w_high'] < -30 else '#fcc419'};">{r['vs_52w_high']:.1f}%</td>
                <td style="padding: 10px; text-align: right;">{r['quality_score']:.0f}</td>
                <td style="padding: 10px; text-align: center;">{f"{naver.get('per'):.1f}" if isinstance(naver.get('per'), (int, float)) else '-'}</td>
                <td style="padding: 10px; text-align: center;">{f"{naver.get('pbr'):.2f}" if isinstance(naver.get('pbr'), (int, float)) else '-'}</td>
            </tr>
            """
        
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통합 스캔 리포트 - {date_str}</title>
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
            display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; 
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
        table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        th {{ 
            background: rgba(102,126,234,0.3); padding: 12px; text-align: center;
            font-weight: bold;
        }}
        td {{ padding: 10px; }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .footer {{ 
            text-align: center; padding: 30px; color: #868e96; 
            border-top: 1px solid #333; margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 통합 종목 스캔 리포트</h1>
            <p>DART 재무 + 기술적 분석 + 네이버증권 웹 정보 + AI 최종 판단</p>
            <p style="margin-top: 10px; font-size: 14px;">{date_str}</p>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card">
                <div class="label">총 선정 종목</div>
                <div class="value" style="color: #4dabf7;">{len(results)}</div>
            </div>
            <div class="summary-card">
                <div class="label">S급 (강력매수)</div>
                <div class="value" style="color: #00ff88;">{grade_counts['S']}</div>
            </div>
            <div class="summary-card">
                <div class="label">A급 (매수)</div>
                <div class="value" style="color: #4dabf7;">{grade_counts['A']}</div>
            </div>
            <div class="summary-card">
                <div class="label">평균 RSI</div>
                <div class="value" style="color: #fcc419;">{np.mean([r['rsi'] for r in results]):.1f}</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🏆 TOP 20 추천 종목 (웹 정보 + 판단 근거 포함)</h2>
            {top_stocks_html}
        </div>
        
        <div class="section">
            <h2 class="section-title">📋 전체 선정 종목 목록</h2>
            <table>
                <thead>
                    <tr>
                        <th>순위</th>
                        <th>등급</th>
                        <th>종목코드</th>
                        <th>종목명</th>
                        <th>현재가</th>
                        <th>RSI</th>
                        <th>52주대비</th>
                        <th>재무점수</th>
                        <th>PER</th>
                        <th>PBR</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>⚠️ 본 리포트는 투자 참고 자료이며, 투자 결정은 본인의 책임하에 신중히 결정하시기 바랍니다.</p>
            <p style="margin-top: 10px;">Generated by DART Integrated Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def run(self, max_stocks=50):
        """전체 파이프라인 실행"""
        print("="*70)
        print("🔍 통합 스캐너 + 웹 검색 + HTML 리포트")
        print("="*70)
        
        # 1. 기본 스캔
        symbols = [r[0] for r in self.price_conn.execute('SELECT symbol FROM stock_info').fetchall()]
        print(f"\n📊 대상: {len(symbols)}개 종목 스캔 중...\n")
        
        results = []
        for i, symbol in enumerate(symbols, 1):
            if i % 200 == 0:
                print(f"   [{i}/{len(symbols)}] 진행중... (선정: {len(results)}개)", end='\r')
            
            result = self.scan_stock(symbol)
            if result:
                results.append(result)
        
        print(f"\n✅ 기본 스캔 완료: {len(results)}개 종목 선정\n")
        
        # 상위 max_stocks개만 진행
        results = sorted(results, key=lambda x: x['quality_score'], reverse=True)[:max_stocks]
        
        # 2. 웹 정보 수집
        print(f"📡 웹 정보 수집: 네이버증권 (상위 {len(results)}개 종목)")
        print("-"*70)
        for i, stock in enumerate(results, 1):
            print(f"[{i}/{len(results)}] {stock['name']} ({stock['symbol']})")
            self.collect_web_info(stock)
        
        print("\n✅ 웹 정보 수집 완료\n")
        
        # 3. 최종 판단
        print("🎯 종합 분석 및 최종 판단 중...")
        final_results = []
        for stock in results:
            self.make_final_judgment(stock)
            final_results.append(stock)
        
        # 등급별 정렬
        final_results = sorted(final_results, key=lambda x: x['final_score'], reverse=True)
        
        # 4. HTML 리포트 생성
        date_str = datetime.now().strftime('%Y%m%d')
        html = self.generate_html_report(final_results, date_str)
        
        output_path = f'/root/.openclaw/workspace/strg/docs/DART_INTEGRATED_SCAN_{date_str}.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ HTML 리포트 생성: {output_path}")
        
        # JSON도 저장
        json_path = f'/root/.openclaw/workspace/strg/docs/dart_integrated_scan_{date_str}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON 데이터 저장: {json_path}")
        
        return final_results, output_path


def main():
    generator = IntegratedReportGenerator()
    results, report_path = generator.run(max_stocks=50)
    
    print("\n" + "="*70)
    print("📊 등급별 통계")
    print("="*70)
    
    grade_counts = {}
    for r in results:
        grade = r['final_grade']
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    
    for grade in ['S', 'A', 'B', 'C']:
        if grade in grade_counts:
            print(f"   {grade}급: {grade_counts[grade]}개")
    
    print(f"\n🏆 TOP 3 추천 종목:")
    for i, r in enumerate(results[:3], 1):
        print(f"   {i}. [{r['final_grade_text']}] {r['name']} ({r['symbol']}) - {r['final_score']}점")
    
    print(f"\n📄 리포트: {report_path}")


if __name__ == '__main__':
    main()
