#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEPA + VCP Visualizer
=====================
VCP 패턴 시각화 모듈

- 캔들스틱 차트에 수축 구간 표시
- 피벗 라인 시각화
- 거래량 차트 포함
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional, Dict
from sepa_vcp_strategy import SEPASignal, VCPContraction, SEPA_VCP_Strategy


class SEPA_VCP_Visualizer:
    """SEPA + VCP 패턴 시각화 클래스"""
    
    def __init__(self, figsize=(16, 12)):
        self.figsize = figsize
        self.colors = {
            'contraction': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'],
            'pivot_line': '#FF0000',
            'ma50': '#FFA500',
            'ma150': '#800080',
            'ma200': '#0000FF',
            'up_candle': '#FF0000',  # 한국식: 상승 빨강
            'down_candle': '#0000FF'  # 한국식: 하락 파랑
        }
    
    def plot_matplotlib(self, df: pd.DataFrame, signal: SEPASignal, 
                       save_path: Optional[str] = None) -> plt.Figure:
        """
        Matplotlib으로 VCP 패턴 시각화
        
        Args:
            df: 주가 데이터
            signal: SEPASignal 객체
            save_path: 저장 경로
        
        Returns:
            matplotlib Figure 객체
        """
        fig, axes = plt.subplots(3, 1, figsize=self.figsize, 
                                gridspec_kw={'height_ratios': [3, 1, 1]})
        
        # 최근 6개월 데이터만
        plot_df = df.tail(120).copy()
        plot_df.reset_index(inplace=True)
        
        x = range(len(plot_df))
        
        # 1. 캔들스틱 차트
        ax1 = axes[0]
        
        # 캔들스틱 그리기
        for i, (idx, row) in enumerate(plot_df.iterrows()):
            color = self.colors['up_candle'] if row['close'] >= row['open'] else self.colors['down_candle']
            
            # 몸통
            height = abs(row['close'] - row['open'])
            bottom = min(row['close'], row['open'])
            rect = Rectangle((i-0.4, bottom), 0.8, height, 
                           facecolor=color, edgecolor=color, linewidth=1)
            ax1.add_patch(rect)
            
            # 꼬리
            ax1.plot([i, i], [row['low'], row['high']], color=color, linewidth=1)
        
        # 이동평균선
        strategy = SEPA_VCP_Strategy()
        plot_df = strategy.calculate_moving_averages(plot_df)
        
        ax1.plot(x, plot_df['ma50'], label='MA50', color=self.colors['ma50'], linewidth=1.5)
        ax1.plot(x, plot_df['ma150'], label='MA150', color=self.colors['ma150'], linewidth=1.5)
        ax1.plot(x, plot_df['ma200'], label='MA200', color=self.colors['ma200'], linewidth=1.5)
        
        # 수축 구간 표시
        if signal.contractions:
            for i, contraction in enumerate(signal.contractions):
                color = self.colors['contraction'][i % len(self.colors['contraction'])]
                
                # 수축 구간 시작/끝 인덱스 찾기
                start_idx = None
                end_idx = None
                for j, row in plot_df.iterrows():
                    if row['date'] == contraction.start_date:
                        start_idx = j
                    if row['date'] == contraction.end_date:
                        end_idx = j
                
                if start_idx is not None and end_idx is not None:
                    # 수축 구간 배경색
                    ax1.axvspan(start_idx, end_idx, alpha=0.2, color=color, 
                              label=f'C{i+1}: {contraction.depth_pct:.1f}%')
                    
                    # 수축 구간 고점/저점 표시
                    ax1.plot([start_idx, end_idx], [contraction.high_price, contraction.high_price], 
                           '--', color=color, linewidth=1)
                    ax1.plot([start_idx, end_idx], [contraction.low_price, contraction.low_price], 
                           '--', color=color, linewidth=1)
        
        # 피벗 라인
        if signal.pivot_line > 0:
            ax1.axhline(y=signal.pivot_line, color=self.colors['pivot_line'], 
                       linestyle='-', linewidth=2, label=f'Pivot: {signal.pivot_line:.0f}')
            
            # 현재가가 피벗 근처면 표시
            if signal.pivot_breakout:
                ax1.axhline(y=signal.pivot_line * 1.03, color='green', 
                           linestyle=':', linewidth=1, alpha=0.5)
                ax1.axhline(y=signal.pivot_line * 0.97, color='green', 
                           linestyle=':', linewidth=1, alpha=0.5)
        
        ax1.set_title(f'{signal.symbol} - SEPA + VCP Pattern Analysis\n' +
                     f'Score: {signal.score} | Contractions: {signal.contraction_count} | ' +
                     f'Volume Surge: {signal.volume_ratio:.1f}x', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price (KRW)')
        ax1.legend(loc='upper left', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # 2. 거래량 차트
        ax2 = axes[1]
        colors_vol = [self.colors['up_candle'] if plot_df.iloc[i]['close'] >= plot_df.iloc[i]['open'] 
                     else self.colors['down_candle'] for i in range(len(plot_df))]
        ax2.bar(x, plot_df['volume'], color=colors_vol, alpha=0.7)
        ax2.set_ylabel('Volume')
        ax2.grid(True, alpha=0.3)
        
        # 거래량 평균선
        vol_ma20 = plot_df['volume'].rolling(20).mean()
        ax2.plot(x, vol_ma20, color='orange', linewidth=1.5, label='Volume MA20')
        ax2.legend(loc='upper left', fontsize=8)
        
        # 3. 상대강도 차트
        ax3 = axes[2]
        ax3.plot(x, plot_df['close'].pct_change(252) * 100 if 'rs' not in plot_df.columns 
                else plot_df['rs'], color='purple', linewidth=1.5)
        ax3.axhline(y=0, color='gray', linestyle='--', linewidth=1)
        ax3.set_ylabel('RS (1Y Return %)')
        ax3.set_xlabel('Date')
        ax3.grid(True, alpha=0.3)
        
        # 정보 텍스트 박스
        info_text = f"""
        Trend Template: {'✓' if signal.trend_template_passed else '✗'}
        VCP Pattern: {'✓' if signal.vcp_passed else '✗'}
        Depth Narrowing: {'✓' if signal.depth_narrowing else '✗'}
        Duration Shortening: {'✓' if signal.duration_shortening else '✗'}
        Volume Dry-up: {'✓' if signal.volume_dry_up else '✗'}
        Volume Surge: {'✓' if signal.volume_surge else '✗'} ({signal.volume_ratio:.1f}x)
        RS Top 25%: {'✓' if signal.rs_top25 else '✗'}
        """
        
        ax1.text(0.02, 0.98, info_text, transform=ax1.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"📊 Chart saved: {save_path}")
        
        return fig
    
    def plot_plotly(self, df: pd.DataFrame, signal: SEPASignal, 
                   save_path: Optional[str] = None) -> go.Figure:
        """
        Plotly로 VCP 패턴 인터랙티브 시각화
        
        Args:
            df: 주가 데이터
            signal: SEPASignal 객체
            save_path: 저장 경로
        
        Returns:
            plotly Figure 객체
        """
        # 최근 6개월 데이터
        plot_df = df.tail(120).copy()
        
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(f'{signal.symbol} - Price', 'Volume', 'Relative Strength')
        )
        
        # 캔들스틱
        fig.add_trace(go.Candlestick(
            x=plot_df['date'],
            open=plot_df['open'],
            high=plot_df['high'],
            low=plot_df['low'],
            close=plot_df['close'],
            name='OHLC',
            increasing_line_color='red',
            decreasing_line_color='blue'
        ), row=1, col=1)
        
        # 이동평균선
        strategy = SEPA_VCP_Strategy()
        plot_df = strategy.calculate_moving_averages(plot_df)
        
        fig.add_trace(go.Scatter(x=plot_df['date'], y=plot_df['ma50'], 
                                name='MA50', line=dict(color='orange')), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df['date'], y=plot_df['ma150'], 
                                name='MA150', line=dict(color='purple')), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df['date'], y=plot_df['ma200'], 
                                name='MA200', line=dict(color='blue')), row=1, col=1)
        
        # 수축 구간 (사각형으로 표시)
        if signal.contractions:
            for i, contraction in enumerate(signal.contractions):
                color = self.colors['contraction'][i % len(self.colors['contraction'])]
                
                fig.add_vrect(
                    x0=contraction.start_date, x1=contraction.end_date,
                    fillcolor=color, opacity=0.2,
                    layer="below", line_width=0,
                    annotation_text=f"C{i+1}",
                    annotation_position="top left",
                    row=1, col=1
                )
                
                # 피벗 라인
                if i == len(signal.contractions) - 1:
                    fig.add_hline(
                        y=contraction.pivot_price, 
                        line_dash="dash", 
                        line_color="red",
                        annotation_text=f"Pivot: {contraction.pivot_price:.0f}",
                        row=1, col=1
                    )
        
        # 거래량
        fig.add_trace(go.Bar(
            x=plot_df['date'],
            y=plot_df['volume'],
            name='Volume',
            marker_color='gray'
        ), row=2, col=1)
        
        # 거래량 MA20
        vol_ma20 = plot_df['volume'].rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=plot_df['date'], y=vol_ma20,
            name='Volume MA20', line=dict(color='orange')
        ), row=2, col=1)
        
        # 상대강도
        fig.add_trace(go.Scatter(
            x=plot_df['date'],
            y=plot_df['close'].pct_change(252) * 100,
            name='RS (1Y)', line=dict(color='purple')
        ), row=3, col=1)
        
        fig.add_hline(y=0, line_dash="dot", line_color="gray", row=3, col=1)
        
        # 레이아웃 설정
        fig.update_layout(
            title=f'{signal.symbol} - SEPA + VCP Analysis | Score: {signal.score}/100',
            height=800,
            showlegend=True,
            xaxis_rangeslider_visible=False
        )
        
        # Y축 레이블
        fig.update_yaxes(title_text="Price (KRW)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="Return %", row=3, col=1)
        
        if save_path:
            fig.write_html(save_path)
            print(f"📊 Interactive chart saved: {save_path}")
        
        return fig
    
    def generate_signal_report(self, signal: SEPASignal) -> str:
        """텍스트 리포트 생성"""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║           SEPA + VCP SIGNAL REPORT                           ║
╚══════════════════════════════════════════════════════════════╝

Symbol: {signal.symbol}
Date: {signal.date}
Current Price: {signal.current_price:,.0f} KRW
Score: {signal.score}/100
Valid Signal: {'✅ YES' if signal.is_valid else '❌ NO'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 TREND TEMPLATE CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Price > MA150:      {'✅' if signal.above_ma150 else '❌'}  
  Price > MA200:      {'✅' if signal.above_ma200 else '❌'}
  MA150 > MA200:      {'✅' if signal.ma150_above_ma200 else '❌'}
  MA200 Trending Up:  {'✅' if signal.ma200_trending_up else '❌'}
  Near 52W High:      {'✅' if signal.near_52w_high else '❌'}
  Above 52W Low:      {'✅' if signal.above_52w_low else '❌'}
  
  Result: {'✅ PASSED' if signal.trend_template_passed else '❌ FAILED'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 VCP PATTERN ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Contraction Count:  {signal.contraction_count}
  Depth Narrowing:    {'✅ YES' if signal.depth_narrowing else '❌ NO'}
  Duration Shortening:{'✅ YES' if signal.duration_shortening else '❌ NO'}
  Volume Dry-up:      {'✅ YES' if signal.volume_dry_up else '❌ NO'}
  
  Result: {'✅ PASSED' if signal.vcp_passed else '❌ FAILED'}

"""
        
        if signal.contractions:
            report += "  Contraction Details:\n"
            for i, c in enumerate(signal.contractions, 1):
                report += f"    C{i}: {c.start_date.strftime('%Y-%m-%d')} ~ {c.end_date.strftime('%Y-%m-%d')} | "
                report += f"Depth: {c.depth_pct:.1f}% | Duration: {c.duration_days} days\n"
        
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 PIVOT & VOLUME SIGNAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Pivot Line:         {signal.pivot_line:,.0f} KRW
  Pivot Breakout:     {'✅ YES' if signal.pivot_breakout else '❌ NO'}
  Volume Surge:       {'✅ YES' if signal.volume_surge else '❌ NO'}
  Volume Ratio:       {signal.volume_ratio:.2f}x (20-day avg)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💪 RELATIVE STRENGTH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RS (1Y Return):     {signal.relative_strength:.1f}%
  RS Rank:            {signal.rs_rank*100:.0f}th percentile
  Top 25%:            {'✅ YES' if signal.rs_top25 else '❌ NO'}

"""
        return report


# 예시 사용법
if __name__ == "__main__":
    print("SEPA + VCP Visualizer Module")
    print("\nUsage:")
    print("  from sepa_vcp_visualizer import SEPA_VCP_Visualizer")
    print("  visualizer = SEPA_VCP_Visualizer()")
    print("  visualizer.plot_matplotlib(df, signal, 'chart.png')")
    print("  visualizer.plot_plotly(df, signal, 'chart.html')")
