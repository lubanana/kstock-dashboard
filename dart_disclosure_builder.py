"""
DART Disclosure Builder - 전체 종목 공시 정보 구축
배치 처리 + 재시도 로직 + 체크포인트 저장
"""
import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Set
import sqlite3
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Load environment variables first
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

from dart_disclosure_wrapper import DartDisclosureWrapper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DARTDisclosureBuilder:
    """Build disclosure cache for all stocks"""
    
    def __init__(self, batch_size: int = 50, delay: float = 0.5):
        self.dart = DartDisclosureWrapper()
        self.batch_size = batch_size
        self.delay = delay
        self.checkpoint_file = './data/.dart_build_checkpoint.json'
        
        # Statistics
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info("🚀 DART Disclosure Builder initialized")
        logger.info(f"   Batch size: {batch_size}")
        logger.info(f"   API delay: {delay}s")
    
    def get_all_stocks(self) -> pd.DataFrame:
        """Get all stocks from stock_info"""
        logger.info("📊 Loading stock universe...")
        
        try:
            conn = sqlite3.connect('./data/pivot_strategy.db')
            query = '''
                SELECT symbol, name, sector
                FROM stock_info
                ORDER BY symbol
            '''
            stocks = pd.read_sql_query(query, conn)
            conn.close()
            
            logger.info(f"✅ Loaded {len(stocks)} stocks")
            return stocks
            
        except Exception as e:
            logger.error(f"❌ Failed to load stocks: {e}")
            return pd.DataFrame()
    
    def load_checkpoint(self) -> Set[str]:
        """Load processed symbols from checkpoint"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    processed = set(data.get('processed', []))
                    logger.info(f"📋 Loaded checkpoint: {len(processed)} symbols processed")
                    return processed
            except Exception as e:
                logger.warning(f"⚠️ Failed to load checkpoint: {e}")
        return set()
    
    def save_checkpoint(self, processed: Set[str]):
        """Save processed symbols to checkpoint"""
        try:
            data = {
                'processed': list(processed),
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats
            }
            with open(self.checkpoint_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Failed to save checkpoint: {e}")
    
    def fetch_disclosures_for_stock(self, symbol: str, max_retries: int = 3) -> Tuple[bool, int, str]:
        """
        Fetch disclosures for a single stock
        Returns: (success, count, message)
        """
        for attempt in range(max_retries):
            try:
                # Get corp_code
                corp_code = self.dart.get_corp_code(symbol)
                if not corp_code:
                    return (False, 0, "No corp code mapping")
                
                # Check if already cached
                cached = self.dart.db.get_disclosures(corp_code, check_expiry=False)
                if cached is not None and len(cached) > 0:
                    return (True, len(cached), "Already cached")
                
                # Fetch from API (no date range to get all disclosures)
                disclosures = self.dart.list_disclosures(corp_code)
                
                if disclosures is not None and len(disclosures) > 0:
                    return (True, len(disclosures), "Fetched from API")
                else:
                    return (False, 0, "No disclosures found")
                    
            except Exception as e:
                error_msg = str(e)[:100]
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"   Retry {attempt + 1} for {symbol} after {wait_time}s: {error_msg}")
                    time.sleep(wait_time)
                else:
                    return (False, 0, f"Error: {error_msg}")
        
        return (False, 0, "Max retries exceeded")
    
    def build_cache(self, max_stocks: Optional[int] = None):
        """Build disclosure cache for all stocks"""
        logger.info("=" * 70)
        logger.info("🔨 DART Disclosure Cache Builder")
        logger.info("=" * 70)
        
        # Load stocks
        stocks = self.get_all_stocks()
        if stocks.empty:
            logger.error("❌ No stocks to process")
            return
        
        if max_stocks:
            stocks = stocks.head(max_stocks)
        
        self.stats['total'] = len(stocks)
        self.stats['start_time'] = datetime.now().isoformat()
        
        # Load checkpoint
        processed = self.load_checkpoint()
        
        # Filter out already processed
        to_process = stocks[~stocks['symbol'].isin(processed)]
        
        logger.info(f"🎯 Processing {len(to_process)}/{len(stocks)} stocks")
        logger.info(f"   (Skipped {len(processed)} already processed)")
        
        # Process in batches
        batch_num = 0
        for i in range(0, len(to_process), self.batch_size):
            batch_num += 1
            batch = to_process.iloc[i:i+self.batch_size]
            
            logger.info(f"\n📦 Batch {batch_num} ({i+1}-{min(i+len(batch), len(to_process))}/{len(to_process)})")
            logger.info("-" * 70)
            
            for idx, row in batch.iterrows():
                symbol = row['symbol']
                name = row['name']
                
                # Fetch disclosures
                success, count, message = self.fetch_disclosures_for_stock(symbol)
                
                if success:
                    self.stats['success'] += 1
                    status = "✅"
                else:
                    if "Already cached" in message:
                        self.stats['skipped'] += 1
                        status = "⏭️"
                    else:
                        self.stats['failed'] += 1
                        status = "❌"
                
                logger.info(f"  {status} {symbol:8s} ({name:20s}): {message} ({count} disclosures)")
                
                # Add to processed
                processed.add(symbol)
                
                # Delay between requests
                time.sleep(self.delay)
            
            # Save checkpoint after each batch
            self.save_checkpoint(processed)
            
            # Progress summary
            total_processed = self.stats['success'] + self.stats['failed'] + self.stats['skipped']
            progress = total_processed / self.stats['total'] * 100
            logger.info(f"\n📊 Progress: {total_processed}/{self.stats['total']} ({progress:.1f}%)")
            logger.info(f"   Success: {self.stats['success']} | Failed: {self.stats['failed']} | Skipped: {self.stats['skipped']}")
        
        self.stats['end_time'] = datetime.now().isoformat()
        
        # Final summary
        logger.info("\n" + "=" * 70)
        logger.info("🎉 Build Complete!")
        logger.info("=" * 70)
        logger.info(f"Total: {self.stats['total']}")
        logger.info(f"Success: {self.stats['success']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped (already cached): {self.stats['skipped']}")
        
        # Save final stats
        self.save_checkpoint(processed)
    
    def get_cache_stats(self):
        """Get current cache statistics"""
        try:
            conn = sqlite3.connect('./data/dart_cache.db')
            cursor = conn.cursor()
            
            # Total disclosures
            cursor.execute('SELECT COUNT(*) FROM disclosures')
            total_disclosures = cursor.fetchone()[0]
            
            # Unique companies
            cursor.execute('SELECT COUNT(DISTINCT corp_code) FROM disclosures')
            unique_companies = cursor.fetchone()[0]
            
            # Top companies by disclosure count
            cursor.execute('''
                SELECT corp_code, COUNT(*) as cnt 
                FROM disclosures 
                GROUP BY corp_code 
                ORDER BY cnt DESC 
                LIMIT 10
            ''')
            top_companies = cursor.fetchall()
            
            conn.close()
            
            logger.info("\n📈 Cache Statistics:")
            logger.info("=" * 70)
            logger.info(f"Total disclosures: {total_disclosures:,}")
            logger.info(f"Unique companies: {unique_companies}")
            logger.info("\nTop 10 companies by disclosure count:")
            for corp_code, count in top_companies:
                logger.info(f"  {corp_code}: {count:,} disclosures")
            
            return {
                'total_disclosures': total_disclosures,
                'unique_companies': unique_companies,
                'top_companies': top_companies
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return None


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DART Disclosure Cache Builder')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size (default: 50)')
    parser.add_argument('--delay', type=float, default=0.5, help='API delay in seconds (default: 0.5)')
    parser.add_argument('--max-stocks', type=int, default=None, help='Max stocks to process (default: all)')
    parser.add_argument('--stats', action='store_true', help='Show cache statistics only')
    
    args = parser.parse_args()
    
    builder = DARTDisclosureBuilder(batch_size=args.batch_size, delay=args.delay)
    
    if args.stats:
        builder.get_cache_stats()
    else:
        builder.build_cache(max_stocks=args.max_stocks)
        builder.get_cache_stats()


if __name__ == '__main__':
    main()
