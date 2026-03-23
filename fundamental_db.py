#!/usr/bin/env python3
"""
FnGuide Fundamental Data Parser
=================================
한경컨센서스/FnGuide 재무지표 파싱
"""

import sqlite3
import pandas as pd
from datetime import datetime


def get_fnguide_url(symbol):
    """FnGuide 종목 분석 URL"""
    return f"https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode=A{symbol}"


def get_consensus_url(symbol):
    """한경컨센서스 종목 URL"""
    return f"https://consensus.hankyung.com/apps.chart/analysis.chart?report_type=CO&code={symbol}"


class FundamentalDB:
    """로컬 재무 데이터베이스 관리"""
    
    def __init__(self, db_path='./data/pivot_strategy.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.init_table()
    
    def init_table(self):
        """stock_info 테이블 초기화"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                market_cap REAL,
                per REAL,
                pbr REAL,
                eps REAL,
                bps REAL,
                roe REAL,
                debt_ratio REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
    
    def update_fundamentals(self, symbol, data):
        """재무지표 업데이트"""
        cursor = self.conn.cursor()
        
        # 기존 데이터 확인
        cursor.execute('SELECT symbol FROM stock_info WHERE symbol = ?', (symbol,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
                UPDATE stock_info SET
                    per = ?, pbr = ?, roe = ?, market_cap = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE symbol = ?
            ''', (
                data.get('per'), data.get('pbr'), data.get('roe'),
                data.get('market_cap'), symbol
            ))
        else:
            cursor.execute('''
                INSERT INTO stock_info 
                (symbol, name, per, pbr, roe, market_cap, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                symbol, data.get('name'), data.get('per'), data.get('pbr'),
                data.get('roe'), data.get('market_cap')
            ))
        
        self.conn.commit()
    
    def get_fundamentals(self, symbol):
        """재무지표 조회"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT per, pbr, roe, market_cap, updated_at
            FROM stock_info WHERE symbol = ?
        ''', (symbol,))
        row = cursor.fetchone()
        
        if row:
            return {
                'per': row[0],
                'pbr': row[1],
                'roe': row[2],
                'market_cap': row[3],
                'updated_at': row[4]
            }
        return None
    
    def get_all_symbols(self):
        """모든 종목 코드 조회"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT symbol FROM stock_prices 
            WHERE date >= '2025-01-01'
        ''')
        return [row[0] for row in cursor.fetchall()]
    
    def close(self):
        self.conn.close()


def load_sample_data():
    """샘플 재무 데이터 (주요 종목) - 실제 스크래핑 전 임시 데이터"""
    # 실제 투자 시 FnGuide에서 수동 확인 필요
    sample_data = {
        # 삼성그룹
        '005930': {'name': '삼성전자', 'per': 12.5, 'pbr': 1.8, 'roe': 15.2, 'market_cap': 450000},
        '000810': {'name': '삼성화재', 'per': 8.2, 'pbr': 0.9, 'roe': 12.5, 'market_cap': 85000},
        
        # 현대차그룹
        '000270': {'name': '기아', 'per': 6.8, 'pbr': 0.9, 'roe': 15.8, 'market_cap': 32000},
        '005380': {'name': '현대차', 'per': 7.2, 'pbr': 0.8, 'roe': 12.3, 'market_cap': 48000},
        
        # 금융
        '055550': {'name': '신한지주', 'per': 6.5, 'pbr': 0.6, 'roe': 10.2, 'market_cap': 52000},
        '086790': {'name': '하나금융지주', 'per': 6.2, 'pbr': 0.5, 'roe': 9.8, 'market_cap': 38000},
        '105560': {'name': 'KB금융', 'per': 6.8, 'pbr': 0.7, 'roe': 11.2, 'market_cap': 65000},
        
        # LG그룹
        '003550': {'name': 'LG', 'per': 15.2, 'pbr': 1.2, 'roe': 8.5, 'market_cap': 28000},
        '051910': {'name': 'LG화학', 'per': 18.5, 'pbr': 1.1, 'roe': 6.2, 'market_cap': 42000},
        
        # SK그룹
        '000660': {'name': 'SK하이닉스', 'per': 25.3, 'pbr': 2.1, 'roe': 12.8, 'market_cap': 120000},
        '034730': {'name': 'SK', 'per': 22.1, 'pbr': 1.8, 'roe': 8.9, 'market_cap': 35000},
        
        # 기타 대형주
        '035420': {'name': 'NAVER', 'per': 28.5, 'pbr': 2.8, 'roe': 10.5, 'market_cap': 65000},
        '207940': {'name': '삼성바이오로직스', 'per': 85.2, 'pbr': 8.5, 'roe': 12.5, 'market_cap': 78000},
        '259960': {'name': '크래프톤', 'per': 35.2, 'pbr': 3.2, 'roe': 11.8, 'market_cap': 55000},
        '035720': {'name': '카카오', 'per': 42.5, 'pbr': 3.8, 'roe': 9.8, 'market_cap': 48000},
        '012450': {'name': '한화에어로스페이스', 'per': 18.2, 'pbr': 2.5, 'roe': 15.2, 'market_cap': 35000},
        
        # 에너지/화학
        '096770': {'name': 'SK이노베이션', 'per': 12.5, 'pbr': 0.8, 'roe': 6.5, 'market_cap': 28000},
        '010950': {'name': 'S-Oil', 'per': 8.5, 'pbr': 0.9, 'roe': 12.5, 'market_cap': 22000},
        
        # 유틸리티
        '015760': {'name': '한국전력', 'per': 8.2, 'pbr': 0.5, 'roe': 6.8, 'market_cap': 28000},
        '051600': {'name': '한전KPS', 'per': 12.5, 'pbr': 1.8, 'roe': 15.2, 'market_cap': 8500},
        
        # 철강
        '005490': {'name': 'POSCO홀딩스', 'per': 18.5, 'pbr': 0.6, 'roe': 3.2, 'market_cap': 42000},
        
        # 건설
        '000720': {'name': '현대건설', 'per': 8.2, 'pbr': 0.5, 'roe': 6.5, 'market_cap': 12000},
        
        # 미디어
        '214320': {'name': '이노션', 'per': 8.5, 'pbr': 1.2, 'roe': 15.2, 'market_cap': 9500},
        
        # 엔터테인먼트
        '035250': {'name': '강원랜드', 'per': 12.5, 'pbr': 1.8, 'roe': 15.2, 'market_cap': 8500},
        
        # 증권
        '003690': {'name': '코리안리', 'per': 8.5, 'pbr': 0.9, 'roe': 11.8, 'market_cap': 5200},
        
        # ETF는 제외하거나 별도 처리
    }
    
    return sample_data


def update_sample_fundamentals():
    """샘플 데이터로 DB 업데이트"""
    db = FundamentalDB()
    sample_data = load_sample_data()
    
    print("=" * 60)
    print("샘플 재무 데이터 DB 업데이트")
    print("=" * 60)
    print(f"대상 종목: {len(sample_data)}개\n")
    
    updated = 0
    for symbol, data in sample_data.items():
        db.update_fundamentals(symbol, data)
        updated += 1
        print(f"  {symbol} {data['name']}: PER {data['per']}x, PBR {data['pbr']}x")
    
    print(f"\n✅ 업데이트 완료: {updated}개 종목")
    print("\n⚠️  참고: 이 데이터는 샘플이며 실제 투자 시")
    print("    FnGuide( https://comp.fnguide.com )에서")
    print("    최신 재무지표를 확인하세요.")
    
    db.close()


def verify_fundamentals():
    """DB의 재무 데이터 검증"""
    db = FundamentalDB()
    
    print("=" * 60)
    print("DB 재무 데이터 현황")
    print("=" * 60)
    
    symbols = db.get_all_symbols()
    print(f"총 종목 수: {len(symbols)}\n")
    
    # 재무 데이터가 있는 종목 확인
    with_data = 0
    sample_check = []
    
    for symbol in symbols[:100]:  # 상위 100개만 확인
        fund = db.get_fundamentals(symbol)
        if fund and fund.get('per'):
            with_data += 1
            if len(sample_check) < 10:
                sample_check.append((symbol, fund))
    
    print(f"재무 데이터 보유: {with_data}개 (샘플 100개 중)")
    print("\n[샘플 데이터]")
    for symbol, fund in sample_check:
        print(f"  {symbol}: PER {fund.get('per', 'N/A')}, PBR {fund.get('pbr', 'N/A')}")
    
    db.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'verify':
        verify_fundamentals()
    else:
        update_sample_fundamentals()
