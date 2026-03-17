"""
NPS Value Scanner - Test Version with Disclosure Check
Tests DART wrapper and handles missing disclosure data
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
from datetime import datetime, timedelta

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
    
    # Disclosure available flag
    has_disclosure: bool = False
    
    # Technical metrics
    returns_1y: float = 0.0
    volatility: float = 0.0
    volume_avg: float = 0.0
    
    # Scores
    score_momentum: float = 0.0
    score_stability: float = 0.0
    score_value: float = 0.0
    total_score: float = 0.0
    rank: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class NPSValueScannerTest:
    """NPS-style scanner with disclosure validation"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.dart = DartDisclosureWrapper()
        self.results: List[NPSStockData] = []
        self.failed_stocks: List[Tuple[str, str]] = []  # (symbol, reason)
        
        # Filters
        self.min_price = 1000
        self.min_volume = 1e7  # 1000만
        self.exclude_sectors = ['은행', '증권', '보험', '금융']
        
        logger.info("🚀 NPS Scanner (Test Mode) initialized")
        logger.info(f"   DART DB: {self.dart.db.db_path}")
    
    def test_disclosure_available(self, symbol: str) -> Tuple[bool, str]:
        """
        Test if disclosure data is available for stock
        Returns: (available, reason)
        """
        try:
            # Get corp code
            corp_code = self.dart.get_corp_code(symbol)
            if not corp_code:
                return (False, "No corp code mapping")
            
            # Try to list disclosures (check cache first, don't fail on API error)
            try:
                disclosures = self.dart.list_disclosures(corp_code)
                if disclosures is not None and hasattr(disclosures, '__len__') and len(disclosures) > 0:
                    return (True, f"Found {len(disclosures)} disclosures")
            except Exception as e:
                # API failed, check if we have any cached data
                pass
            
            # Check cache directly (fallback)
            cached = self.dart.db.get_disclosures(corp_code, check_expiry=False)
            if cached is not None and hasattr(cached, '__len__') and len(cached) > 0:
                return (True, f"Found {len(cached)} cached disclosures")
            
            return (False, "No disclosure data available (API error + no cache)")
            
        except Exception as e:
            return (False, f"Error: {str(e)[:50]}")
    
    def get_stock_universe(self) -> pd.DataFrame:
        """Get stock universe"""
        logger.info("📊 Loading stock universe...")
        
        try:
            import sqlite3
            conn = sqlite3.connect('./data/pivot_strategy.db')
            query = '''
                SELECT s.symbol, s.name, s.sector
                FROM stock_info s
                ORDER BY s.symbol
            '''
            stocks = pd.read_sql_query(query, conn)
            conn.close()
            
            # Exclude financial sector
            for sector in self.exclude_sectors:
                stocks = stocks[~stocks['sector'].str.contains(sector, na=False, case=False)]
            
            logger.info(f"✅ Loaded {len(stocks)} stocks")
            return stocks
            
        except Exception as e:
            logger.error(f"❌ Failed to load stocks: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def analyze_stock(self, row: pd.Series) -> Optional[NPSStockData]:
        """Analyze single stock with disclosure check"""
        symbol = row['symbol']
        name = row['name']
        sector = row.get('sector', 'Unknown')
        
        try:
            # Step 1: Check disclosure availability
            has_disclosure, reason = self.test_disclosure_available(symbol)
            
            if not has_disclosure:
                self.failed_stocks.append((symbol, reason))
                logger.debug(f"❌ {symbol}: {reason}")
                return None
            
            # Step 2: Get price data
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            df = self.fdr.get_price(symbol, start=start_date, end=end_date)
            if df is None or len(df) < 50:
                self.failed_stocks.append((symbol, "Insufficient price data"))
                return None
            
            current_price = df['Close'].iloc[-1]
            
            # Filter: minimum price
            if current_price < self.min_price:
                self.failed_stocks.append((symbol, f"Price too low ({current_price})"))
                return None
            
            # Calculate metrics
            returns_1y = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
            daily_returns = df['Close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252)
            volume_avg = df['Volume'].mean()
            
            if volume_avg < self.min_volume:
                self.failed_stocks.append((symbol, f"Volume too low"))
                return None
            
            # Calculate scores
            if returns_1y >= -0.20:
                momentum_score = 50 + (returns_1y * 100)
                momentum_score = max(0, min(100, momentum_score))
            else:
                momentum_score = 0
            
            # Stability score
            if volatility < 0.20:
                stability_score = 90
            elif volatility < 0.30:
                stability_score = 70
            elif volatility < 0.40:
                stability_score = 50
            else:
                stability_score = max(0, 30 - (volatility - 0.40) * 50)
            
            # Value score
            ma60 = df['Close'].rolling(60).mean().iloc[-1]
            ma120 = df['Close'].rolling(120).mean().iloc[-1]
            
            if current_price < ma60 and current_price < ma120:
                value_score = 80
            elif current_price < ma60:
                value_score = 60
            else:
                value_score = 40
            
            # Total score
            total_score = (
                momentum_score * 0.40 +
                stability_score * 0.25 +
                value_score * 0.20 +
                50 * 0.15
            )
            
            return NPSStockData(
                symbol=symbol,
                name=name,
                sector=sector,
                current_price=current_price,
                has_disclosure=True,
                returns_1y=returns_1y,
                volatility=volatility,
                volume_avg=volume_avg,
                score_momentum=momentum_score,
                score_stability=stability_score,
                score_value=value_score,
                total_score=total_score
            )
            
        except Exception as e:
            self.failed_stocks.append((symbol, f"Analysis error: {str(e)[:30]}"))
            logger.debug(f"Analysis failed for {symbol}: {e}")
            return None
    
    def run_scan(self, max_stocks: Optional[int] = None, test_mode: bool = False) -> List[NPSStockData]:
        """Run scanning pipeline"""
        logger.info("=" * 60)
        logger.info("🔍 NPS Scanner with Disclosure Validation")
        logger.info("=" * 60)
        
        universe = self.get_stock_universe()
        if universe.empty:
            return []
        
        if max_stocks:
            universe = universe.head(max_stocks)
        
        if test_mode:
            logger.info("🧪 TEST MODE: Only checking disclosure availability")
            
            # Just test disclosure availability for all stocks
            disclosure_stats = {'available': 0, 'unavailable': 0}
            
            for idx, (_, row) in enumerate(universe.iterrows(), 1):
                if idx % 100 == 0:
                    logger.info(f"Progress: {idx}/{len(universe)} | Available: {disclosure_stats['available']}")
                
                symbol = row['symbol']
                available, reason = self.test_disclosure_available(symbol)
                
                if available:
                    disclosure_stats['available'] += 1
                else:
                    disclosure_stats['unavailable'] += 1
                    self.failed_stocks.append((symbol, reason))
            
            logger.info("\n📊 Disclosure Availability Report")
            logger.info(f"   Available: {disclosure_stats['available']}")
            logger.info(f"   Unavailable: {disclosure_stats['unavailable']}")
            logger.info(f"   Success Rate: {disclosure_stats['available']/len(universe)*100:.1f}%")
            
            return []
        
        # Full scan
        results = []
        total = len(universe)
        
        for idx, (_, row) in enumerate(universe.iterrows(), 1):
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%) | Found: {len(results)}")
            
            result = self.analyze_stock(row)
            if result:
                results.append(result)
        
        # Sort and rank
        results.sort(key=lambda x: x.total_score, reverse=True)
        for i, r in enumerate(results, 1):
            r.rank = i
        
        self.results = results
        logger.info(f"🎉 Scan complete! {len(results)} stocks selected")
        
        return results
    
    def print_summary(self):
        """Print results"""
        print("\n" + "=" * 80)
        print("🏛️ NPS Value Scanner (Test Mode) - Results")
        print("=" * 80)
        
        if not self.results:
            print("❌ No stocks passed all filters")
            print(f"\n📉 Failed stocks: {len(self.failed_stocks)}")
            
            # Show failure reasons breakdown
            from collections import Counter
            reasons = [reason for _, reason in self.failed_stocks]
            reason_counts = Counter(reasons)
            print("\nTop failure reasons:")
            for reason, count in reason_counts.most_common(10):
                print(f"   {count:4d} | {reason[:50]}")
            
            return
        
        print(f"{'Rank':<6}{'Symbol':<10}{'Name':<20}{'Return':<10}{'Vol':<8}{'Score':<8}")
        print("-" * 80)
        
        for r in self.results[:20]:
            print(f"{r.rank:<6}{r.symbol:<10}{r.name:<20}"
                  f"{r.returns_1y*100:<9.1f}% {r.volatility*100:<7.1f}% {r.total_score:<7.1f}")
        
        print("=" * 80)
    
    def export_results(self, output_dir: str = './reports/nps_value') -> Dict[str, str]:
        """Export results"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # JSON
        json_path = f"{output_dir}/nps_test_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        
        # CSV
        csv_path = f"{output_dir}/nps_test_{timestamp}.csv"
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # Failed stocks
        failed_path = f"{output_dir}/nps_test_failed_{timestamp}.csv"
        failed_df = pd.DataFrame(self.failed_stocks, columns=['symbol', 'reason'])
        failed_df.to_csv(failed_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"💾 Exported: {json_path}, {csv_path}, {failed_path}")
        
        return {'json': json_path, 'csv': csv_path, 'failed': failed_path}


def main():
    """Main"""
    import sys
    
    scanner = NPSValueScannerTest()
    
    # Run in test mode first to check disclosure availability
    logger.info("\n🧪 PHASE 1: Testing disclosure availability")
    scanner.run_scan(test_mode=True)
    
    # Show sample of failed stocks
    if scanner.failed_stocks:
        logger.info("\n📋 Sample failed stocks:")
        for symbol, reason in scanner.failed_stocks[:10]:
            logger.info(f"   {symbol}: {reason}")
    
    # Run full scan
    logger.info("\n🔍 PHASE 2: Full scan with disclosure validation")
    results = scanner.run_scan()
    
    if results:
        scanner.print_summary()
        scanner.export_results()
    else:
        scanner.print_summary()
    
    return results


if __name__ == '__main__':
    main()
