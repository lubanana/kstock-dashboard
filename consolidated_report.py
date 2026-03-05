#!/usr/bin/env python3
import json
import os
from datetime import datetime

BASE_PATH = '/home/programs/kstock_analyzer'
OUTPUT_PATH = '/home/programs/kstock_analyzer/docs'

def main():
    print("KStock Consolidated Report Generator")
    print("=" * 50)
    
    data = {'date': datetime.now().strftime('%Y년 %m월 %d일'), 'stocks': []}
    
    try:
        with open(f'{BASE_PATH}/data/double_signal_results.json', 'r') as f:
            result = json.load(f)
            data['stocks'] = result.get('results', [])
            print(f"Loaded {len(data['stocks'])} stocks")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>KStock Report - {data['date']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 20px; }}
        .section {{ background: white; padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #34495e; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f8f9fa; }}
        .badge {{ display: inline-block; padding: 5px 10px; border-radius: 5px; font-size: 0.85em; margin: 2px; }}
        .L {{ background: #ffebee; color: #c62828; }}
        .O {{ background: #e3f2fd; color: #1565c0; }}
        .M {{ background: #f3e5f5; color: #7b1fa2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>KStock Consolidated Report</h1>
            <p>{data['date']}</p>
            <p>총 {len(data['stocks'])}개 종목 발굴</p>
        </div>
        
        <div class="section">
            <h2>발굴 종목 목록</h2>
            <table>
                <tr><th>순위</th><th>종목명</th><th>현재가</th><th>신호</th><th>점수</th></tr>"""
    
    for i, stock in enumerate(data['stocks'][:20], 1):
        html += f"""
                <tr>
                    <td>{i}</td>
                    <td><strong>{stock.get('name', '')}</strong><br><small>{stock.get('symbol', '')}</small></td>
                    <td>{stock.get('price', 0):,.0f}원</td>
                    <td><span class="badge L">오닐</span><span class="badge M">미너비니</span></td>
                    <td>{stock.get('score', 0)}</td>
                </tr>"""
    
    html += """
            </table>
        </div>
    </div>
</body>
</html>"""
    
    output_file = f'{OUTPUT_PATH}/consolidated_report.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Report saved: {output_file}")

if __name__ == '__main__':
    main()
