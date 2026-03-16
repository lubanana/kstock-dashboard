#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이터닉스 (475150) 심층 기술적 분석
"""

import sqlite3
import pandas as pd
import numpy as np

# DB 연결
conn = sqlite3.connect('./data/pivot_strategy.db')

# 이터닉스 데이터 조회
df = pd.read_sql_query('''
    SELECT date, open, high, low, close, volume 
    FROM stock_prices 
    WHERE symbol = '475150' 
    ORDER BY date DESC 
    LIMIT 120
''', conn)

conn.close()

df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

# 기술적 지표 계산
# 1. 이동평균선
df['MA5'] = df['close'].rolling(window=5).mean()
df['MA10'] = df['close'].rolling(window=10).mean()
df['MA20'] = df['close'].rolling(window=20).mean()
df['MA60'] = df['close'].rolling(window=60).mean()

# 2. RSI
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))

# 3. 볼린저 밴드
df['BB_Middle'] = df['close'].rolling(window=20).mean()
df['BB_Std'] = df['close'].rolling(window=20).std()
df['BB_Upper'] = df['BB_Middle'] + (df['BB_Std'] * 2)
df['BB_Lower'] = df['BB_Middle'] - (df['BB_Std'] * 2)
df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle'] * 100
df['BB_Position'] = (df['close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])

# 4. MACD
exp1 = df['close'].ewm(span=12).mean()
exp2 = df['close'].ewm(span=26).mean()
df['MACD'] = exp1 - exp2
df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

# 5. 거래량 지표
df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
df['Volume_Ratio'] = df['volume'] / df['Volume_MA20']

# 6. ATR
df['TR1'] = df['high'] - df['low']
df['TR2'] = abs(df['high'] - df['close'].shift())
df['TR3'] = abs(df['low'] - df['close'].shift())
df['TR'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
df['ATR14'] = df['TR'].rolling(window=14).mean()

# 7. 스토캐스틱
low_14 = df['low'].rolling(window=14).min()
high_14 = df['high'].rolling(window=14).max()
df['Stoch_K'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()

# 최근 데이터
latest = df.iloc[-1]
prev = df.iloc[-2]
week_ago = df.iloc[-6] if len(df) >= 6 else df.iloc[0]
month_ago = df.iloc[-21] if len(df) >= 21 else df.iloc[0]

# 출력
print('=' * 70)
print('🔬 이터닉스 (475150) 심층 기술적 분석 리포트')
print('=' * 70)
print(f'\n📅 기준일: {latest["date"].strftime("%Y-%m-%d")}')
print(f'🏢 회사명: 이터닉스 (반도체 장비)')
print(f'💰 현재가: {latest["close"]:,.0f}원')
change_pct = (latest["close"] - prev["close"]) / prev["close"] * 100
print(f'📊 전일대비: {change_pct:+.2f}% ({latest["close"] - prev["close"]:+,.0f}원)')
print(f'📈 거래량: {latest["volume"]:,.0f}주 (20일평균 대비 {latest["Volume_Ratio"]:.1f}배)')

# 가격 변동 분석
print('\n' + '=' * 70)
print('📈 가격 변동 분석')
print('=' * 70)
week_change = (latest["close"] - week_ago["close"]) / week_ago["close"] * 100
month_change = (latest["close"] - month_ago["close"]) / month_ago["close"] * 100
print(f'1주일 변동: {week_change:+.2f}%')
print(f'1개월 변동: {month_change:+.2f}%')
print(f'\n🔺 52주 최고가 대비: {(latest["close"] / df["high"].max() * 100):.1f}%')
print(f'🔻 52주 최저가 대비: {(latest["close"] / df["low"].min() * 100):.1f}%')

# 이동평균선 분석
print('\n' + '=' * 70)
print('📊 이동평균선 분석')
print('=' * 70)
print(f'MA5:   {latest["MA5"]:>10,.0f}원 ({"▲" if latest["close"] > latest["MA5"] else "▼"} {abs((latest["close"]/latest["MA5"]-1)*100):.2f}%)')
print(f'MA10:  {latest["MA10"]:>10,.0f}원 ({"▲" if latest["close"] > latest["MA10"] else "▼"} {abs((latest["close"]/latest["MA10"]-1)*100):.2f}%)')
print(f'MA20:  {latest["MA20"]:>10,.0f}원 ({"▲" if latest["close"] > latest["MA20"] else "▼"} {abs((latest["close"]/latest["MA20"]-1)*100):.2f}%)')
print(f'MA60:  {latest["MA60"]:>10,.0f}원 ({"▲" if latest["close"] > latest["MA60"] else "▼"} {abs((latest["close"]/latest["MA60"]-1)*100):.2f}%)')

# 정배열/역배열 판단
ma_trend = "정배열 (강세)" if latest["MA5"] > latest["MA20"] > latest["MA60"] else \
           "역배열 (약세)" if latest["MA5"] < latest["MA20"] < latest["MA60"] else "혼조세"
print(f'\n📈 추세 판단: {ma_trend}')

# RSI 분석
print('\n' + '=' * 70)
print('⚡ RSI(14) 분석')
print('=' * 70)
rsi = latest["RSI"]
rsi_status = "과매수 (>70)" if rsi > 70 else "과매도 (<30)" if rsi < 30 else "중립"
print(f'RSI: {rsi:.1f} ({rsi_status})')
print(f'RSI 추세: {"상승" if latest["RSI"] > prev["RSI"] else "하락"} ({prev["RSI"]:.1f} → {rsi:.1f})')

# 볼린저 밴드 분석
print('\n' + '=' * 70)
print('🎯 볼린저 밴드 분석')
print('=' * 70)
print(f'상단: {latest["BB_Upper"]:,.0f}원')
print(f'중단: {latest["BB_Middle"]:,.0f}원')
print(f'하단: {latest["BB_Lower"]:,.0f}원')
print(f'밴드폭: {latest["BB_Width"]:.1f}%')
print(f'위치: 하단에서 {(latest["BB_Position"]*100):.1f}% 위치')

bb_signal = "상단 돌파 (과매수)" if latest["close"] > latest["BB_Upper"] else \
            "하단 이탈 (과매도)" if latest["close"] < latest["BB_Lower"] else "밴드 내"
print(f'신호: {bb_signal}')

# MACD 분석
print('\n' + '=' * 70)
print('📊 MACD 분석')
print('=' * 70)
print(f'MACD:       {latest["MACD"]:,.0f}')
print(f'Signal:     {latest["MACD_Signal"]:,.0f}')
print(f'Histogram:  {latest["MACD_Hist"]:,.0f}')

macd_signal = "골든크로스" if latest["MACD"] > latest["MACD_Signal"] and prev["MACD"] <= prev["MACD_Signal"] else \
              "데드크로스" if latest["MACD"] < latest["MACD_Signal"] and prev["MACD"] >= prev["MACD_Signal"] else \
              "상승중" if latest["MACD"] > latest["MACD_Signal"] else "하락중"
print(f'신호: {macd_signal}')

# 스토캐스틱 분석
print('\n' + '=' * 70)
print('🔄 스토캐스틱 분석')
print('=' * 70)
print(f'%K: {latest["Stoch_K"]:.1f}')
print(f'%D: {latest["Stoch_D"]:.1f}')
stoch_signal = "과매수 (>80)" if latest["Stoch_K"] > 80 else "과매도 (<20)" if latest["Stoch_K"] < 20 else "중립"
print(f'상태: {stoch_signal}')

# 거래량 분석
print('\n' + '=' * 70)
print('📊 거래량 분석')
print('=' * 70)
print(f'현재: {latest["volume"]:,.0f}주')
print(f'20일평균: {latest["Volume_MA20"]:,.0f}주')
print(f'거래량비율: {latest["Volume_Ratio"]:.1f}배')
vol_signal = "매우활발" if latest["Volume_Ratio"] > 3 else "활발" if latest["Volume_Ratio"] > 1.5 else "보통" if latest["Volume_Ratio"] > 0.8 else "저조"
print(f'판단: {vol_signal}')

# ATR (변동성)
print('\n' + '=' * 70)
print('📈 변동성 (ATR) 분석')
print('=' * 70)
print(f'ATR(14): {latest["ATR14"]:,.0f}원')
print(f'변동률: {(latest["ATR14"]/latest["close"]*100):.2f}%')

# 지지/저항선
print('\n' + '=' * 70)
print('🎯 지지/저항선')
print('=' * 70)
recent_20 = df.tail(20)
resistance = recent_20['high'].max()
support = recent_20['low'].min()
print(f'저항선: {resistance:,.0f}원 (20일 최고)')
print(f'지지선: {support:,.0f}원 (20일 최저)')
print(f'현재가 위치: 저항선 대비 {((resistance-latest["close"])/(resistance-support)*100):.1f}% 아래')

# 종합 판단
print('\n' + '=' * 70)
print('🎯 종합 기술적 판단')
print('=' * 70)

# 매수 신호 카운트
buy_signals = 0
sell_signals = 0

if latest["close"] > latest["MA20"]: buy_signals += 1
else: sell_signals += 1

if 30 < rsi < 70: buy_signals += 0.5
elif rsi < 30: buy_signals += 1
else: sell_signals += 1

if latest["MACD"] > latest["MACD_Signal"]: buy_signals += 1
else: sell_signals += 1

if latest["Volume_Ratio"] > 1.5: buy_signals += 1

if latest["BB_Position"] < 0.3: buy_signals += 0.5
elif latest["BB_Position"] > 0.7: sell_signals += 0.5

print(f'매수 신호: {buy_signals:.1f}점')
print(f'매도 신호: {sell_signals:.1f}점')

if buy_signals >= 3:
    overall = "매우 긍정적 (강력 매수 권장)"
elif buy_signals >= 2:
    overall = "긍정적 (매수 권장)"
elif sell_signals >= 3:
    overall = "부정적 (관망/매도)"
else:
    overall = "중립 (추가 확인 필요)"

print(f'종합 판단: {overall}')

# 목표가/손절가 제안
print('\n' + '=' * 70)
print('💡 매매 전략 제안')
print('=' * 70)
target = latest["close"] * 1.15
cut_loss = latest["close"] * 0.93
print(f'진입가: {latest["close"]:,.0f}원')
print(f'목표가: {target:,.0f}원 (+15%)')
print(f'손절가: {cut_loss:,.0f}원 (-7%)')
print(f'리스크/리워드: 1:{(15/7):.1f}')

# 주요 리스크
print('\n' + '=' * 70)
print('⚠️ 주의사항 및 리스크')
print('=' * 70)
risks = []
if rsi > 70: risks.append("- RSI 과매수 구간 (조정 가능성)")
if latest["close"] > latest["BB_Upper"]: risks.append("- 볼린저 밴드 상단 돌파 (단기 과열)")
if latest["Volume_Ratio"] > 5: risks.append("- 거래량 급증 (변동성 확대)")
if not risks:
    risks.append("- 특이사항 없음 (정상 거래)")
for risk in risks:
    print(risk)

print('\n' + '=' * 70)
print('* 이 분석은 기술적 지표만을 기반으로 하며, 투자 참고용입니다.')
print('=' * 70)
