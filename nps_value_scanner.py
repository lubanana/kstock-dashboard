"""
NPS Value Scanner - 국민연금 장기 가치 투자 패턴 복제
저평가 우량주 선별 알고리즘

필터링 로직:
1. 수익성: 3년 연속 ROE 10~15%
2. 배당: 3년 평균 배당수익률 > 시장평균, 배당성향 20~50%
3. 저평가: PBR ≤ 1.0 or 업종 하위 30%
4. 수급: NPS 지분율 ≥ 5%, 최근 2분기 유지/확대

세부조건:
- 금융업 제외 (은행/증권/보험)
- 관리/환기종목 제외
- 시가총액 1,000억 이상
- 가중치: ROE 유지력 > 배당수익률 > 저PBR
"""
import os
import sys
import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple, Any
from collections import defaultdict
import pandas as pd
import numpy as np

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NPSFilterConfig:
    """NPS Scanner Configuration"""
    # Profitability filters
    roe_min: float = 0.10  # 10%
    roe_max: float = 0.15  # 15%
    roe_years: int = 3
    
    # Dividend filters
    payout_ratio_min: float = 0.20  # 20%
    payout_ratio_max: float = 0.50  # 50%
    dividend_yield_years: int = 3
    
    # Valuation filters
    pbr_max: float = 1.0
    pbr_industry_percentile: float = 0.30  # 하위 30%
    
    # Ownership filters
    nps_min_ownership: float = 0.05  # 5%
    nps_quarters_check: int = 2
    
    # Exclusion filters
    min_market_cap: float = 1000e8  # 1,000억원
    exclude_sectors: List[str] = None
    
    # Scoring weights
    weight_roe: float = 0.5  # ROE 가중치
    weight_dividend: float = 0.3  # 배당 가중치
    weight_pbr: float = 0.2  # PBR 가중치
    
    # Output
    top_n: int = 20
    
    def __post_init__(self):
        if self.exclude_sectors is None:
            self.exclude_sectors = ['은행', '증권', '보험', '금융', '지주']


@dataclass
class StockScore:
    """Stock scoring result"""
    symbol: str
    name: str
    sector: str
    market_cap: float
    
    # ROE metrics
    roe_avg: float
    roe_std: float
    roe_score: float
    
    # Dividend metrics
    dividend_yield: float
    payout_ratio: float
    dividend_score: float
    
    # Valuation metrics
    pbr: float
    pbr_percentile: float
    valuation_score: float
    
    # NPS ownership
    nps_ownership: float
    nps_trend: str  # 'increasing', 'stable', 'decreasing'
    
    # Final score
    total_score: float
    rank: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


class NPSScanner:
    """
    NPS Long-term Value Investment Pattern Scanner
    """
    
    def __init__(self, config: Optional[NPSFilterConfig] = None):
        self.config = config or NPSFilterConfig()
        self.db_path = './data/pivot_strategy.db'
        self.dart_db_path = './data/dart_cache.db'
        self.results: List[StockScore] = []
        
        logger.info("🚀 NPS Value Scanner initialized")
        logger.info(f"   ROE range: {self.config.roe_min*100:.0f}~{self.config.roe_max*100:.0f}%")
        logger.info(f"   PBR max: {self.config.pbr_max:.1f}x")
        logger.info(f"   NPS min ownership: {self.config.nps_min_ownership*100:.0f}%")
    
    def _get_connection(self, db_path: str):
        """Get database connection"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_all_stocks(self) -> pd.DataFrame:
        """Get all stocks from database"""
        try:
            with self._get_connection(self.db_path) as conn:
                query = '''
                    SELECT s.symbol, s.name, s.sector, s.market_cap
                    FROM stock_info s
                    WHERE s.market_cap >= ?
                    ORDER BY s.market_cap DESC
                '''
                df = pd.read_sql_query(query, conn, params=(self.config.min_market_cap,))
                logger.info(f"📊 Loaded {len(df)} stocks from DB (min cap: {self.config.min_market_cap/1e8:.0f}억)")
                return df
        except Exception as e:
            logger.error(f"❌ Failed to load stocks: {e}")
            return pd.DataFrame()
    
    def filter_financial_sector(self, df: pd.DataFrame) -> pd.DataFrame:
        """Exclude financial sector stocks"""
        initial_count = len(df)
        
        mask = ~df['sector'].str.contains('|'.join(self.config.exclude_sectors), na=False, case=False)
        df = df[mask].copy()
        
        filtered_count = initial_count - len(df)
        logger.info(f"🏦 Excluded {filtered_count} financial sector stocks")
        return df
    
    def calculate_roe_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate 3-year ROE metrics
        Note: This is a placeholder - actual implementation needs financial data
        """
        # TODO: Implement actual ROE calculation from financial statements
        # For now, using mock data structure
        
        logger.info("📈 Calculating ROE metrics...")
        
        # Placeholder: In real implementation, fetch from dart or financial DB
        df['roe_y1'] = np.nan
        df['roe_y2'] = np.nan
        df['roe_y3'] = np.nan
        df['roe_avg'] = np.nan
        df['roe_std'] = np.nan
        df['roe_pass'] = False
        
        return df
    
    def calculate_dividend_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate 3-year dividend metrics
        """
        logger.info("💰 Calculating dividend metrics...")
        
        # Placeholder for dividend data
        df['dividend_yield_avg'] = np.nan
        df['payout_ratio'] = np.nan
        df['dividend_pass'] = False
        
        return df
    
    def calculate_valuation_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate PBR and industry comparison
        """
        logger.info("📉 Calculating valuation metrics...")
        
        try:
            with self._get_connection(self.db_path) as conn:
                # Get latest price and book value data
                query = '''
                    SELECT s.symbol, p.close as price, s.market_cap
                    FROM stock_info s
                    LEFT JOIN (
                        SELECT symbol, close
                        FROM stock_prices
                        WHERE date = (SELECT MAX(date) FROM stock_prices)
                    ) p ON s.symbol = p.symbol
                '''
                price_df = pd.read_sql_query(query, conn)
                
                # Merge with main df
                df = df.merge(price_df[['symbol', 'price']], on='symbol', how='left')
                
                # Calculate PBR (placeholder - needs actual book value)
                df['bps'] = np.nan  # Book value per share
                df['pbr'] = df['price'] / df['bps']
                df['pbr'] = df['pbr'].fillna(np.inf)
                
                # Industry percentile
                df['pbr_percentile'] = df.groupby('sector')['pbr'].rank(pct=True)
                
                # Pass condition
                df['valuation_pass'] = (
                    (df['pbr'] <= self.config.pbr_max) |
                    (df['pbr_percentile'] <= self.config.pbr_industry_percentile)
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate valuation: {e}")
            df['pbr'] = np.inf
            df['pbr_percentile'] = 1.0
            df['valuation_pass'] = False
        
        return df
    
    def get_nps_ownership(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get NPS ownership data from DART
        """
        logger.info("🏛️ Fetching NPS ownership data...")
        
        # Placeholder: Fetch from dart_disclosure_wrapper
        # In real implementation, query major_shareholders table
        
        df['nps_ownership'] = 0.0
        df['nps_trend'] = 'unknown'
        df['nps_pass'] = False
        
        return df
    
    def calculate_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate weighted scores
        """
        logger.info("🎯 Calculating weighted scores...")
        
        # ROE Score (centered around 12.5%)
        roe_target = (self.config.roe_min + self.config.roe_max) / 2
        df['roe_score'] = 100 - abs(df['roe_avg'] - roe_target) * 500
        df['roe_score'] = df['roe_score'].clip(0, 100)
        
        # Dividend Score
        df['dividend_score'] = (
            df['dividend_yield_avg'] * 10 + 
            (1 - abs(df['payout_ratio'] - 0.35) / 0.15) * 50
        ).clip(0, 100)
        
        # PBR Score (lower is better)
        df['valuation_score'] = (1 - df['pbr_percentile']) * 100
        
        # Total Score
        df['total_score'] = (
            df['roe_score'] * self.config.weight_roe +
            df['dividend_score'] * self.config.weight_dividend +
            df['valuation_score'] * self.config.weight_pbr
        )
        
        return df
    
    def run_scan(self) -> List[StockScore]:
        """
        Run full NPS scanning pipeline
        """
        logger.info("=" * 60)
        logger.info("🔍 Starting NPS Value Scanner")
        logger.info("=" * 60)
        
        # Step 1: Load all stocks
        df = self.get_all_stocks()
        if df.empty:
            logger.error("❌ No stocks loaded")
            return []
        
        # Step 2: Filter financial sector
        df = self.filter_financial_sector(df)
        
        # Step 3: Calculate ROE metrics (Filter 1)
        df = self.calculate_roe_metrics(df)
        df = df[df['roe_pass']].copy()
        logger.info(f"✅ Filter 1 (ROE): {len(df)} stocks remaining")
        
        # Step 4: Calculate valuation metrics (Filter 2)
        df = self.calculate_valuation_metrics(df)
        df = df[df['valuation_pass']].copy()
        logger.info(f"✅ Filter 2 (PBR): {len(df)} stocks remaining")
        
        # Step 5: Get NPS ownership (Filter 3)
        df = self.get_nps_ownership(df)
        df = df[df['nps_pass']].copy()
        logger.info(f"✅ Filter 3 (NPS): {len(df)} stocks remaining")
        
        # Step 6: Calculate dividend metrics
        df = self.calculate_dividend_metrics(df)
        
        # Step 7: Scoring
        df = self.calculate_scores(df)
        df = df.sort_values('total_score', ascending=False).reset_index(drop=True)
        
        # Step 8: Convert to StockScore objects
        results = []
        for idx, row in df.head(self.config.top_n).iterrows():
            score = StockScore(
                symbol=row['symbol'],
                name=row['name'],
                sector=row['sector'],
                market_cap=row['market_cap'],
                roe_avg=row.get('roe_avg', 0),
                roe_std=row.get('roe_std', 0),
                roe_score=row.get('roe_score', 0),
                dividend_yield=row.get('dividend_yield_avg', 0),
                payout_ratio=row.get('payout_ratio', 0),
                dividend_score=row.get('dividend_score', 0),
                pbr=row.get('pbr', 0),
                pbr_percentile=row.get('pbr_percentile', 0),
                valuation_score=row.get('valuation_score', 0),
                nps_ownership=row.get('nps_ownership', 0),
                nps_trend=row.get('nps_trend', 'unknown'),
                total_score=row['total_score'],
                rank=idx + 1
            )
            results.append(score)
        
        self.results = results
        logger.info(f"🎉 Scan complete! Top {len(results)} stocks selected")
        
        return results
    
    def export_results(self, output_dir: str = './reports/nps_scan') -> Dict[str, str]:
        """
        Export results to JSON and CSV
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # JSON export
        json_path = f"{output_dir}/nps_scan_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        
        # CSV export
        csv_path = f"{output_dir}/nps_scan_{timestamp}.csv"
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"💾 Results exported to:")
        logger.info(f"   JSON: {json_path}")
        logger.info(f"   CSV: {csv_path}")
        
        return {'json': json_path, 'csv': csv_path}
    
    def print_summary(self):
        """Print scan summary"""
        print("\n" + "=" * 80)
        print("🏆 NPS Value Scanner Results")
        print("=" * 80)
        print(f"{'Rank':<6}{'Symbol':<10}{'Name':<20}{'Sector':<15}{'Score':<10}")
        print("-" * 80)
        
        for score in self.results[:10]:
            print(f"{score.rank:<6}{score.symbol:<10}{score.name:<20}"
                  f"{score.sector:<15}{score.total_score:<10.2f}")
        
        print("=" * 80)


def main():
    """Main execution"""
    config = NPSFilterConfig(
        roe_min=0.10,
        roe_max=0.15,
        pbr_max=1.0,
        nps_min_ownership=0.05,
        top_n=20
    )
    
    scanner = NPSScanner(config)
    results = scanner.run_scan()
    
    if results:
        scanner.print_summary()
        scanner.export_results()
    else:
        print("❌ No stocks passed all filters")
    
    return results


if __name__ == '__main__':
    main()
