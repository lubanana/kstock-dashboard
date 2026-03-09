#!/usr/bin/env python3
"""
KStock Level 1 Hybrid Analyzer
추천 조합: FinanceDataReader + PyKRX + 마스터 파일

Data Sources:
- 종목 리스트: 마스터 파일 (JSON)
- 개별 주가: FinanceDataReader
- 한국 인덱스: PyKRX
- 재무 데이터: PyKRX
"""

import json
import os
import sys
import time
import gc
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

import FinanceDataReader as fdr
from pykrx import stock

BASE_PATH = '/home/programs/kstock_analyzer'
DB_FILE = f'{BASE_PATH}/data/job_queue_hybrid.db'
LOG_FILE = f'{BASE_PATH}/logs/hybrid_analyzer.log'

# 설정
SLEEP_SECONDS = 0.3
BATCH_SIZE = 25


def log(message):
    """로그 기록"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


class HybridDataFetcher:
    """하이브리드 데이터 수집기"""
    
    @staticmethod
    def get_price_data_fdr(code: str, days: int = 60) -> Optional[Dict]:
        """FinanceDataReader로 주가 데이터 수집"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            df = fdr.DataReader(code, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            if df is None or len(df) < 5:
                return None
            
            latest = df.iloc[-1]
            
            # 이동평균 계산
            ma5 = df['Close'].rolling(5).mean().iloc[-1] if len(df) >= 5 else latest['Close']
            ma20 = df['Close'].rolling(20).mean().iloc[-1] if len(df) >= 20 else ma5
            
            # 거래량 평균
            volume_avg = df['Volume'].rolling(20).mean().iloc[-1]
            volume_ratio = latest['Volume'] / volume_avg if volume_avg > 0 else 1
            
            return {
                'open': latest['Open'],
                'high': latest['High'],
                'low': latest['Low'],
                'close': latest['Close'],
                'volume': latest['Volume'],
                'change_pct': latest['Change'] * 100 if 'Change' in df.columns else 0,
                'ma5': ma5,
                'ma20': ma20,
                'volume_ratio': volume_ratio,
                'data': df
            }
        except Exception as e:
            log(f"   ⚠️ FDR error for {code}: {str(e)[:40]}")
            return None
    
    @staticmethod
    def get_index_data_pykrx(index_code: str = "1001") -> Optional[Dict]:
        """PyKRX로 KOSPI 지수 데이터 수집"""
        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            df = stock.get_index_ohlcv(start_date, end_date, index_code)
            
            if df is None or len(df) == 0:
                return None
            
            latest = df.iloc[-1]
            return {
                'close': latest['종가'],
                'change_pct': latest['등락률'],
                'volume': latest['거래량']
            }
        except Exception as e:
            log(f"   ⚠️ PyKRX index error: {str(e)[:40]}")
            return None
    
    @staticmethod
    def get_fundamental_pykrx(code: str) -> Optional[Dict]:
        """PyKRX로 재무 데이터 수집"""
        try:
            # PER, PBR 등
            date = datetime.now().strftime('%Y%m%d')
            df = stock.get_market_fundamental(date, date, code)
            
            if df is None or len(df) == 0:
                return None
            
            latest = df.iloc[-1]
            return {
                'per': latest.get('PER', 0),
                'pbr': latest.get('PBR', 0),
                'dividend_yield': latest.get('DIV', 0),
                'bps': latest.get('BPS', 0)
            }
        except Exception as e:
            log(f"   ⚠️ PyKRX fundamental error for {code}: {str(e)[:40]}")
            return None


class JobQueueDB:
    """SQLite 기반 작업 큐"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """DB 초기화"""
        import sqlite3
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
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for s in stocks:
            cursor.execute('''
                INSERT OR IGNORE INTO jobs 
                (code, name, symbol, market, sector, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (s['code'], s['name'], s['symbol'], s['market'], s.get('sector', '기타')))
        
        conn.commit()
        conn.close()
        log(f"✅ Inserted {len(stocks)} stocks")
    
    def get_next_job(self) -> Optional[Dict]:
        """다음 작업 가져오기"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, code, name, symbol, market, sector 
            FROM jobs WHERE status = 'pending' 
            ORDER BY id LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {'id': row[0], 'code': row[1], 'name': row[2], 
                   'symbol': row[3], 'market': row[4], 'sector': row[5]}
        return None
    
    def mark_processing(self, job_id: int):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE jobs SET status = 'processing' WHERE id = ?', (job_id,))
        conn.commit()
        conn.close()
    
    def mark_completed(self, job_id: int, result: Dict):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs SET status = 'completed', result_json = ?, processed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (json.dumps(result, ensure_ascii=False), job_id))
        conn.commit()
        conn.close()
    
    def mark_failed(self, job_id: int, error: str):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE jobs SET status = 'failed', error_msg = ?, retry_count = retry_count + 1,
            processed_at = CURRENT_TIMESTAMP WHERE id = ?
        ''', (error[:500], job_id))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')
        stats = {'total': 0, 'pending': 0, 'processing': 0, 'completed': 0, 'failed': 0}
        for row in cursor.fetchall():
            stats[row[0]] = row[1]
            stats['total'] += row[1]
        conn.close()
        return stats


def analyze_stock_hybrid(stock_info: Dict) -> Tuple[Dict, bool]:
    """하이브리드 방식 종목 분석"""
    code = stock_info['code']
    name = stock_info['name']
    
    result = {
        'symbol': stock_info['symbol'],
        'name': name,
        'market': stock_info.get('market', 'KOSPI'),
        'sector': stock_info.get('sector', 'Unknown'),
        'date': datetime.now().isoformat(),
        'data_source': 'hybrid(fdr+pykrx)',
        'agents': {},
        'status': 'pending'
    }
    
    try:
        fetcher = HybridDataFetcher()
        
        # 1. 주가 데이터 (FinanceDataReader)
        price_data = fetcher.get_price_data_fdr(code)
        if price_data is None:
            # FDR 실패 시 PyKRX 시도
            try:
                from pykrx import stock as pykrx_stock
                df = pykrx_stock.get_market_ohlcv(
                    (datetime.now() - timedelta(days=60)).strftime('%Y%m%d'),
                    datetime.now().strftime('%Y%m%d'), code
                )
                if df is not None and len(df) > 0:
                    latest = df.iloc[-1]
                    price_data = {
                        'close': latest['종가'],
                        'ma5': df['종가'].rolling(5).mean().iloc[-1],
                        'ma20': df['종가'].rolling(20).mean().iloc[-1],
                        'volume_ratio': 1.0,
                        'change_pct': latest['등락률']
                    }
            except:
                pass
        
        if price_data is None:
            result['status'] = 'error'
            result['error'] = 'No price data'
            return result, False
        
        # 2. 기술적 분석 점수
        tech_score = 0
        if price_data['close'] > price_data['ma5']:
            tech_score += 20
        if price_data['close'] > price_data['ma20']:
            tech_score += 20
        if price_data['ma5'] > price_data['ma20']:
            tech_score += 15
        
        # 거래량 점수
        vol_score = min(25, max(0, (price_data['volume_ratio'] - 0.5) * 25))
        
        # 등락률 점수
        change = price_data['change_pct']
        change_score = 25 if -5 <= change <= 5 else max(0, 25 - abs(change) * 2)
        
        tech_total = tech_score + vol_score + change_score
        
        # 3. 재무 데이터 (PyKRX)
        fund_data = fetcher.get_fundamental_pykrx(code)
        fund_score = 50  # 기본값
        
        if fund_data:
            # PER 기반 점수
            per = fund_data.get('per', 15)
            if 5 <= per <= 15:
                fund_score = 70
            elif per < 5:
                fund_score = 60
            elif per > 30:
                fund_score = 30
            else:
                fund_score = 50
            
            result['fundamental'] = fund_data
        
        # 4. 시장 지수 (PyKRX)
        market_data = fetcher.get_index_data_pykrx("1001" if stock_info.get('market') == 'KOSPI' else "2001")
        market_score = 50
        if market_data:
            market_change = market_data.get('change_pct', 0)
            market_score = 60 if market_change > 0 else 40
        
        # 5. 종합 점수
        result['agents'] = {
            'TECH': {'score': tech_total, 'rec': 'BUY' if tech_total >= 60 else 'HOLD' if tech_total >= 40 else 'SELL'},
            'QUANT': {'score': fund_score, 'rec': 'BUY' if fund_score >= 60 else 'HOLD' if fund_score >= 40 else 'SELL'},
            'QUAL': {'score': market_score, 'rec': 'BUY' if market_score >= 55 else 'HOLD'},
            'NEWS': {'score': 50, 'rec': 'HOLD'}
        }
        
        scores = [a['score'] for a in result['agents'].values()]
        result['avg_score'] = round(sum(scores) / len(scores), 1)
        result['consensus'] = 'BUY' if result['avg_score'] >= 60 else 'HOLD' if result['avg_score'] >= 40 else 'SELL'
        result['status'] = 'success'
        result['price_data'] = {
            'current': price_data['close'],
            'change_pct': price_data['change_pct'],
            'ma5': price_data['ma5'],
            'ma20': price_data['ma20']
        }
        
        return result, True
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        return result, False


def send_telegram(message: str):
    try:
        import subprocess
        subprocess.run(['openclaw', 'message', 'send', '--channel', 'telegram', 
                       '--to', '32083875', message], capture_output=True, timeout=10)
    except:
        pass


def main():
    log("=" * 70)
    log("🚀 KStock Level 1 Hybrid Analyzer")
    log("Data Sources: FinanceDataReader + PyKRX + Master Files")
    log("=" * 70)
    log(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = JobQueueDB(DB_FILE)
    
    stats = db.get_stats()
    if stats['total'] == 0:
        log("📂 Loading stock lists from master files...")
        
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
        
        db.insert_stocks(kospi + kosdaq)
    
    send_telegram(f"🚀 Hybrid 분석 시작\n총 {db.get_stats()['total']}개 종목")
    
    start_time = time.time()
    processed = 0
    
    while True:
        try:
            job = db.get_next_job()
            if job is None:
                log("\n✅ All jobs completed!")
                break
            
            db.mark_processing(job['id'])
            processed += 1
            
            if processed % 10 == 1:  # 10개마다 로그
                log(f"\n[{processed}] {job['name']} ({job['code']})")
            
            result, success = analyze_stock_hybrid(job)
            
            if success:
                db.mark_completed(job['id'], result)
                if processed % 10 == 1:
                    log(f"   ✅ {result['avg_score']:.1f}pts")
            else:
                db.mark_failed(job['id'], result.get('error', 'Unknown'))
                log(f"   ❌ Failed: {result.get('error', 'Unknown')[:40]}")
            
            gc.collect()
            
            # 100개마다 알림
            if processed % 100 == 0:
                elapsed = time.time() - start_time
                stats = db.get_stats()
                pct = (stats['completed'] / stats['total']) * 100
                log(f"\n📊 Progress: {stats['completed']}/{stats['total']} ({pct:.1f}%)")
                send_telegram(f"📊 진행: {stats['completed']}/{stats['total']} ({pct:.1f}%)\n⏱️ {elapsed//60}분 경과")
            
            time.sleep(SLEEP_SECONDS)
            
        except KeyboardInterrupt:
            log("\n⚠️ Interrupted")
            break
        except Exception as e:
            log(f"\n❌ Loop error: {e}")
            time.sleep(5)
    
    # 완료
    elapsed = time.time() - start_time
    stats = db.get_stats()
    
    log("\n" + "=" * 70)
    log("✅ ANALYSIS COMPLETE")
    log(f"Total: {stats['total']}, Completed: {stats['completed']}, Failed: {stats['failed']}")
    log(f"Elapsed: {elapsed//3600}h {(elapsed%3600)//60}m")
    
    # 결과 저장
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT result_json FROM jobs WHERE status = 'completed'")
    results = [json.loads(row[0]) for row in cursor.fetchall() if row[0]]
    conn.close()
    
    output_file = f'{BASE_PATH}/data/level1_daily/level1_hybrid_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': datetime.now().isoformat(),
            'data_source': 'hybrid',
            'total': stats['total'],
            'completed': stats['completed'],
            'failed': stats['failed'],
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    log(f"Output: {output_file}")
    send_telegram(f"🎉 완료! {stats['completed']}/{stats['total']}")


if __name__ == '__main__':
    import traceback
    try:
        main()
    except Exception as e:
        log(f"\n❌ Fatal error: {e}")
        log(traceback.format_exc())
