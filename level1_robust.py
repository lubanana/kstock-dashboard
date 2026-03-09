#!/usr/bin/env python3
"""
KStock Level 1 Robust Analyzer
안정성 강화 버전

개선사항:
- 메모리 누수 방지 (주기적 GC)
- 예외 처리 강화
- 타임아웃 설정
- 세션 재사용 최소화
- 상세 로깅
"""

import json
import os
import sys
import time
import gc
import traceback
from datetime import datetime

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/data/level1_daily'
CHECKPOINT_FILE = f'{BASE_PATH}/data/robust_checkpoint.json'
LOG_FILE = f'{BASE_PATH}/logs/robust.log'

# 설정
BATCH_SIZE = 20  # 더 작은 배치
GC_INTERVAL = 10  # 10개마다 가비지 컬렉션
TIMEOUT_SECONDS = 30  # 종목당 타임아웃


def log(message):
    """로그 기록"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


def load_stock_lists():
    """종목 리스트 로드"""
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
    log(f"   ✅ Total: {len(all_stocks)} stocks")
    return all_stocks


def load_checkpoint():
    """체크포인트 로드"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {'completed': 0, 'results': [], 'failed': []}


def save_checkpoint(completed, results, failed):
    """체크포인트 저장"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({
            'completed': completed,
            'results': results,
            'failed': failed,
            'last_update': datetime.now().isoformat()
        }, f)


def analyze_with_timeout(agent_class, symbol, name, timeout=30):
    """타임아웃 설정된 분석"""
    import signal
    
    class TimeoutError(Exception):
        pass
    
    def handler(signum, frame):
        raise TimeoutError()
    
    # 타임아웃 설정
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)
    
    try:
        agent = agent_class(symbol, name)
        result = agent.analyze()
        signal.alarm(0)  # 타임아웃 해제
        return result, True
    except TimeoutError:
        log(f"      ⏱️ Timeout after {timeout}s")
        return {'total_score': 0, 'recommendation': 'HOLD'}, False
    except Exception as e:
        log(f"      ❌ Error: {str(e)[:50]}")
        return {'total_score': 0, 'recommendation': 'HOLD'}, False
    finally:
        signal.alarm(0)


def analyze_stock_safe(stock):
    """안전한 단일 종목 분석"""
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
        # 지연 로딩
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
        
        success_count = 0
        for agent_name, agent_class in agents:
            try:
                r, success = analyze_with_timeout(agent_class, symbol, name, TIMEOUT_SECONDS)
                result['agents'][agent_name] = {
                    'score': r.get('total_score', 0),
                    'rec': r.get('recommendation', 'HOLD')
                }
                if success:
                    success_count += 1
            except Exception as e:
                log(f"      ⚠️ {agent_name}: {str(e)[:30]}")
                result['agents'][agent_name] = {'score': 0, 'rec': 'HOLD'}
        
        # 종합 점수
        scores = [a['score'] for a in result['agents'].values()]
        result['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        
        recs = [a['rec'] for a in result['agents'].values()]
        buy_count = recs.count('BUY')
        result['consensus'] = 'BUY' if buy_count >= 2 else 'HOLD'
        result['status'] = 'success' if success_count >= 2 else 'partial'
        
        return result, True
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        log(f"   ❌ Critical error: {str(e)[:50]}")
        return result, False


def send_telegram(message):
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
    log("🚀 KStock Level 1 Robust Analyzer")
    log("=" * 70)
    log(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"PID: {os.getpid()}")
    log("=" * 70)
    
    # 종목 로드
    stocks = load_stock_lists()
    total = len(stocks)
    
    # 체크포인트 확인
    checkpoint = load_checkpoint()
    start_idx = checkpoint['completed']
    results = checkpoint['results']
    failed = checkpoint['failed']
    
    log(f"\n📊 Starting from: {start_idx}/{total}")
    log(f"   Already completed: {len(results)}")
    
    start_time = time.time()
    batch_start = start_idx
    
    # 순차 처리
    for i in range(start_idx, total):
        stock = stocks[i]
        log(f"\n[{i+1}/{total}] {stock['name']}")
        
        try:
            result, success = analyze_stock_safe(stock)
            
            if success:
                results.append(result)
                log(f"   ✅ {result['avg_score']:.1f}pts - {result['consensus']}")
            else:
                failed.append({'code': stock['code'], 'name': stock['name']})
                log(f"   ⚠️ Partial success")
            
            # 즉시 저장
            save_checkpoint(i + 1, results, failed)
            
            # 배치 완료 확인
            if (i + 1 - batch_start) >= BATCH_SIZE:
                elapsed = time.time() - start_time
                pct = (i + 1) / total * 100
                log(f"\n📦 Batch complete: {i+1} stocks ({pct:.1f}%)")
                log(f"   Elapsed: {elapsed//60}m")
                
                # 가비지 컬렉션
                gc.collect()
                log("   🧹 Garbage collected")
                
                batch_start = i + 1
            
            # 100개마다 알림
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                pct = (i + 1) / total * 100
                send_telegram(f"📊 진행: {i+1}/{total} ({pct:.1f}%)\n⏱️ {elapsed//60}분 경과")
            
            # 메모리 정리
            if (i + 1) % GC_INTERVAL == 0:
                gc.collect()
            
            # 대기 (서버 부하 방지)
            time.sleep(0.5)
            
        except Exception as e:
            log(f"   ❌ Critical error: {e}")
            log(traceback.format_exc())
            failed.append({'code': stock['code'], 'name': stock['name'], 'error': str(e)})
            save_checkpoint(i + 1, results, failed)
            time.sleep(2)
    
    # 완료
    elapsed = time.time() - start_time
    log("\n" + "=" * 70)
    log("✅ ANALYSIS COMPLETE")
    log("=" * 70)
    log(f"Total: {total}")
    log(f"Success: {len(results)}")
    log(f"Failed: {len(failed)}")
    log(f"Elapsed: {elapsed//3600}h {(elapsed%3600)//60}m")
    
    # 결과 저장
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = f"{OUTPUT_PATH}/level1_robust_{date_str}.json"
    
    final = {
        'date': datetime.now().isoformat(),
        'total': total,
        'success': len(results),
        'failed': len(failed),
        'elapsed_minutes': elapsed / 60,
        'results': results,
        'failed_stocks': failed
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    
    log(f"Output: {output_file}")
    send_telegram(f"🎉 완료! {len(results)}/{total} 성공\n⏱️ {elapsed//60}분 소요")
    
    # 체크포인트 삭제
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️ Interrupted by user")
        log("Checkpoint saved.")
    except Exception as e:
        log(f"\n❌ Fatal error: {e}")
        log(traceback.format_exc())
