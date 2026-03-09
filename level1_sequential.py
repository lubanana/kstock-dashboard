#!/usr/bin/env python3
"""
KStock Level 1 Sequential Analyzer
순차 처리 방식 (한 종목씩) - 안정성 우선

Features:
- 한 종목씩 순차 처리
- 각 종목 완료 후 즉시 체크포인트 저장
- 메모리 사용 최소화
- 오류 발생 시에도 계속 진행
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from technical_agent import TechnicalAnalysisAgent
from quant_agent import QuantAnalysisAgent
from qualitative_agent import QualitativeAnalysisAgent
from news_agent import NewsSentimentAgent

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/data/level1_daily'
CHECKPOINT_FILE = f'{BASE_PATH}/data/sequential_checkpoint.json'
LOG_FILE = f'{BASE_PATH}/logs/sequential.log'


def log(message):
    """로그 출력 및 저장"""
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
    
    # 심볼 및 마켓 정보 추가
    for s in kospi:
        s['symbol'] = f"{s['code']}.KS"
        s['market'] = 'KOSPI'
    
    for s in kosdaq:
        s['symbol'] = f"{s['code']}.KQ"
        s['market'] = 'KOSDAQ'
    
    all_stocks = kospi + kosdaq
    log(f"   ✅ Total: {len(all_stocks)} stocks (KOSPI: {len(kospi)}, KOSDAQ: {len(kosdaq)})")
    
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


def analyze_stock(stock):
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
        # 4개 에이전트 순차 분석
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
                log(f"      ⚠️  {agent_name} error: {e}")
                result['agents'][agent_name] = {'score': 0, 'rec': 'HOLD'}
        
        # 종합 점수
        scores = [a['score'] for a in result['agents'].values()]
        result['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        
        recs = [a['rec'] for a in result['agents'].values()]
        buy_count = recs.count('BUY')
        result['consensus'] = 'BUY' if buy_count >= 2 else 'HOLD'
        result['status'] = 'success'
        
        return result, True
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
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
        ], capture_output=True, timeout=30)
    except:
        pass


def main():
    """메인 실행"""
    log("=" * 70)
    log("🚀 KStock Level 1 Sequential Analyzer")
    log("=" * 70)
    log(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    log(f"   Previously failed: {len(failed)}")
    
    start_time = time.time()
    last_notification = start_idx
    
    # 순차 처리
    for i in range(start_idx, total):
        stock = stocks[i]
        log(f"\n[{i+1}/{total}] {stock['name']} ({stock['code']})")
        
        try:
            result, success = analyze_stock(stock)
            
            if success:
                results.append(result)
                log(f"   ✅ {result['avg_score']:.1f}pts - {result['consensus']}")
            else:
                failed.append({'code': stock['code'], 'name': stock['name'], 'error': result.get('error')})
                log(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
            
            # 즉시 체크포인트 저장
            save_checkpoint(i + 1, results, failed)
            
            # 100개마다 알림
            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                pct = (i + 1) / total * 100
                avg_time = elapsed / (i + 1 - start_idx)
                remaining = avg_time * (total - i - 1)
                
                log(f"\n📊 Progress: {i+1}/{total} ({pct:.1f}%)")
                log(f"   Elapsed: {elapsed//60}m {elapsed%60:.0f}s")
                log(f"   ETA: {remaining//60}m remaining")
                
                send_telegram(f"📊 진행: {i+1}/{total} ({pct:.1f}%)\n⏱️ {elapsed//60}분 경과\n⏰ {remaining//60}분 남음")
            
            # 서버 부하 방지 (1초 대기)
            time.sleep(1)
            
        except Exception as e:
            log(f"   ❌ Critical error: {e}")
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
    output_file = f"{OUTPUT_PATH}/level1_sequential_{date_str}.json"
    
    final = {
        'date': datetime.now().isoformat(),
        'data_source': 'KOSPI+KOSDAQ Sequential',
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
    
    # 완료 알림
    send_telegram(f"🎉 Level 1 완료!\n✅ {len(results)}/{total} 성공\n⏱️ {elapsed//60}분 소요")
    
    # 체크포인트 삭제
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️ Interrupted by user")
        log("Checkpoint saved. Resume anytime.")
    except Exception as e:
        log(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
