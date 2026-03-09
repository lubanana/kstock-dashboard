#!/usr/bin/env python3
"""
KStock Level 1 Analyzer with PyKRX
PyKRX 기반 데이터 수집 (yfinance 대체)

Features:
- PyKRX로 한국 주식 데이터 수집
- SQLite DB 기반 작업 큐
- 메모리 효율적 처리
"""

import sqlite3
import json
import os
import sys
import time
import gc
from datetime import datetime, timedelta
from typing import Optional, Dict, List

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from pykrx import stock

BASE_PATH = '/home/programs/kstock_analyzer'
DB_FILE = f'{BASE_PATH}/data/job_queue_pykrx.db'
LOG_FILE = f'{BASE_PATH}/logs/pykrx_analyzer.log'

# 설정
BATCH_SIZE = 20
SLEEP_SECONDS = 0.5
RETRY_MAX = 3


def log(message):
    """로그 기록"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


def get_stock_data_pykrx(code: str, days: int = 30) -> Optional[Dict]:
    """
    PyKRX로 주식 데이터 수집
    """
    try:
        # 날짜 계산
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        # OHLCV 데이터
        df = stock.get_market_ohlcv(start_date, end_date, code)
        
        if df is None or len(df) == 0:
            return None
        
        # 최신 데이터
        latest = df.iloc[-1]
        
        return {
            'open': latest['시가'],
            'high': latest['고가'],
            'low': latest['저가'],
            'close': latest['종가'],
            'volume': latest['거래량'],
            'change_pct': latest['등락률'],
            'data': df
        }
    except Exception as e:
        log(f"   ⚠️ PyKRX error for {code}: {e}")
        return None


class JobQueueDB:
    """SQLite 기반 작업 큐 DB"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                sector TEXT DEFAULT '기타',
                status TEXT DEFAULT 'pending',
                result_json TEXT,
                error_msg TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code ON jobs(code)')
        
        conn.commit()
        conn.close()
        log("✅ DB initialized")
    
    def insert_stocks(self, stocks: List[Dict]):
        """종목 리스트 삽입"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for stock_item in stocks:
            cursor.execute('''
                INSERT OR IGNORE INTO jobs 
                (code, name, symbol, market, sector, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (
                stock_item['code'],
                stock_item['name'],
                stock_item['symbol'],
                stock_item['market'],
                stock_item.get('sector', '기타')
            ))
        
        conn.commit()
        conn.close()
        log(f"✅ Inserted {len(stocks)} stocks")
    
    def get_next_job(self) -> Optional[Dict]:
        """다음 작업 가져오기"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, code, name, symbol, market, sector 
            FROM jobs 
            WHERE status = 'pending' 
            ORDER BY id 
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'code': row[1],
                'name': row[2],
                'symbol': row[3],
                'market': row[4],
                'sector': row[5]
            }
        return None
    
    def mark_processing(self, job_id: int):
        """작업 시작 표시"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs SET status = 'processing' WHERE id = ?
        ''', (job_id,))
        conn.commit()
        conn.close()
    
    def mark_completed(self, job_id: int, result: Dict):
        """작업 완료 표시"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs 
            SET status = 'completed',
                result_json = ?,
                processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (json.dumps(result, ensure_ascii=False), job_id))
        conn.commit()
        conn.close()
    
    def mark_failed(self, job_id: int, error: str):
        """작업 실패 표시"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs 
            SET status = 'failed',
                error_msg = ?,
                retry_count = retry_count + 1,
                processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (error[:500], job_id))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """작업 통계"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) FROM jobs GROUP BY status
        ''')
        
        stats = {'total': 0, 'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0}
        for row in cursor.fetchall():
            status, count = row
            stats[status] = count
            stats['total'] += count
        
        conn.close()
        return stats


def analyze_stock_pykrx(stock_info: Dict) -> tuple:
    """
    PyKRX 기반 단일 종목 분석
    """
    code = stock_info['code']
    name = stock_info['name']
    
    result = {
        'symbol': stock_info['symbol'],
        'name': name,
        'market': stock_info.get('market', 'KOSPI'),
        'sector': stock_info.get('sector', 'Unknown'),
        'date': datetime.now().isoformat(),
        'data_source': 'pykrx',
        'agents': {},
        'status': 'pending'
    }
    
    try:
        # PyKRX로 데이터 수집
        data = get_stock_data_pykrx(code, days=60)
        
        if data is None:
            result['status'] = 'error'
            result['error'] = 'No data from PyKRX'
            return result, False
        
        # 간단한 기술적 분석 (PyKRX 데이터 기반)
        df = data['data']
        
        # 이동평균
        ma5 = df['종가'].rolling(5).mean().iloc[-1]
        ma20 = df['종가'].rolling(20).mean().iloc[-1]
        current_price = data['close']
        
        # 추세 판단
        trend_score = 0
        if current_price > ma5:
            trend_score += 15
        if current_price > ma20:
            trend_score += 15
        if ma5 > ma20:
            trend_score += 10
        
        # 거래량
        volume_avg = df['거래량'].rolling(20).mean().iloc[-1]
        volume_ratio = data['volume'] / volume_avg if volume_avg > 0 else 1
        volume_score = min(25, max(0, (volume_ratio - 0.5) * 25))
        
        # 등락률
        change_score = 25 if -5 <= data['change_pct'] <= 5 else max(0, 25 - abs(data['change_pct']))
        
        # 총점
        total_score = trend_score + volume_score + change_score
        
        result['agents'] = {
            'TECH': {'score': total_score, 'rec': 'BUY' if total_score >= 60 else 'HOLD' if total_score >= 40 else 'SELL'},
            'QUANT': {'score': 50, 'rec': 'HOLD'},
            'QUAL': {'score': 50, 'rec': 'HOLD'},
            'NEWS': {'score': 50, 'rec': 'HOLD'}
        }
        
        result['avg_score'] = round((total_score + 50 + 50 + 50) / 4, 1)
        result['consensus'] = 'BUY' if result['avg_score'] >= 60 else 'HOLD' if result['avg_score'] >= 40 else 'SELL'
        result['status'] = 'success'
        result['price_data'] = {
            'current': current_price,
            'change_pct': data['change_pct'],
            'volume': data['volume']
        }
        
        return result, True
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        return result, False


def send_telegram(message: str):
    """Telegram 알림"""
    try:
        import subprocess
        subprocess.run([
            'openclaw', 'message', 'send',
            '--channel', 'telegram',
            '--to', '32083875',
            message
        ], capture_output=True, timeout=10)
    except:
        pass


def main():
    """메인 실행"""
    log("=" * 70)
    log("🚀 KStock Level 1 PyKRX Analyzer")
    log("=" * 70)
    log(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("Data Source: PyKRX (yfinance replaced)")
    log("=" * 70)
    
    # DB 초기화
    db = JobQueueDB(DB_FILE)
    
    # 종목 리스트 확인 및 삽입
    stats = db.get_stats()
    if stats['total'] == 0:
        log("📂 Loading stock lists...")
        
        with open(f'{BASE_PATH}/data/kospi_stocks.json', 'r') as f:
            kospi = json.load(f)['stocks']
        
        with open(f'{BASE_PATH}/data/kosdaq_stocks.json', 'r') as f:
            kosdaq = json.load(f)['stocks']
        
        for s in kospi:
            s['symbol'] = f"{s['code']}.KS"
            s['market'] = 'KOSPI'
        
        for s in kosdaq:
            s['symbol'] = f"{s['code']}.KQ"
            s['market'] = 'KOSDAQ'
        
        all_stocks = kospi + kosdaq
        db.insert_stocks(all_stocks)
        
        log(f"   ✅ Total: {len(all_stocks)} stocks")
    else:
        log(f"📂 DB already has {stats['total']} stocks")
    
    # 시작 알림
    send_telegram(f"🚀 PyKRX 분석 시작\n총 {db.get_stats()['total']}개 종목")
    
    start_time = time.time()
    processed = 0
    
    # 메인 루프
    while True:
        try:
            job = db.get_next_job()
            
            if job is None:
                log("\n✅ All jobs completed!")
                break
            
            db.mark_processing(job['id'])
            
            processed += 1
            log(f"\n[{processed}] {job['name']} ({job['code']})")
            
            result, success = analyze_stock_pykrx(job)
            
            if success:
                db.mark_completed(job['id'], result)
                log(f"   ✅ {result['avg_score']:.1f}pts - {result['consensus']}")
            else:
                db.mark_failed(job['id'], result.get('error', 'Unknown'))
                log(f"   ❌ Failed: {result.get('error', 'Unknown')}")
            
            gc.collect()
            
            # 50개마다 알림
            if processed % 50 == 0:
                elapsed = time.time() - start_time
                stats = db.get_stats()
                pct = (stats['completed'] / stats['total']) * 100
                
                log(f"\n📊 Progress: {stats['completed']}/{stats['total']} ({pct:.1f}%)")
                send_telegram(
                    f"📊 PyKRX 진행: {stats['completed']}/{stats['total']} ({pct:.1f}%)\n"
                    f"⏱️ {elapsed//60}분 경과"
                )
            
            time.sleep(SLEEP_SECONDS)
            
        except KeyboardInterrupt:
            log("\n⚠️ Interrupted by user")
            break
        except Exception as e:
            log(f"\n❌ Loop error: {e}")
            time.sleep(5)
    
    # 완료
    elapsed = time.time() - start_time
    stats = db.get_stats()
    
    log("\n" + "=" * 70)
    log("✅ ANALYSIS COMPLETE")
    log("=" * 70)
    log(f"Total: {stats['total']}")
    log(f"Completed: {stats['completed']}")
    log(f"Failed: {stats['failed']}")
    log(f"Elapsed: {elapsed//3600}h {(elapsed%3600)//60}m")
    
    # 결과 저장
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = f'{BASE_PATH}/data/level1_daily/level1_pykrx_{date_str}.json'
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT result_json FROM jobs WHERE status = 'completed'")
    results = [json.loads(row[0]) for row in cursor.fetchall() if row[0]]
    conn.close()
    
    final = {
        'date': datetime.now().isoformat(),
        'data_source': 'PyKRX',
        'total': stats['total'],
        'completed': stats['completed'],
        'failed': stats['failed'],
        'elapsed_minutes': elapsed / 60,
        'results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    
    log(f"Output: {output_file}")
    send_telegram(f"🎉 PyKRX 완료! {stats['completed']}/{stats['total']}")


if __name__ == '__main__':
    import traceback
    try:
        main()
    except Exception as e:
        log(f"\n❌ Fatal error: {e}")
        log(traceback.format_exc())
