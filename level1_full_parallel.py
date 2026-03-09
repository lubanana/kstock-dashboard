#!/usr/bin/env python3
"""
KStock Level 1 Full Market Analyzer with Progress Tracking
전체 종목 분석 + 진행 상황 10% 단위 알림

Features:
- 진행률 10%마다 Telegram 알림
- 병렬 처리 (ProcessPoolExecutor)
- 진행 상황 실시간 저장
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Value
import ctypes

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from technical_agent import TechnicalAnalysisAgent
from quant_agent import QuantAnalysisAgent
from qualitative_agent import QualitativeAnalysisAgent
from news_agent import NewsSentimentAgent

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/data/level1_daily'
PROGRESS_FILE = f'{BASE_PATH}/data/progress.json'
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '32083875')

# 전역 변수로 진행률 공유
manager = Manager()
completed_count = manager.Value('i', 0)
total_count = manager.Value('i', 0)


def send_telegram_progress(percent: int, current: int, total: int, elapsed: float):
    """진행률 Telegram 알림 발송"""
    try:
        # 남은 시간 예상
        if current > 0:
            avg_time = elapsed / current
            remaining = avg_time * (total - current)
            eta_str = f"{remaining//60:.0f}분 {remaining%60:.0f}초"
        else:
            eta_str = "계산중..."
        
        message = f"""📊 KStock Level 1 분석 진행 상황

━━━━━━━━━━━━━━━━━━━━
█{'█' * (percent//10)}{'░' * (10 - percent//10)} {percent}%
━━━━━━━━━━━━━━━━━━━━

📈 진행: {current}/{total} 종목
⏱️ 경과: {elapsed//60:.0f}분 {elapsed%60:.0f}초
⏰ 예상 남은 시간: {eta_str}

🕐 업데이트: {datetime.now().strftime('%H:%M:%S')}"""

        subprocess.run([
            'openclaw', 'message', 'send',
            '--channel', 'telegram',
            '--to', TELEGRAM_CHAT_ID,
            message
        ], capture_output=True, timeout=30)
        
    except Exception as e:
        print(f"Telegram error: {e}")


def analyze_single_stock(stock: Dict, progress_counter) -> Dict:
    """
    단일 종목 분석 (병렬 처리용)
    """
    symbol = stock['symbol']
    name = stock['name']
    market = stock.get('market', 'KOSPI')
    
    result = {
        'symbol': symbol,
        'name': name,
        'market': market,
        'sector': stock.get('sector', 'Unknown'),
        'date': datetime.now().isoformat(),
        'agents': {},
        'status': 'pending'
    }
    
    try:
        # 4개 에이전트 병렬 분석
        agents = {
            'TECH': TechnicalAnalysisAgent(symbol, name),
            'QUANT': QuantAnalysisAgent(symbol, name),
            'QUAL': QualitativeAnalysisAgent(symbol, name),
            'NEWS': NewsSentimentAgent(symbol, name)
        }
        
        for agent_name, agent in agents.items():
            try:
                r = agent.analyze()
                result['agents'][agent_name] = {
                    'score': r.get('total_score', 0),
                    'rec': r.get('recommendation', 'HOLD')
                }
            except Exception as e:
                result['agents'][agent_name] = {'score': 0, 'rec': 'HOLD'}
        
        # 종합 점수 계산
        scores = [a['score'] for a in result['agents'].values()]
        result['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        
        # 컨센서스
        recs = [a['rec'] for a in result['agents'].values()]
        buy_count = recs.count('BUY')
        result['consensus'] = 'BUY' if buy_count >= 2 else 'HOLD'
        result['status'] = 'success'
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    # 진행 카운트 증가
    with progress_counter.get_lock():
        progress_counter.value += 1
    
    return result


def run_full_analysis_parallel(max_workers: int = 4):
    """
    전체 종목 병렬 분석 실행
    """
    global completed_count, total_count
    
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    # 종목 로드
    print("📂 Loading stock lists...")
    
    kospi_file = f'{BASE_PATH}/data/kospi_stocks.json'
    kosdaq_file = f'{BASE_PATH}/data/kosdaq_stocks.json'
    
    with open(kospi_file, 'r') as f:
        kospi_stocks = json.load(f)['stocks']
    
    with open(kosdaq_file, 'r') as f:
        kosdaq_stocks = json.load(f)['stocks']
    
    # 모든 종목 준비
    all_stocks = []
    for s in kospi_stocks:
        s['symbol'] = f"{s['code']}.KS"
        s['market'] = 'KOSPI'
        s['sector'] = s.get('sector', '기타')
        all_stocks.append(s)
    
    for s in kosdaq_stocks:
        s['symbol'] = f"{s['code']}.KQ"
        s['market'] = 'KOSDAQ'
        s['sector'] = s.get('sector', '기타')
        all_stocks.append(s)
    
    total = len(all_stocks)
    total_count.value = total
    completed_count.value = 0
    
    print(f"\n🚀 Starting parallel analysis of {total} stocks")
    print(f"   Workers: {max_workers}")
    print(f"   Estimated time: {total * 15 / max_workers / 60:.1f} minutes")
    print("=" * 70)
    
    start_time = time.time()
    last_percent = 0
    results = []
    
    # 병렬 처리
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 작업 제출
        futures = {
            executor.submit(analyze_single_stock, stock, completed_count): stock
            for stock in all_stocks
        }
        
        # 결과 수집 및 진행 상황 체크
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            
            current = completed_count.value
            percent = int((current / total) * 100)
            elapsed = time.time() - start_time
            
            # 10% 단위 알림
            if percent >= last_percent + 10:
                last_percent = (percent // 10) * 10
                send_telegram_progress(last_percent, current, total, elapsed)
                print(f"📊 Progress: {last_percent}% ({current}/{total})")
    
    # 최종 알림
    elapsed = time.time() - start_time
    send_telegram_progress(100, total, total, elapsed)
    
    # 결과 저장
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = f"{OUTPUT_PATH}/level1_fullmarket_{date_str}.json"
    
    final = {
        'date': datetime.now().isoformat(),
        'data_source': 'KOSPI+KOSDAQ Master Files',
        'total': total,
        'success': len([r for r in results if r.get('status') == 'success']),
        'kospi_count': len(kospi_stocks),
        'kosdaq_count': len(kosdaq_stocks),
        'results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    
    # 최종 요약
    print("\n" + "=" * 70)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"   Total: {total} | Success: {final['success']}")
    print(f"   Elapsed: {elapsed//60:.0f}분 {elapsed%60:.0f}초")
    print(f"   Output: {output_file}")
    
    return final


def main():
    """메인 실행"""
    print("=" * 70)
    print("🚀 KStock Level 1 Full Market Parallel Analyzer")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 병렬 처리 워커 수 (CPU 코어 수 기준)
    import multiprocessing
    max_workers = min(multiprocessing.cpu_count(), 8)
    
    print(f"CPU cores: {multiprocessing.cpu_count()}")
    print(f"Workers: {max_workers}")
    print("=" * 70 + "\n")
    
    try:
        result = run_full_analysis_parallel(max_workers=max_workers)
        print("\n🎉 All done!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
