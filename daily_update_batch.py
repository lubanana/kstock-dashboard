#!/usr/bin/env python3
"""
Daily Price Update Batch - 매일 전체 종목 가격정보 업데이트
Reports progress every 10 minutes
"""

import sys
sys.path.insert(0, '.')
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fdr_wrapper import get_price
import time
import FinanceDataReader as fdr

DB_PATH = 'data/pivot_strategy.db'
BATCH_SIZE = 100  # 한 번에 처리할 종목 수
REPORT_INTERVAL = 600  # 10분 (초)


class DailyUpdateBatch:
    def __init__(self):
        self.db_path = DB_PATH
        self.symbols = self._load_all_symbols()
        self.stats = {
            'total': len(self.symbols),
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': None,
            'last_report_time': None
        }
    
    def _load_all_symbols(self) -> list:
        """전체 종목 리스트 로드 (KOSPI + KOSDAQ)"""
        symbols = []
        
        try:
            # 1. DB에 있는 종목 먼저
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT symbol FROM stock_prices')
            db_symbols = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            symbols.extend(db_symbols)
            
            # 2. KOSPI 종목 추가
            try:
                kospi = fdr.StockListing('KOSPI')
                kospi_symbols = kospi['Code'].tolist()
                symbols.extend(kospi_symbols)
            except Exception as e:
                pass
            
            # 3. KOSDAQ 종목 추가
            try:
                kosdaq = fdr.StockListing('KOSDAQ')
                kosdaq_symbols = kosdaq['Code'].tolist()
                symbols.extend(kosdaq_symbols)
            except Exception as e:
                pass
            
            # 중복 제거 및 정렬
            symbols = sorted(list(set(symbols)))
            
            # ETF/ETN 필터링 (일부)
            exclude_patterns = ['K', 'Q', 'V', 'W', 'T']
            symbols = [s for s in symbols if not any(s.startswith(p) for p in exclude_patterns)]
            
            return symbols
            
        except Exception as e:
            self.log(f"⚠️ 전체 종목 로드 실패, DB 종목만 사용: {e}")
            return db_symbols if 'db_symbols' in dir() else []
    
    def log(self, message):
        """타임스탬프와 함께 로그 출력"""
        now = datetime.now(timezone(timedelta(hours=9)))
        print(f"[{now.strftime('%H:%M:%S')}] {message}", flush=True)
    
    def should_report_progress(self) -> bool:
        """10분 경과 여부 확인"""
        if self.stats['last_report_time'] is None:
            return True
        elapsed = (datetime.now() - self.stats['last_report_time']).total_seconds()
        return elapsed >= REPORT_INTERVAL
    
    def report_progress(self, force=False):
        """진행 상황 보고"""
        if not force and not self.should_report_progress():
            return
        
        elapsed = datetime.now() - self.stats['start_time']
        elapsed_str = str(elapsed).split('.')[0]
        
        processed = self.stats['updated'] + self.stats['skipped'] + self.stats['failed']
        progress_pct = (processed / self.stats['total']) * 100 if self.stats['total'] > 0 else 0
        
        self.log("=" * 60)
        self.log("📊 진행 상황 보고")
        self.log("=" * 60)
        self.log(f"   경과 시간: {elapsed_str}")
        self.log(f"   진행률: {processed}/{self.stats['total']} ({progress_pct:.1f}%)")
        self.log(f"   ✅ 업데이트: {self.stats['updated']}")
        self.log(f"   ⏭️  스킵: {self.stats['skipped']}")
        self.log(f"   ❌ 실패: {self.stats['failed']}")
        self.log("=" * 60)
        
        self.stats['last_report_time'] = datetime.now()
    
    def get_db_latest_date(self, symbol: str) -> str:
        """DB에서 해당 종목의 최신 날짜 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT MAX(date) FROM stock_prices WHERE symbol = ?',
                (symbol,)
            )
            result = cursor.fetchone()
            conn.close()
            return result[0] if result and result[0] else None
        except Exception as e:
            return None
    
    def update_symbol(self, symbol: str, target_date: str = None) -> bool:
        """단일 종목 업데이트"""
        try:
            # DB 최신 날짜 확인
            db_latest = self.get_db_latest_date(symbol)
            
            if target_date:
                # 특정 날짜 업데이트
                if db_latest and db_latest >= target_date:
                    self.stats['skipped'] += 1
                    return True
                end_date = target_date
                start_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
            else:
                # 오늘까지 업데이트
                today = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
                if db_latest and db_latest >= today:
                    self.stats['skipped'] += 1
                    return True
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                end_date = today
            
            # 데이터 조회 (fdr_wrapper가 자동으로 DB에 저장)
            df = get_price(symbol, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                self.stats['failed'] += 1
                return False
            
            self.stats['updated'] += 1
            return True
            
        except Exception as e:
            self.stats['failed'] += 1
            return False
    
    def daily_update(self, target_date: str = None):
        """일일 업데이트 실행"""
        self.stats['start_time'] = datetime.now()
        self.stats['last_report_time'] = datetime.now()
        
        if target_date is None:
            target_date = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
        
        self.log("=" * 70)
        self.log(f"📅 전체 종목 일일 가격 업데이트 - {target_date}")
        self.log("=" * 70)
        self.log(f"총 대상 종목: {self.stats['total']:,}개")
        
        # 오늘 날짜 업데이트
        self.log(f"\n🔄 오늘 ({target_date}) 가격 업데이트 시작")
        
        for i, symbol in enumerate(self.symbols, 1):
            self.update_symbol(symbol, target_date)
            
            # 10분마다 진행 보고
            if i % BATCH_SIZE == 0 or i == self.stats['total']:
                self.report_progress()
                # API rate limit 방지
                time.sleep(1)
        
        # 최종 보고
        self.report_progress(force=True)
        
        self.log("\n" + "=" * 70)
        self.log("✅ 일일 업데이트 완료")
        self.log("=" * 70)
        
        return self.stats


def main():
    """메인 실행"""
    batch = DailyUpdateBatch()
    
    # 명령줄 인자로 날짜 지정 가능
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    
    batch.daily_update(target_date)


if __name__ == '__main__':
    main()
