#!/usr/bin/env python3
"""
KStock Level 1 PyKRX Simple Analyzer
PyKRX만 사용하는 최소화 버전

Features:
- PyKRX만 사용 (FinanceDataReader 제외)
- 최소한의 기능만 구현
- 최대 안정성 우선
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from pykrx import stock

BASE_PATH = '/home/programs/kstock_analyzer'
DB_FILE = f'{BASE_PATH}/data/job_queue_simple.db'
LOG_FILE = f'{BASE_PATH}/logs/simple_analyzer.log'

SLEEP_SECONDS = 2  # 더 긴 대기 시간


def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


class SimpleDB:
    """간단한 SQLite DB"""
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                market TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)')
        conn.commit()
        conn.close()
    
    def insert_stocks(self, stocks):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for s in stocks:
            cursor.execute('''
                INSERT OR IGNORE INTO jobs (code, name, market, status)
                VALUES (?, ?, ?, 'pending')
            ''', (s['code'], s['name'], s['market']))
        conn.commit()
        conn.close()
        log(f"Inserted {len(stocks)} stocks")
    
    def get_next_job(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, code, name, market FROM jobs 
            WHERE status = 'pending' ORDER BY id LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'code': row[1], 'name': row[2], 'market': row[3]}
        return None
    
    def mark_completed(self, job_id, result):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs SET status='completed', result_json=?, processed_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (json.dumps(result), job_id))
        conn.commit()
        conn.close()
    
    def mark_failed(self, job_id):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs SET status='failed', processed_at=CURRENT_TIMESTAMP WHERE id=?
        ''', (job_id,))
        conn.commit()
        conn.close()
    
    def get_stats(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')
        stats = {'total': 0, 'completed': 0, 'failed': 0, 'pending': 0}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
            stats['total'] += row[1]
        conn.close()
        return stats


def analyze_with_pykrx(code, name, market):
    """PyKRX로만 분석"""
    result = {
        'code': code,
        'name': name,
        'market': market,
        'date': datetime.now().isoformat(),
        'avg_score': 50,
        'consensus': 'HOLD'
    }
    
    try:
        # OHLCV 데이터
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        df = stock.get_market_ohlcv(start_date, end_date, code)
        
        if df is None or len(df) < 5:
            return result, False
        
        latest = df.iloc[-1]
        
        # 간단한 점수 계산
        close = latest['종가']
        change = latest['등락률']
        
        # 등락률 기반 점수
        if change > 2:
            score = 65
            rec = 'BUY'
        elif change < -2:
            score = 35
            rec = 'SELL'
        else:
            score = 50
            rec = 'HOLD'
        
        result['avg_score'] = score
        result['consensus'] = rec
        result['price'] = close
        result['change_pct'] = change
        
        return result, True
        
    except Exception as e:
        log(f"   Error: {str(e)[:40]}")
        return result, False


def send_telegram(msg):
    try:
        import subprocess
        subprocess.run(['openclaw', 'message', 'send', '--channel', 'telegram',
                       '--to', '32083875', msg], capture_output=True, timeout=10)
    except:
        pass


def main():
    log("=" * 60)
    log("🚀 PyKRX Simple Analyzer")
    log("=" * 60)
    log(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = SimpleDB(DB_FILE)
    
    # 종목 로드
    stats = db.get_stats()
    if stats['total'] == 0:
        log("Loading stocks...")
        with open(f'{BASE_PATH}/data/kospi_stocks.json') as f:
            kospi = json.load(f)['stocks']
        with open(f'{BASE_PATH}/data/kosdaq_stocks.json') as f:
            kosdaq = json.load(f)['stocks']
        
        for s in kospi:
            s['market'] = 'KOSPI'
        for s in kosdaq:
            s['market'] = 'KOSDAQ'
        
        db.insert_stocks(kospi + kosdaq)
        log(f"Total: {len(kospi) + len(kosdaq)} stocks")
    
    send_telegram(f"🚀 PyKRX Simple 시작\n총 {db.get_stats()['total']}개")
    
    start_time = time.time()
    processed = 0
    
    while True:
        try:
            job = db.get_next_job()
            if job is None:
                log("✅ All completed!")
                break
            
            processed += 1
            if processed % 10 == 1:
                log(f"\n[{processed}] {job['name']} ({job['code']})")
            
            result, success = analyze_with_pykrx(job['code'], job['name'], job['market'])
            
            if success:
                db.mark_completed(job['id'], result)
                if processed % 10 == 1:
                    log(f"   ✅ {result['avg_score']}pts")
            else:
                db.mark_failed(job['id'])
                log(f"   ❌ Failed")
            
            # 50개마다 알림
            if processed % 50 == 0:
                stats = db.get_stats()
                elapsed = time.time() - start_time
                pct = stats['completed'] / stats['total'] * 100
                log(f"Progress: {stats['completed']}/{stats['total']} ({pct:.1f}%)")
                send_telegram(f"📊 {stats['completed']}/{stats['total']} ({pct:.1f}%)\n⏱️ {elapsed//60}분")
            
            time.sleep(SLEEP_SECONDS)
            
        except KeyboardInterrupt:
            log("Stopped by user")
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(5)
    
    # 완료
    stats = db.get_stats()
    elapsed = time.time() - start_time
    log(f"\n✅ Complete: {stats['completed']}/{stats['total']}")
    log(f"Time: {elapsed//3600}h {(elapsed%3600)//60}m")
    send_telegram(f"🎉 완료! {stats['completed']}/{stats['total']}")


if __name__ == '__main__':
    import traceback
    try:
        main()
    except Exception as e:
        log(f"Fatal error: {e}")
        log(traceback.format_exc())
