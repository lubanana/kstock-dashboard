#!/usr/bin/env python3
"""
Crypto Signal Aggregator (CSA)
10개 데이터 소스 통합 자동 시그널 프로그램

데이터 소스:
1. MacroMicro - 거시경제 (CPI, 금리)
2. fuckbtc.com - BTC 사이클, 공포지수
3. RootData - VC 투자 흐름
4. CoinGlass - 펀딩비, 청산맵
5. DeFiLlama - TVL, 프로토콜
6. Dune Analytics - 온체인
7. Tokenomist - 언락 일정
8. Arkham - 고래 추적
9. Airdrops.io - 에어드랍
10. CoinGecko - 시세, 시총
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import os
import sys

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 텔레그램 알림 임포트
try:
    from telegram_alert import TelegramAlert, get_telegram_alert
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("telegram_alert 모듈을 찾을 수 없습니다.")

# 페이퍼트레이딩 연동 임포트
try:
    from paper_connector import PaperTradingConnector, get_paper_connector
    PAPER_AVAILABLE = True
except ImportError:
    PAPER_AVAILABLE = False
    logger.warning("paper_connector 모듈을 찾을 수 없습니다.")


class SignalStrength(Enum):
    STRONG_BUY = "STRONG_BUY"  # 80-100
    BUY = "BUY"                # 60-79
    NEUTRAL = "NEUTRAL"        # 40-59
    SELL = "SELL"              # 20-39
    STRONG_SELL = "STRONG_SELL" # 0-19


@dataclass
class DataSourceScore:
    """개별 데이터 소스 점수"""
    source: str
    score: float  # 0-100
    weight: float  # 가중치
    raw_data: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TradingSignal:
    """통합 트레이딩 신호"""
    symbol: str  # BTC, ETH 등
    strength: SignalStrength
    total_score: float  # 0-100
    source_scores: List[DataSourceScore]
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'strength': self.strength.value,
            'total_score': round(self.total_score, 2),
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'sources': [
                {
                    'source': s.source,
                    'score': round(s.score, 2),
                    'weight': s.weight
                } for s in self.source_scores
            ]
        }


class CoinGeckoAPI:
    """CoinGecko API 연동"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def get_price(self, ids: List[str]) -> Dict[str, float]:
        """현재가 조회"""
        url = f"{self.BASE_URL}/simple/price"
        params = {
            'ids': ','.join(ids),
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true'
        }
        
        try:
            async with self.session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        k: {
                            'price': v.get('usd', 0),
                            'change_24h': v.get('usd_24h_change', 0),
                            'volume': v.get('usd_24h_vol', 0)
                        }
                        for k, v in data.items()
                    }
        except Exception as e:
            logger.error(f"CoinGecko error: {e}")
        
        return {}
    
    async def get_fear_greed(self) -> Optional[Dict]:
        """공포탐욕지수"""
        try:
            url = "https://api.alternative.me/fng/"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('data', [{}])[0]
        except Exception as e:
            logger.error(f"FearGreed error: {e}")
        return None


class DeFiLlamaAPI:
    """DeFiLlama API 연동"""
    
    BASE_URL = "https://api.llama.fi"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def get_tvl(self, protocol: str = None) -> Dict:
        """TVL 데이터"""
        try:
            if protocol:
                url = f"{self.BASE_URL}/protocol/{protocol}"
            else:
                url = f"{self.BASE_URL}/charts"
            
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"DeFiLlama error: {e}")
        return {}
    
    async def get_stablecoins(self) -> Dict:
        """스테이블코인 유동성"""
        try:
            url = f"{self.BASE_URL}/stablecoins"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"Stablecoins error: {e}")
        return {}


class CoinGlassAPI:
    """CoinGlass API 연동 (일부 물리 API)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def get_funding_rate(self, symbol: str = "BTC") -> Optional[float]:
        """펀딩비 조회"""
        # 물리 API 필요 - 크롤링으로 대체 가능
        return None
    
    async def get_long_short_ratio(self, symbol: str = "BTC") -> Optional[Dict]:
        """롱숏 비율"""
        return None


class BithumbAPI:
    """Bithumb Public API"""
    
    BASE_URL = "https://api.bithumb.com/public"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def get_ticker(self, coin: str) -> Optional[Dict]:
        """현재가 조회"""
        try:
            url = f"{self.BASE_URL}/ticker/{coin}_KRW"
            async with self.session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('status') == '0000':
                        return data['data']
        except Exception as e:
            logger.error(f"Bithumb error: {e}")
        return None


class SignalEngine:
    """신호 생성 엔진"""
    
    # 데이터 소스별 가중치
    WEIGHTS = {
        'coingecko': 0.25,      # 시세, 거래량, 공포지수
        'defillama': 0.15,      # TVL, 유동성
        'coinglass': 0.20,      # 펀딩비, 롱숏
        'fear_greed': 0.15,     # 심리 지표
        'macro': 0.10,          # 거시경제
        'onchain': 0.15,        # 온체인
    }
    
    def __init__(self):
        self.scores: Dict[str, List[DataSourceScore]] = {}
    
    def calculate_fear_greed_score(self, fear_greed_data: Optional[Dict]) -> float:
        """공포탐욕지수 점수 계산 (0-100)"""
        if not fear_greed_data:
            return 50  # 중립
        
        try:
            value = int(fear_greed_data.get('value', 50))
            # 공포(0) → 매수, 탐욕(100) → 매도
            # 점수 반전: 공포가 높을수록 매수 신호 강함
            score = 100 - value
            return score
        except:
            return 50
    
    def calculate_price_momentum_score(self, price_data: Dict) -> float:
        """가격 모멘텀 점수"""
        change = price_data.get('change_24h', 0)
        volume = price_data.get('volume', 0)
        
        # 과도한 상승은 피로도, 과도한 하락은 반등 기회
        if change > 15:  # 과열
            return 30
        elif change > 5:  # 상승
            return 60
        elif change > -5:  # 보합
            return 50
        elif change > -15:  # 하띜
            return 70  # 반등 기회
        else:  # 과매도
            return 85  # 강한 매수
    
    def calculate_defi_score(self, tvl_data: Dict) -> float:
        """DeFi 점수"""
        # TVL 성장률 기반
        return 50  # 기본값
    
    async def generate_signal(self, symbol: str = "BTC") -> Optional[TradingSignal]:
        """통합 신호 생성"""
        source_scores = []
        
        async with CoinGeckoAPI() as cg:
            # CoinGecko 데이터
            price_data = await cg.get_price(['bitcoin'])
            fear_greed = await cg.get_fear_greed()
            
            # 공포탐욕 점수
            fg_score = self.calculate_fear_greed_score(fear_greed)
            source_scores.append(DataSourceScore(
                source='fear_greed',
                score=fg_score,
                weight=self.WEIGHTS['fear_greed'],
                raw_data=fear_greed or {}
            ))
            
            # 가격 모멘텀 점수
            if 'bitcoin' in price_data:
                pm_score = self.calculate_price_momentum_score(price_data['bitcoin'])
                source_scores.append(DataSourceScore(
                    source='coingecko_price',
                    score=pm_score,
                    weight=0.15,
                    raw_data=price_data['bitcoin']
                ))
        
        async with DeFiLlamaAPI() as llama:
            tvl_data = await llama.get_tvl()
            defi_score = self.calculate_defi_score(tvl_data)
            source_scores.append(DataSourceScore(
                source='defillama',
                score=defi_score,
                weight=self.WEIGHTS['defillama'],
                raw_data=tvl_data
            ))
        
        # 총점 계산
        total_weight = sum(s.weight for s in source_scores)
        if total_weight == 0:
            return None
        
        weighted_sum = sum(s.score * s.weight for s in source_scores)
        total_score = weighted_sum / total_weight
        
        # 신호 강도 결정
        if total_score >= 80:
            strength = SignalStrength.STRONG_BUY
        elif total_score >= 60:
            strength = SignalStrength.BUY
        elif total_score >= 40:
            strength = SignalStrength.NEUTRAL
        elif total_score >= 20:
            strength = SignalStrength.SELL
        else:
            strength = SignalStrength.STRONG_SELL
        
        # 진입가 계산 (Bithumb)
        entry_price = None
        async with BithumbAPI() as bithumb:
            ticker = await bithumb.get_ticker("BTC")
            if ticker:
                entry_price = float(ticker.get('closing_price', 0))
        
        # 손절/익절 설정
        stop_loss = entry_price * 0.93 if entry_price else None  # -7%
        take_profit = entry_price * 1.21 if entry_price else None  # +21%
        
        # 신호 사유
        reasons = []
        if fg_score < 30:
            reasons.append(f"극도의 공포(지수 {100-fg_score})")
        elif fg_score > 70:
            reasons.append(f"과도한 탐욕(지수 {100-fg_score})")
        
        return TradingSignal(
            symbol=symbol,
            strength=strength,
            total_score=total_score,
            source_scores=source_scores,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason="; ".join(reasons) if reasons else "중립적 시장 상황",
            timestamp=datetime.now()
        )


class SignalMonitor:
    """신호 모니터링 및 알림"""
    
    def __init__(self, check_interval_minutes: int = 60, auto_trade: bool = True):
        self.check_interval = check_interval_minutes
        self.engine = SignalEngine()
        self.last_signal: Optional[TradingSignal] = None
        self.data_dir = '/tmp/crypto_signal_data'
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 텔레그램 알림
        self.telegram = get_telegram_alert() if TELEGRAM_AVAILABLE else None
        
        # 페이퍼트레이딩 연동
        self.paper = get_paper_connector() if PAPER_AVAILABLE else None
        self.auto_trade = auto_trade and PAPER_AVAILABLE
    
    def save_signal(self, signal: TradingSignal):
        """신호 저장"""
        filename = f"{self.data_dir}/signal_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(signal.to_dict(), f, indent=2)
        logger.info(f"Signal saved: {filename}")
    
    def load_history(self) -> List[Dict]:
        """히스토리 로드"""
        signals = []
        for f in os.listdir(self.data_dir):
            if f.startswith('signal_') and f.endswith('.json'):
                with open(f"{self.data_dir}/{f}") as file:
                    signals.append(json.load(file))
        return sorted(signals, key=lambda x: x['timestamp'])
    
    async def run(self):
        """메인 실행 루프"""
        logger.info("="*70)
        logger.info("🚀 Crypto Signal Aggregator 시작")
        if self.auto_trade:
            logger.info("📊 페이퍼트레이딩 자동 주문: 활성화")
        if self.telegram and self.telegram.enabled:
            logger.info("📱 텔레그램 알림: 활성화")
        logger.info("="*70)
        
        while True:
            try:
                logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 신호 분석 시작...")
                
                # 신호 생성
                signal = await self.engine.generate_signal("BTC")
                
                if signal:
                    self.save_signal(signal)
                    self.last_signal = signal
                    
                    # 콘솔 출력
                    self.print_signal(signal)
                    
                    # 강한 신호일 때만 알림/주문 (BUY 이상)
                    if signal.strength in [SignalStrength.BUY, SignalStrength.STRONG_BUY]:
                        logger.info(f"🚨 강한 매수 신호 감지: {signal.strength.value}")
                        
                        # 텔레그램 알림
                        if self.telegram:
                            await self.telegram.send_signal_alert(signal)
                        
                        # 페이퍼트레이딩 자동 주문
                        if self.auto_trade and self.paper:
                            self.paper.execute_signal(signal)
                
                # 페이퍼트레이딩 익절/손절 체크
                if self.paper:
                    current_prices = await self._get_current_prices()
                    self.paper.check_take_profit_stop_loss(current_prices)
                    self.paper.print_portfolio(current_prices)
                
                # 대기
                logger.info(f"다음 체크: {(datetime.now() + timedelta(minutes=self.check_interval)).strftime('%H:%M:%S')}")
                await asyncio.sleep(self.check_interval * 60)
                
            except Exception as e:
                logger.error(f"Error: {e}")
                await asyncio.sleep(60)
    
    async def _get_current_prices(self) -> dict:
        """현재가 조회"""
        prices = {}
        async with BithumbAPI() as api:
            for coin in ['BTC', 'ETH', 'XRP', 'SOL']:
                ticker = await api.get_ticker(coin)
                if ticker:
                    prices[coin] = float(ticker.get('closing_price', 0))
        return prices
    
    def print_signal(self, signal: TradingSignal):
        """신호 출력"""
        emoji = {
            SignalStrength.STRONG_BUY: "🟢🟢",
            SignalStrength.BUY: "🟢",
            SignalStrength.NEUTRAL: "⚪",
            SignalStrength.SELL: "🔴",
            SignalStrength.STRONG_SELL: "🔴🔴"
        }
        
        print(f"\n{'='*70}")
        print(f"{emoji.get(signal.strength, '⚪')} {signal.symbol} 신호: {signal.strength.value}")
        print(f"{'='*70}")
        print(f"총점: {signal.total_score:.1f}/100")
        print(f"진입가: {signal.entry_price:,.0f} KRW" if signal.entry_price else "진입가: N/A")
        print(f"손절가: {signal.stop_loss:,.0f} KRW (-7%)" if signal.stop_loss else "")
        print(f"익절가: {signal.take_profit:,.0f} KRW (+21%)" if signal.take_profit else "")
        print(f"사유: {signal.reason}")
        print(f"\n세부 점수:")
        for s in signal.source_scores:
            bar = "█" * int(s.score / 10) + "░" * (10 - int(s.score / 10))
            print(f"  {s.source:15} [{bar}] {s.score:5.1f} (w:{s.weight:.2f})")
        print(f"{'='*70}\n")
    
    async def send_alert(self, signal: TradingSignal):
        """알림 전송 (텔레그램 등)"""
        logger.info(f"🚨 ALERT: {signal.symbol} {signal.strength.value} 신호!")


async def main():
    """메인 함수"""
    monitor = SignalMonitor(check_interval_minutes=60)
    
    # 단일 실행 모드
    if '--once' in os.sys.argv:
        signal = await monitor.engine.generate_signal("BTC")
        if signal:
            monitor.print_signal(signal)
            monitor.save_signal(signal)
        return
    
    # 지속 모니터링
    await monitor.run()


if __name__ == '__main__':
    asyncio.run(main())
