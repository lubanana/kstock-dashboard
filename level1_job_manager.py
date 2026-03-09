#!/usr/bin/env python3
"""
KStock Level 1 Job Manager
전체 종목 분석 작업 관리 시스템

Features:
- 체크포인트 기반 상태 저장/복구
- 진행률 실시간 추적 및 Telegram 알림
- 오류 발생 시 자동 재시도
- 배치 단위 처리
- 작업 큐 관리
"""

import json
import os
import sys
import time
import signal
import subprocess
import traceback
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

sys.path.insert(0, '/home/programs/kstock_analyzer/agents')

from technical_agent import TechnicalAnalysisAgent
from quant_agent import QuantAnalysisAgent
from qualitative_agent import QualitativeAnalysisAgent
from news_agent import NewsSentimentAgent

# 설정
BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = f'{BASE_PATH}/data/level1_daily'
STATE_FILE = f'{BASE_PATH}/data/job_state.json'
LOG_FILE = f'{BASE_PATH}/logs/job_manager.log'
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '32083875')

BATCH_SIZE = 50  # 배치 크기 (안정성을 위해 50개로 조정)
MAX_RETRIES = 3  # 최대 재시도 횟수
SAVE_INTERVAL = 10  # 10개마다 체크포인트 저장


@dataclass
class JobState:
    """작업 상태 데이터 클래스"""
    total_stocks: int = 0
    completed: int = 0
    failed: int = 0
    current_batch: int = 0
    total_batches: int = 0
    start_time: str = ""
    last_update: str = ""
    status: str = "idle"  # idle, running, paused, completed, error
    results: List[Dict] = None
    failed_stocks: List[Dict] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []
        if self.failed_stocks is None:
            self.failed_stocks = []
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'JobState':
        return cls(**data)
    
    @property
    def progress_pct(self) -> float:
        if self.total_stocks == 0:
            return 0.0
        return (self.completed / self.total_stocks) * 100
    
    @property
    def elapsed_seconds(self) -> float:
        if not self.start_time:
            return 0.0
        start = datetime.fromisoformat(self.start_time)
        now = datetime.now()
        return (now - start).total_seconds()
    
    @property
    def eta_seconds(self) -> float:
        if self.completed == 0:
            return 0.0
        avg_time = self.elapsed_seconds / self.completed
        remaining = self.total_stocks - self.completed
        return avg_time * remaining


class JobManager:
    """작업 관리자"""
    
    def __init__(self):
        self.state = JobState()
        self.running = False
        self.stock_list: List[Dict] = []
        self._setup_signal_handlers()
        os.makedirs(OUTPUT_PATH, exist_ok=True)
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """종료 시그널 처리"""
        print(f"\n⚠️ Received signal {signum}, saving state...")
        self.state.status = "paused"
        self._save_state()
        self._send_telegram("⏸️ 분석 일시 중단됨. 체크포인트에 상태 저장됨.")
        sys.exit(0)
    
    def _log(self, message: str):
        """로그 기록"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def _send_telegram(self, message: str):
        """Telegram 메시지 발송"""
        try:
            subprocess.run([
                'openclaw', 'message', 'send',
                '--channel', 'telegram',
                '--to', TELEGRAM_CHAT_ID,
                message
            ], capture_output=True, timeout=30)
        except Exception as e:
            self._log(f"Telegram error: {e}")
    
    def _save_state(self):
        """상태 저장"""
        self.state.last_update = datetime.now().isoformat()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _load_state(self) -> bool:
        """상태 복구"""
        if not os.path.exists(STATE_FILE):
            return False
        
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.state = JobState.from_dict(data)
            self._log(f"✅ State restored: {self.state.completed}/{self.state.total_stocks} completed")
            return True
        except Exception as e:
            self._log(f"❌ Failed to load state: {e}")
            return False
    
    def _send_progress_notification(self, force: bool = False):
        """진행 상황 알림 발송"""
        pct = int(self.state.progress_pct)
        
        # 10% 단위 또는 force
        if not force and pct % 10 != 0 and pct != 100:
            return
        
        elapsed_m = self.state.elapsed_seconds / 60
        eta_m = self.state.eta_seconds / 60
        
        message = f"""📊 KStock Level 1 진행 상황

{'█' * (pct//10)}{'░' * (10 - pct//10)} {pct}%

📈 진행: {self.state.completed:,}/{self.state.total_stocks:,} 종목
✅ 성공: {len(self.state.results):,} | ❌ 실패: {self.state.failed}
📦 배치: {self.state.current_batch}/{self.state.total_batches}

⏱️ 경과: {elapsed_m:.0f}분
⏰ 예상: {eta_m:.0f}분 남음

🕐 {datetime.now().strftime('%H:%M:%S')}"""

        self._send_telegram(message)
    
    def _send_completion_notification(self):
        """완료 알림"""
        elapsed_m = self.state.elapsed_seconds / 60
        success_rate = (len(self.state.results) / self.state.total_stocks * 100) if self.state.total_stocks > 0 else 0
        
        message = f"""🎉 Level 1 분석 완료!

📊 결과 요약:
   • 총 종목: {self.state.total_stocks:,}
   • 성공: {len(self.state.results):,} ({success_rate:.1f}%)
   • 실패: {self.state.failed}

⏱️ 총 소요: {elapsed_m:.0f}분

🔄 Level 2/3 자동 실행 중..."""

        self._send_telegram(message)
    
    def load_stock_lists(self):
        """종목 리스트 로드"""
        self._log("📂 Loading stock lists...")
        
        try:
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
            
            self.stock_list = kospi + kosdaq
            self.state.total_stocks = len(self.stock_list)
            self.state.total_batches = (self.state.total_stocks + BATCH_SIZE - 1) // BATCH_SIZE
            
            self._log(f"   ✅ Loaded {self.state.total_stocks} stocks (KOSPI: {len(kospi)}, KOSDAQ: {len(kosdaq)})")
            
        except Exception as e:
            self._log(f"❌ Failed to load stocks: {e}")
            raise
    
    def analyze_single_stock(self, stock: Dict, retry: int = 0) -> Tuple[Dict, bool]:
        """
        단일 종목 분석 (재시도 포함)
        Returns: (result, success)
        """
        symbol = stock['symbol']
        name = stock['name']
        
        result = {
            'symbol': symbol,
            'name': name,
            'market': stock.get('market', 'KOSPI'),
            'sector': stock.get('sector', 'Unknown'),
            'date': datetime.now().isoformat(),
            'agents': {},
            'status': 'pending',
            'retry_count': retry
        }
        
        try:
            # 4개 에이전트 분석
            agents = [
                ('TECH', TechnicalAnalysisAgent(symbol, name)),
                ('QUANT', QuantAnalysisAgent(symbol, name)),
                ('QUAL', QualitativeAnalysisAgent(symbol, name)),
                ('NEWS', NewsSentimentAgent(symbol, name))
            ]
            
            for agent_name, agent in agents:
                try:
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
            
            return result, True
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            
            # 재시도
            if retry < MAX_RETRIES:
                time.sleep(2)  # 재시도 전 대기
                return self.analyze_single_stock(stock, retry + 1)
            
            return result, False
    
    def run_batch(self, start_idx: int, end_idx: int) -> List[Dict]:
        """배치 실행"""
        batch_results = []
        batch_success = 0
        batch_failed = 0
        
        for i in range(start_idx, end_idx):
            if not self.running:
                break
            
            stock = self.stock_list[i]
            self._log(f"   [{i+1}/{self.state.total_stocks}] {stock['name']} ({stock['code']})")
            
            result, success = self.analyze_single_stock(stock)
            batch_results.append(result)
            
            if success:
                batch_success += 1
                self.state.completed += 1
            else:
                batch_failed += 1
                self.state.failed += 1
                self.state.failed_stocks.append(stock)
            
            # 결과 누적
            if success:
                self.state.results.append(result)
            
            # 중간 저장
            if (i + 1) % SAVE_INTERVAL == 0:
                self._save_state()
            
            # 진행 알림
            if (i + 1) % 50 == 0:
                self._send_progress_notification()
            
            time.sleep(0.2)  # 서버 부하 방지
        
        return batch_results
    
    def run(self):
        """메인 실행"""
        self._log("=" * 70)
        self._log("🚀 KStock Level 1 Job Manager")
        self._log("=" * 70)
        
        try:
            # 상태 복구 또는 초기화
            if self._load_state():
                self._send_telegram(f"📂 작업 복구됨: {self.state.completed}/{self.state.total_stocks} 완료")
            else:
                self.load_stock_lists()
                self.state.start_time = datetime.now().isoformat()
                self.state.status = "running"
                self._save_state()
            
            if self.state.status == "completed":
                self._log("✅ Job already completed")
                return
            
            self.running = True
            start_batch = self.state.current_batch
            
            # 배치 처리
            for batch_num in range(start_batch, self.state.total_batches):
                if not self.running:
                    break
                
                self.state.current_batch = batch_num
                start_idx = batch_num * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, self.state.total_stocks)
                
                self._log(f"\n📦 Batch {batch_num + 1}/{self.state.total_batches} ({start_idx+1}-{end_idx})")
                self._log("-" * 70)
                
                batch_start = time.time()
                self.run_batch(start_idx, end_idx)
                batch_elapsed = time.time() - batch_start
                
                # 배치 완료 저장
                self._save_state()
                
                self._log(f"✅ Batch {batch_num + 1} complete in {batch_elapsed:.0f}s")
                self._log(f"   Progress: {self.state.progress_pct:.1f}%")
            
            # 완료 처리
            if self.running:
                self.state.status = "completed"
                self._save_state()
                self._send_completion_notification()
                self._save_final_results()
                self._run_level2_3()
            
        except Exception as e:
            self._log(f"❌ Error: {e}")
            self._log(traceback.format_exc())
            self.state.status = "error"
            self._save_state()
            self._send_telegram(f"❌ 분석 오류: {e}")
    
    def _save_final_results(self):
        """최종 결과 저장"""
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        output_file = f"{OUTPUT_PATH}/level1_fullmarket_{date_str}.json"
        
        final = {
            'date': datetime.now().isoformat(),
            'data_source': 'KOSPI+KOSDAQ Master Files',
            'total': self.state.total_stocks,
            'completed': self.state.completed,
            'success': len(self.state.results),
            'failed': self.state.failed,
            'elapsed_minutes': self.state.elapsed_seconds / 60,
            'results': self.state.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final, f, indent=2, ensure_ascii=False)
        
        self._log(f"✅ Results saved: {output_file}")
        return output_file
    
    def _run_level2_3(self):
        """Level 2/3 실행"""
        self._log("\n🌍 Running Level 2/3...")
        
        try:
            subprocess.run(['python3', f'{BASE_PATH}/agents/sector_agent.py'], 
                          cwd=BASE_PATH, timeout=600)
            subprocess.run(['python3', f'{BASE_PATH}/agents/macro_agent.py'],
                          cwd=BASE_PATH, timeout=600)
            subprocess.run(['python3', f'{BASE_PATH}/agents/pm_agent.py'],
                          cwd=BASE_PATH, timeout=1200)
            
            self._send_telegram("✅ Level 1/2/3 전체 완료!\n🔗 https://lubanana.github.io/kstock-dashboard/")
            
        except Exception as e:
            self._log(f"❌ Level 2/3 Error: {e}")


def main():
    manager = JobManager()
    manager.run()


if __name__ == '__main__':
    main()
