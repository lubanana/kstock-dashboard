#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local SQLite Database for Pivot Strategy
========================================
간단한 로컬 데이터베이스 설정 및 관리 모듈

기능:
1. 주가 데이터 캐싱 (FinanceDataReader API 호출 최소화)
2. 백테스트 결과 저장
3. 스캔 결과 저장
4. 포트폴리오 관리
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import json


class LocalDB:
    """
    로컬 SQLite 데이터베이스 관리 클래스
    """
    
    def __init__(self, db_path: str = './data/pivot_strategy.db'):
        """
        Parameters:
        -----------
        db_path : str
            데이터베이스 파일 경로
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
        # 테이블 초기화
        self._init_tables()
        print(f"✅ 데이터베이스 연결됨: {db_path}")
    
    def _init_tables(self):
        """테이블 초기화"""
        cursor = self.conn.cursor()
        
        # 1. 주가 데이터 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 2. 종목 정보 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_info (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                market TEXT,
                sector TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. 백테스트 결과 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                initial_capital REAL,
                final_capital REAL,
                total_return_pct REAL,
                mdd_pct REAL,
                win_rate_pct REAL,
                profit_factor REAL,
                total_trades INTEGER,
                pivot_period INTEGER,
                volume_threshold REAL,
                stop_loss_pct REAL,
                trailing_stop_pct REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 4. 거래 내역 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id INTEGER,
                symbol TEXT,
                entry_date TEXT,
                exit_date TEXT,
                entry_price REAL,
                exit_price REAL,
                shares_1st INTEGER,
                shares_2nd INTEGER,
                shares_3rd INTEGER,
                avg_cost REAL,
                total_invested REAL,
                pnl REAL,
                return_pct REAL,
                exit_reason TEXT,
                FOREIGN KEY (backtest_id) REFERENCES backtest_results(id)
            )
        ''')
        
        # 5. 스캔 결과 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_date TEXT,
                symbol TEXT,
                name TEXT,
                market TEXT,
                signal_date TEXT,
                close_price REAL,
                volume INTEGER,
                pivot_high REAL,
                volume_ma20 INTEGER,
                volume_ratio REAL,
                price_change_pct REAL,
                score REAL,
                is_processed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(scan_date, symbol)
            )
        ''')
        
        # 6. 포트폴리오 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                entry_date TEXT,
                entry_price REAL,
                shares INTEGER,
                avg_cost REAL,
                current_price REAL,
                current_value REAL,
                unrealized_pnl REAL,
                unrealized_return_pct REAL,
                highest_price REAL,
                stop_loss_price REAL,
                trailing_stop_price REAL,
                status TEXT DEFAULT 'HOLDING',
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_symbol ON stock_prices(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_date ON stock_prices(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scan_date ON scan_results(scan_date)')
        
        self.conn.commit()
    
    # ========== 주가 데이터 메서드 ==========
    
    def save_prices(self, df: pd.DataFrame, symbol: str):
        """
        주가 데이터 저장
        
        Parameters:
        -----------
        df : pd.DataFrame
            주가 데이터 (open, high, low, close, volume 컬럼 필요)
        symbol : str
            종목코드
        """
        df = df.copy()
        df['symbol'] = symbol
        df['date'] = df.index.strftime('%Y-%m-%d')
        
        # 컬럼명 소문자로 통일
        df.columns = [c.lower() for c in df.columns]
        
        # 필요한 컬럼만 선택
        cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        df_save = df[[c for c in cols if c in df.columns]]
        
        # UPSERT (INSERT OR REPLACE)
        df_save.to_sql('stock_prices', self.conn, if_exists='append', index=False)
        print(f"💾 {symbol} 주가 데이터 저장됨: {len(df_save)}건")
    
    def get_prices(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        주가 데이터 조회
        
        Parameters:
        -----------
        symbol : str
            종목코드
        start_date : str
            시작일 (YYYY-MM-DD)
        end_date : str
            종료일 (YYYY-MM-DD)
        
        Returns:
        --------
        pd.DataFrame
        """
        query = "SELECT * FROM stock_prices WHERE symbol = ?"
        params = [symbol]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        df = pd.read_sql_query(query, self.conn, params=params, parse_dates=['date'])
        
        if not df.empty:
            df.set_index('date', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
        
        return df
    
    def is_cached(self, symbol: str, date: str) -> bool:
        """
        특정 날짜의 데이터가 캐시되어 있는지 확인
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM stock_prices WHERE symbol = ? AND date = ?",
            (symbol, date)
        )
        return cursor.fetchone() is not None
    
    def get_last_update(self, symbol: str) -> Optional[str]:
        """
        마지막 업데이트 날짜 조회
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(date) FROM stock_prices WHERE symbol = ?",
            (symbol,)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    
    # ========== 백테스트 결과 메서드 ==========
    
    def save_backtest(self, strategy, result, trades_df: pd.DataFrame) -> int:
        """
        백테스트 결과 저장
        
        Returns:
        --------
        int : 생성된 backtest_id
        """
        cursor = self.conn.cursor()
        
        # 백테스트 메타데이터 저장
        cursor.execute('''
            INSERT INTO backtest_results 
            (symbol, start_date, end_date, initial_capital, final_capital,
             total_return_pct, mdd_pct, win_rate_pct, profit_factor, total_trades,
             pivot_period, volume_threshold, stop_loss_pct, trailing_stop_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            strategy.symbol,
            strategy.start_date,
            strategy.end_date,
            strategy.initial_capital,
            result.equity_curve['total_value'].iloc[-1],
            result.final_return,
            result.mdd,
            result.win_rate,
            result.profit_factor,
            len(result.trades),
            strategy.pivot_period,
            strategy.volume_threshold,
            strategy.stop_loss_pct,
            strategy.trailing_stop_pct
        ))
        
        backtest_id = cursor.lastrowid
        
        # 거래 내역 저장
        for trade in result.trades:
            cursor.execute('''
                INSERT INTO trade_records
                (backtest_id, symbol, entry_date, exit_date, entry_price, exit_price,
                 shares_1st, shares_2nd, shares_3rd, avg_cost, total_invested,
                 pnl, return_pct, exit_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                backtest_id,
                strategy.symbol,
                trade.entry_date.strftime('%Y-%m-%d'),
                trade.exit_date.strftime('%Y-%m-%d') if trade.exit_date else None,
                trade.entry_price,
                trade.exit_price,
                trade.shares_1st,
                trade.shares_2nd,
                trade.shares_3rd,
                trade.avg_cost,
                trade.total_invested,
                trade.pnl,
                trade.return_pct,
                trade.exit_reason
            ))
        
        self.conn.commit()
        print(f"💾 백테스트 결과 저장됨 (ID: {backtest_id})")
        return backtest_id
    
    def get_backtest_history(self, symbol: str = None) -> pd.DataFrame:
        """
        백테스트 히스토리 조회
        """
        query = "SELECT * FROM backtest_results"
        params = []
        
        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)
        
        query += " ORDER BY created_at DESC"
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    # ========== 스캔 결과 메서드 ==========
    
    def save_scan_results(self, df: pd.DataFrame, scan_date: str = None):
        """
        스캔 결과 저장
        """
        if scan_date is None:
            scan_date = datetime.now().strftime('%Y-%m-%d')
        
        df = df.copy()
        df['scan_date'] = scan_date
        
        # 컬럼명 매핑
        col_map = {
            'symbol': 'symbol',
            'name': 'name',
            'market': 'market',
            'date': 'signal_date',
            'close': 'close_price',
            'volume': 'volume',
            'pivot_high': 'pivot_high',
            'volume_ma20': 'volume_ma20',
            'volume_ratio': 'volume_ratio',
            'price_change_pct': 'price_change_pct',
            'score': 'score'
        }
        
        df_save = pd.DataFrame()
        for old_col, new_col in col_map.items():
            if old_col in df.columns:
                df_save[new_col] = df[old_col]
        
        df_save.to_sql('scan_results', self.conn, if_exists='append', index=False)
        print(f"💾 스캔 결과 저장됨: {len(df_save)}건 ({scan_date})")
    
    def get_scan_results(self, scan_date: str = None, min_score: float = None) -> pd.DataFrame:
        """
        스캔 결과 조회
        """
        query = "SELECT * FROM scan_results WHERE 1=1"
        params = []
        
        if scan_date:
            query += " AND scan_date = ?"
            params.append(scan_date)
        if min_score:
            query += " AND score >= ?"
            params.append(min_score)
        
        query += " ORDER BY score DESC"
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    # ========== 포트폴리오 메서드 ==========
    
    def add_position(self, symbol: str, entry_date: str, entry_price: float, 
                     shares: int, notes: str = ''):
        """
        포지션 추가
        """
        avg_cost = entry_price
        stop_loss = entry_price * 0.9  # -10%
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO portfolio
            (symbol, entry_date, entry_price, shares, avg_cost, current_price,
             current_value, highest_price, stop_loss_price, trailing_stop_price, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol, entry_date, entry_price, shares, avg_cost, entry_price,
            entry_price * shares, entry_price, stop_loss, entry_price * 0.85, notes
        ))
        
        self.conn.commit()
        print(f"💾 포지션 추가: {symbol} {shares}주 @ {entry_price:,.0f}원")
    
    def update_position(self, symbol: str, current_price: float):
        """
        포지션 업데이트 (현재가 반영)
        """
        cursor = self.conn.cursor()
        
        # 현재 포지션 조회
        cursor.execute(
            "SELECT * FROM portfolio WHERE symbol = ? AND status = 'HOLDING'",
            (symbol,)
        )
        row = cursor.fetchone()
        
        if row:
            shares = row['shares']
            avg_cost = row['avg_cost']
            highest = max(row['highest_price'], current_price)
            
            current_value = current_price * shares
            unrealized_pnl = (current_price - avg_cost) * shares
            unrealized_pct = ((current_price - avg_cost) / avg_cost) * 100
            
            # 트레일링 스탑 가격 업데이트
            trailing_stop = highest * 0.85  # -15%
            
            cursor.execute('''
                UPDATE portfolio SET
                    current_price = ?,
                    current_value = ?,
                    unrealized_pnl = ?,
                    unrealized_return_pct = ?,
                    highest_price = ?,
                    trailing_stop_price = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (current_price, current_value, unrealized_pnl, unrealized_pct,
                  highest, trailing_stop, row['id']))
            
            self.conn.commit()
    
    def get_portfolio(self) -> pd.DataFrame:
        """
        현재 포트폴리오 조회
        """
        return pd.read_sql_query(
            "SELECT * FROM portfolio WHERE status = 'HOLDING' ORDER BY entry_date",
            self.conn
        )
    
    def close_position(self, symbol: str, exit_price: float, exit_date: str = None):
        """
        포지션 청산
        """
        if exit_date is None:
            exit_date = datetime.now().strftime('%Y-%m-%d')
        
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE portfolio SET
                status = 'CLOSED',
                exit_price = ?,
                exit_date = ?,
                realized_pnl = (current_price - avg_cost) * shares,
                realized_return_pct = ((current_price - avg_cost) / avg_cost) * 100,
                updated_at = CURRENT_TIMESTAMP
            WHERE symbol = ? AND status = 'HOLDING'
        ''', (exit_price, exit_date, symbol))
        
        self.conn.commit()
        print(f"🔴 포지션 청산: {symbol} @ {exit_price:,.0f}원")
    
    # ========== 유틸리티 메서드 ==========
    
    def export_to_csv(self, table: str, filepath: str):
        """
        테이블을 CSV로 낳춰
        """
        df = pd.read_sql_query(f"SELECT * FROM {table}", self.conn)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"📁 낳춰 완료: {filepath}")
    
    def close(self):
        """데이터베이스 연결 종료"""
        self.conn.close()
        print("🔌 데이터베이스 연결 종료")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def init_database(db_path: str = './data/pivot_strategy.db'):
    """
    데이터베이스 초기화 (간단한 시작용)
    
    Usage:
        from local_db import init_database
        db = init_database()
    """
    return LocalDB(db_path)


# 간단한 사용 예시
if __name__ == "__main__":
    print("🚀 LocalDB 테스트")
    
    # 데이터베이스 초기화
    db = init_database()
    
    # 테스트 데이터 저장 예시
    test_df = pd.DataFrame({
        'open': [100, 102, 101],
        'high': [103, 104, 102],
        'low': [99, 101, 100],
        'close': [102, 103, 101],
        'volume': [10000, 15000, 12000]
    }, index=pd.date_range('2024-01-01', periods=3))
    
    db.save_prices(test_df, '005930')
    
    # 조회 테스트
    result = db.get_prices('005930')
    print("\n📊 조회 결과:")
    print(result)
    
    db.close()
