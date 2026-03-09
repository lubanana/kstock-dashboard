#!/usr/bin/env python3
"""
KStock Level 1 Batch Analyzer with Progress Tracking
배치 처리 + 진행 상황 Telegram 알림 + 자동 Level 2/3 연계

Features:
- 100개 단위 배치 처리
- 배치 완료 시 Telegram 알림
- 체크포인트 저장 (중단 시 복구)
- 완료 후 자동 Level 2/3 실행
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from technical_agent import TechnicalAnalysisAgent
from quant_agent import QuantAnalysisAgent  
from qualitative_agent import QualitativeAnalysisAgent
from news_agent import NewsSentimentAgent

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/data/level1_daily'
CHECKPOINT_FILE = f'{BASE_PATH}/data/batch_checkpoint.json'
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '32083875')
BATCH_SIZE = 100  # 배치 크기


def send_telegram(message: str):
    """Telegram 메시지 발송"""
    try:
        subprocess.run([
            'openclaw', 'message', 'send',
            '--channel', 'telegram',
            '--to', TELEGRAM_CHAT_ID,
            message
        ], capture_output=True, timeout=30)
    except Exception as e:
        print(f"Telegram error: {e}")


def load_stock_lists():
    """KOSPI/KOSDAQ 종목 로드"""
    print("📂 Loading stock lists...")
    
    with open(f'{BASE_PATH}/data/kospi_stocks.json', 'r') as f:
        kospi = json.load(f)['stocks']
    
    with open(f'{BASE_PATH}/data/kosdaq_stocks.json', 'r') as f:
        kosdaq = json.load(f)['stocks']
    
    # 심볼 및 마켓 정보 추가
    for s in kospi:
        s['symbol'] = f"{s['code']}.KS"
        s['market'] = 'KOSPI'
        s['sector'] = s.get('sector', '기타')
    
    for s in kosdaq:
        s['symbol'] = f"{s['code']}.KQ"
        s['market'] = 'KOSDAQ'
        s['sector'] = s.get('sector', '기타')
    
    all_stocks = kospi + kosdaq
    print(f"   ✅ Total: {len(all_stocks)} stocks (KOSPI: {len(kospi)}, KOSDAQ: {len(kosdaq)})")
    
    return all_stocks


def load_checkpoint():
    """체크포인트 로드"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {'completed': 0, 'results': []}


def save_checkpoint(completed: int, results: list):
    """체크포인트 저장"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'completed': completed, 'results': results}, f)


def analyze_stock(stock: Dict) -> Dict:
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
        
        scores = [a['score'] for a in result['agents'].values()]
        result['avg_score'] = round(sum(scores) / len(scores), 1) if scores else 0
        
        recs = [a['rec'] for a in result['agents'].values()]
        buy_count = recs.count('BUY')
        result['consensus'] = 'BUY' if buy_count >= 2 else 'HOLD'
        result['status'] = 'success'
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def run_batch_analysis():
    """배치 분석 실행"""
    print("=" * 70)
    print("🚀 KStock Level 1 Batch Analyzer")
    print("=" * 70)
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 종목 로드
    all_stocks = load_stock_lists()
    total = len(all_stocks)
    
    # 체크포인트 확인
    checkpoint = load_checkpoint()
    start_idx = checkpoint['completed']
    results = checkpoint['results']
    
    print(f"\n📊 Starting from: {start_idx}/{total}")
    print(f"   Already completed: {len(results)}")
    print(f"   Remaining: {total - start_idx}")
    
    start_time = time.time()
    
    # 배치 처리
    for batch_start in range(start_idx, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\n📦 Batch {batch_num}/{total_batches} ({batch_start+1}-{batch_end})")
        print("-" * 70)
        
        batch_start_time = time.time()
        batch_results = []
        
        for i, stock in enumerate(all_stocks[batch_start:batch_end], batch_start+1):
            print(f"   [{i}/{total}] {stock['name']}", end=' ', flush=True)
            result = analyze_stock(stock)
            batch_results.append(result)
            print(f"→ {result['avg_score']:.1f}pts ({result['status']})")
            time.sleep(0.3)  # 서버 부하 방지
        
        # 결과 누적
        results.extend(batch_results)
        completed = len(results)
        
        # 체크포인트 저장
        save_checkpoint(completed, results)
        
        # 배치 완료 알림
        batch_elapsed = time.time() - batch_start_time
        total_elapsed = time.time() - start_time
        progress_pct = (completed / total) * 100
        
        message = f"""📊 Level 1 배치 분석 진행 상황

📦 배치 {batch_num}/{total_batches} 완료
   └ 처리: {batch_start+1}-{batch_end} ({batch_end-batch_start}개)
   └ 소요: {batch_elapsed//60}분 {batch_elapsed%60:.0f}초

📈 전체 진행: {completed}/{total} ({progress_pct:.1f}%)
⏱️ 총 소요: {total_elapsed//60}분 {total_elapsed%60:.0f}초
⏰ 예상 남은: {(total_elapsed/completed)*(total-completed)//60}분

✅ 다음 배치: {batch_num+1 if batch_end < total else '완료'}
🕐 {datetime.now().strftime('%H:%M:%S')}"""

        send_telegram(message)
        print(f"\n✅ Batch {batch_num} complete! Progress: {progress_pct:.1f}%")
    
    # 최종 결과 저장
    date_str = datetime.now().strftime('%Y%m%d_%H%M')
    output_file = f"{OUTPUT_PATH}/level1_fullmarket_{date_str}.json"
    
    final = {
        'date': datetime.now().isoformat(),
        'data_source': 'KOSPI+KOSDAQ Master Files',
        'total': total,
        'success': len([r for r in results if r.get('status') == 'success']),
        'kospi_count': len([s for s in all_stocks if s['market'] == 'KOSPI']),
        'kosdaq_count': len([s for s in all_stocks if s['market'] == 'KOSDAQ']),
        'results': results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    
    total_elapsed = time.time() - start_time
    
    # 완료 알림
    message = f"""🎉 Level 1 분석 완료!

📊 결과 요약:
   • 총 종목: {total}
   • 성공: {final['success']}
   • KOSPI: {final['kospi_count']}
   • KOSDAQ: {final['kosdaq_count']}

⏱️ 총 소요: {total_elapsed//3600}시간 {(total_elapsed%3600)//60}분

🔄 Level 2/3 자동 실행 시작..."""

    send_telegram(message)
    
    print("\n" + "=" * 70)
    print("✅ Level 1 Complete!")
    print("=" * 70)
    print(f"Output: {output_file}")
    
    # 체크포인트 삭제
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    
    return output_file


def run_level2():
    """Level 2 실행"""
    print("\n🌍 Running Level 2 Analysis...")
    send_telegram("🌍 Level 2 분석 시작 (섹터/매크로)")
    
    try:
        # Sector Analysis
        subprocess.run(['python3', f'{BASE_PATH}/agents/sector_agent.py'], 
                      cwd=BASE_PATH, timeout=600)
        
        # Macro Analysis  
        subprocess.run(['python3', f'{BASE_PATH}/agents/macro_agent.py'],
                      cwd=BASE_PATH, timeout=600)
        
        send_telegram("✅ Level 2 분석 완료")
        return True
    except Exception as e:
        send_telegram(f"❌ Level 2 Error: {e}")
        return False


def run_level3():
    """Level 3 실행"""
    print("\n🎯 Running Level 3 Analysis...")
    send_telegram("🎯 Level 3 분석 시작 (포트폴리오 구성)")
    
    try:
        subprocess.run(['python3', f'{BASE_PATH}/agents/pm_agent.py'],
                      cwd=BASE_PATH, timeout=1200)
        
        send_telegram("✅ Level 3 분석 완료!\n📊 리포트 생성 중...")
        
        # 리포트 생성
        subprocess.run(['python3', f'{BASE_PATH}/generate_enhanced_level3_report.py'],
                      cwd=BASE_PATH, timeout=300)
        
        send_telegram("✅ 전체 분석 완료!\n🔗 https://lubanana.github.io/kstock-dashboard/")
        return True
    except Exception as e:
        send_telegram(f"❌ Level 3 Error: {e}")
        return False


def main():
    """메인 실행"""
    try:
        # Level 1 실행
        output_file = run_batch_analysis()
        
        # Level 2 실행
        if run_level2():
            # Level 3 실행
            run_level3()
        
        print("\n🎉 All analysis complete!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user. Progress saved to checkpoint.")
        send_telegram("⚠️ 분석 중단됨. 체크포인트에 진행 상황 저장됨.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        send_telegram(f"❌ 분석 오류: {e}")


if __name__ == '__main__':
    main()
