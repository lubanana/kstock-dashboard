#!/usr/bin/env python3
"""
NPS Value Scanner - Fast Mode v2 (Dual Database Support)
N01 전략: dart_cache.db + dart_focused.db 동시 활용
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
import sqlite3
import warnings
warnings.filterwarnings('ignore')

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


class NPSValueScannerN01FastV2:
    """N01 Fast Scanner v2 - Uses both dart_cache.db and dart_focused.db"""
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.results: List[NPSStockData] = []
        self.excluded_stocks: List[Tuple[str, str]] = []
        
        self.min_price = 1000
        self.min_volume = 1e7
        self.exclude_sectors = ['은행', '증권', '보험', '금융']
        
        # Get stocks with disclosure data from BOTH databases
        self.disclosure_stocks = self._get_disclosure_stocks()
        
        logger.info("🚀 N01 NPS Fast Scanner v2 initialized")
        logger.info(f"   Stocks with disclosure data: {len(self.disclosure_stocks)}")
        logger.info(f"   - From dart_cache.db: {len([s for s in self.disclosure_stocks if s['source'] == 'cache'])}")
        logger.info(f"   - From dart_focused.db: {len([s for s in self.disclosure_stocks if s['source'] == 'focused'])}")
    
    def _get_disclosure_stocks(self) -> List[Dict]:
        """Get stocks with disclosure data from both databases"""
        stocks = []
        cache_symbols = set()
        
        # 1. Get from dart_focused.db (NEW - has more data)
        try:
            conn = sqlite3.connect('./data/dart_focused.db')
            cursor = conn.cursor()
            
            # Get stocks with financial statements
            cursor.execute('''
                SELECT DISTINCT stock_code, COUNT(*) as count 
                FROM financial_statements 
                WHERE stock_code IS NOT NULL 
                GROUP BY stock_code
            ''')
            for row in cursor.fetchall():
                if row[0]:
                    stocks.append({
                        'symbol': row[0],
                        'count': row[1],
                        'source': 'focused',
                        'type': 'financial'
                    })
                    cache_symbols.add(row[0])
            
            # Get stocks with shareholding disclosures
            cursor.execute('''
                SELECT DISTINCT stock_code, COUNT(*) as count 
                FROM shareholding_disclosures 
                WHERE stock_code IS NOT NULL 
                GROUP BY stock_code
            ''')
            for row in cursor.fetchall():
                if row[0] and row[0] not in cache_symbols:
                    stocks.append({
                        'symbol': row[0],
                        'count': row[1],
                        'source': 'focused',
                        'type': 'shareholding'
                    })
                    cache_symbols.add(row[0])
            
            conn.close()
            logger.info(f"✅ Loaded {len(stocks)} stocks from dart_focused.db")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load from dart_focused.db: {e}")
        
        # 2. Get from dart_cache.db (fallback)
        try:
            conn = sqlite3.connect('./data/dart_cache.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ci.stock_code, COUNT(d.id) as count
                FROM company_info ci
                LEFT JOIN disclosures d ON ci.corp_code = d.corp_code
                WHERE ci.stock_code IS NOT NULL
                GROUP BY ci.stock_code
                HAVING count > 0
            ''')
            
            added = 0
            for row in cursor.fetchall():
                if row[0] and row[0] not in cache_symbols:
                    stocks.append({
                        'symbol': row[0],
                        'count': row[1],
                        'source': 'cache',
                        'type': 'disclosure'
                    })
                    cache_symbols.add(row[0])
                    added += 1
            
            conn.close()
            logger.info(f"✅ Loaded {added} additional stocks from dart_cache.db")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load from dart_cache.db: {e}")
        
        return stocks
    
    def get_stock_universe(self) -> pd.DataFrame:
        """Get stock universe with disclosure data"""
        logger.info("📊 Loading stock universe...")
        
        # Get stock info from main DB
        conn = sqlite3.connect('./data/pivot_strategy.db')
        query = '''
            SELECT s.symbol, s.name, s.market, s.sector
            FROM stock_info s
            ORDER BY s.symbol
        '''
        all_stocks = pd.read_sql_query(query, conn)
        conn.close()
        
        # Filter to only stocks with disclosure data
        disclosure_symbols = {s['symbol'] for s in self.disclosure_stocks}
        filtered = all_stocks[all_stocks['symbol'].isin(disclosure_symbols)].copy()
        
        # Add disclosure count
        disclosure_map = {s['symbol']: s['count'] for s in self.disclosure_stocks}
        filtered['disclosure_count'] = filtered['symbol'].map(disclosure_map)
        
        # Filter out financials
        if self.exclude_sectors:
            mask = ~filtered['sector'].str.contains('|'.join(self.exclude_sectors), na=False)
            filtered = filtered[mask]
        
        logger.info(f"✅ Loaded {len(filtered)} stocks with disclosure data")
        return filtered
    
    def calculate_returns(self, symbol: str) -> Tuple[float, float]:
        """Calculate 1-year returns and volatility"""
        try:
            df = self.fdr.get_price(symbol, min_days=252)
            if df is None or len(df) < 50:
                return 0.0, 0.0
            
            # 1-year return
            returns = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
            
            # Volatility (annualized)
            daily_returns = df['close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252) * 100
            
            return returns, volatility
        except Exception as e:
            logger.debug(f"Failed to calculate returns for {symbol}: {e}")
            return 0.0, 0.0
    
    def analyze_stock(self, row) -> Optional[NPSStockData]:
        """Analyze single stock"""
        symbol = row['symbol']
        name = row['name']
        sector = row.get('sector', 'N/A')
        
        try:
            # Get price data
            df = self.fdr.get_price(symbol, min_days=20)
            if df is None or len(df) < 5:
                return None
            
            current_price = df['close'].iloc[-1]
            volume_avg = df['volume'].mean()
            
            # Basic filters
            if current_price < self.min_price:
                return None
            if volume_avg < self.min_volume:
                return None
            
            # Calculate returns
            returns_1y, volatility = self.calculate_returns(symbol)
            
            # Get disclosure count
            disclosure_count = row.get('disclosure_count', 0)
            
            # Scoring (simplified version for fast mode)
            # Momentum score (based on 1Y return)
            if returns_1y > 100:
                score_momentum = 90
            elif returns_1y > 50:
                score_momentum = 80
            elif returns_1y > 20:
                score_momentum = 70
            elif returns_1y > 0:
                score_momentum = 60
            else:
                score_momentum = 40
            
            # Stability score (inverse of volatility)
            if volatility < 20:
                score_stability = 80
            elif volatility < 30:
                score_stability = 60
            elif volatility < 40:
                score_stability = 40
            else:
                score_stability = 20
            
            # Value score (based on disclosure count as proxy for transparency)
            if disclosure_count > 1000:
                score_value = 80
            elif disclosure_count > 500:
                score_value = 60
            elif disclosure_count > 100:
                score_value = 40
            else:
                score_value = 20
            
            # NPS score (placeholder - would need actual NPS data)
            score_nps = 50
            
            # Calculate total score
            total_score = (
                score_momentum * 0.30 +
                score_stability * 0.25 +
                score_value * 0.20 +
                score_nps * 0.25
            )
            
            # Grade
            if total_score >= 85:
                grade = 'A'
            elif total_score >= 70:
                grade = 'B'
            elif total_score >= 55:
                grade = 'C'
            elif total_score >= 40:
                grade = 'D'
            else:
                grade = 'F'
            
            return NPSStockData(
                symbol=symbol,
                name=name,
                sector=sector,
                current_price=current_price,
                has_disclosure=True,
                disclosure_count=disclosure_count,
                returns_1y=returns_1y,
                volatility=volatility,
                volume_avg=volume_avg,
                score_momentum=score_momentum,
                score_stability=score_stability,
                score_value=score_value,
                score_nps=score_nps,
                total_score=total_score,
                grade=grade
            )
            
        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            return None
    
    def run_scan(self) -> List[NPSStockData]:
        """Run N01 scan"""
        logger.info("=" * 70)
        logger.info("🔍 N01 Strategy: NPS Value Scanner (Fast Mode v2)")
        logger.info("=" * 70)
        
        universe = self.get_stock_universe()
        if universe.empty:
            logger.error("❌ No stocks in universe")
            return []
        
        results = []
        total = len(universe)
        
        for idx, (_, row) in enumerate(universe.iterrows(), 1):
            if idx % 100 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")
            
            result = self.analyze_stock(row)
            if result and result.total_score >= 60:  # Only include B grade or better
                results.append(result)
                logger.info(f"✅ {result.name}: Score {result.total_score:.1f} (Grade {result.grade})")
        
        # Sort by score
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        # Assign ranks
        for i, r in enumerate(results, 1):
            r.rank = i
        
        self.results = results
        logger.info(f"🎉 Scan complete! {len(results)} stocks passed filters")
        
        return results
    
    def print_summary(self):
        """Print summary"""
        if not self.results:
            print("\n❌ No stocks passed filters")
            return
        
        print("\n" + "=" * 80)
        print("🏛️ N01 NPS Value Scanner v2 - Results")
        print("=" * 80)
        print(f"{'Rank':<6}{'Symbol':<10}{'Name':<18}{'Grade':<8}{'Score':<10}{'Return':<12}{'Disclosures'}")
        print("-" * 80)
        
        for r in self.results[:20]:
            print(f"{r.rank:<6}{r.symbol:<10}{r.name:<18}{r.grade:<8}{r.total_score:<10.1f}{r.returns_1y:<11.1f}% {r.disclosure_count}")
        
        print("=" * 80)
    
    def export_results(self, output_dir: str = './reports/nps_value') -> Dict[str, str]:
        """Export results"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # JSON
        json_path = f"{output_dir}/n01_v2_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        
        # CSV
        csv_path = f"{output_dir}/n01_v2_{timestamp}.csv"
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"💾 Exported: {json_path}, {csv_path}")
        return {'json': json_path, 'csv': csv_path}


def main():
    """Main execution"""
    scanner = NPSValueScannerN01FastV2()
    results = scanner.run_scan()
    
    if results:
        scanner.print_summary()
        scanner.export_results()
    else:
        print("\n❌ No stocks passed filters")
    
    return results


if __name__ == '__main__':
    main()
