#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chart Generator for February 2026 Selected Stocks
=================================================
2026년 2월 발굴 종목들의 현재까지 차트 생성
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

from fdr_wrapper import FDRWrapper
from buy_strength_scanner import BuyStrengthScanner


def plot_stock_chart(symbol: str, name: str, output_path: str):
    """단일 종목 차트 생성"""
    
    fdr = FDRWrapper()
    scanner = BuyStrengthScanner()
    
    # 데이터 로드
    df = fdr.get_price(symbol, min_days=60)
    df.columns = [c.lower() for c in df.columns]
    df['date'] = pd.to_datetime(df['date'])
    
    # 지표 계산
    df['ema20'] = scanner.calculate_ema(df['close'], 20)
    df['ema60'] = scanner.calculate_ema(df['close'], 60)
    df['rsi14'] = scanner.calculate_rsi(df['close'], 14)
    
    # 2월 1일 이후 데이터만
    df = df[df['date'] >= '2026-02-01'].copy()
    
    if len(df) < 10:
        return False
    
    # 차트 생성
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), 
                            gridspec_kw={'height_ratios': [3, 1, 1]})
    fig.suptitle(f'{symbol} - {name}\nFeb 2026 Signal → Current Performance', 
                fontsize=14, fontweight='bold')
    
    # 1. 가격 차트
    ax1 = axes[0]
    ax1.plot(df['date'], df['close'], label='Close', color='black', linewidth=2)
    ax1.plot(df['date'], df['ema20'], label='EMA20', color='blue', linewidth=1, alpha=0.7)
    ax1.plot(df['date'], df['ema60'], label='EMA60', color='red', linewidth=1, alpha=0.7)
    
    # 2월 발굴 시점 표시
    feb_start = df['close'].iloc[0]
    current = df['close'].iloc[-1]
    change_pct = (current / feb_start - 1) * 100
    
    ax1.axvline(x=df['date'].iloc[0], color='green', linestyle='--', alpha=0.5, label='Feb Signal')
    ax1.fill_between(df['date'], df['low'], df['high'], alpha=0.1, color='gray')
    
    ax1.set_ylabel('Price (KRW)', fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_title(f'Return: {change_pct:+.1f}% ({feb_start:,.0f} → {current:,.0f})', 
                 fontweight='bold', color='green' if change_pct > 0 else 'red')
    
    # 2. 거래량
    ax2 = axes[1]
    colors = ['red' if c >= o else 'blue' for c, o in zip(df['close'], df['open'])]
    ax2.bar(df['date'], df['volume'], color=colors, alpha=0.6)
    ax2.set_ylabel('Volume', fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 거래량 평균선
    vol_ma20 = df['volume'].rolling(20).mean()
    ax2.plot(df['date'], vol_ma20, color='orange', linewidth=1, label='VMA20')
    ax2.legend(loc='upper left')
    
    # 3. RSI
    ax3 = axes[2]
    ax3.plot(df['date'], df['rsi14'], color='purple', linewidth=1.5)
    ax3.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='Overbought (70)')
    ax3.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='Neutral (50)')
    ax3.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='Oversold (30)')
    ax3.fill_between(df['date'], 30, 70, alpha=0.1, color='gray')
    ax3.set_ylabel('RSI(14)', fontweight='bold')
    ax3.set_xlabel('Date', fontweight='bold')
    ax3.set_ylim(0, 100)
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    
    # 날짜 포맷
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return True


def generate_all_charts():
    """모든 발굴 종목 차트 생성"""
    
    # 2월 발굴 종목 리스트
    stocks = [
        ('486450', '미국AI전력인프라'),
        ('261240', '미국달러선물'),
        ('002100', '경농'),
        ('001130', '대한제분'),
        ('003925', '남양유업우'),
        ('019180', '티에이치엔'),
        ('025860', '남해화학'),
    ]
    
    output_dir = './reports/buy_strength_feb2026/charts'
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    print("🎨 차트 생성 중...")
    print("=" * 60)
    
    for symbol, name in stocks:
        output_path = f'{output_dir}/{symbol}_{name}.png'
        if plot_stock_chart(symbol, name, output_path):
            print(f"✅ {symbol} ({name}) 차트 생성 완료")
        else:
            print(f"⚠️ {symbol} ({name}) 데이터 부족")
    
    print("=" * 60)
    print(f"📁 차트 저장 완료: {output_dir}")
    
    # 종합 리포트 차트
    plot_summary_chart(stocks, f'{output_dir}/summary.png')


def plot_summary_chart(stocks, output_path):
    """종합 요약 차트"""
    
    fdr = FDRWrapper()
    
    fig, axes = plt.subplots(len(stocks), 1, figsize=(14, 3*len(stocks)))
    if len(stocks) == 1:
        axes = [axes]
    
    fig.suptitle('February 2026 Buy Strength Signals - Performance Summary', 
                fontsize=16, fontweight='bold')
    
    for idx, (symbol, name) in enumerate(stocks):
        try:
            df = fdr.get_price(symbol, min_days=60)
            df.columns = [c.lower() for c in df.columns]
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'] >= '2026-02-01'].copy()
            
            ax = axes[idx]
            
            # 정규화 (2월 1일 = 100)
            base_price = df['close'].iloc[0]
            normalized = (df['close'] / base_price) * 100
            
            ax.plot(df['date'], normalized, linewidth=2)
            ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5)
            ax.fill_between(df['date'], 100, normalized, 
                          where=normalized >= 100, alpha=0.3, color='green')
            ax.fill_between(df['date'], 100, normalized, 
                          where=normalized < 100, alpha=0.3, color='red')
            
            final_return = normalized.iloc[-1] - 100
            ax.set_title(f'{symbol} - {name}: {final_return:+.1f}%', 
                        fontweight='bold',
                        color='green' if final_return > 0 else 'red')
            ax.set_ylabel('Normalized (Feb 1 = 100)')
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            
        except Exception as e:
            ax = axes[idx]
            ax.text(0.5, 0.5, f'{symbol} - Error', ha='center', va='center')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"📊 종합 차트 저장: {output_path}")


if __name__ == "__main__":
    generate_all_charts()
    print("\n✅ 모든 차트 생성 완료!")
