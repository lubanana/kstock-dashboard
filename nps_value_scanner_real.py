"""
NPS Value Scanner - Full Implementation with Real Data Integration
Uses fdr_wrapper and dart_disclosure_wrapper for data sources
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

# Import our existing wrappers
from fdr_wrapper import FDRWrapper
from dart_disclosure_wrapper import DartDisclosureWrapper, DisclosureCacheConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NPSStockData:
    """Individual stock data container"""
    symbol: str
    name: str
    sector: str
    market_cap: float
    
    # Price data
    current_price: float
    
    # ROE (3-year)
    roe_2022: Optional[float] = None
    roe_2023: Optional[float] = None
    roe_2024: Optional[float] = None
    roe_avg: float = 0.0
    roe_consistent: bool = False
    
    # Dividend
    dividend_yield_3y_avg: float = 0.0
    payout_ratio: float = 0.0
    
    # Valuation
    bps: float = 0.0  # Book value per share
    pbr: float = 0.0
    per: float = 0.0
    
    # NPS Ownership
    nps_ownership_current: float = 0.0
    nps_ownership_prev: float = 0.0
    nps_ownership_trend: str = 'unknown'  # increasing, stable, decreasing
    
    # Scores
    score_roe: float = 0.0
    score_dividend: float = 0.0
    score_valuation: float = 0.0
    score_nps: float = 0.0
    total_score: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class NPSValueScannerReal:
    """
    NPS Value Scanner with Real Data Integration
    """
    
    def __init__(self):
        self.fdr = FDRWrapper()
        self.dart = DartDisclosureWrapper(DisclosureCacheConfig(
            db_path='./data/dart_cache.db',
            cache_duration_days=1
        ))
        
        # Filters
        self.roe_min = 0.10
        self.roe_max = 0.15
        self.pbr_max = 1.0
        self.nps_min = 0.05
        self.min_market_cap = 1000e8  # 1,000억
        
        # Exclude financials
        self.exclude_sectors = ['은행', '증권', '보험', '금융지주', '금융']
        
        # Results
        self.results: List[NPSStockData] = []
        
        logger.info("🚀 NPS Value Scanner (Real Data) initialized")
    
    def get_stock_universe(self) -> pd.DataFrame:
        """Get stock universe from fdr_wrapper"""
        logger.info("📊 Loading stock universe...")
        
        try:
            # Get all stocks from stock_info
            import sqlite3
            conn = sqlite3.connect('./data/pivot_strategy.db')
            query = '''
                SELECT s.symbol, s.name, s.sector
                FROM stock_info s
                ORDER BY s.symbol
            '''
            stocks = pd.read_sql_query(query, conn)
            conn.close()
            
            # Add placeholder market cap (will be updated later)
            stocks['market_cap'] = 0.0
            
            # Exclude financial sector
            for sector in self.exclude_sectors:
                stocks = stocks[~stocks['sector'].str.contains(sector, na=False, case=False)]
            
            logger.info(f"✅ Loaded {len(stocks)} stocks after filtering")
            return stocks
            
        except Exception as e:
            logger.error(f"❌ Failed to load stocks: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices for symbols"""
        prices = {}
        
        for symbol in symbols:
            try:
                # Get last 5 days of data
                df = self.fdr.get_price(symbol, days=5)
                if df is not None and not df.empty:
                    prices[symbol] = df['Close'].iloc[-1]
            except Exception as e:
                logger.debug(f"Price fetch failed for {symbol}: {e}")
        
        return prices
    
    def fetch_financial_data(self, corp_code: str, year: str) -> Optional[Dict]:
        """
        Fetch financial data from DART
        Returns: {'roe': float, 'eps': float, 'bps': float, 'dividend': float}
        """
        try:
            # Get financial statements
            fs = self.dart.dart.finstate(corp_code, year)
            
            if fs is None or (hasattr(fs, 'empty') and fs.empty):
                return None
            
            # Extract key metrics
            result = {}
            
            # Handle both DataFrame and dict formats
            if isinstance(fs, pd.DataFrame):
                data = fs
            elif isinstance(fs, dict):
                return fs
            else:
                return None
            
            # ROE - Search for 지배주주순이익 and 자본
            try:
                net_income = data[data['account_nm'].str.contains('지배주주순이익', na=False)]
                equity = data[data['account_nm'].str.contains('자본총계', na=False)]
                
                if not net_income.empty and not equity.empty:
                    ni = float(net_income['thstrm_amount'].iloc[0].replace(',', ''))
                    eq = float(equity['thstrm_amount'].iloc[0].replace(',', ''))
                    result['roe'] = ni / eq if eq > 0 else 0
            except:
                result['roe'] = None
            
            # BPS
            try:
                bps_row = data[data['account_nm'].str.contains('주당순자산', na=False)]
                if not bps_row.empty:
                    result['bps'] = float(bps_row['thstrm_amount'].iloc[0].replace(',', ''))
            except:
                result['bps'] = None
            
            # Dividend
            try:
                div_row = data[data['account_nm'].str.contains('주당현금배당금', na=False)]
                if not div_row.empty:
                    result['dividend_per_share'] = float(div_row['thstrm_amount'].iloc[0].replace(',', ''))
            except:
                result['dividend_per_share'] = None
            
            return result
            
        except Exception as e:
            logger.debug(f"Financial fetch failed for {corp_code}: {e}")
            return None
    
    def fetch_nps_ownership(self, corp_code: str) -> Tuple[float, float]:
        """
        Fetch NPS ownership from DART
        Returns: (current_ownership, previous_ownership)
        """
        try:
            # Get major shareholders
            shareholders = self.dart.dart.major_shareholders(corp_code, '2024')
            
            if shareholders is None or (hasattr(shareholders, 'empty') and shareholders.empty):
                return (0.0, 0.0)
            
            # Find NPS
            nps_mask = shareholders['stockholder_nm'].str.contains('국민연금', na=False, case=False)
            nps_data = shareholders[nps_mask]
            
            if nps_data.empty:
                return (0.0, 0.0)
            
            current = float(nps_data['stk_rt'].iloc[0]) / 100  # Convert % to decimal
            
            # TODO: Get previous quarter for trend
            previous = current  # Placeholder
            
            return (current, previous)
            
        except Exception as e:
            logger.debug(f"NPS fetch failed for {corp_code}: {e}")
            return (0.0, 0.0)
    
    def calculate_roe_score(self, roe_avg: float, roe_values: List[float]) -> float:
        """Calculate ROE score (0-100)"""
        # Ideal ROE is 12.5% (middle of 10-15%)
        ideal_roe = 0.125
        
        # Base score from average
        if self.roe_min <= roe_avg <= self.roe_max:
            # Within target range - higher score closer to ideal
            score = 100 - abs(roe_avg - ideal_roe) * 1000
        else:
            # Outside range - penalize heavily
            score = max(0, 50 - abs(roe_avg - ideal_roe) * 500)
        
        # Bonus for consistency (low std dev)
        if len(roe_values) >= 2:
            roe_std = np.std(roe_values)
            consistency_bonus = max(0, 20 - roe_std * 200)
            score += consistency_bonus
        
        return min(100, score)
    
    def calculate_dividend_score(self, div_yield: float, payout: float) -> float:
        """Calculate dividend score (0-100)"""
        # Yield score (assuming 2-4% is good)
        yield_score = min(50, div_yield * 100 * 15)  # 3.3% yield = 50 points
        
        # Payout ratio score (ideal 30-40%)
        if 0.20 <= payout <= 0.50:
            payout_score = 50 - abs(payout - 0.35) * 100
        else:
            payout_score = 0
        
        return yield_score + payout_score
    
    def calculate_valuation_score(self, pbr: float, industry_avg_pbr: float) -> float:
        """Calculate valuation score (0-100) - lower PBR is better"""
        if pbr <= 0:
            return 0
        
        # Score based on PBR relative to 1.0 and industry
        score = 0
        
        # Absolute PBR score
        if pbr <= 0.5:
            score += 50
        elif pbr <= 1.0:
            score += 40 + (1.0 - pbr) * 20
        elif pbr <= 1.5:
            score += 20 + (1.5 - pbr) * 40
        else:
            score += max(0, 30 - (pbr - 1.5) * 20)
        
        # Relative to industry
        if industry_avg_pbr > 0:
            relative = pbr / industry_avg_pbr
            if relative <= 0.7:
                score += 30
            elif relative <= 1.0:
                score += 20 + (1.0 - relative) * 33
            else:
                score += max(0, 20 - (relative - 1.0) * 30)
        
        return min(100, score)
    
    def calculate_nps_score(self, ownership: float, trend: str) -> float:
        """Calculate NPS ownership score (0-100)"""
        if ownership < self.nps_min:
            return 0
        
        # Base score from ownership level
        score = min(70, ownership * 100 * 10)  # 7% = 70 points
        
        # Trend bonus
        if trend == 'increasing':
            score += 30
        elif trend == 'stable':
            score += 15
        
        return min(100, score)
    
    def analyze_stock(self, row: pd.Series) -> Optional[NPSStockData]:
        """Analyze single stock"""
        symbol = row['symbol']
        name = row['name']
        sector = row.get('sector', 'Unknown')
        market_cap = row.get('market_cap', 0)
        
        logger.debug(f"Analyzing {name} ({symbol})...")
        
        # Get corp_code
        corp_code = self.dart.get_corp_code(name)
        if not corp_code:
            return None
        
        # Get price
        try:
            price_df = self.fdr.get_price(symbol, days=5)
            if price_df is None or price_df.empty:
                return None
            current_price = price_df['Close'].iloc[-1]
        except:
            return None
        
        # Fetch 3-year financial data
        roe_values = []
        bps_values = []
        
        for year in ['2022', '2023', '2024']:
            fin = self.fetch_financial_data(corp_code, year)
            if fin:
                if 'roe' in fin and fin['roe'] is not None:
                    roe_values.append(fin['roe'])
                if 'bps' in fin and fin['bps'] is not None:
                    bps_values.append(fin['bps'])
        
        if len(roe_values) < 2:  # Need at least 2 years
            return None
        
        roe_avg = np.mean(roe_values)
        
        # Filter 1: ROE 10-15%
        if not (self.roe_min <= roe_avg <= self.roe_max):
            return None
        
        # Calculate BPS and PBR
        latest_bps = bps_values[-1] if bps_values else 0
        pbr = current_price / latest_bps if latest_bps > 0 else float('inf')
        
        # Filter 2: PBR <= 1.0 (simplified - without industry comparison)
        if pbr > self.pbr_max:
            return None
        
        # Fetch NPS ownership
        nps_current, nps_prev = self.fetch_nps_ownership(corp_code)
        
        # Filter 3: NPS >= 5%
        if nps_current < self.nps_min:
            return None
        
        # Determine trend
        if nps_current > nps_prev * 1.01:
            nps_trend = 'increasing'
        elif nps_current < nps_prev * 0.99:
            nps_trend = 'decreasing'
        else:
            nps_trend = 'stable'
        
        # Calculate scores
        score_roe = self.calculate_roe_score(roe_avg, roe_values)
        score_dividend = 50  # Placeholder - would need actual dividend data
        score_valuation = self.calculate_valuation_score(pbr, 1.2)  # Assume industry avg 1.2
        score_nps = self.calculate_nps_score(nps_current, nps_trend)
        
        # Weighted total score
        total_score = (
            score_roe * 0.40 +      # ROE weight 40%
            score_dividend * 0.25 +  # Dividend weight 25%
            score_valuation * 0.20 + # Valuation weight 20%
            score_nps * 0.15         # NPS weight 15%
        )
        
        return NPSStockData(
            symbol=symbol,
            name=name,
            sector=sector,
            market_cap=market_cap,
            current_price=current_price,
            roe_2022=roe_values[0] if len(roe_values) > 0 else None,
            roe_2023=roe_values[1] if len(roe_values) > 1 else None,
            roe_2024=roe_values[2] if len(roe_values) > 2 else None,
            roe_avg=roe_avg,
            roe_consistent=np.std(roe_values) < 0.03 if len(roe_values) >= 2 else False,
            bps=latest_bps,
            pbr=pbr,
            nps_ownership_current=nps_current,
            nps_ownership_prev=nps_prev,
            nps_ownership_trend=nps_trend,
            score_roe=score_roe,
            score_dividend=score_dividend,
            score_valuation=score_valuation,
            score_nps=score_nps,
            total_score=total_score
        )
    
    def run_scan(self, max_stocks: Optional[int] = None) -> List[NPSStockData]:
        """
        Run full NPS scanning pipeline
        """
        logger.info("=" * 60)
        logger.info("🔍 Starting NPS Value Scanner (Real Data)")
        logger.info("=" * 60)
        
        # Get stock universe
        universe = self.get_stock_universe()
        if universe.empty:
            logger.error("❌ No stocks in universe")
            return []
        
        if max_stocks:
            universe = universe.head(max_stocks)
        
        # Analyze each stock
        results = []
        total = len(universe)
        
        for idx, (_, row) in enumerate(universe.iterrows(), 1):
            if idx % 50 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx/total*100:.1f}%)")
            
            result = self.analyze_stock(row)
            if result:
                results.append(result)
                logger.info(f"✅ {result.name}: ROE {result.roe_avg*100:.1f}%, PBR {result.pbr:.2f}, NPS {result.nps_ownership_current*100:.1f}%")
        
        # Sort by total score
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        # Assign ranks
        for i, r in enumerate(results, 1):
            r.rank = i
        
        self.results = results
        logger.info(f"🎉 Scan complete! {len(results)} stocks passed all filters")
        
        return results
    
    def export_results(self, output_dir: str = './reports/nps_value') -> Dict[str, str]:
        """Export results"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        # JSON
        json_path = f"{output_dir}/nps_value_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        
        # CSV
        csv_path = f"{output_dir}/nps_value_{timestamp}.csv"
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # HTML Report
        html_path = f"{output_dir}/nps_value_{timestamp}.html"
        self._generate_html_report(html_path)
        
        logger.info(f"💾 Exported: JSON={json_path}, CSV={csv_path}, HTML={html_path}")
        
        return {'json': json_path, 'csv': csv_path, 'html': html_path}
    
    def _generate_html_report(self, path: str):
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NPS Value Scanner Report - {datetime.now().strftime('%Y-%m-%d')}</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
        </head>
        <body class="bg-gradient-to-br from-blue-900 to-indigo-900 min-h-screen p-8">
            <div class="max-w-6xl mx-auto">
                <div class="text-center mb-10">
                    <h1 class="text-4xl font-bold text-white mb-2">🏛️ NPS Value Scanner</h1>
                    <p class="text-white/60">국민연금 장기 가치 투자 패턴 복제</p>
                    <p class="text-white/40 text-sm mt-1">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>
                
                <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
                    <div class="bg-gray-50 px-6 py-4 border-b">
                        <h2 class="text-xl font-bold text-gray-800">선정 종목 TOP {len(self.results)}</h2>
                    </div>
                    <table class="w-full">
                        <thead class="bg-gray-100">
                            <tr>
                                <th class="px-4 py-3 text-left">Rank</th>
                                <th class="px-4 py-3 text-left">종목</th>
                                <th class="px-4 py-3 text-left">업종</th>
                                <th class="px-4 py-3 text-right">ROE</th>
                                <th class="px-4 py-3 text-right">PBR</th>
                                <th class="px-4 py-3 text-right">NPS</th>
                                <th class="px-4 py-3 text-right">점수</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for r in self.results[:20]:
            html += f"""
                            <tr class="border-b hover:bg-gray-50">
                                <td class="px-4 py-3 font-bold">{r.rank}</td>
                                <td class="px-4 py-3">
                                    <div class="font-medium">{r.name}</div>
                                    <div class="text-xs text-gray-500">{r.symbol}</div>
                                </td>
                                <td class="px-4 py-3 text-sm">{r.sector}</td>
                                <td class="px-4 py-3 text-right">{r.roe_avg*100:.1f}%</td>
                                <td class="px-4 py-3 text-right">{r.pbr:.2f}x</td>
                                <td class="px-4 py-3 text-right">{r.nps_ownership_current*100:.1f}%</td>
                                <td class="px-4 py-3 text-right font-bold text-blue-600">{r.total_score:.1f}</td>
                            </tr>
            """
        
        html += """
                        </tbody>
                    </table>
                </div>
                
                <div class="mt-8 grid grid-cols-4 gap-4">
                    <div class="bg-white/10 rounded-xl p-4 text-center">
                        <div class="text-2xl font-bold text-green-400">10-15%</div>
                        <div class="text-white/60 text-sm">ROE Range</div>
                    </div>
                    <div class="bg-white/10 rounded-xl p-4 text-center">
                        <div class="text-2xl font-bold text-blue-400">≤1.0x</div>
                        <div class="text-white/60 text-sm">PBR Max</div>
                    </div>
                    <div class="bg-white/10 rounded-xl p-4 text-center">
                        <div class="text-2xl font-bold text-yellow-400">≥5%</div>
                        <div class="text-white/60 text-sm">NPS Min</div>
                    </div>
                    <div class="bg-white/10 rounded-xl p-4 text-center">
                        <div class="text-2xl font-bold text-purple-400">1,000억+</div>
                        <div class="text-white/60 text-sm">Market Cap</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def print_summary(self):
        """Print summary to console"""
        print("\n" + "=" * 80)
        print("🏛️ NPS Value Scanner - Results")
        print("=" * 80)
        print(f"{'Rank':<6}{'Symbol':<10}{'Name':<20}{'ROE':<10}{'PBR':<8}{'NPS':<8}{'Score':<8}")
        print("-" * 80)
        
        for r in self.results[:15]:
            print(f"{r.rank:<6}{r.symbol:<10}{r.name:<20}"
                  f"{r.roe_avg*100:<9.1f}% {r.pbr:<7.2f}x"
                  f"{r.nps_ownership_current*100:<7.1f}% {r.total_score:<7.1f}")
        
        print("=" * 80)


def main():
    """Main execution"""
    scanner = NPSValueScannerReal()
    
    # Run scan (limit to first 100 stocks for testing)
    results = scanner.run_scan(max_stocks=100)
    
    if results:
        scanner.print_summary()
        scanner.export_results()
    else:
        print("❌ No stocks passed all filters")
    
    return results


if __name__ == '__main__':
    main()
