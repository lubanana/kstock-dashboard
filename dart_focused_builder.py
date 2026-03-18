#!/usr/bin/env python3
"""
DART Financial & Shareholding Builder
재무제표 + 지분공시만 구축하는 전용 빌더
"""

import os
import sys
import json
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

sys.path.insert(0, '/root/.openclaw/workspace/strg')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FocusedDARTBuilder:
    """재무제표 + 지분공시 전용 빌더"""
    
    def __init__(self, db_path: str = './data/dart_focused.db'):
        self.db_path = db_path
        self.batch_size = 10
        self.api_delay = 0.5
        
        # Load API key
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / '.env'
        load_dotenv(dotenv_path=env_path, override=True)
        
        api_key = os.getenv('OPENDART_API_KEY')
        if not api_key:
            raise ValueError("OPENDART_API_KEY not found")
        
        # Initialize OpenDartReader
        import OpenDartReader
        self.dart = OpenDartReader(api_key)
        
        # Init DB
        self._init_db()
        
        # Load stock list
        self.stocks = self._load_stocks()
        
    def _init_db(self):
        """Initialize focused database"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 재무제표 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_code TEXT NOT NULL,
                stock_code TEXT,
                year TEXT NOT NULL,
                report_code TEXT NOT NULL,
                fs_div TEXT,
                account_nm TEXT,
                account_detail TEXT,
                sj_nm TEXT,
                thstrm_nm TEXT,
                thstrm_amount TEXT,
                frmtrm_nm TEXT,
                frmtrm_amount TEXT,
                bfefrmtrm_nm TEXT,
                bfefrmtrm_amount TEXT,
                currency TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 지분공시 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shareholding_disclosures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                corp_code TEXT NOT NULL,
                stock_code TEXT,
                report_nm TEXT,
                rcept_no TEXT UNIQUE,
                rcept_dt TEXT,
                report_type TEXT,
                report_detail TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 진행상황 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS build_progress (
                stock_code TEXT PRIMARY KEY,
                financial_done BOOLEAN DEFAULT 0,
                shareholding_done BOOLEAN DEFAULT 0,
                processed_at TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")
    
    def _load_stocks(self) -> List[Dict]:
        """Load stock list from pivot_strategy.db"""
        conn = sqlite3.connect('./data/pivot_strategy.db')
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, name, market FROM stock_info ORDER BY market, symbol")
        stocks = [{'symbol': row[0], 'name': row[1], 'market': row[2]} 
                  for row in cursor.fetchall()]
        conn.close()
        logger.info(f"📊 Loaded {len(stocks)} stocks")
        return stocks
    
    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """Get corp_code from stock_code"""
        try:
            corp_code = self.dart.find_corp_code(stock_code)
            return corp_code
        except Exception as e:
            logger.warning(f"⚠️ Failed to get corp_code for {stock_code}: {e}")
            return None
    
    def fetch_financial_statements(self, corp_code: str, stock_code: str) -> bool:
        """Fetch financial statements for a company"""
        try:
            time.sleep(self.api_delay)
            
            # 최근 3개년 재무제표 조회
            current_year = datetime.now().year
            years = [str(current_year - i) for i in range(3)]
            
            total_records = 0
            for year in years:
                try:
                    # 연결재무제표 (CFS)
                    fs = self.dart.finstate(corp_code, year)
                    if fs is not None and not fs.empty:
                        self._save_financial_statements(corp_code, stock_code, year, fs)
                        total_records += len(fs)
                except Exception as e:
                    logger.debug(f"No FS for {corp_code} {year}: {e}")
                    continue
            
            if total_records > 0:
                logger.info(f"  ✅ Financial statements: {total_records} records")
                return True
            else:
                logger.info(f"  ⚠️ No financial statements found")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Error fetching FS for {corp_code}: {e}")
            return False
    
    def _save_financial_statements(self, corp_code: str, stock_code: str, year: str, df):
        """Save financial statements to DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO financial_statements 
                    (corp_code, stock_code, year, report_code, fs_div, account_nm, account_detail,
                     sj_nm, thstrm_nm, thstrm_amount, frmtrm_nm, frmtrm_amount,
                     bfefrmtrm_nm, bfefrmtrm_amount, currency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    corp_code, stock_code, year,
                    row.get('reprt_code', ''), row.get('fs_div', ''),
                    row.get('account_nm', ''), row.get('account_detail', ''),
                    row.get('sj_nm', ''), row.get('thstrm_nm', ''),
                    str(row.get('thstrm_amount', '')), row.get('frmtrm_nm', ''),
                    str(row.get('frmtrm_amount', '')), row.get('bfefrmtrm_nm', ''),
                    str(row.get('bfefrmtrm_amount', '')), row.get('currency', '')
                ))
            except Exception as e:
                logger.debug(f"Skip row: {e}")
                continue
        
        conn.commit()
        conn.close()
    
    def fetch_shareholding_disclosures(self, corp_code: str, stock_code: str) -> bool:
        """Fetch shareholding disclosures (지분공시)"""
        try:
            time.sleep(self.api_delay)
            
            # 최근 2년간 지분공시 조회
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y%m%d')
            
            df = self.dart.list(corp_code, start=start_date, end=end_date)
            
            if df is None or df.empty:
                logger.info(f"  ⚠️ No disclosures found")
                return False
            
            # 지분공시만 필터링
            shareholding_keywords = [
                '임원ㆍ주요주주', '지분', '소유상황', '특정증권',
                '주식', '지배주주', '최대주주'
            ]
            
            filtered = df[df['report_nm'].str.contains('|'.join(shareholding_keywords), na=False)]
            
            if filtered.empty:
                logger.info(f"  ⚠️ No shareholding disclosures found")
                return False
            
            self._save_shareholding_disclosures(corp_code, stock_code, filtered)
            logger.info(f"  ✅ Shareholding disclosures: {len(filtered)} records")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Error fetching shareholding for {corp_code}: {e}")
            return False
    
    def _save_shareholding_disclosures(self, corp_code: str, stock_code: str, df):
        """Save shareholding disclosures to DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO shareholding_disclosures 
                    (corp_code, stock_code, report_nm, rcept_no, rcept_dt, report_type, report_detail)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    corp_code, stock_code,
                    row.get('report_nm', ''),
                    row.get('rcept_no', ''),
                    row.get('rcept_dt', ''),
                    row.get('report_tp', ''),
                    row.get('rm', '')
                ))
            except Exception as e:
                logger.debug(f"Skip row: {e}")
                continue
        
        conn.commit()
        conn.close()
    
    def update_progress(self, stock_code: str, financial_done: bool, shareholding_done: bool):
        """Update build progress"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO build_progress 
            (stock_code, financial_done, shareholding_done, processed_at)
            VALUES (?, ?, ?, ?)
        ''', (stock_code, financial_done, shareholding_done, datetime.now()))
        conn.commit()
        conn.close()
    
    def get_progress(self) -> Dict:
        """Get current build progress"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN financial_done THEN 1 ELSE 0 END) as fs_done,
                SUM(CASE WHEN shareholding_done THEN 1 ELSE 0 END) as sh_done
            FROM build_progress
        ''')
        row = cursor.fetchone()
        conn.close()
        
        total_processed = row[0] if row[0] else 0
        fs_done = row[1] if row[1] else 0
        sh_done = row[2] if row[2] else 0
        
        return {
            'total_stocks': len(self.stocks),
            'processed': total_processed,
            'financial_done': fs_done,
            'shareholding_done': sh_done,
            'progress_pct': (total_processed / len(self.stocks) * 100) if self.stocks else 0
        }
    
    def run(self, limit: Optional[int] = None):
        """Run focused builder"""
        logger.info("🚀 DART Focused Builder (재무제표 + 지분공시)")
        logger.info("=" * 60)
        
        # Check progress
        progress = self.get_progress()
        logger.info(f"📊 Current progress: {progress['processed']}/{progress['total_stocks']} ({progress['progress_pct']:.1f}%)")
        
        # Get remaining stocks
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT stock_code FROM build_progress WHERE financial_done = 1 AND shareholding_done = 1")
        processed = set(row[0] for row in cursor.fetchall())
        conn.close()
        
        remaining = [s for s in self.stocks if s['symbol'] not in processed]
        if limit:
            remaining = remaining[:limit]
        
        logger.info(f"🎯 Processing {len(remaining)} stocks")
        logger.info("")
        
        success_count = 0
        for i, stock in enumerate(remaining, 1):
            symbol = stock['symbol']
            name = stock['name']
            
            logger.info(f"[{i}/{len(remaining)}] {symbol} {name}")
            
            # Get corp_code
            corp_code = self.get_corp_code(symbol)
            if not corp_code:
                logger.warning(f"  ⚠️ No corp_code found")
                continue
            
            # Fetch financial statements
            fs_success = self.fetch_financial_statements(corp_code, symbol)
            
            # Fetch shareholding disclosures
            sh_success = self.fetch_shareholding_disclosures(corp_code, symbol)
            
            # Update progress
            self.update_progress(symbol, fs_success, sh_success)
            
            if fs_success or sh_success:
                success_count += 1
            
            # Progress log every 10 stocks
            if i % 10 == 0:
                progress = self.get_progress()
                logger.info("")
                logger.info(f"📈 Progress: {progress['processed']}/{progress['total_stocks']} ({progress['progress_pct']:.1f}%)")
                logger.info(f"   Financial: {progress['financial_done']} | Shareholding: {progress['shareholding_done']}")
                logger.info("")
        
        # Final stats
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Build completed!")
        progress = self.get_progress()
        logger.info(f"📊 Total processed: {progress['processed']}/{progress['total_stocks']}")
        logger.info(f"📊 Financial statements: {progress['financial_done']}")
        logger.info(f"📊 Shareholding disclosures: {progress['shareholding_done']}")
        
        # DB stats
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM financial_statements")
        fs_records = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM shareholding_disclosures")
        sh_records = cursor.fetchone()[0]
        conn.close()
        
        logger.info(f"📄 Total FS records: {fs_records:,}")
        logger.info(f"📄 Total SH records: {sh_records:,}")


if __name__ == '__main__':
    builder = FocusedDARTBuilder()
    builder.run()
