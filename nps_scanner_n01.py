"""
NPS Value Scanner - Production Version with Disclosure Validation
N01 전략: 국민연금 가치 투자 패턴 (공시 정보 기반)
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
    
    # Disclosure info
    has_disclosure: bool = False
    disclosure_count: int = 0
    
    # Technical metrics
    returns_1y: float = 0.0
    volatility: float = 0.0
    volume_avg: float = 0.0
    
    # Scores (NPS 4-Filter logic)
    score_momentum: float = 0.0  # ROE proxy
    score_stability: float = 0.0  # Dividend proxy  
    score_value: float = 0.0  # PBR proxy
    score_nps: float = 50.0  # Placeholder for NPS ownership
    total_score: float = 0.0
    grade: str = 'D'
    rank: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class NPSValueScannerN01:
    """
    N01 Strategy: NPS Value Scanner
    - Filters stocks with disclosure data available
    - Uses technical indicators as proxies for fundamental metrics
    - Implements NPS 4-Filter scoring logic
    """
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.dart = DartDisclosureWrapper()
        self.results: List[NPSStockData] = []
        self.excluded_stocks: List[Tuple[str, str]] = []
        
        # Filters
        self.min_price = 1000
        self.min_volume = 1e7  # 1000만
        self.exclude_sectors = ['은행', '증권', '보험', '금융']
        
        logger.info("🚀 N01 NPS Value Scanner initialized")
        logger.info(f"   DART Cache DB: {self.dart.db.db_path}")
    
    def check_disclosure_available(self, symbol: str) -> Tuple[bool, int]:
        """
        Check if disclosure data is available (cache or API)
        Returns: (available, count)
        """
        try:
            corp_code = self.dart.get_corp_code(symbol)
            if not corp_code:
                return (False, 0)
            
            # Try to get disclosures (cache first)
            disclosures = self.dart.list_disclosures(corp_code)
            if disclosures is not None and len(disclosures) > 0:
                return (True, len(disclosures))
            
            # Check cache directly (fallback)
            cached = self.dart.db.get_disclosures(corp_code, check_expiry=False)
            if cached is not None and len(cached) > 0:
                return (True, len(cached))
            
            return (False, 0)
            
        except Exception as e:
            return (False, 0)
    
    def get_stock_universe(self) -> pd.DataFrame:
        """Get stock universe (financial sector excluded)"""
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
            
            logger.info(f"✅ Loaded {len(stocks)} stocks (financial sector excluded)")
            return stocks
            
        except Exception as e:
            logger.error(f"❌ Failed to load stocks: {e}")
            return pd.DataFrame()
    
    def analyze_stock(self, row: pd.Series) -> Optional[NPSStockData]:
        """Analyze single stock with NPS 4-Filter logic"""
        symbol = row['symbol']
        name = row['name']
        sector = row.get('sector', 'Unknown')
        
        try:
            # Step 1: Check disclosure availability
            has_disclosure, disc_count = self.check_disclosure_available(symbol)
            if not has_disclosure:
                self.excluded_stocks.append((symbol, "No disclosure data"))
                return None
            
            # Step 2: Get price data
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            df = self.fdr.get_price(symbol, start=start_date, end=end_date)
            if df is None or len(df) < 50:
                self.excluded_stocks.append((symbol, "Insufficient price data"))
                return None
            
            current_price = df['Close'].iloc[-1]
            
            # Filter: minimum price
            if current_price < self.min_price:
                self.excluded_stocks.append((symbol, f"Price too low ({current_price:,.0f})"))
                return None
            
            # Calculate metrics
            returns_1y = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
            daily_returns = df['Close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252)
            volume_avg = df['Volume'].mean()
            
            if volume_avg < self.min_volume:
                self.excluded_stocks.append((symbol, "Volume too low"))
                return None
            
            # NPS 4-Filter Scoring
            
            # Filter 1: Momentum score (ROE proxy)
            # Consistent positive returns = good "ROE"
            if returns_1y >= 0.10:  # >10% annual return
                momentum_score = 90
            elif returns_1y >= 0.05:
                momentum_score = 75
            elif returns_1y >= 0.0:
                momentum_score = 60
            elif returns_1y >= -0.10:
                momentum_score = 40
            else:
                momentum_score = 20
            
            # Filter 2: Stability score (Dividend consistency proxy)
            # Low volatility = stable "dividend" pattern
            if volatility < 0.25:
                stability_score = 90
            elif volatility < 0.35:
                stability_score = 70
            elif volatility < 0.45:
                stability_score = 50
            else:
                stability_score = 30
            
            # Filter 3: Value score (PBR proxy)
            # Price relative to moving averages
            ma60 = df['Close'].rolling(60).mean().iloc[-1]
            ma120 = df['Close'].rolling(120).mean().iloc[-1]
            
            if current_price < ma60 and current_price < ma120:
                value_score = 90  # Below both MAs = undervalued
            elif current_price < ma60:
                value_score = 70
            elif current_price < ma120:
                value_score = 50
            else:
                value_score = 30
            
            # Filter 4: NPS score (placeholder - would need NPS ownership data)
            # For now, use disclosure count as proxy
            if disc_count > 1000:
                nps_score = 80
            elif disc_count > 500:
                nps_score = 60
            else:
                nps_score = 40
            
            # Total score (NPS 4-Filter weights)
            total_score = (
                momentum_score * 0.40 +   # ROE weight
                stability_score * 0.25 +   # Dividend weight
                value_score * 0.20 +       # PBR weight
                nps_score * 0.15           # NPS weight
            )
            
            # Assign grade
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
            self.excluded_stocks.append((symbol, f"Analysis error: {str(e)[:30]}"))
            logger.debug(f"Analysis failed for {symbol}: {e}")
            return None
    
    def run_scan(self, max_stocks: Optional[int] = None) -> List[NPSStockData]:
        """Run N01 scanning pipeline"""
        logger.info("=" * 70)
        logger.info("🔍 N01 Strategy: NPS Value Scanner (with Disclosure Validation)")
        logger.info("=" * 70)
        
        universe = self.get_stock_universe()
        if universe.empty:
            return []
        
        if max_stocks:
            universe = universe.head(max_stocks)
        
        results = []
        total = len(universe)
        
        logger.info(f"🎯 Scanning {total} stocks...")
        logger.info("   (Stocks without disclosure data will be auto-excluded)")
        
        for idx, (_, row) in enumerate(universe.iterrows(), 1):
            if idx % 100 == 0:
                progress = idx / total * 100
                logger.info(f"Progress: {idx}/{total} ({progress:.1f}%) | Selected: {len(results)}")
            
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
        logger.info(f"   Total universe: {total}")
        logger.info(f"   Selected: {len(results)}")
        logger.info(f"   Excluded: {len(self.excluded_stocks)}")
        if total > 0:
            logger.info(f"   Selection rate: {len(results)/total*100:.1f}%")
        
        return results
    
    def print_summary(self):
        """Print results summary"""
        print("\n" + "=" * 80)
        print("🏛️ N01 NPS Value Scanner - Results")
        print("=" * 80)
        
        if not self.results:
            print("❌ No stocks passed all filters")
            print(f"\n📉 Excluded stocks breakdown:")
            from collections import Counter
            reasons = [reason for _, reason in self.excluded_stocks]
            reason_counts = Counter(reasons)
            for reason, count in reason_counts.most_common(10):
                print(f"   {count:4d} | {reason[:50]}")
            return
        
        # A-grade stocks
        a_grade = [r for r in self.results if r.grade == 'A']
        print(f"\n🌟 A-Grade Stocks: {len(a_grade)}")
        print("-" * 80)
        
        for r in a_grade[:10]:
            print(f"  {r.rank:2d}. [{r.symbol}] {r.name:20s} | Score: {r.total_score:.1f}")
            print(f"      Return: {r.returns_1y*100:+.1f}% | Vol: {r.volatility*100:.1f}% | Disclosures: {r.disclosure_count}")
        
        # Top 20 summary
        print(f"\n📊 Top 20 Stocks:")
        print("-" * 80)
        print(f"{'Rank':<6}{'Symbol':<10}{'Name':<20}{'Grade':<8}{'Score':<8}{'Return':<10}")
        print("-" * 80)
        
        for r in self.results[:20]:
            print(f"{r.rank:<6}{r.symbol:<10}{r.name:<20}{r.grade:<8}{r.total_score:<7.1f}{r.returns_1y*100:<+9.1f}%")
        
        # Grade distribution
        print("\n📈 Grade Distribution:")
        grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        for r in self.results:
            grades[r.grade] = grades.get(r.grade, 0) + 1
        for g in ['A', 'B', 'C', 'D']:
            bar = '█' * grades[g]
            print(f"  Grade {g}: {grades[g]:3d} {bar}")
        
        print("=" * 80)
    
    def export_results(self, output_dir: str = './reports/nps_value') -> Dict[str, str]:
        """Export results to files"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        files = {}
        
        # JSON
        json_path = f"{output_dir}/n01_nps_value_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        files['json'] = json_path
        
        # CSV
        csv_path = f"{output_dir}/n01_nps_value_{timestamp}.csv"
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        files['csv'] = csv_path
        
        # Excluded stocks
        if self.excluded_stocks:
            failed_path = f"{output_dir}/n01_excluded_{timestamp}.csv"
            failed_df = pd.DataFrame(self.excluded_stocks, columns=['symbol', 'reason'])
            failed_df.to_csv(failed_path, index=False, encoding='utf-8-sig')
            files['excluded'] = failed_path
        
        logger.info(f"💾 Exported:")
        for k, v in files.items():
            logger.info(f"   {k}: {v}")
        
        return files


def main():
    """Main entry point"""
    scanner = NPSValueScannerN01()
    results = scanner.run_scan()
    
    if results:
        scanner.print_summary()
        scanner.export_results()
    else:
        scanner.print_summary()
    
    return results


if __name__ == '__main__':
    main()
