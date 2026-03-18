#!/usr/bin/env python3
"""
NPS Value Scanner - Ultra Fast Mode (Cache Only, No API)
N01 전략: DB 캐시만 사용하여 고속 분석
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
import sqlite3
import warnings
warnings.filterwarnings('ignore')

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


class NPSValueScannerN01UltraFast:
    """N01 Ultra Fast Scanner - Uses DB cache only, no API calls"""
    
    def __init__(self):
        self.results: List[NPSStockData] = []
        self.disclosure_stocks = self._get_disclosure_stocks()
        
        logger.info("🚀 N01 NPS Ultra Fast Scanner initialized")
        logger.info(f"   Stocks with disclosure data: {len(self.disclosure_stocks)}")
    
    def _get_disclosure_stocks(self) -> List[Dict]:
        """Get stocks with disclosure data from both databases"""
        stocks = {}
        
        # 1. Get from dart_focused.db
        try:
            conn = sqlite3.connect('./data/dart_focused.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT stock_code, COUNT(*) as count 
                FROM financial_statements 
                WHERE stock_code IS NOT NULL 
                GROUP BY stock_code
            ''')
            for row in cursor.fetchall():
                if row[0]:
                    stocks[row[0]] = {'count': row[1], 'source': 'focused'}
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ dart_focused.db error: {e}")
        
        # 2. Get from dart_cache.db
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
            
            for row in cursor.fetchall():
                if row[0] and row[0] not in stocks:
                    stocks[row[0]] = {'count': row[1], 'source': 'cache'}
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ dart_cache.db error: {e}")
        
        return [{'symbol': k, **v} for k, v in stocks.items()]
    
    def get_stock_data_from_db(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get stock price data from DB only (no API)"""
        try:
            conn = sqlite3.connect('./data/pivot_strategy.db')
            query = '''
                SELECT date, open, high, low, close, volume
                FROM stock_prices
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 252
            '''
            df = pd.read_sql_query(query, conn, params=(symbol,))
            conn.close()
            
            if len(df) >= 20:
                df = df.sort_values('date')
                return df
            return None
        except Exception as e:
            logger.debug(f"DB error for {symbol}: {e}")
            return None
    
    def analyze_stock(self, row: pd.Series) -> Optional[NPSStockData]:
        """Analyze single stock using DB data only"""
        symbol = row['symbol']
        name = row['name']
        sector = row.get('sector', 'N/A')
        
        try:
            # Get price data from DB
            df = self.get_stock_data_from_db(symbol)
            if df is None or len(df) < 20:
                return None
            
            current_price = df['close'].iloc[-1]
            volume_avg = df['volume'].mean()
            
            # Basic filters
            if current_price < 1000:
                return None
            if volume_avg < 1e7:
                return None
            
            # Calculate returns
            returns_1y = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
            
            # Volatility
            daily_returns = df['close'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252) * 100
            
            # Get disclosure count
            disclosure_count = row.get('disclosure_count', 0)
            
            # Scoring
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
            
            if volatility < 20:
                score_stability = 80
            elif volatility < 30:
                score_stability = 60
            elif volatility < 40:
                score_stability = 40
            else:
                score_stability = 20
            
            if disclosure_count > 1000:
                score_value = 80
            elif disclosure_count > 500:
                score_value = 60
            elif disclosure_count > 100:
                score_value = 40
            else:
                score_value = 20
            
            score_nps = 50
            
            total_score = (
                score_momentum * 0.30 +
                score_stability * 0.25 +
                score_value * 0.20 +
                score_nps * 0.25
            )
            
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
    
    def get_stock_universe(self) -> pd.DataFrame:
        """Get stock universe"""
        logger.info("📊 Loading stock universe...")
        
        conn = sqlite3.connect('./data/pivot_strategy.db')
        query = '''
            SELECT s.symbol, s.name, s.market, s.sector
            FROM stock_info s
            ORDER BY s.symbol
        '''
        all_stocks = pd.read_sql_query(query, conn)
        conn.close()
        
        # Filter to stocks with disclosure data
        disclosure_symbols = {s['symbol'] for s in self.disclosure_stocks}
        filtered = all_stocks[all_stocks['symbol'].isin(disclosure_symbols)].copy()
        
        # Add disclosure count
        disclosure_map = {s['symbol']: s['count'] for s in self.disclosure_stocks}
        filtered['disclosure_count'] = filtered['symbol'].map(disclosure_map)
        
        # Exclude financials
        exclude_sectors = ['은행', '증권', '보험', '금융']
        mask = ~filtered['sector'].str.contains('|'.join(exclude_sectors), na=False)
        filtered = filtered[mask]
        
        logger.info(f"✅ Loaded {len(filtered)} stocks")
        return filtered
    
    def run_scan(self) -> List[NPSStockData]:
        """Run N01 scan"""
        logger.info("=" * 70)
        logger.info("🔍 N01 Strategy: NPS Value Scanner (Ultra Fast Mode)")
        logger.info("=" * 70)
        
        universe = self.get_stock_universe()
        if universe.empty:
            logger.error("❌ No stocks in universe")
            return []
        
        results = []
        total = len(universe)
        
        for idx, (_, row) in enumerate(universe.iterrows(), 1):
            if idx % 200 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")
            
            result = self.analyze_stock(row)
            if result:
                results.append(result)
                logger.info(f"✅ {result.name}: Score {result.total_score:.1f} (Grade {result.grade})")
        
        results.sort(key=lambda x: x.total_score, reverse=True)
        
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
        print("🏛️ N01 NPS Value Scanner - Results")
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
        
        json_path = f"{output_dir}/n01_ufast_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        
        csv_path = f"{output_dir}/n01_ufast_{timestamp}.csv"
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"💾 Exported: {json_path}, {csv_path}")
        return {'json': json_path, 'csv': csv_path}


def main():
    scanner = NPSValueScannerN01UltraFast()
    results = scanner.run_scan()
    
    if results:
        scanner.print_summary()
        scanner.export_results()
    else:
        print("\n❌ No stocks passed filters")
    
    return results


if __name__ == '__main__':
    main()
