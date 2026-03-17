"""
NPS Value Scanner - Fast Mode (Cache Only)
N01 전략: 캐시된 공시 데이터가 있는 종목만 분석
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Import wrappers
from fdr_wrapper import FDRWrapper
from dart_disclosure_wrapper import DartDisclosureWrapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NPSStockData:
    """Stock data container"""
    symbol: str
    name: str
    sector: str
    current_price: float
    has_disclosure: bool = False
    disclosure_count: int = 0
    returns_1y: float = 0.0
    volatility: float = 0.0
    volume_avg: float = 0.0
    score_momentum: float = 0.0
    score_stability: float = 0.0
    score_value: float = 0.0
    score_nps: float = 50.0
    total_score: float = 0.0
    grade: str = 'D'
    rank: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class NPSValueScannerN01Fast:
    """N01 Fast Scanner - Uses cached disclosure data only"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.dart = DartDisclosureWrapper()
        self.results: List[NPSStockData] = []
        self.excluded_stocks: List[Tuple[str, str]] = []
        
        self.min_price = 1000
        self.min_volume = 1e7
        self.exclude_sectors = ['은행', '증권', '보험', '금융']
        
        # Get list of stocks with cached disclosure data
        self.cached_corp_codes = self._get_cached_corp_codes()
        
        logger.info("🚀 N01 NPS Fast Scanner initialized")
        logger.info(f"   Stocks with cached disclosures: {len(self.cached_corp_codes)}")
    
    def _get_cached_corp_codes(self) -> List[str]:
        """Get list of corp_codes with cached disclosure data"""
        try:
            import sqlite3
            conn = sqlite3.connect('./data/dart_cache.db')
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT corp_code FROM disclosures')
            codes = [row[0] for row in cursor.fetchall()]
            conn.close()
            return codes
        except Exception as e:
            logger.error(f"Failed to get cached corp codes: {e}")
            return []
    
    def _corp_code_to_symbol(self, corp_code: str) -> Optional[str]:
        """Convert corp_code to stock symbol using cache DB"""
        try:
            import sqlite3
            conn = sqlite3.connect('./data/dart_cache.db')
            cursor = conn.cursor()
            cursor.execute(
                'SELECT stock_code FROM company_info WHERE corp_code = ?',
                (corp_code,)
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.debug(f"Failed to get stock code for {corp_code}: {e}")
            return None
    
    def get_stock_universe(self) -> pd.DataFrame:
        """Get only stocks with cached disclosure data"""
        logger.info("📊 Loading stock universe (cache-only)...")
        
        # Get stock codes from cached corp_codes
        symbols = []
        for corp_code in self.cached_corp_codes:
            symbol = self._corp_code_to_symbol(corp_code)
            if symbol:
                symbols.append((symbol, corp_code))
        
        if not symbols:
            logger.warning("⚠️ No stocks with cached disclosure data found")
            return pd.DataFrame()
        
        # Get stock info from DB
        try:
            import sqlite3
            conn = sqlite3.connect('./data/pivot_strategy.db')
            
            # Build symbol list for query
            symbol_list = ','.join([f"'{s}'" for s, _ in symbols])
            query = f'''
                SELECT s.symbol, s.name, s.sector
                FROM stock_info s
                WHERE s.symbol IN ({symbol_list})
                ORDER BY s.symbol
            '''
            stocks = pd.read_sql_query(query, conn)
            conn.close()
            
            # Exclude financial sector
            for sector in self.exclude_sectors:
                stocks = stocks[~stocks['sector'].str.contains(sector, na=False, case=False)]
            
            logger.info(f"✅ Loaded {len(stocks)} stocks with cached disclosures")
            return stocks
            
        except Exception as e:
            logger.error(f"❌ Failed to load stocks: {e}")
            return pd.DataFrame()
    
    def analyze_stock(self, row: pd.Series) -> Optional[NPSStockData]:
        """Analyze single stock"""
        symbol = row['symbol']
        name = row['name']
        sector = row.get('sector', 'Unknown')
        
        try:
            # Get disclosure count from cache
            corp_code = self.dart.get_corp_code(symbol)
            if not corp_code:
                self.excluded_stocks.append((symbol, "No corp code"))
                return None
            
            cached = self.dart.db.get_disclosures(corp_code, check_expiry=False)
            if cached is None or len(cached) == 0:
                self.excluded_stocks.append((symbol, "No cached disclosures"))
                return None
            
            disc_count = len(cached)
            
            # Get price data
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            df = self.fdr.get_price(symbol, start=start_date, end=end_date)
            if df is None or len(df) < 5:  # Only need 5 days minimum
                self.excluded_stocks.append((symbol, f"Insufficient price data ({len(df) if df is not None else 0} days)"))
                return None
            
            current_price = df['close'].iloc[-1]
            
            if current_price < self.min_price:
                self.excluded_stocks.append((symbol, f"Price too low"))
                return None
            
            # Calculate metrics
            returns_1y = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
            daily_returns = df['close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252)
            volume_avg = df['volume'].mean()
            
            if volume_avg < self.min_volume:
                self.excluded_stocks.append((symbol, "Volume too low"))
                return None
            
            # NPS 4-Filter Scoring
            if returns_1y >= 0.10:
                momentum_score = 90
            elif returns_1y >= 0.05:
                momentum_score = 75
            elif returns_1y >= 0.0:
                momentum_score = 60
            elif returns_1y >= -0.10:
                momentum_score = 40
            else:
                momentum_score = 20
            
            if volatility < 0.25:
                stability_score = 90
            elif volatility < 0.35:
                stability_score = 70
            elif volatility < 0.45:
                stability_score = 50
            else:
                stability_score = 30
            
            ma60 = df['close'].rolling(60).mean().iloc[-1]
            ma120 = df['close'].rolling(120).mean().iloc[-1]
            
            if current_price < ma60 and current_price < ma120:
                value_score = 90
            elif current_price < ma60:
                value_score = 70
            elif current_price < ma120:
                value_score = 50
            else:
                value_score = 30
            
            if disc_count > 1000:
                nps_score = 80
            elif disc_count > 500:
                nps_score = 60
            else:
                nps_score = 40
            
            total_score = (
                momentum_score * 0.40 +
                stability_score * 0.25 +
                value_score * 0.20 +
                nps_score * 0.15
            )
            
            if total_score >= 75:
                grade = 'A'
            elif total_score >= 60:
                grade = 'B'
            elif total_score >= 45:
                grade = 'C'
            else:
                grade = 'D'
            
            return NPSStockData(
                symbol=symbol,
                name=name,
                sector=sector,
                current_price=current_price,
                has_disclosure=True,
                disclosure_count=disc_count,
                returns_1y=returns_1y,
                volatility=volatility,
                volume_avg=volume_avg,
                score_momentum=momentum_score,
                score_stability=stability_score,
                score_value=value_score,
                score_nps=nps_score,
                total_score=total_score,
                grade=grade
            )
            
        except Exception as e:
            self.excluded_stocks.append((symbol, f"Error: {str(e)[:30]}"))
            return None
    
    def run_scan(self) -> List[NPSStockData]:
        """Run fast scan"""
        logger.info("=" * 70)
        logger.info("🔍 N01 Strategy: NPS Value Scanner (Fast Mode - Cache Only)")
        logger.info("=" * 70)
        
        universe = self.get_stock_universe()
        if universe.empty:
            logger.warning("⚠️ No stocks to scan")
            return []
        
        results = []
        total = len(universe)
        
        logger.info(f"🎯 Scanning {total} stocks with cached disclosures...")
        
        for idx, (_, row) in enumerate(universe.iterrows(), 1):
            logger.info(f"[{idx}/{total}] {row['symbol']} {row['name']}")
            
            result = self.analyze_stock(row)
            if result:
                results.append(result)
        
        # Sort and rank
        results.sort(key=lambda x: x.total_score, reverse=True)
        for i, r in enumerate(results, 1):
            r.rank = i
        
        self.results = results
        
        logger.info("=" * 70)
        logger.info("🎉 N01 Scan Complete!")
        logger.info(f"   Total: {total}")
        logger.info(f"   Selected: {len(results)}")
        
        return results
    
    def print_summary(self):
        """Print results"""
        print("\n" + "=" * 80)
        print("🏛️ N01 NPS Value Scanner - Results (Fast Mode)")
        print("=" * 80)
        
        if not self.results:
            print("❌ No stocks passed all filters")
            return
        
        # All results
        print(f"\n📊 All Stocks ({len(self.results)}):")
        print("-" * 80)
        print(f"{'Rank':<6}{'Symbol':<10}{'Name':<20}{'Grade':<8}{'Score':<8}{'Return':<10}{'Disclosures':<12}")
        print("-" * 80)
        
        for r in self.results:
            print(f"{r.rank:<6}{r.symbol:<10}{r.name:<20}{r.grade:<8}{r.total_score:<7.1f}{r.returns_1y*100:<+9.1f}%{r.disclosure_count:<12}")
        
        print("=" * 80)
    
    def export_results(self, output_dir: str = './reports/nps_value') -> Dict[str, str]:
        """Export results"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        files = {}
        
        # JSON
        json_path = f"{output_dir}/n01_nps_fast_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        files['json'] = json_path
        
        # CSV
        csv_path = f"{output_dir}/n01_nps_fast_{timestamp}.csv"
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        files['csv'] = csv_path
        
        logger.info(f"💾 Exported: {json_path}, {csv_path}")
        
        return files


def main():
    """Main"""
    scanner = NPSValueScannerN01Fast()
    results = scanner.run_scan()
    
    if results:
        scanner.print_summary()
        files = scanner.export_results()
        print(f"\n📁 Results saved to: {files['csv']}")
    else:
        scanner.print_summary()
    
    return results


if __name__ == '__main__':
    main()
