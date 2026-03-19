#!/usr/bin/env python3
"""
SMC FVG Visualizer - LuxAlgo Style Chart
SMC FVG 차트 시각화 (트레이딩뷰 스타일)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from datetime import datetime
from typing import Dict, List, Optional


class SMCFVGVisualizer:
    """
    SMC FVG 차트 시각화 클래스
    """
    
    def __init__(self, figsize=(16, 10)):
        self.figsize = figsize
        plt.style.use('dark_background')
    
    def plot_smc_chart(self, df: pd.DataFrame, 
                       swing_highs: List[int], 
                       swing_lows: List[int],
                       fvgs: List[Dict],
                       msb: Optional[Dict],
                       signal: Optional[Dict],
                       title: str = "SMC FVG Chart"):
        """
        SMC 스타일 차트 그리기
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        # 메인 차트
        self._plot_candles(ax1, df)
        self._plot_swing_points(ax1, df, swing_highs, swing_lows)
        self._plot_fvgs(ax1, df, fvgs)
        self._plot_msb(ax1, df, msb)
        
        if signal:
            self._plot_signal(ax1, signal)
        
        # 볼륨 차트
        self._plot_volume(ax2, df)
        
        # 스타일링
        ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax1.set_ylabel('Price (USDT)', fontsize=11)
        ax1.grid(True, alpha=0.2)
        ax1.legend(loc='upper left')
        
        ax2.set_ylabel('Volume', fontsize=11)
        ax2.set_xlabel('Time', fontsize=11)
        ax2.grid(True, alpha=0.2)
        
        plt.tight_layout()
        return fig
    
    def _plot_candles(self, ax, df: pd.DataFrame):
        """
        캔들스틱 그리기
        """
        width = 0.6
        width2 = 0.05
        
        for i, (idx, row) in enumerate(df.iterrows()):
            color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
            
            # 몸통
            height = abs(row['close'] - row['open'])
            bottom = min(row['close'], row['open'])
            ax.bar(i, height, width, bottom=bottom, color=color, edgecolor=color)
            
            # 꼬리
            ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.8)
    
    def _plot_swing_points(self, ax, df: pd.DataFrame, 
                          swing_highs: List[int], swing_lows: List[int]):
        """
        스윙 포인트 표시
        """
        highs = df['high'].values
        lows = df['low'].values
        
        # 스윙 하이 (빨간색 다이아몬드)
        for idx in swing_highs:
            ax.scatter(idx, highs[idx], marker='D', color='#ff5252', 
                      s=80, zorder=5, label='Swing High' if idx == swing_highs[0] else "")
        
        # 스윙 로우 (초록색 다이아몬드)
        for idx in swing_lows:
            ax.scatter(idx, lows[idx], marker='D', color='#69f0ae', 
                      s=80, zorder=5, label='Swing Low' if idx == swing_lows[0] else "")
    
    def _plot_fvgs(self, ax, df: pd.DataFrame, fvgs: List[Dict]):
        """
        FVG 구간 표시 (LuxAlgo 스타일)
        """
        for i, fvg in enumerate(fvgs):
            idx = fvg['idx']
            
            if fvg['type'] == 'BULLISH':
                # 불리쉬 FVG: 초록색 박스
                rect = Rectangle((idx-0.5, fvg['bottom']), 3, fvg['top']-fvg['bottom'],
                                linewidth=1, edgecolor='#00c853', 
                                facecolor='#00c853', alpha=0.2)
                ax.add_patch(rect)
                
                # 레이블
                ax.text(idx+1, fvg['top'], f'Bull FVG {fvg["size"]:.2f}%',
                       fontsize=8, color='#00c853', ha='center', va='bottom')
                
                # 오더블록 표시
                if 'ob_low' in fvg:
                    ax.axhline(y=fvg['ob_low'], xmin=(idx-0.5)/len(df), 
                              xmax=(idx+2.5)/len(df), color='#ff9100', 
                              linestyle='--', linewidth=1.5, alpha=0.7)
            
            else:  # BEARISH
                # 베리쉬 FVG: 빨간색 박스
                rect = Rectangle((idx-0.5, fvg['bottom']), 3, fvg['top']-fvg['bottom'],
                                linewidth=1, edgecolor='#ff1744',
                                facecolor='#ff1744', alpha=0.2)
                ax.add_patch(rect)
                
                ax.text(idx+1, fvg['bottom'], f'Bear FVG {fvg["size"]:.2f}%',
                       fontsize=8, color='#ff1744', ha='center', va='top')
    
    def _plot_msb(self, ax, df: pd.DataFrame, msb: Optional[Dict]):
        """
        MSB (Market Structure Break) 표시
        """
        if not msb:
            return
        
        # 이전 스윙 하이 수평선
        ax.axhline(y=msb['prev_swing_high'], color='#ff5252', 
                  linestyle='-', linewidth=2, alpha=0.8, label='Previous SH')
        
        # 돌파 화살표
        last_idx = len(df) - 1
        ax.annotate('MSB', xy=(last_idx, msb['breakout_price']),
                   xytext=(last_idx-5, msb['breakout_price']*1.02),
                   arrowprops=dict(arrowstyle='->', color='#ffd700', lw=2),
                   fontsize=12, color='#ffd700', fontweight='bold')
    
    def _plot_signal(self, ax, signal: Dict):
        """
        진입 신호 표시
        """
        last_idx = len(ax.get_xlim()) - 1 if hasattr(ax, 'get_xlim') else 100
        
        # 진입가
        ax.axhline(y=signal['entry_price'], color='#00e676', 
                  linestyle='--', linewidth=2, label=f'Entry ${signal["entry_price"]:.2f}')
        
        # 손절가
        ax.axhline(y=signal['sl_price'], color='#ff1744',
                  linestyle='--', linewidth=2, label=f'SL ${signal["sl_price"]:.2f}')
        
        # 익절가
        ax.axhline(y=signal['tp_price'], color='#ffd700',
                  linestyle='--', linewidth=2, label=f'TP ${signal["tp_price"]:.2f}')
        
        # 리스크/리워드 비율 텍스트
        textstr = f'R:R = 1:{signal["rr_ratio"]:.2f}\nExpected: {signal["expected_return"]:.1f}%'
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes,
               fontsize=11, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
    
    def _plot_volume(self, ax, df: pd.DataFrame):
        """
        거래량 차트
        """
        colors = ['#26a69a' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ef5350' 
                 for i in range(len(df))]
        ax.bar(range(len(df)), df['volume'], color=colors, alpha=0.7)
        ax.set_ylim(0, df['volume'].max() * 1.2)


def generate_sample_data():
    """
    테스트용 샘플 데이터 생성
    """
    np.random.seed(42)
    n = 100
    
    # 가격 생성
    price = 45000
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []
    
    for i in range(n):
        change = np.random.randn() * 200
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + abs(np.random.randn()) * 100
        low_p = min(open_p, close_p) - abs(np.random.randn()) * 100
        
        opens.append(open_p)
        highs.append(high_p)
        lows.append(low_p)
        closes.append(close_p)
        volumes.append(np.random.randint(1000, 5000))
        
        price = close_p
    
    dates = pd.date_range(end=datetime.now(), periods=n, freq='1h')
    
    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)
    
    return df


def main():
    """
    테스트 실행
    """
    print("🎨 SMC FVG 시각화 테스트")
    
    # 샘플 데이터 생성
    df = generate_sample_data()
    
    # 임의의 분석 결과
    swing_highs = [20, 45, 70, 85]
    swing_lows = [10, 30, 55, 75]
    
    fvgs = [
        {'type': 'BULLISH', 'idx': 35, 'top': 45800, 'bottom': 45500, 
         'size': 0.66, 'ob_low': 45400},
        {'type': 'BULLISH', 'idx': 60, 'top': 47200, 'bottom': 46800,
         'size': 0.85, 'ob_low': 46700}
    ]
    
    msb = {
        'prev_swing_high': 47000,
        'breakout_price': 47500,
        'strength': 1.06
    }
    
    signal = {
        'entry_price': 47300,
        'sl_price': 46700,
        'tp_price': 48800,
        'rr_ratio': 2.5,
        'expected_return': 3.17
    }
    
    # 차트 그리기
    visualizer = SMCFVGVisualizer()
    fig = visualizer.plot_smc_chart(
        df=df,
        swing_highs=swing_highs,
        swing_lows=swing_lows,
        fvgs=fvgs,
        msb=msb,
        signal=signal,
        title="BTC/USDT SMC FVG Analysis (1H)"
    )
    
    # 저장
    plt.savefig('./smc_fvg_chart.png', dpi=150, bbox_inches='tight',
               facecolor='#1a1a2e', edgecolor='none')
    print("✅ 차트 저장: ./smc_fvg_chart.png")
    
    plt.show()


if __name__ == '__main__':
    main()
