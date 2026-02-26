#!/usr/bin/env python3
"""
KStock Data Updater - 매일 자동 데이터 갱신
"""

import yfinance as yf
import pandas as pd
import json
from datetime import datetime
import os

BASE_PATH = '/home/programs/kstock_analyzer'

def update_kospi():
    """KOSPI 데이터 갱신"""
    print(f"[{datetime.now()}] KOSPI 데이터 갱신 중...")
    
    try:
        df = yf.download('^KS11', period='1y', progress=False)
        if not df.empty:
            df.to_csv(f'{BASE_PATH}/data/kospi_history.csv')
            print(f"  ✅ KOSPI: {len(df)}일 데이터 저장")
            return df
    except Exception as e:
        print(f"  ❌ KOSPI 오류: {e}")
    return None

def update_kosdaq():
    """KOSDAQ 데이터 갱신"""
    print(f"[{datetime.now()}] KOSDAQ 데이터 갱신 중...")
    
    try:
        df = yf.download('^KQ11', period='1y', progress=False)
        if not df.empty:
            df.to_csv(f'{BASE_PATH}/data/kosdaq_history.csv')
            print(f"  ✅ KOSDAQ: {len(df)}일 데이터 저장")
            return df
    except Exception as e:
        print(f"  ❌ KOSDAQ 오류: {e}")
    return None

def update_stocks():
    """개별 종목 갱신"""
    stocks = {
        '005930.KS': ('samsung', '삼성전자'),
        '000660.KS': ('skhynix', 'SK하이닉스')
    }
    
    for symbol, (filename, name) in stocks.items():
        try:
            df = yf.download(symbol, period='6mo', progress=False)
            if not df.empty:
                df.to_csv(f'{BASE_PATH}/data/{filename}.csv')
                print(f"  ✅ {name}: {len(df)}일 데이터")
        except Exception as e:
            print(f"  ❌ {name} 오류: {e}")

def analyze_kospi(df):
    """KOSPI 기술적 분석"""
    if df is None or df.empty:
        return {}
    
    # 데이터 정제
    df = df.copy()
    df.columns = ['Close', 'High', 'Low', 'Open', 'Volume']
    
    # 이동평균
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 추세 판단
    if latest['Close'] > latest['MA20'] > latest['MA60']:
        trend = 'BULLISH'
    elif latest['Close'] < latest['MA20'] < latest['MA60']:
        trend = 'BEARISH'
    else:
        trend = 'NEUTRAL'
    
    # 알림
    rsi = latest['RSI']
    alert = None
    if rsi > 80:
        alert = 'RSI 과매수 (80+)'
    elif rsi > 70:
        alert = 'RSI 과매수 (70+)'
    elif rsi < 20:
        alert = 'RSI 과매도 (20-)'
    elif rsi < 30:
        alert = 'RSI 과매도 (30-)'
    
    analysis = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_price': round(latest['Close'], 2),
        'change': round(latest['Close'] - prev['Close'], 2),
        'change_pct': round((latest['Close'] - prev['Close']) / prev['Close'] * 100, 2),
        'volume': int(latest['Volume']),
        'ma20': round(latest['MA20'], 2),
        'ma60': round(latest['MA60'], 2),
        'rsi': round(rsi, 2),
        'trend': trend,
        'alert': alert
    }
    
    # CSV 저장
    pd.DataFrame([analysis]).to_csv(f'{BASE_PATH}/data/kospi_analysis.csv', index=False)
    
    # JSON 인덱스 업데이트
    update_index(analysis)
    
    return analysis

def update_index(analysis):
    """데이터 인덱스 업데이트"""
    index_file = f'{BASE_PATH}/market_data_index.json'
    
    try:
        with open(index_file, 'r') as f:
            index = json.load(f)
    except:
        index = {}
    
    index['last_updated'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00')
    
    if 'indices' not in index:
        index['indices'] = {}
    
    index['indices']['kospi'] = {
        'symbol': '^KS11',
        'name': 'KOSPI',
        'currency': 'KRW',
        'last_price': analysis.get('last_price'),
        'change_percent': analysis.get('change_pct'),
        'trend': analysis.get('trend'),
        'rsi': analysis.get('rsi'),
        'ma20': analysis.get('ma20'),
        'ma60': analysis.get('ma60'),
        'alert': analysis.get('alert')
    }
    
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)
    
    print(f"  ✅ 인덱스 업데이트 완료")

def main():
    """메인 업데이트 함수"""
    print(f"\n{'='*60}")
    print(f"🚀 KStock 데이터 자동 갱신")
    print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 데이터 갱신
    kospi_df = update_kospi()
    kosdaq_df = update_kosdaq()
    update_stocks()
    
    # 분석
    if kospi_df is not None:
        analysis = analyze_kospi(kospi_df)
        print(f"\n📊 분석 결과:")
        print(f"  종가: {analysis['last_price']:,.0f}")
        print(f"  등락: {analysis['change']:+.0f} ({analysis['change_pct']:+.2f}%)")
        print(f"  추세: {analysis['trend']}")
        print(f"  RSI: {analysis['rsi']:.2f}")
        if analysis['alert']:
            print(f"  알림: {analysis['alert']}")
    
    # 대시보드 생성
    print(f"\n📈 대시보드 생성 중...")
    try:
        import subprocess
        result = subprocess.run(['python3', 'generate_dashboard.py'], 
                              capture_output=True, text=True, cwd=BASE_PATH)
        if result.returncode == 0:
            print("  ✅ 대시보드 생성 완료")
        else:
            print(f"  ⚠️ 대시보드 생성 오류: {result.stderr}")
    except Exception as e:
        print(f"  ⚠️ 대시보드 생성 실패: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ 갱신 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
