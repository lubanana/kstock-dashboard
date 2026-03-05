#!/usr/bin/env python3
"""
KStock Enhanced Report Generator
"""

import json
import os
from datetime import datetime

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = '/home/programs/kstock_analyzer/docs'

def load_data():
    """데이터 로드"""
    kospi = {}
    try:
        with open(f'{BASE_PATH}/data/kospi_analysis.csv', 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:
                headers = lines[0].strip().split(',')
                values = lines[1].strip().split(',')
                kospi = dict(zip(headers, values))
    except:
        pass
    
    double = []
    try:
        with open(f'{BASE_PATH}/data/double_signal_results.json', 'r') as f:
            data = json.load(f)
            double = data.get('results', [])
    except:
        pass
    
    return kospi, double

def generate_html():
    """HTML 생성"""
    kospi, double = load_data()
    
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KStock Daily Report - {datetime.now().strftime('%Y년 %m월 %d일')}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; padding: 40px; 
                   background: rgba(255,255,255,0.95); border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }}
        .header h1 {{ font-size: 2.8em; margin-bottom: 10px; color: #2c3e50; }}
        .header .date {{ color: #7f8c8d; font-size: 1.2em; margin-bottom: 20px; }}
        .summary-boxes {{ display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }}
        .summary-box {{ padding: 15px 25px; background: linear-gradient(135deg, #3498db, #2980b9); 
                        color: white; border-radius: 12px; font-weight: 500; }}
        .section {{ background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.1); margin-bottom: 25px; }}
        .section h2 {{ color: #2c3e50; margin-bottom: 20px; padding-bottom: 10px; 
                      border-bottom: 3px solid #3498db; font-size: 1.5em; }}
        .kospi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }}
        .kospi-card {{ text-align: center; padding: 20px; background: linear-gradient(135deg, #f5f7fa, #e4e8ec); border-radius: 12px; }}
        .kospi-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .kospi-label {{ color: #7f8c8d; font-size: 0.9em; margin-top: 5px; }}
        .positive {{ color: #27ae60; }} .negative {{ color: #e74c3c; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }}
        .stat-card {{ text-align: center; padding: 25px; border-radius: 15px; color: white; }}
        .stat-triple {{ background: linear-gradient(135deg, #e74c3c, #c0392b); }}
        .stat-double {{ background: linear-gradient(135deg, #27ae60, #229954); }}
        .stat-total {{ background: linear-gradient(135deg, #3498db, #2980b9); }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; }}
        .stock-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.95em; }}
        .stock-table th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
        .stock-table td {{ padding: 12px; border-bottom: 1px solid #ecf0f1; }}
        .stock-table tr:hover {{ background: #f8f9fa; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 500; margin-right: 5px; }}
        .badge-L {{ background: #ffebee; color: #c62828; }}
        .badge-O {{ background: #e3f2fd; color: #1565c0; }}
        .badge-M {{ background: #f3e5f5; color: #7b1fa2; }}
        .chart-container {{ position: relative; height: 250px; margin: 20px 0; }}
        .footer {{ text-align: center; padding: 30px; color: rgba(255,255,255,0.8); font-size: 0.9em; }}
        @media (max-width: 768px) {{ .kospi-grid {{ grid-template-columns: repeat(2, 1fr); }} .stats-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 KStock Daily Report</h1>
            <div class="date">{datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</div>
            <div class="summary-boxes">
                <div class="summary-box">KOSPI: {kospi.get('close', '-')} ({kospi.get('change_pct', '-')}%)</div>
                <div class="summary-box">2중 신호: {len(double)}개 종목</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 KOSPI 시장 요약</h2>
            <div class="kospi-grid">
                <div class="kospi-card">
                    <div class="kospi-value">{kospi.get('close', '-'):,}</div>
                    <div class="kospi-label">현재가</div>
                </div>
                <div class="kospi-card">
                    <div class="kospi-value {'positive' if float(kospi.get('change_pct', 0)) > 0 else 'negative'}">{kospi.get('change_pct', '-')}%</div>
                    <div class="kospi-label">등락률</div>
                </div>
                <div class="kospi-card">
                    <div class="kospi-value {'warning' if float(kospi.get('rsi', 50)) > 70 else ''}">{kospi.get('rsi', '-')}</div>
                    <div class="kospi-label">RSI(14)</div>
                </div>
                <div class="kospi-card">
                    <div class="kospi-value {'positive' if kospi.get('trend') == 'BULLISH' else 'negative'}">{kosp
