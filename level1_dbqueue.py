#!/usr/bin/env python3
"""
KStock Level 1 SQLite Queue Manager
가벼운 DB 기반 작업 큐 관리

Features:
- SQLite DB 기반 작업 큐
- 메모리에 전체 종목 로드하지 않음
- 개별 작업 성공/실패 DB 기록
- 체크포인트 기능 내장
- 재시작 시 자동 복구
"""

import sqlite3
import json
import os
import sys
import time
import gc
from datetime import datetime
from typing import Optional, Dict, List

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

BASE_PATH = '/home/programs/kstock_analyzer'
DB_FILE = f'{BASE_PATH}/data/job_queue.db'
LOG_FILE = f'{BASE_PATH}/logs/db_queue.log'

BATCH_SIZE = 10  # 작은 배치
SLEEP_SECONDS = 1  # 서버 부하 방지


def log(message):
    """로그 기록"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


class JobQueueDB:
    """SQLite 기반 작업 큐 DB"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 작업 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                market TEXT NOT NULL,
                sector TEXT DEFAULT '기타',
                status TEXT DEFAULT 'pending',
                -- pending, processing, completed, failed
                result_json TEXT,
                error_msg TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code ON jobs(code)')
        
        conn.commit()
        conn.close()
        log("✅ DB initialized")
    
    def insert_stocks(self, stocks: List[Dict]):
        """종목 리스트 삽입"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for stock in stocks:
            cursor.execute('''
                INSERT OR IGNORE INTO jobs 
                (code, name, symbol, market, sector, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (
                stock['code'],
                stock['name'],
                stock['symbol'],
                stock['market'],
                stock.get('sector', '기타')
            ))
        
        conn.commit()
        conn.close()
        log(f"✅ Inserted {len(stocks)} stocks")
    
    def get_next_job(self) -> Optional[Dict]:
        """다음 작업 가져오기"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # pending 상태인 작업 하나 가져오기
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
        ''', (error[:500], job_id))  # 오류 메시지 길이 제한
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        """작업 통계"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) FROM jobs GROUP BY status
        ''')
        
        stats = {
            'total': 0,
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0
        }
        
        for row in cursor.fetchall():
            status, count = row
            stats[status] = count
            stats['total'] += count
        
        conn.close()
        return stats
    
    def get_pending_count(self) -> int:
        """남은 작업 수"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM jobs WHERE status = 'pending'')
        count = cursor.fetchone()[0]
        conn.close()
        return count


def analyze_stock(stock: Dict) -> tuple:
    """단일 종목 분석"""
    symbol = stock['symbol']
    name = stock['name']
    
    result = {
        'symbol': symbol,
        'name': name,
        'market': stock.get('market', 'KOSPI'),
        'sector': stock.get('sector', 'Unknown'),
        'date': datetime.now().isoformat(),
        'agents': {},
        'status': 'pending'
    }
    
    try:
        # 지연 로딩으로 메모리 효율
        from technical_agent import TechnicalAnalysisAgent
        from quant_agent import QuantAnalysisAgent
        from qualitative_agent import QualitativeAnalysisAgent
        from news_agent import NewsSentimentAgent
        
        agents = [
            ('TECH', TechnicalAnalysisAgent),
            ('QUANT', QuantAnalysisAgent),
            ('QUAL', QualitativeAnalysisAgent),
            ('NEWS', NewsSentimentAgent)
        ]
        
        for agent_name, agent_class in agents:
            try:
                agent = agent_class(symbol, name)
                r = agent.analyze()
                result['agents'][agent_name] = {
                    'score': r.get('total_score', 0),
                    'rec': r.get('recommendation', 'HOLD')
                }
            except Exception as e:
                result['agents'][agent_name] = {'score': 0, 'rec': 'HOLD'}
        
        # 종합 점수
        scores = [a['score'] for a in result['agents'].values()]
        result['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        
        recs = [a['rec'] for a in result['agents'].values()]
        buy_count = recs.count('BUY')
        result['consensus'] = 'BUY' if buy_count >= 2 else 'HOLD'
        result['status'] = 'success'
        
        return result, True, None
        
    except Exception as e:
        result['status'] = 'error'
        return result, False, str(e)


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
    log("🚀 KStock Level 1 DB Queue Manager")
    log("=" * 70)
    log(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"PID: {os.getpid()}")
    log("=" * 70)
    
    # DB 초기화
    db = JobQueueDB(DB_FILE)
    
    # 종목 리스트 확인 및 삽입 (처음 한 번만)
    stats = db.get_stats()
    if stats['total'] == 0:
        log("📂 Loading stock lists...")
        
        with open(f'{BASE_PATH}/data/kospi_stocks.json', 'r') as f:
            kospi = json.load(f)['stocks']
        
        with open(f'{BASE_PATH}/data/kosdaq_stocks.json', 'r') as f:
            kosdaq = json.load(f)['stocks']
        
        # 심볼 및 마켓 정보 추가
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
    send_telegram(f"🚀 DB Queue 시작\n총 {db.get_stats()['total']}개 종목")
    
    start_time = time.time()
    processed = 0
    last_notification = 0
    
    # 메인 루프 - 하나씩 처리
    while True:
        try:
            # 다음 작업 가져오기
            job = db.get_next_job()
            
            if job is None:
                # 모든 작업 완료
                log("\n✅ All jobs completed!")
                break
            
            # 작업 시작 표시
            db.mark_processing(job['id'])
            
            # 로그
            processed += 1
            log(f"\n[{processed}] {job['name']} ({job['code']})")
            
            # 분석 실행
            result, success, error = analyze_stock(job)
            
            if success:
                db.mark_completed(job['id'], result)
                log(f"   ✅ {result['avg_score']:.1f}pts - {result['consensus']}")
            else:
                db.mark_failed(job['id'], error or 'Unknown error')
                log(f"   ❌ Failed: {error[:50] if error else 'Unknown'}")
            
            # 메모리 정리
            gc.collect()
            
            # 100개마다 알림
            if processed % 100 == 0:
                elapsed = time.time() - start_time
                stats = db.get_stats()
                pct = (stats['completed'] / stats['total']) * 100
                
                log(f"\n📊 Progress: {stats['completed']}/{stats['total']} ({pct:.1f}%)")
                send_telegram(
                    f"📊 진행: {stats['completed']}/{stats['total']} ({pct:.1f}%)\n"
                    f"⏱️ {elapsed//60}분 경과\n"
                    f"✅ 성공: {stats['completed']} | ❌ 실패: {stats['failed']}"
                )
            
            # 대기
            time.sleep(SLEEP_SECONDS)
            
        except KeyboardInterrupt:
            log("\n⚠️ Interrupted by user")
            break
        except Exception as e:
            log(f"\n❌ Loop error: {e}")
            log(traceback.format_exc())
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
    
    # 결과 날짜별 파일로 저장
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = f'{BASE_PATH}/data/level1_daily/level1_dbqueue_{date_str}.json'
    
    # DB에서 결과 추출
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT result_json FROM jobs WHERE status = 'completed'')
    results = [json.loads(row[0]) for row in cursor.fetchall() if row[0]]
    conn.close()
    
    final = {
        'date': datetime.now().isoformat(),
        'total': stats['total'],
        'completed': stats['completed'],
        'failed': stats['failed'],
        'elapsed_minutes': elapsed / 60,
        'results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    
    log(f"Output: {output_file}")
    
    # 완료 알림
    send_telegram(
        f"🎉 완료!\n"
        f"✅ {stats['completed']}/{stats['total']} 성공\n"
        f"⏱️ {elapsed//60}분 소요"
    )
    
    # Level 2/3 자동 실행
    log("\n🌍 Starting Level 2/3...")
    try:
        import subprocess
        subprocess.run(['python3', f'{BASE_PATH}/agents/sector_agent.py'], 
                      cwd=BASE_PATH, timeout=600)
        subprocess.run(['python3', f'{BASE_PATH}/agents/macro_agent.py'],
                      cwd=BASE_PATH, timeout=600)
        subprocess.run(['python3', f'{BASE_PATH}/agents/pm_agent.py'],
                      cwd=BASE_PATH, timeout=1200)
        send_telegram("✅ Level 1/2/3 전체 완료!")
    except Exception as e:
        log(f"❌ Level 2/3 Error: {e}")


if __name__ == '__main__':
    import traceback
    try:
        main()
    except Exception as e:
        log(f"\n❌ Fatal error: {e}")
        log(traceback.format_exc())
