#!/usr/bin/env python3
"""
KStock Level 1 Cron Batch Analyzer
1시간마다 50개씩 처리하는 크론용 분석기

Features:
- 50개 단위 배치 처리
- 누적 결과 저장
- 완료 시 Level 2/3 자동 실행
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from pykrx import stock

BASE_PATH = '/home/programs/kstock_analyzer'
DB_FILE = f'{BASE_PATH}/data/job_queue_cron.db'
RESULT_FILE = f'{BASE_PATH}/data/cron_results.json'
LOG_FILE = f'{BASE_PATH}/logs/cron_analyzer.log'

BATCH_SIZE = 50  # 한 번에 50개


def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


def init_db():
    """DB 초기화"""
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            market TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)')
    conn.commit()
    conn.close()


def load_stocks_if_empty():
    """종목이 없으면 로드"""
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM jobs')
    count = cursor.fetchone()[0]
    conn.close()
    
    if count == 0:
        log("Loading stocks...")
        with open(f'{BASE_PATH}/data/kospi_stocks.json') as f:
            kospi = json.load(f)['stocks']
        with open(f'{BASE_PATH}/data/kosdaq_stocks.json') as f:
            kosdaq = json.load(f)['stocks']
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        for s in kospi:
            cursor.execute('INSERT INTO jobs (code, name, market) VALUES (?, ?, ?)',
                         (s['code'], s['name'], 'KOSPI'))
        for s in kosdaq:
            cursor.execute('INSERT INTO jobs (code, name, market) VALUES (?, ?, ?)',
                         (s['code'], s['name'], 'KOSDAQ'))
        conn.commit()
        conn.close()
        log(f"Loaded {len(kospi) + len(kosdaq)} stocks")


def get_batch():
    """다음 배치 가져오기"""
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, code, name, market FROM jobs 
        WHERE status = 'pending' ORDER BY id LIMIT ?
    ''', (BATCH_SIZE,))
    rows = cursor.fetchall()
    conn.close()
    return [{'id': r[0], 'code': r[1], 'name': r[2], 'market': r[3]} for r in rows]


def analyze_stock(code, name, market):
    """PyKRX로 분석"""
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        df = stock.get_market_ohlcv(start_date, end_date, code)
        
        if df is None or len(df) < 5:
            return None
        
        latest = df.iloc[-1]
        change = latest['등락률']
        
        if change > 2:
            score, rec = 65, 'BUY'
        elif change < -2:
            score, rec = 35, 'SELL'
        else:
            score, rec = 50, 'HOLD'
        
        return {
            'code': code,
            'name': name,
            'market': market,
            'avg_score': score,
            'consensus': rec,
            'price': latest['종가'],
            'change_pct': change
        }
    except Exception as e:
        log(f"   Error: {str(e)[:30]}")
        return None


def save_batch_results(results):
    """배치 결과 누적 저장"""
    if os.path.exists(RESULT_FILE):
        with open(RESULT_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {'results': [], 'total': 0}
    
    data['results'].extend(results)
    data['total'] = len(data['results'])
    data['last_update'] = datetime.now().isoformat()
    
    with open(RESULT_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_db_status(job_ids):
    """DB 상태 업데이트"""
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for job_id in job_ids:
        cursor.execute('UPDATE jobs SET status = 'completed' WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()


def get_stats():
    """통계"""
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')
    stats = {'total': 0, 'completed': 0, 'pending': 0}
    for row in cursor.fetchall():
        stats[row[0]] = row[1]
        stats['total'] += row[1]
    conn.close()
    return stats


def send_telegram(msg):
    try:
        import subprocess
        subprocess.run(['openclaw', 'message', 'send', '--channel', 'telegram',
                       '--to', '32083875', msg], capture_output=True, timeout=10)
    except:
        pass


def main():
    log("=" * 60)
    log("🚀 Cron Batch Analyzer")
    log("=" * 60)
    log(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    init_db()
    load_stocks_if_empty()
    
    stats = get_stats()
    log(f"Stats: {stats['completed']}/{stats['total']} completed")
    
    # 배치 가져오기
    batch = get_batch()
    if not batch:
        log("No pending jobs - all done!")
        return
    
    log(f"Processing batch of {len(batch)} stocks...")
    
    results = []
    completed_ids = []
    
    for i, job in enumerate(batch, 1):
        log(f"  [{i}/{len(batch)}] {job['name']}")
        
        result = analyze_stock(job['code'], job['name'], job['market'])
        
        if result:
            results.append(result)
            completed_ids.append(job['id'])
            log(f"     ✅ {result['avg_score']}pts")
        else:
            log(f"     ❌ Failed")
        
        time.sleep(1)  # 서버 부하 방지
    
    # 결과 저장
    if results:
        save_batch_results(results)
        update_db_status(completed_ids)
        log(f"✅ Saved {len(results)} results")
    
    # 최종 통계
    stats = get_stats()
    pct = stats['completed'] / stats['total'] * 100
    log(f"Progress: {stats['completed']}/{stats['total']} ({pct:.1f}%)")
    
    send_telegram(f"📊 크론 배치 완료\n{stats['completed']}/{stats['total']} ({pct:.1f}%)\n이번 배치: {len(results)}개")
    
    # 완료 시 Level 2/3 실행
    if stats['completed'] >= stats['total']:
        log("🎉 All done! Running Level 2/3...")
        send_telegram("🎉 전체 완료! Level 2/3 실행 중...")
        
        import subprocess
        try:
            subprocess.run(['python3', f'{BASE_PATH}/agents/sector_agent.py'], cwd=BASE_PATH, timeout=600)
            subprocess.run(['python3', f'{BASE_PATH}/agents/macro_agent.py'], cwd=BASE_PATH, timeout=600)
            subprocess.run(['python3', f'{BASE_PATH}/agents/pm_agent.py'], cwd=BASE_PATH, timeout=1200)
            send_telegram("✅ Level 1/2/3 전체 완료!")
        except Exception as e:
            log(f"Level 2/3 error: {e}")


if __name__ == '__main__':
    main()
