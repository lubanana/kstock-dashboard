#!/usr/bin/env python3
"""
Ultimate Stock Screener - 1000 Point Scale
==========================================
종합 분석 시스템

개선사항:
- ETF/개별주 분리 표시 (리스크 관리)
- 유동성 필터: 거래량비율 < 0.5 별도 표시
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import json
import sys
import os

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)


class UltimateScreener:
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.stock_names = self._load_names()
    
    def _load_names(self):
        names = {}
        cursor = self.conn.cursor()
        try:
            cursor.execute('SELECT symbol, name FROM stock_info')
            for row in cursor.fetchall():
                names[row[0]] = row[1]
        except:
            pass
        
        # 기본 매핑 추가
        defaults = {
            '000440': '중앙에너비스', 'BYC': 'BYC', '000250': '삼천당제약',
            '000490': '대동공업', '003350': '기산텔레콤', '001750': '한양증권',
            '001515': 'SK증권우', '154030': '아이윈', '139480': '이마트',
            '049720': '고려신용정보', '002870': '신풍', '005930': '삼성전자'
        }
        names.update(defaults)
        return names
    
    def is_etf(self, symbol, name):
        """ETF 여부 확인"""
        # ETF 관련 키워드
        etf_keywords = ['ETF', 'etf', 'ETN', 'etn', '레버리지', '인버스', ' securities', 'fund']
        # 특정 ETF 패턴 (코드 기반)
        etf_patterns = ['3', '37', '38', '39', '4', '5', '6']  # ETF 코드 패턴
        
        # 이름에서 ETF 키워드 확인
        name_upper = name.upper()
        for keyword in etf_keywords:
            if keyword.upper() in name_upper:
                return True
        
        # 특정 코드 패턴 (한국 ETF)
        if symbol.startswith(('3', '37', '38', '39', '4', '5', '6')):
            return True
        
        return False
    
    def check_liquidity(self, vol_ratio):
        """유동성 체크
        Returns:
            'high' - 거래량비율 >= 1.0 (정상)
            'medium' - 거래량비율 0.5 ~ 1.0 (주의)
            'low' - 거래량비율 < 0.5 (유동성 부족)
        """
        if vol_ratio >= 1.0:
            return 'high'
        elif vol_ratio >= 0.5:
            return 'medium'
        else:
            return 'low'
    
    def get_price(self, symbol, days=120):
        query = '''SELECT date, open, high, low, close, volume 
                   FROM stock_prices WHERE symbol = ? 
                   AND date >= date('now', '-{} days') ORDER BY date'''.format(days)
        df = pd.read_sql_query(query, self.conn, params=(symbol,))
        if df.empty:
            return None
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    
    def calc_indicators(self, df):
        if len(df) < 60:
            return None
        
        # EMA
        df['ema20'] = df['close'].ewm(span=20).mean()
        df['ema60'] = df['close'].ewm(span=60).mean()
        df['ema120'] = df['close'].ewm(span=120).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain / loss))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_sig'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_sig']
        
        # 볼린저
        df['ma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['bb_up'] = df['ma20'] + df['std20'] * 2
        df['bb_low'] = df['ma20'] - df['std20'] * 2
        
        # ATR
        df['tr'] = np.maximum(df['high'] - df['low'],
            np.maximum(abs(df['high'] - df['close'].shift(1)),
                      abs(df['low'] - df['close'].shift(1))))
        df['atr14'] = df['tr'].rolling(14).mean()
        
        # 거래량
        df['vol_ma20'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma20']
        
        return df
    
    def score_stock(self, symbol):
        df = self.get_price(symbol)
        if df is None or len(df) < 60:
            return None
        
        df = self.calc_indicators(df)
        if df is None:
            return None
        
        latest = df.iloc[-1]
        price = latest['close']
        name = self.stock_names.get(symbol, symbol)
        vol_ratio = latest['vol_ratio']
        
        # ETF 여부 확인
        is_etf = self.is_etf(symbol, name)
        
        # 유동성 상태 확인
        liquidity = self.check_liquidity(vol_ratio)
        
        scores = {'total': 0}
        reasons = []
        
        # 1. 추세 점수 (0-250)
        trend_score = 0
        if price > latest['ema20']:
            trend_score += 60
            reasons.append('주가>EMA20')
        if latest['ema20'] > latest['ema60']:
            trend_score += 60
            reasons.append('정배열20>60')
        if latest['ema60'] > latest['ema120']:
            trend_score += 50
            reasons.append('정배열60>120')
        
        high_52w = df['high'].tail(252).max() if len(df) >= 252 else df['high'].max()
        if high_52w > 0:
            from_high = (high_52w - price) / high_52w
            if from_high < 0.10:
                trend_score += 50
                reasons.append('52주고가-10%')
            elif from_high < 0.20:
                trend_score += 30
                reasons.append('52주고가-20%')
        
        if len(df) >= 60:
            ret60 = (price - df['close'].iloc[-60]) / df['close'].iloc[-60] * 100
            if ret60 > 20:
                trend_score += 30
                reasons.append(f'60일+{ret60:.0f}%')
        
        scores['trend'] = min(trend_score, 250)
        scores['total'] += scores['trend']
        
        # 2. 모멘텀 점수 (0-200)
        mom_score = 0
        rsi = latest['rsi']
        if 45 <= rsi <= 65:
            mom_score += 60
            reasons.append(f'RSI{rsi:.0f}')
        elif 40 <= rsi <= 70:
            mom_score += 30
        
        if latest['macd_hist'] > 0:
            mom_score += 40
            reasons.append('MACD+')
        
        if len(df) >= 3 and df['macd_hist'].iloc[-1] > df['macd_hist'].iloc[-2] > df['macd_hist'].iloc[-3]:
            mom_score += 30
            reasons.append('MACD증가')
        
        if len(df) >= 20:
            ret20 = (price - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
            if 5 <= ret20 <= 30:
                mom_score += 50
                reasons.append(f'20일+{ret20:.0f}%')
            elif ret20 > 0:
                mom_score += 20
        
        scores['momentum'] = min(mom_score, 200)
        scores['total'] += scores['momentum']
        
        # 3. 거래량 점수 (0-200)
        vol_score = 0
        if vol_ratio >= 2.5:
            vol_score += 80
            reasons.append(f'거래량{vol_ratio:.1f}배')
        elif vol_ratio >= 2.0:
            vol_score += 60
            reasons.append(f'거래량{vol_ratio:.1f}배')
        elif vol_ratio >= 1.5:
            vol_score += 40
        elif vol_ratio >= 1.0:
            vol_score += 20
        
        if len(df) >= 20:
            amount = (df['close'].tail(20) * df['volume'].tail(20)).mean() / 100000000
            if amount >= 100:
                vol_score += 60
                reasons.append(f'대금{amount:.0f}억')
            elif amount >= 50:
                vol_score += 40
            elif amount >= 10:
                vol_score += 20
        
        if df['volume'].tail(5).mean() > df['volume'].tail(20).mean():
            vol_score += 20
            reasons.append('거래량증가')
        
        scores['volume'] = min(vol_score, 200)
        scores['total'] += scores['volume']
        
        # 4. 변동성/리스크 점수 (0-150)
        vola_score = 0
        if latest['atr14'] > 0:
            atr_pct = latest['atr14'] / price * 100
            if 2 <= atr_pct <= 5:
                vola_score += 60
                reasons.append(f'ATR{atr_pct:.1f}%')
        
        bb_range = latest['bb_up'] - latest['bb_low']
        if bb_range > 0:
            bb_pos = (price - latest['bb_low']) / bb_range
            if 0.4 <= bb_pos <= 0.7:
                vola_score += 50
                reasons.append(f'BB상단{bb_pos*100:.0f}%')
        
        scores['volatility'] = min(vola_score, 150)
        scores['total'] += scores['volatility']
        
        # 5. 피봇/브레이크아웃 점수 (0-200)
        pivot_score = 0
        if len(df) >= 30:
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            
            if recent_high > 0:
                proximity = (recent_high - price) / recent_high * 100
                if proximity <= 3:
                    pivot_score += 80
                    reasons.append(f'고가근접{proximity:.1f}%')
                elif proximity <= 7:
                    pivot_score += 40
                    reasons.append(f'눌림목{proximity:.1f}%')
            
            if recent_high > recent_low:
                box_range = (recent_high - recent_low) / recent_low * 100
                if box_range < 15:
                    pivot_score += 40
                    reasons.append('박스권수렴')
        
        scores['pivot'] = min(pivot_score, 200)
        scores['total'] += scores['pivot']
        
        # 목표가/손절가 계산
        if latest['atr14'] > 0 and len(df) >= 20:
            atr = latest['atr14']
            recent_high = df['high'].tail(20).max()
            recent_low = df['low'].tail(20).min()
            
            targets = []
            targets.append(price + atr * 3)
            targets.append(price + atr * 4.5)
            
            if recent_high > price:
                box_range = recent_high - recent_low
                targets.append(recent_high + box_range * 0.5)
                targets.append(recent_high + box_range * 0.8)
            
            if len(df) >= 10:
                last_low = df['low'].tail(10).min()
                if price > last_low:
                    move = price - last_low
                    targets.append(price + move * 1.272)
                    targets.append(price + move * 1.618)
            
            stop_losses = []
            stop_losses.append(price - atr * 1.5)
            stop_losses.append(price - atr * 2.0)
            stop_losses.append(price - atr * 2.5)
            stop_losses.append(latest['ema20'] * 0.98)
            stop_losses.append(latest['ema20'] * 0.95)
            
            recent_low_5d = df['low'].tail(5).min()
            stop_losses.append(recent_low_5d * 0.99)
            
            target = max([t for t in targets if t > price] or [price * 1.10])
            stop_loss = min([s for s in stop_losses if s < price] or [price * 0.93])
            
            potential_gain = target - price
            potential_loss = price - stop_loss
            rr = potential_gain / potential_loss if potential_loss > 0 else 0
        else:
            stop_loss = price * 0.93
            target = price * 1.15
            rr = (target - price) / (price - stop_loss)
        
        return {
            'symbol': symbol,
            'name': name,
            'price': round(price, 0),
            'score': scores['total'],
            'scores': scores,
            'rsi': round(latest['rsi'], 1),
            'vol_ratio': round(vol_ratio, 2),
            'stop_loss': round(stop_loss, 0),
            'target': round(target, 0),
            'rr_ratio': round(rr, 2),
            'reasons': reasons[:8],
            'is_etf': is_etf,
            'liquidity': liquidity
        }
    
    def scan_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT symbol FROM stock_prices WHERE date >= "2025-01-01"')
        symbols = [row[0] for row in cursor.fetchall()]
        
        print(f"총 {len(symbols)}개 종목 분석 시작...")
        
        all_results = []
        etf_results = []
        stock_results = []
        low_liquidity = []  # 유동성 부족 종목
        
        for i, symbol in enumerate(symbols, 1):
            if i % 100 == 0:
                print(f"  진행: {i}/{len(symbols)} ({i/len(symbols)*100:.1f}%)")
            
            result = self.score_stock(symbol)
            if result and result['score'] >= 500:
                all_results.append(result)
                
                # ETF/개별주 분리
                if result['is_etf']:
                    etf_results.append(result)
                else:
                    stock_results.append(result)
                
                # 유동성 부족 종목 체크
                if result['liquidity'] == 'low':
                    low_liquidity.append(result)
        
        # 점수 순 정렬
        all_results.sort(key=lambda x: x['score'], reverse=True)
        etf_results.sort(key=lambda x: x['score'], reverse=True)
        stock_results.sort(key=lambda x: x['score'], reverse=True)
        low_liquidity.sort(key=lambda x: x['score'], reverse=True)
        
        return {
            'all': all_results,
            'etf': etf_results,
            'stock': stock_results,
            'low_liquidity': low_liquidity
        }
    
    def generate_report(self, results):
        now = datetime.now().strftime('%Y%m%d_%H%M')
        
        all_results = results['all']
        etf_results = results['etf']
        stock_results = results['stock']
        low_liquidity = results['low_liquidity']
        
        # HTML 리포트
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Ultimate Stock Screener - Top Picks</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .summary {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
        .summary-item {{ text-align: center; padding: 15px; border-radius: 8px; background: #f8f9fa; }}
        .summary-item h3 {{ margin: 0; font-size: 24px; color: #667eea; }}
        .summary-item p {{ margin: 5px 0 0 0; color: #666; font-size: 14px; }}
        .section {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .section h2 {{ color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .tabs {{ display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #eee; }}
        .tab {{ padding: 10px 20px; cursor: pointer; border-radius: 5px 5px 0 0; background: #f5f5f5; }}
        .tab.active {{ background: #667eea; color: white; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #667eea; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f8f9ff; }}
        .rank {{ font-weight: bold; font-size: 18px; width: 50px; text-align: center; }}
        .score {{ font-weight: bold; color: #667eea; font-size: 20px; }}
        .price {{ font-weight: bold; color: #333; }}
        .target {{ color: #28a745; font-weight: bold; }}
        .stop {{ color: #dc3545; }}
        .rr {{ color: #666; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; margin: 2px; }}
        .badge-blue {{ background: #e3f2fd; color: #1976d2; }}
        .badge-green {{ background: #e8f5e9; color: #388e3c; }}
        .badge-orange {{ background: #fff3e0; color: #f57c00; }}
        .badge-red {{ background: #ffebee; color: #d32f2f; }}
        .badge-gray {{ background: #eeeeee; color: #616161; }}
        .badge-purple {{ background: #f3e5f5; color: #7b1fa2; }}
        .badge-liquidity-low {{ background: #ffcdd2; color: #c62828; border: 1px solid #ef5350; }}
        .badge-liquidity-medium {{ background: #fff9c4; color: #f57f17; }}
        .badge-etf {{ background: #e1f5fe; color: #0277bd; border: 1px solid #4fc3f7; }}
        .reasons {{ font-size: 12px; color: #666; }}
        .top3 {{ background: linear-gradient(135deg, #ffd700 0%, #ffb700 100%); color: #333; }}
        .warning-box {{ background: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .danger-box {{ background: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        .methodology {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 13px; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Ultimate Stock Screener</h1>
        <p>내일 급등 가능성 높은 종목 TOP 10 (1000점 체계) | 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <!-- 요약 통계 -->
    <div class="summary">
        <h2 style="margin-top:0;">📊 분석 요약</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <h3>{len(all_results)}</h3>
                <p>전체 선정 종목</p>
            </div>
            <div class="summary-item">
                <h3>{len(stock_results)}</h3>
                <p>개별주</p>
            </div>
            <div class="summary-item">
                <h3>{len(etf_results)}</h3>
                <p>ETF/ETN</p>
            </div>
            <div class="summary-item" style="background:#ffcdd2;">
                <h3 style="color:#c62828;">{len(low_liquidity)}</h3>
                <p style="color:#c62828;">유동성 부족 ⚠️</p>
            </div>
        </div>
    </div>
"""
        
        # 유동성 부족 경고 박스
        if low_liquidity:
            html += f"""
    <div class="danger-box">
        <strong>⚠️ 유동성 주의 종목 ({len(low_liquidity)}개)</strong><br>
        거래량비율 0.5 미만 종목은 체결 리스크가 높습니다. 투자 시 주의가 필요합니다.<br>
        <small>대상: {', '.join([r['name'] for r in low_liquidity[:10]])}{'...' if len(low_liquidity) > 10 else ''}</small>
    </div>
"""
        
        # 탭 메뉴
        html += """
    <div class="tabs">
        <div class="tab active" onclick="showTab('stocks')">🏢 개별주</div>
        <div class="tab" onclick="showTab('etfs')">📈 ETF/ETN</div>
        <div class="tab" onclick="showTab('all')">📋 전체 순위</div>
        <div class="tab" onclick="showTab('liquidity')">⚠️ 유동성 부족</div>
    </div>
"""
        
        # 개별주 탭
        html += self._generate_table_section('stocks', 'active', stock_results, '개별주 TOP 10', True)
        
        # ETF 탭
        html += self._generate_table_section('etfs', '', etf_results, 'ETF/ETN TOP 10', True)
        
        # 전체 순위 탭
        html += self._generate_table_section('all', '', all_results, '전체 순위 TOP 10', True)
        
        # 유동성 부족 탭
        html += self._generate_table_section('liquidity', '', low_liquidity, '유동성 부족 종목', False)
        
        # JavaScript
        html += """
    <script>
        function showTab(tabName) {
            // 모든 탭 비활성화
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            // 선택한 탭 활성화
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
        }
    </script>
"""
        
        # 방법론 섹션
        html += """
    <div class="section">
        <h2>📈 채점 방법론 (1000점 체계)</h2>
        <div class="methodology">
            <strong>1. 추세 점수 (250점)</strong><br>
            • 주가 > EMA20 (60점) | EMA20 > EMA60 (60점) | EMA60 > EMA120 (50점)<br>
            • 52주 고가 근접 10% 이내 (50점) | 20% 이내 (30점)<br>
            • 60일 수익률 +20% 이상 (30점)<br><br>
            
            <strong>2. 모멘텀 점수 (200점)</strong><br>
            • RSI 45-65 (60점) | MACD > 0 (40점) | MACD 3일 연속 증가 (30점)<br>
            • 20일 수익률 +5~30% (50점)<br><br>
            
            <strong>3. 거래량 점수 (200점)</strong><br>
            • 거래량 2.5배 이상 (80점) | 2배 (60점) | 1.5배 (40점)<br>
            • 거래대금 100억 이상 (60점) | 50억 (40점)<br>
            • 거래량 증가 추세 (20점)<br><br>
            
            <strong>4. 변동성/리스크 점수 (150점)</strong><br>
            • ATR 2-5% 적정 변동성 (60점) | BB 중상단 위치 (50점)<br><br>
            
            <strong>5. 피봇/브레이크아웃 점수 (200점)</strong><br>
            • 20일 고가 3% 이내 근접 (80점) | 7% 이내 눌림목 (40점)<br>
            • 좁은 박스권 수렴 (40점)<br><br>
            
            <strong>유동성 필터:</strong><br>
            • 🟢 정상: 거래량비율 ≥ 1.0 | 🟡 주의: 0.5 ~ 1.0 | 🔴 부족: < 0.5<br><br>
            
            <strong>목표가/손절가:</strong> ATR 기반 동적 계산
        </div>
    </div>
    
    <div class="section" style="text-align: center; color: #666; font-size: 12px;">
        <p>⚠️ 본 분석은 기술적 분석 기반 예측이며, 투자 결정은 본인의 판단과 책임하에 신중히 이루어져야 합니다.</p>
        <p>ETF와 개별주는 리스크 특성이 다륯오, 포트폴리오 구성 시 유의하시기 바랍니다.</p>
        <p>Generated by Ultimate Stock Screener | Data: FinanceDataReader | DB: pivot_strategy.db</p>
    </div>
</body>
</html>
"""
        
        # 저장
        filename = f'Ultimate_Screener_TOP10_{now}.html'
        with open(f'./reports/{filename}', 'w', encoding='utf-8') as f:
            f.write(html)
        with open(f'./docs/{filename}', 'w', encoding='utf-8') as f:
            f.write(html)
        
        # JSON 저장
        json_data = {
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total': len(all_results),
                'stocks': len(stock_results),
                'etfs': len(etf_results),
                'low_liquidity': len(low_liquidity)
            },
            'top10_stocks': stock_results[:10],
            'top10_etfs': etf_results[:10],
            'low_liquidity': low_liquidity
        }
        with open(f'./reports/Ultimate_Screener_{now}.json', 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def _generate_table_section(self, tab_id, active_class, results, title, show_rr):
        """테이블 섹션 생성 헬퍼"""
        html = f'<div id="{tab_id}" class="tab-content {active_class}">\n'
        html += f'<div class="section">\n<h2>{title}</h2>\n'
        
        if not results:
            html += '<p style="text-align:center; color:#999; padding:40px;">해당 조건을 만족하는 종목이 없습니다.</p>\n'
            html += '</div></div>\n'
            return html
        
        html += """<table>
            <tr>
                <th>순위</th>
                <th>종목</th>
                <th>유형</th>
                <th>유동성</th>
                <th>현재가</th>
                <th>종합점수</th>
                <th>목표가</th>
                <th>손절가</th>
"""
        if show_rr:
            html += "                <th>손익비</th>\n"
        html += "                <th>선정근거</th>\n            </tr>\n"
        
        for i, r in enumerate(results[:10], 1):
            row_class = 'top3' if i <= 3 else ''
            badge_class = 'badge-red' if i <= 3 else ('badge-orange' if i <= 6 else 'badge-blue')
            
            # 유형 뱃지
            type_badge = '<span class="badge badge-etf">ETF</span>' if r['is_etf'] else '<span class="badge badge-green">개별주</span>'
            
            # 유동성 뱃지
            if r['liquidity'] == 'low':
                liq_badge = '<span class="badge badge-liquidity-low">부족</span>'
            elif r['liquidity'] == 'medium':
                liq_badge = '<span class="badge badge-liquidity-medium">주의</span>'
            else:
                liq_badge = '<span class="badge badge-blue">정상</span>'
            
            reasons_html = ' '.join([f'<span class="badge {badge_class}">{reason}</span>' for reason in r['reasons'][:4]])
            
            html += f"""
            <tr class="{row_class}">
                <td class="rank">#{i}</td>
                <td><strong>{r['name']}</strong><br><small>{r['symbol']}</small></td>
                <td>{type_badge}</td>
                <td>{liq_badge}</td>
                <td class="price">{r['price']:,.0f}원</td>
                <td class="score">{r['score']}점</td>
                <td class="target">{r['target']:,.0f}원</td>
                <td class="stop">{r['stop_loss']:,.0f}원</td>
"""
            if show_rr:
                html += f"                <td class=\"rr\">1:{r['rr_ratio']:.1f}</td>\n"
            html += f"                <td class=\"reasons\">{reasons_html}</td>\n            </tr>\n"
        
        html += """</table>
    </div>
</div>
"""
        return html


def main():
    screener = UltimateScreener()
    
    print("=" * 70)
    print("🚀 Ultimate Stock Screener - 1000 Point Scale")
    print("=" * 70)
    print("개선사항: ETF/개별주 분리 | 유동성 필터 추가")
    print()
    
    results = screener.scan_all()
    
    print(f"\n✅ 분석 완료!")
    print(f"   전체 선정: {len(results['all'])}개")
    print(f"   개별주: {len(results['stock'])}개")
    print(f"   ETF/ETN: {len(results['etf'])}개")
    print(f"   유동성 부족: {len(results['low_liquidity'])}개")
    
    if results['all']:
        # 결과 출력
        if results['stock']:
            print("\n" + "=" * 70)
            print("🏢 개별주 TOP 10")
            print("=" * 70)
            for i, r in enumerate(results['stock'][:10], 1):
                liq_warn = " ⚠️유동성부족" if r['liquidity'] == 'low' else ""
                print(f"\n#{i} {r['name']} ({r['symbol']}){liq_warn}")
                print(f"   현재가: {r['price']:,.0f}원 | 점수: {r['score']}/1000점")
                print(f"   목표가: {r['target']:,.0f}원 | 손절가: {r['stop_loss']:,.0f}원")
                print(f"   손익비: 1:{r['rr_ratio']:.2f} | 거래량비율: {r['vol_ratio']:.2f}x")
        
        if results['etf']:
            print("\n" + "=" * 70)
            print("📈 ETF/ETN TOP 10")
            print("=" * 70)
            for i, r in enumerate(results['etf'][:10], 1):
                print(f"\n#{i} {r['name']} ({r['symbol']})")
                print(f"   현재가: {r['price']:,.0f}원 | 점수: {r['score']}/1000점")
                print(f"   거래량비율: {r['vol_ratio']:.2f}x")
        
        if results['low_liquidity']:
            print("\n" + "=" * 70)
            print("⚠️ 유동성 부족 종목 (거래량비율 < 0.5)")
            print("=" * 70)
            for r in results['low_liquidity'][:10]:
                print(f"   {r['name']} ({r['symbol']}): 거래량비율 {r['vol_ratio']:.2f}x")
        
        # 리포트 생성
        filename = screener.generate_report(results)
        print(f"\n📄 리포트 저장: reports/{filename}")
    
    screener.conn.close()


if __name__ == '__main__':
    main()
