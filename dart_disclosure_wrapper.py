"""
OpenDart Caching Wrapper with fdr_wrapper-style Architecture
Provides SQLite-based caching for disclosure data with automatic fallback
"""
import os
import json
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DisclosureCacheConfig:
    """Cache configuration"""
    db_path: str = './data/dart_cache.db'
    cache_duration_days: int = 1  # 공시는 자주 변경되므로 1일 캐시
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_delay: float = 0.2  # 5 req/sec


class DisclosureDatabaseManager:
    """SQLite database manager for disclosure caching"""
    
    def __init__(self, db_path: str = './data/dart_cache.db'):
        self.db_path = db_path
        self._ensure_directory()
        self._init_database()
    
    def _ensure_directory(self):
        """Ensure database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Disclosures table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS disclosures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    corp_code TEXT NOT NULL,
                    corp_name TEXT,
                    report_nm TEXT,
                    rcept_no TEXT UNIQUE,
                    rcept_dt TEXT,
                    report_type TEXT,
                    content_hash TEXT,
                    raw_data TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')
            
            # Company info table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS company_info (
                    corp_code TEXT PRIMARY KEY,
                    corp_name TEXT NOT NULL,
                    stock_code TEXT,
                    ceo_nm TEXT,
                    jurir_no TEXT,
                    bizr_no TEXT,
                    adres TEXT,
                    hm_url TEXT,
                    phn_no TEXT,
                    fax_no TEXT,
                    induty_code TEXT,
                    est_dt TEXT,
                    acc_mt TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Financial statements cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS financial_statements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    corp_code TEXT NOT NULL,
                    year TEXT NOT NULL,
                    report_code TEXT NOT NULL,
                    account_nm TEXT NOT NULL,
                    sj_nm TEXT,
                    thstrm_amount TEXT,
                    frmtrm_amount TEXT,
                    bfefrmtrm_amount TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(corp_code, year, report_code, account_nm)
                )
            ''')
            
            # Major shareholders cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS major_shareholders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    corp_code TEXT NOT NULL,
                    year TEXT NOT NULL,
                    stockholder_nm TEXT,
                    stockholder_rel TEXT,
                    stockholder_stk TEXT,
                    stockholder_rate TEXT,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(corp_code, year, stockholder_nm)
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_disclosures_corp ON disclosures(corp_code, rcept_dt)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_disclosures_date ON disclosures(rcept_dt)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fs_lookup ON financial_statements(corp_code, year, report_code)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expires ON disclosures(expires_at)')
            
            conn.commit()
            logger.info("✅ Database initialized")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_disclosures(self, corp_code: str, disclosures: List[Dict], 
                         cache_days: int = 1) -> bool:
        """Save disclosures to cache"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                expires_at = datetime.now() + timedelta(days=cache_days)
                
                for disc in disclosures:
                    # Generate content hash for change detection
                    content = json.dumps(disc, sort_keys=True)
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO disclosures 
                        (corp_code, corp_name, report_nm, rcept_no, rcept_dt, 
                         report_type, content_hash, raw_data, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        corp_code,
                        disc.get('corp_name', ''),
                        disc.get('report_nm', ''),
                        disc.get('rcept_no', ''),
                        disc.get('rcept_dt', ''),
                        disc.get('report_tp', ''),
                        content_hash,
                        json.dumps(disc, ensure_ascii=False),
                        expires_at.isoformat()
                    ))
                
                conn.commit()
                logger.info(f"💾 Cached {len(disclosures)} disclosures for {corp_code}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to save disclosures: {e}")
            return False
    
    def get_disclosures(self, corp_code: str, start_date: Optional[str] = None,
                        end_date: Optional[str] = None, 
                        check_expiry: bool = True) -> Optional[pd.DataFrame]:
        """Get disclosures from cache"""
        try:
            with self._get_connection() as conn:
                query = '''
                    SELECT corp_code, corp_name, report_nm, rcept_no, 
                           rcept_dt, report_type, raw_data, cached_at, expires_at
                    FROM disclosures 
                    WHERE corp_code = ?
                '''
                params = [corp_code]
                
                if start_date:
                    query += ' AND rcept_dt >= ?'
                    params.append(start_date)
                if end_date:
                    query += ' AND rcept_dt <= ?'
                    params.append(end_date)
                if check_expiry:
                    query += ' AND (expires_at IS NULL OR expires_at > datetime("now"))'
                
                query += ' ORDER BY rcept_dt DESC'
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    # Parse raw_data JSON
                    df['raw_data'] = df['raw_data'].apply(json.loads)
                    logger.info(f"📦 Cache hit: {len(df)} disclosures for {corp_code}")
                    return df
                
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get disclosures: {e}")
            return None
    
    def save_company_info(self, corp_code: str, info: Dict) -> bool:
        """Save company info to cache"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO company_info 
                    (corp_code, corp_name, stock_code, ceo_nm, jurir_no, bizr_no,
                     adres, hm_url, phn_no, fax_no, induty_code, est_dt, acc_mt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    corp_code, info.get('corp_name', ''), info.get('stock_code', ''),
                    info.get('ceo_nm', ''), info.get('jurir_no', ''), info.get('bizr_no', ''),
                    info.get('adres', ''), info.get('hm_url', ''), info.get('phn_no', ''),
                    info.get('fax_no', ''), info.get('induty_code', ''), info.get('est_dt', ''),
                    info.get('acc_mt', '')
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Failed to save company info: {e}")
            return False
    
    def get_company_info(self, corp_code: str) -> Optional[Dict]:
        """Get company info from cache"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM company_info WHERE corp_code = ?
                ''', (corp_code,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"❌ Failed to get company info: {e}")
            return None
    
    def clear_expired_cache(self) -> int:
        """Clear expired cache entries"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM disclosures 
                    WHERE expires_at IS NOT NULL AND expires_at < datetime("now")
                ''')
                deleted = cursor.rowcount
                conn.commit()
                logger.info(f"🧹 Cleared {deleted} expired cache entries")
                return deleted
        except Exception as e:
            logger.error(f"❌ Failed to clear cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                stats = {}
                
                for table in ['disclosures', 'company_info', 'financial_statements', 'major_shareholders']:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    stats[table] = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM disclosures 
                    WHERE expires_at IS NOT NULL AND expires_at < datetime("now")
                ''')
                stats['expired'] = cursor.fetchone()[0]
                
                return stats
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {}


class DartDisclosureWrapper:
    """
    OpenDartReader wrapper with SQLite caching (fdr_wrapper-style)
    """
    
    def __init__(self, config: Optional[DisclosureCacheConfig] = None):
        self.config = config or DisclosureCacheConfig()
        self.db = DisclosureDatabaseManager(self.config.db_path)
        
        # Import OpenDartReader
        try:
            import OpenDartReader
            api_key = os.getenv('OPENDART_API_KEY')
            if not api_key:
                raise ValueError("OPENDART_API_KEY not found in .env")
            self.dart = OpenDartReader(api_key)
            logger.info("✅ DartDisclosureWrapper initialized")
        except ImportError:
            raise ImportError("OpenDartReader not installed. Run: pip install OpenDartReader")
    
    def _fetch_from_api(self, fetch_func, *args, **kwargs) -> Any:
        """Fetch data from API with retry logic"""
        import time
        
        for attempt in range(self.config.max_retries):
            try:
                time.sleep(self.config.rate_limit_delay)  # Rate limiting
                result = fetch_func(*args, **kwargs)
                return result
            except Exception as e:
                logger.warning(f"⚠️ API attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    raise
        return None
    
    def find_disclosures(self, corp_name: str, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         use_cache: bool = True) -> pd.DataFrame:
        """
        Find disclosures by company name with caching
        
        Parameters:
        -----------
        corp_name : str
            기업명 (예: '삼성전자')
        start_date : str, optional
            시작일 (YYYYMMDD)
        end_date : str, optional
            종료일 (YYYYMMDD)
        use_cache : bool
            캐시 사용 여부
        
        Returns:
        --------
        pd.DataFrame : 공시 목록
        """
        # Get corp_code first
        corp_code = self.dart.find_corp_code(corp_name)
        if not corp_code:
            logger.warning(f"⚠️ Company not found: {corp_name}")
            return pd.DataFrame()
        
        # Try cache first
        if use_cache:
            cached = self.db.get_disclosures(corp_code, start_date, end_date)
            if cached is not None and not cached.empty:
                logger.info(f"✅ Cache hit for {corp_name}")
                return pd.DataFrame(cached['raw_data'].tolist())
        
        # Fetch from API
        try:
            logger.info(f"🌐 Fetching disclosures from API: {corp_name}")
            df = self._fetch_from_api(self.dart.list, corp_code, start_date, end_date)
            
            if df is not None and not df.empty:
                # Save to cache
                records = df.to_dict('records')
                self.db.save_disclosures(corp_code, records, self.config.cache_duration_days)
                return df
                
        except Exception as e:
            logger.error(f"❌ API fetch failed: {e}")
            # Try fallback to cache (even if expired)
            cached = self.db.get_disclosures(corp_code, start_date, end_date, check_expiry=False)
            if cached is not None and not cached.empty:
                logger.warning("⚠️ Using expired cache as fallback")
                return pd.DataFrame(cached['raw_data'].tolist())
        
        return pd.DataFrame()
    
    def list_disclosures(self, corp_code: str,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         page_count: int = 100,
                         use_cache: bool = True) -> pd.DataFrame:
        """
        List disclosures by corp_code with caching
        """
        # Try cache first
        if use_cache:
            cached = self.db.get_disclosures(corp_code, start_date, end_date)
            if cached is not None and not cached.empty:
                return pd.DataFrame(cached['raw_data'].tolist())
        
        # Fetch from API
        try:
            logger.info(f"🌐 Fetching disclosures from API: {corp_code}")
            df = self._fetch_from_api(self.dart.list, corp_code, start_date, end_date, page_count)
            
            if df is not None and not df.empty:
                records = df.to_dict('records')
                self.db.save_disclosures(corp_code, records, self.config.cache_duration_days)
                return df
                
        except Exception as e:
            logger.error(f"❌ API fetch failed: {e}")
            cached = self.db.get_disclosures(corp_code, start_date, end_date, check_expiry=False)
            if cached is not None and not cached.empty:
                logger.warning("⚠️ Using expired cache as fallback")
                return pd.DataFrame(cached['raw_data'].tolist())
        
        return pd.DataFrame()
    
    def get_company_info(self, corp_code: str, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """
        Get company info with caching
        """
        # Try cache first
        if use_cache:
            cached = self.db.get_company_info(corp_code)
            if cached:
                return pd.DataFrame([cached])
        
        # Fetch from API
        try:
            logger.info(f"🌐 Fetching company info from API: {corp_code}")
            result = self._fetch_from_api(self.dart.company, corp_code)
            
            if result and isinstance(result, dict):
                # Convert dict to DataFrame
                df = pd.DataFrame([result])
                # Save to cache
                self.db.save_company_info(corp_code, result)
                return df
            elif result is not None and hasattr(result, 'empty') and not result.empty:
                # It's already a DataFrame
                info = result.iloc[0].to_dict() if hasattr(result, 'iloc') else result
                self.db.save_company_info(corp_code, info)
                return result
                
        except Exception as e:
            logger.error(f"❌ API fetch failed: {e}")
            cached = self.db.get_company_info(corp_code)
            if cached:
                logger.warning("⚠️ Using cached company info")
                return pd.DataFrame([cached])
        
        return None
    
    def get_corp_code(self, corp_name: str) -> Optional[str]:
        """Get corp_code by company name"""
        return self.dart.find_corp_code(corp_name)
    
    def get_stock_code(self, corp_code: str) -> Optional[str]:
        """Get stock_code by corp_code"""
        return self.dart.get_stock_code(corp_code)
    
    def clear_cache(self) -> int:
        """Clear all expired cache"""
        return self.db.clear_expired_cache()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.db.get_cache_stats()


# ============================================================
# Example Usage
# ============================================================

def example():
    """Example usage of DartDisclosureWrapper"""
    print("🚀 DartDisclosureWrapper Example")
    print("=" * 60)
    
    # Initialize wrapper
    config = DisclosureCacheConfig(
        db_path='./data/dart_cache.db',
        cache_duration_days=1
    )
    dart = DartDisclosureWrapper(config)
    
    # Show cache stats
    stats = dart.get_cache_stats()
    print(f"\n📊 Cache Stats:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Find disclosures
    print(f"\n📋 Finding disclosures for 삼성전자...")
    df = dart.find_disclosures('삼성전자', start_date='20250301')
    
    if not df.empty:
        print(f"   Found {len(df)} disclosures")
        if 'report_nm' in df.columns and 'rcept_dt' in df.columns:
            print(df[['report_nm', 'rcept_dt']].head())
        else:
            print(df.head())
    else:
        print("   No disclosures found")
    
    # Second call (should use cache)
    print(f"\n📋 Second call (cache)...")
    df2 = dart.find_disclosures('삼성전자', start_date='20250301')
    print(f"   Found {len(df2)} disclosures")
    
    # Company info
    print(f"\n🏢 Company Info...")
    corp_code = dart.get_corp_code('삼성전자')
    print(f"   Corp code: {corp_code}")
    info = dart.get_company_info(corp_code)
    if info is not None and not info.empty:
        print(f"   {info['corp_name'].iloc[0]} ({info.get('stock_code', ['N/A']).iloc[0]})")
    
    print("\n✅ Example completed!")


if __name__ == '__main__':
    example()
