#!/usr/bin/env python3
"""
Korea Stock Fundamental Data Fetcher
======================================
네이버 금융에서 재무지표 스크래핑
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import json


class FundamentalFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.cache = {}
    
    def fetch_from_naver(self, symbol):
        """네이버 금융에서 재무지표 스크래핑"""
        try:
            url = f"https://finance.naver.com/item/main.nhn?code={symbol}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'euc-kr'
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 재무지표 테이블 찾기
            data = {
                'symbol': symbol,
                'per': None,
                'pbr': None,
                'roe': None,
                'market_cap': None,
                'source': 'naver'
            }
            
            # 시가총액
            try:
                market_cap_elem = soup.select_one('#_market_sum')
                if market_cap_elem:
                    market_cap_text = market_cap_elem.text.strip().replace(',', '').replace('억', '')
                    data['market_cap'] = float(market_cap_text)
            except:
                pass
            
            # PER, PBR, ROE
            try:
                # 테이블에서 검색
                tables = soup.find_all('table', {'class': 'per_table'})
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        ths = row.find_all('th')
                        tds = row.find_all('td')
                        for i, th in enumerate(ths):
                            if i < len(tds):
                                label = th.text.strip()
                                value = tds[i].text.strip().replace(',', '')
                                
                                if 'PER' in label and 'EPS' not in label:
                                    try:
                                        data['per'] = float(value.split('l')[0].strip())
                                    except:
                                        pass
                                elif 'PBR' in label:
                                    try:
                                        data['pbr'] = float(value.split('l')[0].strip())
                                    except:
                                        pass
                                elif 'ROE' in label:
                                    try:
                                        data['roe'] = float(value.replace('%', ''))
                                    except:
                                        pass
            except:
                pass
            
            # 추가 검색 - em 태그 활용
            try:
                em_tags = soup.find_all('em', {'class': 'per'})
                for em in em_tags:
                    text = em.text.strip()
                    if text and data['per'] is None:
                        try:
                            data['per'] = float(text.replace(',', ''))
                        except:
                            pass
            except:
                pass
            
            # 유효성 검사
            if data['per'] is None or data['per'] > 1000:
                data['per'] = None
            if data['pbr'] is None or data['pbr'] > 100:
                data['pbr'] = None
            if data['roe'] is not None and (data['roe'] < -100 or data['roe'] > 200):
                data['roe'] = None
                
            return data if (data['per'] or data['pbr']) else None
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    def fetch_batch(self, symbols, delay=0.5):
        """여러 종목의 재무지표 일괄 수집"""
        results = {}
        total = len(symbols)
        
        print(f"재무지표 수집 시작: {total}개 종목")
        
        for i, symbol in enumerate(symbols, 1):
            if i % 5 == 0:
                print(f"  진행: {i}/{total} ({i/total*100:.1f}%)")
            
            data = self.fetch_from_naver(symbol)
            if data:
                results[symbol] = data
            
            time.sleep(delay)  # 서버 부하 방지
        
        print(f"✅ 수집 완료: {len(results)}개 종목")
        return results
    
    def update_db(self, db_path='./data/pivot_strategy.db'):
        """DB의 stock_info 테이블 업데이트"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 테이블 존재 확인 및 생성
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_info (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    market_cap REAL,
                    per REAL,
                    pbr REAL,
                    eps REAL,
                    bps REAL,
                    roe REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        except:
            pass
        
        # 재무 데이터가 없는 종목 조회
        cursor.execute('''
            SELECT DISTINCT s.symbol 
            FROM stock_prices s
            LEFT JOIN stock_info i ON s.symbol = i.symbol
            WHERE s.date >= '2025-01-01' 
            AND (i.per IS NULL OR i.pbr IS NULL)
        ''')
        
        symbols = [row[0] for row in cursor.fetchall()]
        print(f"재무 데이터 필요 종목: {len(symbols)}개")
        
        # 상위 50개만 우선 처리 (속도 고려)
        top_symbols = symbols[:50]
        
        # 데이터 수집
        results = self.fetch_batch(top_symbols, delay=0.3)
        
        # DB 업데이트
        updated = 0
        for symbol, data in results.items():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_info 
                    (symbol, market_cap, per, pbr, roe, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    symbol,
                    data.get('market_cap'),
                    data.get('per'),
                    data.get('pbr'),
                    data.get('roe')
                ))
                updated += 1
            except Exception as e:
                print(f"DB update error for {symbol}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ DB 업데이트 완료: {updated}개 종목")
        return updated


def main():
    fetcher = FundamentalFetcher()
    
    # 테스트 - 단일 종목
    test_symbols = ['005930', '035250', '003550', '055550', '000270']
    
    print("=" * 60)
    print("재무지표 수집 테스트")
    print("=" * 60)
    
    for symbol in test_symbols:
        print(f"\n{symbol} 조회 중...")
        data = fetcher.fetch_from_naver(symbol)
        if data:
            print(f"  PER: {data.get('per', 'N/A')}")
            print(f"  PBR: {data.get('pbr', 'N/A')}")
            print(f"  ROE: {data.get('roe', 'N/A')}")
            print(f"  시총: {data.get('market_cap', 'N/A')}억")
        else:
            print("  데이터 없음")
        time.sleep(0.5)


if __name__ == '__main__':
    main()
