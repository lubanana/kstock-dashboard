"""
NPS Value Scanner - Simplified Version
Uses available data sources for quick scanning
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import wrappers
from fdr_wrapper import FDRWrapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NPSStockData:
    """Stock data container"""
    symbol: str
    name: str
    sector: str
    current_price: float
    
    # Technical metrics (as proxy for fundamentals)
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


class NPSScannerSimplified:
    """Simplified NPS-style scanner using technical indicators"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.results: List[NPSStockData] = []
        
        # Filters
        self.min_price = 1000
        self.min_volume = 1e7  # 1000만 (완화)
        self.exclude_sectors = ['은행', '증권', '보험', '금융']
        
        logger.info("🚀 NPS Simplified Scanner initialized")
    
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
            return pd.DataFrame()
    
    def analyze_stock(self, row: pd.Series) -> Optional[NPSStockData]:
        """Analyze single stock"""
        symbol = row['symbol']
        name = row['name']
        sector = row.get('sector', 'Unknown')
        
        try:
            # Get 1 year of price data
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            df = self.fdr.get_price(symbol, start=start_date, end=end_date)
            if df is None or len(df) < 50:  # 50일만 있으면 OK (완화)
                return None
            
            current_price = df['Close'].iloc[-1]
            
            # Filter: minimum price
            if current_price < self.min_price:
                return None
            
            # Calculate returns
            returns_1y = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
            
            # Calculate volatility (annualized)
            daily_returns = df['Close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252)
            
            # Volume
            volume_avg = df['Volume'].mean()
            if volume_avg < self.min_volume:
                return None
            
            # Calculate scores (NPS-style logic)
            
            # Momentum score (like ROE consistency)
            # Accept some negative returns but prefer positive
            if returns_1y >= -0.20:  # -20% 이상만 OK
                momentum_score = 50 + (returns_1y * 100)  # -20% = 30점, 0% = 50점, +20% = 70점
                momentum_score = max(0, min(100, momentum_score))
            else:
                momentum_score = 0
            
            # Stability score (like dividend consistency)
            # Lower volatility = higher score
            if volatility < 0.20:
                stability_score = 90
            elif volatility < 0.30:
                stability_score = 70
            elif volatility < 0.40:
                stability_score = 50
            else:
                stability_score = max(0, 30 - (volatility - 0.40) * 50)
            
            # Value score (like low PBR)
            # Price relative to moving averages
            ma60 = df['Close'].rolling(60).mean().iloc[-1]
            ma120 = df['Close'].rolling(120).mean().iloc[-1]
            
            if current_price < ma60 and current_price < ma120:
                # Below averages = potentially undervalued
                value_score = 80
            elif current_price < ma60:
                value_score = 60
            else:
                value_score = 40
            
            # Total score (weighted like NPS)
            total_score = (
                momentum_score * 0.40 +   # Like ROE
                stability_score * 0.25 +   # Like dividend
                value_score * 0.20 +       # Like PBR
                50 * 0.15                  # Placeholder for NPS
            )
            
            return NPSStockData(
                symbol=symbol,
                name=name,
                sector=sector,
                current_price=current_price,
                returns_1y=returns_1y,
                volatility=volatility,
                volume_avg=volume_avg,
                score_momentum=momentum_score,
                score_stability=stability_score,
                score_value=value_score,
                total_score=total_score
            )
            
        except Exception as e:
            logger.debug(f"Analysis failed for {symbol}: {e}")
            return None
    
    def run_scan(self, max_stocks: Optional[int] = None) -> List[NPSStockData]:
        """Run scanning pipeline"""
        logger.info("=" * 60)
        logger.info("🔍 Starting NPS Simplified Scanner")
        logger.info("=" * 60)
        
        universe = self.get_stock_universe()
        if universe.empty:
            return []
        
        if max_stocks:
            universe = universe.head(max_stocks)
        
        results = []
        total = len(universe)
        
        for idx, (_, row) in enumerate(universe.iterrows(), 1):
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")
            
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
        print("🏛️ NPS Value Scanner (Simplified) - Results")
        print("=" * 80)
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
        json_path = f"{output_dir}/nps_simplified_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        
        # CSV
        csv_path = f"{output_dir}/nps_simplified_{timestamp}.csv"
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"💾 Exported: {json_path}, {csv_path}")
        
        return {'json': json_path, 'csv': csv_path}


def main():
    """Main"""
    scanner = NPSScannerSimplified()
    results = scanner.run_scan()
    
    if results:
        scanner.print_summary()
        scanner.export_results()
    else:
        print("❌ No stocks found")
    
    return results


if __name__ == '__main__':
    main()
