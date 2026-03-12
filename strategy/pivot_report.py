#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pivot Point Strategy Report Generator
=====================================
피벗 포인트 전략 시각화 및 보고서 생성 프로그램

기능:
1. Matplotlib을 활용한 정적 차트 생성
2. Plotly를 활용한 인터랙티브 차트 생성
3. 포트폴리오 성과 분석 리포트 생성
4. 다중 종목 비교 분석
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.lines import Line2D
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os

# pivot_strategy 모듈 임포트
from pivot_strategy import PivotPointStrategy, BacktestResult, TradeRecord


class StrategyVisualizer:
    """
    전략 시각화 클래스
    """
    
    def __init__(self, style: str = 'seaborn-v0_8'):
        """
        Parameters:
        -----------
        style : str
            Matplotlib 스타일 (기본: 'seaborn-v0_8')
        """
        self.style = style
        try:
            plt.style.use(style)
        except:
            plt.style.use('default')
    
    def plot_trades_matplotlib(
        self,
        strategy: PivotPointStrategy,
        result: BacktestResult,
        save_path: Optional[str] = None,
        figsize: Tuple[int, int] = (16, 12)
    ) -> plt.Figure:
        """
        Matplotlib으로 매매 타점 시각화
        
        서브플롯 구성:
        1. 주가 + 매매 신호
        2. 거래량
        3. 자산 가치 변화
        4. 낙폭 (Drawdown)
        """
        df = strategy.data.copy()
        
        # 4개 서브플롯 생성
        fig, axes = plt.subplots(4, 1, figsize=figsize, 
                                gridspec_kw={'height_ratios': [3, 1, 2, 1]})
        fig.suptitle(f'Pivot Point Strategy - {strategy.symbol}\n'
                    f'Return: {result.final_return:+.2f}% | MDD: {result.mdd:.2f}%', 
                    fontsize=14, fontweight='bold')
        
        # === 서브플롯 1: 주가 + 매매 신호 ===
        ax1 = axes[0]
        
        # 캔들스틱 (종가 라인으로 간단 표현)
        ax1.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1, alpha=0.8)
        
        # 피벗 고가 라인
        pivot_high_col = f'high_{strategy.pivot_period}'
        if pivot_high_col in df.columns:
            ax1.plot(df.index, df[pivot_high_col], 
                    label=f'{strategy.pivot_period}-day High', 
                    color='blue', linestyle='--', alpha=0.5)
        
        # 매매 신호 표시
        for trade in result.trades:
            # 진입 포인트
            ax1.scatter(trade.entry_date, trade.entry_price, 
                       marker='^', color='green', s=200, zorder=5, 
                       label='Entry' if trade == result.trades[0] else "")
            
            # 청산 포인트
            color = 'red' if trade.exit_reason == 'stop_loss' else 'lime'
            ax1.scatter(trade.exit_date, trade.exit_price, 
                       marker='v', color=color, s=200, zorder=5,
                       label='Exit (SL)' if trade.exit_reason == 'stop_loss' and 
                              sum(1 for t in result.trades if t.exit_reason == 'stop_loss') == 1 else
                             'Exit (TP)' if trade.exit_reason == 'take_profit' and 
                              sum(1 for t in result.trades if t.exit_reason == 'take_profit') == 1 else "")
            
            # 보유 기간 라인
            ax1.plot([trade.entry_date, trade.exit_date], 
                    [trade.entry_price, trade.exit_price],
                    color='gray', alpha=0.3, linewidth=1)
        
        ax1.set_ylabel('Price (KRW)', fontsize=11)
        ax1.set_title('Stock Price with Entry/Exit Points', fontsize=12)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3)
        
        # === 서브플롯 2: 거래량 ===
        ax2 = axes[1]
        colors = ['red' if df['close'].iloc[i] > df['open'].iloc[i] else 'blue' 
                  for i in range(len(df))]
        ax2.bar(df.index, df['volume'], color=colors, alpha=0.6, width=0.8)
        
        # 거래량 이동평균
        if 'volume_ma20' in df.columns:
            ax2.plot(df.index, df['volume_ma20'], 
                    color='orange', linewidth=1.5, label='Volume MA20')
        
        ax2.set_ylabel('Volume', fontsize=11)
        ax2.set_title('Trading Volume', fontsize=12)
        ax2.legend(loc='upper left', fontsize=9)
        ax2.grid(True, alpha=0.3)
        
        # === 서브플롯 3: 자산 가치 ===
        ax3 = axes[2]
        equity = result.equity_curve
        
        ax3.fill_between(equity.index, equity['total_value'], 
                        alpha=0.3, color='green', label='Total Value')
        ax3.plot(equity.index, equity['total_value'], 
                color='green', linewidth=2, label='Portfolio Value')
        ax3.axhline(y=strategy.initial_capital, color='red', 
                   linestyle='--', alpha=0.5, label='Initial Capital')
        
        ax3.set_ylabel('Value (KRW)', fontsize=11)
        ax3.set_title('Portfolio Value Over Time', fontsize=12)
        ax3.legend(loc='upper left', fontsize=9)
        ax3.grid(True, alpha=0.3)
        
        # === 서브플롯 4: Drawdown ===
        ax4 = axes[3]
        ax4.fill_between(equity.index, equity['drawdown'], 0, 
                        alpha=0.5, color='red', label='Drawdown')
        ax4.plot(equity.index, equity['drawdown'], 
                color='red', linewidth=1, label='Drawdown %')
        
        # MDD 라인
        mdd_idx = equity['drawdown'].idxmin()
        ax4.axhline(y=result.mdd, color='darkred', linestyle='--', 
                   alpha=0.7, label=f'MDD: {result.mdd:.1f}%')
        ax4.scatter([mdd_idx], [result.mdd], color='darkred', s=100, zorder=5)
        
        ax4.set_ylabel('Drawdown (%)', fontsize=11)
        ax4.set_xlabel('Date', fontsize=11)
        ax4.set_title('Drawdown (Maximum Decline from Peak)', fontsize=12)
        ax4.legend(loc='lower left', fontsize=9)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 차트 저장 완료: {save_path}")
        
        return fig
    
    def plot_trades_plotly(
        self,
        strategy: PivotPointStrategy,
        result: BacktestResult,
        save_path: Optional[str] = None
    ) -> go.Figure:
        """
        Plotly로 인터랙티브 차트 생성
        """
        df = strategy.data.copy()
        equity = result.equity_curve
        
        # 서브플롯 생성
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('Stock Price with Signals', 'Volume', 
                          'Portfolio Value', 'Drawdown'),
            row_heights=[0.4, 0.15, 0.3, 0.15]
        )
        
        # === 주가 차트 ===
        # 캔들스틱
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC',
            increasing_line_color='red',
            decreasing_line_color='blue'
        ), row=1, col=1)
        
        # 피벗 고가
        pivot_high_col = f'high_{strategy.pivot_period}'
        if pivot_high_col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[pivot_high_col],
                mode='lines',
                name=f'{strategy.pivot_period}-day High',
                line=dict(color='blue', dash='dash', width=1)
            ), row=1, col=1)
        
        # 진입/청산 포인트
        for i, trade in enumerate(result.trades):
            # 진입
            fig.add_trace(go.Scatter(
                x=[trade.entry_date],
                y=[trade.entry_price],
                mode='markers',
                marker=dict(color='green', size=15, symbol='triangle-up'),
                name=f'Entry #{i+1}' if i == 0 else None,
                showlegend=(i == 0),
                hovertemplate=f'Entry #{i+1}<br>Date: %{{x}}<br>Price: %{{y:,.0f}}<extra></extra>'
            ), row=1, col=1)
            
            # 청산
            exit_color = 'red' if trade.exit_reason == 'stop_loss' else 'lime'
            fig.add_trace(go.Scatter(
                x=[trade.exit_date],
                y=[trade.exit_price],
                mode='markers',
                marker=dict(color=exit_color, size=15, symbol='triangle-down'),
                name=f'Exit #{i+1}' if i == 0 else None,
                showlegend=(i == 0),
                hovertemplate=f'Exit #{i+1} ({trade.exit_reason})<br>Date: %{{x}}<br>Price: %{{y:,.0f}}<br>Return: {trade.return_pct:+.2f}%<extra></extra>'
            ), row=1, col=1)
        
        # === 거래량 ===
        colors = ['red' if c >= o else 'blue' 
                  for c, o in zip(df['close'], df['open'])]
        fig.add_trace(go.Bar(
            x=df.index, y=df['volume'],
            marker_color=colors,
            name='Volume',
            opacity=0.6
        ), row=2, col=1)
        
        # === 포트폴리오 가치 ===
        fig.add_trace(go.Scatter(
            x=equity.index, y=equity['total_value'],
            mode='lines',
            name='Portfolio Value',
            line=dict(color='green', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 0, 0.2)'
        ), row=3, col=1)
        
        # 초기 자본 라인
        fig.add_hline(y=strategy.initial_capital, line_dash="dash", 
                     line_color="red", row=3, col=1,
                     annotation_text="Initial Capital")
        
        # === Drawdown ===
        fig.add_trace(go.Scatter(
            x=equity.index, y=equity['drawdown'],
            mode='lines',
            name='Drawdown',
            line=dict(color='red', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 0, 0, 0.3)'
        ), row=4, col=1)
        
        # MDD 라인
        fig.add_hline(y=result.mdd, line_dash="dash", 
                     line_color="darkred", row=4, col=1,
                     annotation_text=f"MDD: {result.mdd:.1f}%")
        
        # 레이아웃 설정
        fig.update_layout(
            title=f'Pivot Point Strategy - {strategy.symbol}<br>'
                  f'Return: {result.final_return:+.2f}% | MDD: {result.mdd:.2f}% | '
                  f'Win Rate: {result.win_rate:.1f}%',
            height=900,
            showlegend=True,
            hovermode='x unified'
        )
        
        fig.update_xaxes(rangeslider_visible=False)
        fig.update_yaxes(title_text="Price (KRW)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="Value (KRW)", row=3, col=1)
        fig.update_yaxes(title_text="Drawdown (%)", row=4, col=1)
        fig.update_xaxes(title_text="Date", row=4, col=1)
        
        if save_path:
            fig.write_html(save_path)
            print(f"📊 인터랙티브 차트 저장 완료: {save_path}")
        
        return fig


class StrategyReport:
    """
    전략 분석 보고서 생성 클래스
    """
    
    def __init__(self, output_dir: str = './reports'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(
        self,
        strategy: PivotPointStrategy,
        result: BacktestResult,
        trades_df: pd.DataFrame,
        include_charts: bool = True
    ) -> str:
        """
        종합 보고서 생성
        
        Returns:
        --------
        str : 보고서 파일 경로
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"{strategy.symbol}_report_{timestamp}.html"
        report_path = os.path.join(self.output_dir, report_filename)
        
        # 차트 생성
        if include_charts:
            visualizer = StrategyVisualizer()
            
            # 정적 차트
            static_chart_path = os.path.join(self.output_dir, 
                                             f"{strategy.symbol}_chart_{timestamp}.png")
            visualizer.plot_trades_matplotlib(strategy, result, static_chart_path)
            
            # 인터랙티브 차트
            interactive_chart_path = os.path.join(self.output_dir, 
                                                  f"{strategy.symbol}_interactive_{timestamp}.html")
            visualizer.plot_trades_plotly(strategy, result, interactive_chart_path)
        
        # HTML 보고서 생성
        # 거래 내역 DataFrame 포맷팅
        trades_display = trades_df.copy()
        if not trades_display.empty:
            trades_display['진입일'] = trades_display['진입일'].dt.strftime('%Y-%m-%d')
            trades_display['청산일'] = trades_display['청산일'].dt.strftime('%Y-%m-%d')
            trades_display['진입가'] = trades_display['진입가'].apply(lambda x: f'{x:,.0f}')
            trades_display['청산가'] = trades_display['청산가'].apply(lambda x: f'{x:,.0f}')
            trades_display['평균단가'] = trades_display['평균단가'].apply(lambda x: f'{x:,.0f}')
            trades_display['투자금액'] = trades_display['투자금액'].apply(lambda x: f'{x:,.0f}')
            trades_display['손익'] = trades_display['손익'].apply(
                lambda x: f'<span class="{"positive" if x > 0 else "negative"}">{x:+,.0f}</span>'
            )
            trades_display['수익률(%)'] = trades_display['수익률(%)'].apply(
                lambda x: f'<span class="{"positive" if x > 0 else "negative"}">{x:+.2f}%</span>'
            )
            trades_display['청산사유'] = trades_display['청산사유'].apply(
                lambda x: f'<span class="tag {"tag-loss" if x == "stop_loss" else "tag-profit"}">{x}</span>'
            )
        
        trades_html = trades_display.to_html(index=False, classes='dataframe', escape=False)
        
        html_content = self._generate_html(strategy, result, trades_html, timestamp)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 보고서 생성 완료: {report_path}")
        return report_path
    
    def _generate_html(
        self, 
        strategy: PivotPointStrategy, 
        result: BacktestResult, 
        trades_html: str,
        timestamp: str
    ) -> str:
        """
        HTML 보고서 템플릿
        """
        # 승/패 거래 분리
        win_trades = [t for t in result.trades if t.pnl > 0]
        loss_trades = [t for t in result.trades if t.pnl <= 0]
        
        avg_win = np.mean([t.return_pct for t in win_trades]) if win_trades else 0
        avg_loss = np.mean([t.return_pct for t in loss_trades]) if loss_trades else 0
        
        # 청산 사유별 통계
        sl_count = sum(1 for t in result.trades if t.exit_reason == 'stop_loss')
        tp_count = sum(1 for t in result.trades if t.exit_reason == 'take_profit')
        
        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pivot Point Strategy Report - {strategy.symbol}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
        }}
        .card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}
        .positive {{ color: #27ae60; }}
        .negative {{ color: #e74c3c; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #555;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .tag {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        .tag-profit {{
            background-color: #d4edda;
            color: #155724;
        }}
        .tag-loss {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .config-item {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .config-item strong {{
            color: #666;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Pivot Point Strategy Report</h1>
        <p>종목: <strong>{strategy.symbol}</strong> | 
           분석 기간: {strategy.start_date} ~ {strategy.end_date} | 
           생성일: {timestamp}</p>
    </div>
    
    <div class="summary-cards">
        <div class="card">
            <h3>최종 수익률</h3>
            <div class="value {'positive' if result.final_return >= 0 else 'negative'}">
                {result.final_return:+.2f}%
            </div>
        </div>
        <div class="card">
            <h3>최대 낙폭 (MDD)</h3>
            <div class="value negative">{result.mdd:.2f}%</div>
        </div>
        
        <div class="card">
            <h3>승률</h3>
            <div class="value">{result.win_rate:.1f}%</div>
        </div>
        
        <div class="card">
            <h3>Profit Factor</h3>
            <div class="value">{result.profit_factor:.2f}</div>
        </div>
        
        <div class="card">
            <h3>총 거래 횟수</h3>
            <div class="value">{len(result.trades)}회</div>
        </div>
        
        <div class="card">
            <h3>최종 자산</h3>
            <div class="value">{result.equity_curve['total_value'].iloc[-1]:,.0f}원</div>
        </div>
    </div>
    
    <div class="section">
        <h2>⚙️ 전략 설정</h2>
        <div class="config-grid">
            <div class="config-item">
                <strong>초기 자본</strong><br>
                {strategy.initial_capital:,.0f}원
            </div>
            <div class="config-item">
                <strong>피벗 기간</strong><br>
                {strategy.pivot_period}일
            </div>
            <div class="config-item">
                <strong>거래량 임계값</strong><br>
                {strategy.volume_threshold*100:.0f}%
            </div>
            <div class="config-item">
                <strong>손절 라인</strong><br>
                -{strategy.stop_loss_pct*100:.0f}%
            </div>
            <div class="config-item">
                <strong>트레일링 스탑</strong><br>
                -{strategy.trailing_stop_pct*100:.0f}%
            </div>
            <div class="config-item">
                <strong>피라미딩 단계</strong><br>
                {strategy.pyramiding_pct[0]*100:.0f}% → {strategy.pyramiding_pct[1]*100:.0f}% → {strategy.pyramiding_pct[2]*100:.0f}%
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>📈 거래 내역</h2>
        {trades_html}
    </div>
    
    <div class="section">
        <h2>📊 통계 분석</h2>
        <div class="config-grid">
            <div class="config-item">
                <strong>평균 수익 (승)</strong><br>
                <span class="positive">+{avg_win:.2f}%</span>
            </div>
            <div class="config-item">
                <strong>평균 손실 (패)</strong><br>
                <span class="negative">{avg_loss:.2f}%</span>
            </div>
            <div class="config-item">
                <strong>손절 청산</strong><br>
                {sl_count}회
            </div>
            <div class="config-item">
                <strong>익절 청산</strong><br>
                {tp_count}회
            </div>
        </div>
    </div>
    
    <footer style="text-align: center; color: #999; padding: 20px;">
        <p>Generated by Pivot Point Strategy Report Generator</p>
    </footer>
</body>
</html>
"""
        return html


def main():
    """
    메인 실행 함수 - 예시
    """
    # 전략 실행
    strategy = PivotPointStrategy(
        symbol='005930',  # 삼성전자
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=10_000_000,
        pivot_period=20,
        volume_threshold=1.5,
    )
    
    result, trades_df = strategy.run_backtest()
    
    # 보고서 생성
    report = StrategyReport(output_dir='./reports')
    report_path = report.generate_report(strategy, result, trades_df)
    
    print(f"\n✅ 모든 결과가 저장되었습니다!")
    print(f"   보고서: {report_path}")
    
    return strategy, result, trades_df


if __name__ == "__main__":
    strategy, result, trades_df = main()
