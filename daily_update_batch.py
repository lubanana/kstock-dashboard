#!/usr/bin/env python3
"""
Daily Price Update Batch - 매일 가격정보 업데이트
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

# 전체 종목 리스트
ALL_SYMBOLS = [
    # 코스피 대형주
    '005930', '000660', '051910', '005380', '035720', '068270', '207940',
    '006400', '000270', '012330', '005490', '028260', '105560', '018260',
    '032830', '034730', '000150', '016360', '009830', '003490', '004170',
    '000100', '011200', '030200', '010950', '034220', '086790', '055550',
    '047050', '032640', '009540', '030000', '018880', '000810', '024110',
    '005940', '010140', '001040', '003550', '008770', '007310', '006800',
    '000120', '001120', '010130', '002790', '001800', '003000', '005420',
    # 코스닥 대형주
    '247540', '086520', '091990', '035900', '293490', '263750', '151860',
    '196170', '214150', '221840', '183490', '095340', '100090', '137310',
    '058470', '048260', '042000', '041140', '025980', '014990', '039030',
]

DB_PATH = 'data/pivot_strategy.db'


class DailyUpdateBatch:
    def __init__(self):
        self.db_path = DB_PATH
        self.symbols = ALL_SYMBOLS
        self.stats = {
            'total': len(self.symbols),
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': None,
            'last_report_time': None
        }
    
    def log(self, message):
        """타임스탬프와 함께 로그 출력"""
        now = datetime.now(timezone(timedelta(hours=9)))
        print(f"[{now.strftime('%H:%M:%S')}] {message}")
    
    def should_report_progress(self) -> bool:
        """10분 경과 여부 확인"""
        if self.stats['last_report_time'] is None:
            return True
        elapsed = (datetime.now() - self.stats['last_report_time']).total_seconds()
        return elapsed >= 600  # 10 minutes
    
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
    
    def get_missing_symbols(self) -> list:
        """DB에 데이터가 없는 종목 목록"""
        missing = []
        self.log("🔍 DB 미존재 종목 확인 중...")
        
        for symbol in self.symbols:
            latest = self.get_db_latest_date(symbol)
            if latest is None:
                missing.append(symbol)
        
        self.log(f"   미존재 종목: {len(missing)}개")
        return missing
    
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
            
            # 데이터 조회
            df = get_price(symbol, start_date=start_date, end_date=end_date)
            
            if df.empty:
                self.stats['failed'] += 1
                return False
            
            self.stats['updated'] += 1
            return True
            
        except Exception as e:
            self.stats['failed'] += 1
            self.log(f"   ⚠️ {symbol}: {str(e)[:50]}")
            return False
    
    def build_missing_data(self, days: int = 365):
        """누락된 종목 데이터 구축"""
        missing = self.get_missing_symbols()
        
        if not missing:
            self.log("✅ 모든 종목이 DB에 존재합니다")
            return
        
        self.log(f"\n🔧 누락 종목 데이터 구축 시작 ({days}일치)")
        self.log(f"   대상: {len(missing)}개 종목")
        
        end_date = datetime.now(timezone(timedelta(hours=9)))
        start_date = end_date - timedelta(days=days)
        
        for i, symbol in enumerate(missing, 1):
            try:
                self.log(f"   [{i}/{len(missing)}] {symbol} 구축 중...")
                
                df = get_price(
                    symbol,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                if not df.empty:
                    self.stats['updated'] += 1
                    self.log(f"      ✅ {len(df)}일 데이터 구축 완료")
                else:
                    self.stats['failed'] += 1
                    
            except Exception as e:
                self.stats['failed'] += 1
                self.log(f"      ❌ 오류: {str(e)[:50]}")
            
            # 10분마다 진행 보고
            self.report_progress()
            
            # API rate limit 방지
            time.sleep(0.1)
        
        self.log(f"\n✅ 누락 데이터 구축 완료")
    
    def daily_update(self, target_date: str = None):
        """일일 업데이트 실행"""
        self.stats['start_time'] = datetime.now()
        self.stats['last_report_time'] = datetime.now()
        
        if target_date is None:
            target_date = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
        
        self.log("=" * 70)
        self.log(f"📅 일일 가격 업데이트 배치 - {target_date}")
        self.log("=" * 70)
        self.log(f"총 대상 종목: {self.stats['total']}개")
        
        # 1. 먼저 누락된 종목 구축
        self.build_missing_data(days=365)
        
        # 2. 오늘 날짜 업데이트
        self.log(f"\n🔄 오늘 ({target_date}) 가격 업데이트 시작")
        
        for i, symbol in enumerate(self.symbols, 1):
            self.update_symbol(symbol, target_date)
            
            # 10분마다 진행 보고
            if i % 10 == 0:
                self.report_progress()
        
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
