"""
D+ Leading Stock Trading Strategy (D플러스 주도주 매매법)
Based on 대왕개미 홍인기's YouTube Video Analysis
Video: https://youtu.be/cI9XTnBS5JQ

Core Strategy:
- Trade the strongest leader stocks in dominant themes for 2-3 days
- Enter after confirming theme and leader around 9:30 AM
- Take partial profits, hold overnight, swing trade D+1 and D+2
- Use market crashes as buying opportunities for leaders
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import sqlite3


class DPlusLeadingStockStrategy:
    """
    D+ 주도주 매매법
    
    Key Rules:
    1. Theme Detection: Multiple stocks in same sector hit limit up
    2. Leader Selection: Pick the strongest leader (not small caps)
    3. Entry: Around 9:30 AM after confirming theme
    4. Management: Partial profit at limit up, overnight hold
    5. D+1/D+2: Continue trading with profit-taking and re-entry
    """
    
    def __init__(self, 
                 initial_capital: float = 100_000_000,  # 1억원
                 max_positions: int = 3,
                 position_size_pct: float = 0.20,  # 20% per trade
                 stop_loss_pct: float = -0.07,  # -7% stop loss
                 profit_take_1: float = 0.10,  # 10% partial
                 profit_take_2: float = 0.20,  # 20% more
                 overnight_hold: bool = True):
        
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_positions = max_positions
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.profit_take_1 = profit_take_1
        self.profit_take_2 = profit_take_2
        self.overnight_hold = overnight_hold
        
        self.positions = {}  # symbol -> position info
        self.trades = []
        self.daily_stats = []
        
    def detect_dominant_theme(self, 
                             market_data: pd.DataFrame,
                             date: datetime,
                             min_limit_up_stocks: int = 5,
                             sector_col: str = 'sector') -> List[str]:
        """
        Detect dominant themes with multiple limit-up stocks
        
        Args:
            market_data: DataFrame with all stocks for the day
            date: Trading date
            min_limit_up_stocks: Minimum stocks hitting limit up in theme
            
        Returns:
            List of dominant theme sectors
        """
        daily_data = market_data[market_data['date'] == date].copy()
        
        # Find stocks that hit limit up (typically +30% for KOSDAQ, +15% for KOSPI)
        daily_data['hit_limit_up'] = daily_data['change_pct'] >= 29.5  # Approximate
        
        # Group by sector and count
        sector_stats = daily_data.groupby(sector_col).agg({
            'hit_limit_up': 'sum',
            'code': 'count'
        }).rename(columns={'code': 'total_stocks'})
        
        # Filter sectors with multiple limit-ups
        dominant_themes = sector_stats[
            sector_stats['hit_limit_up'] >= min_limit_up_stocks
        ].index.tolist()
        
        return dominant_themes
    
    def select_leader_stock(self,
                           market_data: pd.DataFrame,
                           theme_sectors: List[str],
                           date: datetime,
                           min_volume: float = 1_000_000_000,  # 10억 거래대금
                           min_price: float = 1000) -> Optional[str]:
        """
        Select the strongest leader stock in dominant theme
        
        Criteria:
        - Highest price increase in theme
        - Adequate trading volume (not too small)
        - Strong momentum (끼)
        """
        daily_data = market_data[
            (market_data['date'] == date) & 
            (market_data['sector'].isin(theme_sectors))
        ].copy()
        
        # Filter by minimum volume and price
        candidates = daily_data[
            (daily_data['volume'] * daily_data['close'] >= min_volume) &
            (daily_data['close'] >= min_price)
        ].copy()
        
        if candidates.empty:
            return None
        
        # Score stocks based on multiple factors
        candidates['score'] = (
            candidates['change_pct'] * 0.4 +  # Price change weight
            (candidates['volume'] / candidates['volume'].max()) * 30 +  # Volume
            candidates['high'] / candidates['close'] * 20  # Intraday strength
        )
        
        # Select top scorer
        leader = candidates.loc[candidates['score'].idxmax(), 'code']
        return leader
    
    def check_entry_conditions(self,
                              stock_data: pd.DataFrame,
                              market_data: pd.DataFrame,
                              date: datetime,
                              entry_time: str = "09:30") -> bool:
        """
        Check if entry conditions are met
        
        Entry Rules:
        1. Stock is leader in dominant theme
        2. Around 9:30 AM (after initial volatility settles)
        3. Theme confirmed strong
        4. Market direction not against (optional)
        """
        # Check if already in position
        stock_code = stock_data['code'].iloc[0]
        if stock_code in self.positions:
            return False
        
        # Check position limit
        if len(self.positions) >= self.max_positions:
            return False
        
        # Check if stock has risen significantly (can enter even after big rise)
        daily_change = stock_data[stock_data['date'] == date]['change_pct'].iloc[0]
        
        # Enter if stock has risen >10% and theme is strong
        if daily_change < 10:
            return False
        
        return True
    
    def calculate_position_size(self, stock_price: float) -> int:
        """Calculate number of shares to buy"""
        position_value = self.cash * self.position_size_pct
        shares = int(position_value / stock_price)
        return shares
    
    def enter_position(self,
                      stock_code: str,
                      entry_date: datetime,
                      entry_price: float,
                      is_overnight: bool = False) -> Dict:
        """Enter a new position"""
        
        shares = self.calculate_position_size(entry_price)
        if shares == 0:
            return None
        
        cost = shares * entry_price
        if cost > self.cash:
            return None
        
        self.cash -= cost
        
        position = {
            'code': stock_code,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'shares': shares,
            'cost': cost,
            'partial_sold': 0,
            'profit_taken': 0,
            'is_overnight': is_overnight,
            'day_count': 0  # D+0, D+1, D+2
        }
        
        self.positions[stock_code] = position
        
        self.trades.append({
            'date': entry_date,
            'code': stock_code,
            'action': 'BUY',
            'price': entry_price,
            'shares': shares,
            'value': cost
        })
        
        return position
    
    def manage_position(self,
                       stock_code: str,
                       current_date: datetime,
                       current_price: float,
                       high_price: float,
                       low_price: float) -> str:
        """
        Manage open position
        
        Rules:
        1. Partial profit at +10%
        2. More profit at +20%
        3. Stop loss at -7%
        4. Can hold overnight for D+1/D+2 continuation
        """
        if stock_code not in self.positions:
            return 'NO_POSITION'
        
        pos = self.positions[stock_code]
        entry_price = pos['entry_price']
        current_return = (current_price - entry_price) / entry_price
        
        # Check stop loss
        if current_return <= self.stop_loss_pct:
            self.close_position(stock_code, current_date, current_price, 'STOP_LOSS')
            return 'STOPPED'
        
        # Partial profit taking at +10% (if not already done)
        if current_return >= self.profit_take_1 and pos['partial_sold'] == 0:
            self.take_partial_profit(stock_code, current_date, current_price, 0.5)
            pos['partial_sold'] = 1
            return 'PARTIAL_1'
        
        # More profit taking at +20%
        if current_return >= self.profit_take_2 and pos['partial_sold'] == 1:
            self.take_partial_profit(stock_code, current_date, current_price, 0.5)
            pos['partial_sold'] = 2
            return 'PARTIAL_2'
        
        # If hit limit up (+30%), take more profits
        if current_return >= 0.29 and pos['partial_sold'] < 2:
            self.take_partial_profit(stock_code, current_date, current_price, 0.3)
            pos['partial_sold'] = 2
            return 'LIMIT_UP_PARTIAL'
        
        return 'HOLD'
    
    def take_partial_profit(self,
                           stock_code: str,
                           date: datetime,
                           price: float,
                           portion: float):
        """Take partial profits"""
        pos = self.positions[stock_code]
        shares_to_sell = int(pos['shares'] * portion)
        
        if shares_to_sell == 0:
            return
        
        value = shares_to_sell * price
        self.cash += value
        pos['shares'] -= shares_to_sell
        pos['profit_taken'] += value - (shares_to_sell * pos['entry_price'])
        
        self.trades.append({
            'date': date,
            'code': stock_code,
            'action': 'SELL_PARTIAL',
            'price': price,
            'shares': shares_to_sell,
            'value': value
        })
    
    def close_position(self,
                      stock_code: str,
                      date: datetime,
                      price: float,
                      reason: str):
        """Close entire position"""
        pos = self.positions[stock_code]
        
        if pos['shares'] > 0:
            value = pos['shares'] * price
            self.cash += value
            
            # Calculate profit
            cost_basis = pos['shares'] * pos['entry_price']
            profit = value - cost_basis
            
            self.trades.append({
                'date': date,
                'code': stock_code,
                'action': 'SELL_ALL',
                'price': price,
                'shares': pos['shares'],
                'value': value,
                'profit': profit,
                'reason': reason,
                'total_return': (price - pos['entry_price']) / pos['entry_price']
            })
        
        del self.positions[stock_code]
    
    def check_overnight_hold(self,
                            stock_code: str,
                            current_date: datetime,
                            current_price: float) -> bool:
        """
        Decide whether to hold overnight
        
        Hold overnight if:
        1. Stock is leader in strong theme
        2. Has shown strength throughout day
        3. Market conditions favorable
        """
        pos = self.positions[stock_code]
        
        # If D+0 and strong performance, hold for D+1
        if pos['day_count'] == 0 and pos['partial_sold'] >= 1:
            return True
        
        return False
    
    def run_backtest(self,
                    market_data: pd.DataFrame,
                    start_date: datetime,
                    end_date: datetime) -> pd.DataFrame:
        """
        Run backtest of the strategy
        
        Args:
            market_data: DataFrame with columns:
                - date, code, name, sector, open, high, low, close, volume, change_pct
            start_date: Backtest start date
            end_date: Backtest end date
        """
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
        
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            
            # Skip if no data for this date
            day_data = market_data[market_data['date'] == date_str]
            if day_data.empty:
                continue
            
            # 1. Detect dominant themes
            dominant_themes = self.detect_dominant_theme(market_data, date_str)
            
            if dominant_themes:
                # 2. Select leader stock
                leader = self.select_leader_stock(market_data, dominant_themes, date_str)
                
                if leader:
                    leader_data = day_data[day_data['code'] == leader]
                    if not leader_data.empty:
                        # 3. Check entry conditions and enter
                        if self.check_entry_conditions(leader_data, market_data, date_str):
                            entry_price = leader_data.iloc[0]['open'] * 1.05  # Enter after some rise
                            self.enter_position(leader, date_str, entry_price)
            
            # 4. Manage existing positions
            for stock_code in list(self.positions.keys()):
                stock_day_data = day_data[day_data['code'] == stock_code]
                if not stock_day_data.empty:
                    self.manage_position(
                        stock_code,
                        date_str,
                        stock_day_data.iloc[0]['close'],
                        stock_day_data.iloc[0]['high'],
                        stock_day_data.iloc[0]['low']
                    )
            
            # 5. Record daily stats
            portfolio_value = self.cash + sum(
                pos['shares'] * day_data[day_data['code'] == code]['close'].iloc[0]
                for code, pos in self.positions.items()
                if not day_data[day_data['code'] == code].empty
            )
            
            self.daily_stats.append({
                'date': date_str,
                'cash': self.cash,
                'positions': len(self.positions),
                'portfolio_value': portfolio_value,
                'return_pct': (portfolio_value - self.initial_capital) / self.initial_capital * 100
            })
        
        return pd.DataFrame(self.daily_stats)
    
    def get_trade_summary(self) -> pd.DataFrame:
        """Get summary of all completed trades"""
        completed_trades = [
            t for t in self.trades 
            if t['action'] == 'SELL_ALL'
        ]
        return pd.DataFrame(completed_trades)
    
    def calculate_performance_metrics(self) -> Dict:
        """Calculate key performance metrics"""
        if not self.daily_stats:
            return {}
        
        df = pd.DataFrame(self.daily_stats)
        trades_df = self.get_trade_summary()
        
        metrics = {
            'total_return_pct': df['return_pct'].iloc[-1] if len(df) > 0 else 0,
            'max_drawdown_pct': (df['portfolio_value'].cummax() - df['portfolio_value']).max() / df['portfolio_value'].cummax().max() * 100,
            'trading_days': len(df),
            'total_trades': len(trades_df),
        }
        
        if not trades_df.empty:
            metrics['win_rate'] = (trades_df['profit'] > 0).mean() * 100
            metrics['avg_profit'] = trades_df[trades_df['profit'] > 0]['profit'].mean()
            metrics['avg_loss'] = trades_df[trades_df['profit'] < 0]['profit'].mean()
            metrics['profit_factor'] = abs(
                trades_df[trades_df['profit'] > 0]['profit'].sum() / 
                trades_df[trades_df['profit'] < 0]['profit'].sum()
            ) if trades_df[trades_df['profit'] < 0]['profit'].sum() != 0 else float('inf')
        
        return metrics


def load_market_data_from_db(db_path: str, scan_date: str) -> pd.DataFrame:
    """
    Load market data from SQLite database for specific date
    
    Args:
        db_path: Path to level1_prices.db
        scan_date: Date string in 'YYYY-MM-DD' format
    """
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT 
        code,
        name,
        date,
        open,
        high,
        low,
        close,
        volume,
        change_pct,
        market,
        volume * close as trading_value
    FROM price_data 
    WHERE date = ?
    """
    
    df = pd.read_sql_query(query, conn, params=(scan_date,))
    conn.close()
    
    # Filter out index codes
    df = df[~df['code'].str.startswith('^', na=False)]
    
    return df


def get_sector_mapping() -> Dict[str, str]:
    """
    Get sector mapping for stocks using pykrx
    Returns dictionary mapping stock code to sector
    """
    try:
        from pykrx import stock
        
        # Get KOSPI and KOSDAQ stock info
        kospi_df = stock.get_market_ticker_list(market="KOSPI")
        kosdaq_df = stock.get_market_ticker_list(market="KOSDAQ")
        
        sector_map = {}
        
        # Map KOSPI stocks
        for ticker in kospi_df:
            try:
                info = stock.get_market_ticker_name(ticker)
                # Try to get sector from various sources
                sector_map[ticker] = "KOSPI"
            except:
                pass
        
        # Map KOSDAQ stocks  
        for ticker in kosdaq_df:
            try:
                info = stock.get_market_ticker_name(ticker)
                sector_map[ticker] = "KOSDAQ"
            except:
                pass
                
        return sector_map
    except Exception as e:
        print(f"Warning: Could not load sector mapping: {e}")
        return {}


def assign_sectors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign sectors to stocks based on code patterns and external data
    """
    # Create a copy
    df = df.copy()
    
    # Initialize sector column
    df['sector'] = '기타'
    
    # Try to get sector info from stock_list.json if available
    try:
        import json
        with open('data/stock_list.json', 'r', encoding='utf-8') as f:
            stock_list = json.load(f)
            
        # Create code to sector mapping
        code_to_sector = {}
        for stock in stock_list:
            code = stock.get('code', '')
            sector = stock.get('sector', stock.get('industry', '기타'))
            if code:
                code_to_sector[code] = sector
        
        # Apply mapping
        df['sector'] = df['code'].map(code_to_sector).fillna('기타')
    except Exception as e:
        print(f"Warning: Could not load stock_list.json: {e}")
        
        # Fallback: use code-based sector assignment
        # Group by first 2 digits of code as proxy for sector
        df['sector'] = df['code'].str[:2].apply(
            lambda x: f'그룹_{x}' if pd.notna(x) else '기타'
        )
    
    return df


def scan_dominant_themes(scan_date: str = "2026-04-03", 
                         db_path: str = "data/level1_prices.db",
                         min_limit_up: float = 29.5,
                         min_theme_stocks: int = 5) -> Dict:
    """
    Scan for dominant themes on specific date
    
    Returns:
        Dictionary with dominant themes and their leader stocks
    """
    print(f"\n{'='*60}")
    print(f"D+ 주도주 스캐너 - {scan_date}")
    print(f"{'='*60}\n")
    
    # Load market data
    print(f"📊 데이터 로드 중... ({db_path})")
    market_data = load_market_data_from_db(db_path, scan_date)
    
    if market_data.empty:
        print(f"❌ {scan_date} 데이터가 없습니다.")
        return {}
    
    print(f"✅ {len(market_data)}개 종목 데이터 로드 완료")
    
    # Assign sectors
    print("🏷️  섹터 정보 할당 중...")
    market_data = assign_sectors(market_data)
    
    # Calculate trading value
    market_data['trading_value'] = market_data['volume'] * market_data['close']
    
    # Limit up detection (29.5%+ for KOSDAQ, typically 30%)
    market_data['is_limit_up'] = market_data['change_pct'] >= min_limit_up
    limit_up_stocks = market_data[market_data['is_limit_up']].copy()
    
    print(f"\n🚀 상한가 종목: {len(limit_up_stocks)}개")
    
    if len(limit_up_stocks) == 0:
        print("⚠️  상한가 종목이 없습니다.")
        return {}
    
    # Show limit up stocks
    print("\n📋 상한가 종목 목록:")
    for _, stock in limit_up_stocks.iterrows():
        print(f"   • {stock['code']} | {stock['change_pct']:.1f}% | {stock['sector']}")
    
    # Group by sector
    sector_analysis = limit_up_stocks.groupby('sector').agg({
        'code': 'count',
        'name': lambda x: list(x),
        'change_pct': 'mean',
        'trading_value': 'sum'
    }).rename(columns={'code': 'limit_up_count'})
    
    # Filter dominant themes (5+ stocks)
    dominant_themes = sector_analysis[
        sector_analysis['limit_up_count'] >= min_theme_stocks
    ].sort_values('limit_up_count', ascending=False)
    
    print(f"\n📈 주도 테마 감지 결과:")
    print(f"{'-'*60}")
    
    results = {
        'scan_date': scan_date,
        'total_stocks': len(market_data),
        'limit_up_count': len(limit_up_stocks),
        'dominant_themes': []
    }
    
    if dominant_themes.empty:
        print("⚠️  5개 이상 상한가인 주도 테마가 없습니다.")
        print(f"   (상한가 종목: {len(limit_up_stocks)}개)")
        
        # Show sectors with limit-up stocks anyway
        print(f"\n📋 섹터별 상한가 현황:")
        for sector, row in sector_analysis.head(10).iterrows():
            print(f"   • {sector}: {row['limit_up_count']}개")
            
        # Even without dominant themes, show top performers
        print(f"\n🔥 상한가 종목 상세:")
        for _, stock in limit_up_stocks.iterrows():
            print(f"   • {stock['code']} | {stock['sector']} | +{stock['change_pct']:.1f}% | 거래대금 {stock['trading_value']/1e8:.0f}억")
    else:
        print(f"✅ 주도 테마 {len(dominant_themes)}개 감지!\n")
        
        for sector, row in dominant_themes.iterrows():
            print(f"🎯 테마: {sector}")
            print(f"   상한가 종목: {row['limit_up_count']}개")
            print(f"   평균 상승률: {row['change_pct']:.2f}%")
            print(f"   거래대금: {row['trading_value']/1e8:.0f}억원")
            
            # Get stocks in this theme
            theme_stocks = market_data[
                (market_data['sector'] == sector) &
                (market_data['change_pct'] >= min_limit_up)
            ].copy()
            
            # Select leader stock
            if len(theme_stocks) > 0:
                theme_stocks['score'] = (
                    theme_stocks['change_pct'] * 0.4 +
                    (theme_stocks['trading_value'] / theme_stocks['trading_value'].max()) * 30 +
                    (theme_stocks['high'] / theme_stocks['close']) * 20
                )
                
                leader = theme_stocks.loc[theme_stocks['score'].idxmax()]
                
                print(f"\n   🏆 대장주: {leader['code']}")
                print(f"      상승률: {leader['change_pct']:.2f}%")
                print(f"      거래대금: {leader['trading_value']/1e8:.1f}억원")
                print(f"      종가: {leader['close']:,.0f}원")
                print()
                
                theme_data = {
                    'sector': sector,
                    'limit_up_count': int(row['limit_up_count']),
                    'avg_change_pct': float(row['change_pct']),
                    'total_trading_value': float(row['trading_value']),
                    'leader': {
                        'code': leader['code'],
                        'name': leader['name'],
                        'change_pct': float(leader['change_pct']),
                        'trading_value': float(leader['trading_value']),
                        'close': float(leader['close']),
                        'volume': int(leader['volume'])
                    },
                    'all_stocks': theme_stocks[['code', 'name', 'change_pct', 'trading_value']].to_dict('records')
                }
                results['dominant_themes'].append(theme_data)
    
    # Additional: Strong stocks that didn't hit limit up
    print(f"\n🔥 강한 상승 종목 (상한가 미달, +15% 이상):")
    print(f"{'-'*60}")
    strong_stocks = market_data[
        (market_data['change_pct'] >= 15) & 
        (market_data['change_pct'] < min_limit_up) &
        (market_data['trading_value'] >= 1e9)  # 10억 이상 거래대금
    ].sort_values('change_pct', ascending=False).head(10)
    
    results['strong_stocks'] = []
    for _, stock in strong_stocks.iterrows():
        print(f"   • {stock['code']} | {stock['change_pct']:.1f}% | {stock['sector']} | 거래대금 {stock['trading_value']/1e8:.0f}억")
        results['strong_stocks'].append({
            'code': stock['code'],
            'name': stock['name'],
            'change_pct': float(stock['change_pct']),
            'sector': stock['sector'],
            'trading_value': float(stock['trading_value'])
        })
    
    return results


def generate_html_report(scan_results: Dict, output_path: str):
    """Generate HTML report for D+ scanner"""
    
    scan_date = scan_results.get('scan_date', '2026-04-03')
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>D+ 주도주 스캔 리포트 - {scan_date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ 
            text-align: center; 
            padding: 40px 20px; 
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(233, 69, 96, 0.3);
        }}
        h1 {{ font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .subtitle {{ font-size: 1.2em; opacity: 0.9; }}
        .summary-cards {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px;
        }}
        .card {{ 
            background: rgba(255,255,255,0.05); 
            padding: 25px; 
            border-radius: 12px; 
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }}
        .card-value {{ 
            font-size: 2.5em; 
            font-weight: bold; 
            color: #e94560;
            margin: 10px 0;
        }}
        .card-label {{ color: #aaa; font-size: 0.9em; }}
        .theme-section {{ 
            background: rgba(255,255,255,0.03); 
            border-radius: 15px; 
            padding: 30px; 
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .theme-header {{ 
            display: flex; 
            align-items: center; 
            gap: 15px; 
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e94560;
        }}
        .theme-badge {{ 
            background: #e94560; 
            color: white; 
            padding: 8px 20px; 
            border-radius: 25px; 
            font-weight: bold;
        }}
        .leader-card {{ 
            background: linear-gradient(135deg, #0f3460, #16213e);
            padding: 25px; 
            border-radius: 12px; 
            margin: 20px 0;
            border-left: 4px solid #e94560;
        }}
        .leader-title {{ 
            font-size: 1.3em; 
            color: #ffd700; 
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .leader-stats {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
            gap: 15px;
        }}
        .stat {{ 
            background: rgba(0,0,0,0.2); 
            padding: 15px; 
            border-radius: 8px;
        }}
        .stat-value {{ 
            font-size: 1.5em; 
            font-weight: bold; 
            color: #4ecca3;
        }}
        .stat-label {{ font-size: 0.85em; color: #888; margin-top: 5px; }}
        .strategy-box {{ 
            background: linear-gradient(135deg, #1e3a5f, #0f3460);
            padding: 25px; 
            border-radius: 12px; 
            margin-top: 20px;
        }}
        .strategy-title {{ 
            color: #4ecca3; 
            font-size: 1.2em; 
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .strategy-list {{ 
            list-style: none;
            padding-left: 0;
        }}
        .strategy-list li {{ 
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .strategy-list li:before {{ 
            content: "→"; 
            color: #e94560; 
            font-weight: bold;
        }}
        .risk-box {{ 
            background: linear-gradient(135deg, #3a1c1c, #1a1a2e);
            padding: 20px; 
            border-radius: 12px; 
            margin-top: 20px;
            border: 1px solid #e94560;
        }}
        .risk-title {{ color: #ff6b6b; margin-bottom: 10px; }}
        .footer {{ 
            text-align: center; 
            padding: 30px; 
            color: #666;
            margin-top: 40px;
        }}
        .timestamp {{ color: #4ecca3; }}
        .strong-stocks {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
            gap: 15px;
            margin-top: 15px;
        }}
        .stock-item {{ 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .stock-name {{ font-weight: bold; }}
        .stock-sector {{ font-size: 0.8em; color: #888; }}
        .change-up {{ color: #ff6b6b; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏆 D+ 주도주 스캔 리포트</h1>
            <p class="subtitle">홍인기 D+ 매매법 기반 주도 테마 및 대장주 분석</p>
            <p class="subtitle">Scan Date: {scan_date}</p>
        </header>
        
        <div class="summary-cards">
            <div class="card">
                <div class="card-label">전체 종목</div>
                <div class="card-value">{scan_results.get('total_stocks', 0):,}</div>
            </div>
            <div class="card">
                <div class="card-label">상한가 종목</div>
                <div class="card-value">{scan_results.get('limit_up_count', 0)}</div>
            </div>
            <div class="card">
                <div class="card-label">주도 테마</div>
                <div class="card-value">{len(scan_results.get('dominant_themes', []))}</div>
            </div>
        </div>
"""
    
    # Add dominant themes
    for theme in scan_results.get('dominant_themes', []):
        leader = theme.get('leader', {})
        html += f"""
        <div class="theme-section">
            <div class="theme-header">
                <span class="theme-badge">{theme.get('sector', 'N/A')}</span>
                <span>상한가 {theme.get('limit_up_count', 0)}개 | 평균 +{theme.get('avg_change_pct', 0):.1f}%</span>
            </div>
            
            <div class="leader-card">
                <div class="leader-title">👑 대장주: {leader.get('name', 'N/A')} ({leader.get('code', 'N/A')})</div>
                <div class="leader-stats">
                    <div class="stat">
                        <div class="stat-value">+{leader.get('change_pct', 0):.1f}%</div>
                        <div class="stat-label">상승률</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{leader.get('trading_value', 0)/1e8:.0f}억</div>
                        <div class="stat-label">거래대금</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{leader.get('close', 0):,.0f}</div>
                        <div class="stat-label">종가 (원)</div>
                    </div>
                </div>
            </div>
            
            <div class="strategy-box">
                <div class="strategy-title">📈 D+ 매매 전략 가이드</div>
                <ul class="strategy-list">
                    <li>D+0 (오늘): 오전 9:30 이후 테마 확인 후 진입, 분할 매수</li>
                    <li>상한가 도달 시: 30~50% 수익 실현, 나머지 오버나잇</li>
                    <li>D+1 (내일): 갭상승 시 절반 추가 수익 실현</li>
                    <li>D+2 (모레): 전량 수익 실현 또는 추세 유지 시 재진입</li>
                    <li>손절 기준: -7% 손실 시 전량 매도</li>
                </ul>
            </div>
            
            <div class="risk-box">
                <div class="risk-title">⚠️ 리스크 관리 포인트</div>
                <p>• 해당 테마 이미 {theme.get('limit_up_count', 0)}개 종목 상한가 - 과열 가능성 주시</p>
                <p>• 시장 급락 시 주도주 분할 매수 기회로 활용</p>
                <p>• 동일 섹터 중복 포지션 금지</p>
            </div>
        </div>
"""
    
    # Add strong stocks section
    if scan_results.get('strong_stocks'):
        html += """
        <div class="theme-section">
            <div class="theme-header">
                <span class="theme-badge" style="background: #4ecca3;">강한 상승 종목</span>
                <span>상한가 미달 (+15% 이상)</span>
            </div>
            <div class="strong-stocks">
"""
        for stock in scan_results.get('strong_stocks', [])[:10]:
            html += f"""
                <div class="stock-item">
                    <div>
                        <div class="stock-name">{stock.get('name', 'N/A')}</div>
                        <div class="stock-sector">{stock.get('sector', 'N/A')}</div>
                    </div>
                    <div class="change-up">+{stock.get('change_pct', 0):.1f}%</div>
                </div>
"""
        html += """
            </div>
        </div>
"""
    
    html += f"""
        <div class="footer">
            <p>Generated by D+ Leading Stock Scanner</p>
            <p class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p style="margin-top: 10px; font-size: 0.85em;">
                ⚠️ 본 리포트는 정보 제공 목적이며, 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n📄 HTML 리포트 생성 완료: {output_path}")


# Example usage and backtest runner
def run_dplus_backtest_example():
    """Example of running the D+ strategy backtest"""
    
    # Initialize strategy
    strategy = DPlusLeadingStockStrategy(
        initial_capital=100_000_000,  # 1억원
        max_positions=3,
        position_size_pct=0.20,  # 20% per position
        stop_loss_pct=-0.07,  # -7% stop
        profit_take_1=0.10,  # 10% partial
        profit_take_2=0.20   # 20% partial
    )
    
    # Note: Actual market data would need to be loaded from database
    # This is just the strategy framework
    
    print("D+ Leading Stock Strategy Initialized")
    print("=" * 50)
    print("Core Rules:")
    print("1. Detect themes with 5+ limit-up stocks")
    print("2. Select strongest leader (high volume, strong momentum)")
    print("3. Enter around 9:30 AM after confirming theme")
    print("4. Partial profit at +10%, +20%, limit up")
    print("5. Hold overnight for D+1/D+2 continuation")
    print("6. Stop loss at -7%")
    print("=" * 50)
    
    return strategy


if __name__ == "__main__":
    import json
    
    # Run scanner for 2026-04-03
    SCAN_DATE = "2026-04-03"
    DB_PATH = "data/level1_prices.db"
    OUTPUT_JSON = f"honginki_scan_results_{SCAN_DATE.replace('-', '')}.json"
    OUTPUT_HTML = f"docs/honginki_dplus_report_{SCAN_DATE.replace('-', '')}.html"
    
    # Run scan
    results = scan_dominant_themes(
        scan_date=SCAN_DATE,
        db_path=DB_PATH,
        min_limit_up=29.5,
        min_theme_stocks=5
    )
    
    # Save JSON results
    if results:
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 JSON 결과 저장: {OUTPUT_JSON}")
        
        # Generate HTML report
        generate_html_report(results, OUTPUT_HTML)
    else:
        print("\n⚠️  스캔 결과가 없습니다.")
