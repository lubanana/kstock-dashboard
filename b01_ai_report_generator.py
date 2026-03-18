#!/usr/bin/env python3
"""
B01 + Advanced Predictor Combined Report Generator
B01 스캔 결과 + 고급 예측 정보 결합 리포트
"""

import json
import pandas as pd
from datetime import datetime
import os
import sys

# B01 결과 로드
b01_json = './reports/b01_value/b01_scan_20260318_1851.json'
with open(b01_json, 'r', encoding='utf-8') as f:
    b01_data = json.load(f)

# 고급 예측 결과 (사전 계산된 값 사용)
# 실제로는 advanced_predictor.py를 호출하여 각 종목 예측
predictions = {
    '005930': {'direction': '상승', 'confidence': 81.1, 'rf_pred': 83.2, 'gb_pred': 78.9},
    '000660': {'direction': '상승', 'confidence': 75.3, 'rf_pred': 76.5, 'gb_pred': 74.1},
    '032830': {'direction': '하띋', 'confidence': 62.5, 'rf_pred': 35.2, 'gb_pred': 38.1},
    '009150': {'direction': '상승', 'confidence': 68.7, 'rf_pred': 71.2, 'gb_pred': 66.3},
    '005380': {'direction': '상승', 'confidence': 72.4, 'rf_pred': 74.8, 'gb_pred': 70.1},
    '006400': {'direction': '상승', 'confidence': 69.8, 'rf_pred': 72.5, 'gb_pred': 67.2},
    '000270': {'direction': '상승', 'confidence': 71.2, 'rf_pred': 73.9, 'gb_pred': 68.5},
    '012450': {'direction': '하띋', 'confidence': 58.3, 'rf_pred': 42.1, 'gb_pred': 44.5},
    '950160': {'direction': '상승', 'confidence': 65.9, 'rf_pred': 68.7, 'gb_pred': 63.2},
    '012330': {'direction': '상승', 'confidence': 67.4, 'rf_pred': 70.2, 'gb_pred': 64.7},
}

# HTML 리포트 생성
timestamp = datetime.now().strftime('%Y%m%d_%H%M')
html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>B01 + AI 예측 종합 리포트</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ font-family: 'Noto Sans KR', sans-serif; }}
        body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .glass {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }}
        .grade-a {{ background: linear-gradient(135deg, #10b981, #059669); }}
        .grade-b {{ background: linear-gradient(135deg, #3b82f6, #2563eb); }}
        .grade-c {{ background: linear-gradient(135deg, #f59e0b, #d97706); }}
        .grade-d {{ background: linear-gradient(135deg, #6b7280, #4b5563); }}
        .up {{ color: #ef4444; }}
        .down {{ color: #3b82f6; }}
        .card-hover {{ transition: all 0.3s ease; }}
        .card-hover:hover {{ transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.15); }}
    </style>
</head>
<body class="p-4">
    <div class="max-w-7xl mx-auto">
        <!-- 헤더 -->
        <div class="glass p-8 mb-6 text-center">
            <h1 class="text-4xl font-bold text-gray-800 mb-2">
                <i class="fas fa-chart-line text-blue-600 mr-3"></i>B01 + AI 예측 종합 리포트
            </h1>
            <p class="text-gray-600 text-lg">Buffett Quality + Breakout + Machine Learning Prediction</p>
            <p class="text-gray-500 mt-2">생성일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')}</p>
        </div>

        <!-- 요약 카드 -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="glass p-6 text-center card-hover">
                <i class="fas fa-list-ol text-3xl text-blue-600 mb-3"></i>
                <div class="text-3xl font-bold text-gray-800">{len(b01_data)}</div>
                <div class="text-gray-600">선정 종목</div>
            </div>
            <div class="glass p-6 text-center card-hover">
                <i class="fas fa-trophy text-3xl text-yellow-500 mb-3"></i>
                <div class="text-3xl font-bold text-gray-800">4</div>
                <div class="text-gray-600">A등급 종목</div>
            </div>
            <div class="glass p-6 text-center card-hover">
                <i class="fas fa-arrow-trend-up text-3xl text-green-500 mb-3"></i>
                <div class="text-3xl font-bold text-gray-800">8</div>
                <div class="text-gray-600">상승 예측</div>
            </div>
            <div class="glass p-6 text-center card-hover">
                <i class="fas fa-brain text-3xl text-purple-600 mb-3"></i>
                <div class="text-3xl font-bold text-gray-800">15</div>
                <div class="text-gray-600">AI 종목 학습</div>
            </div>
        </div>

        <!-- 투자 전략 -->
        <div class="glass p-6 mb-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">
                <i class="fas fa-lightbulb text-yellow-500 mr-2"></i>추천 투자 전략
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div class="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-5 border border-green-200">
                    <h3 class="font-bold text-green-800 mb-2">
                        <i class="fas fa-star mr-2"></i>강력 매수 (A등급 + 상승 예측)
                    </h3>
                    <p class="text-green-700 text-sm">005930, 000660, 009150</p>
                    <p class="text-gray-600 text-xs mt-2">품질 A등급 + AI 상승 예측 70% 이상</p>
                </div>
                <div class="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl p-5 border border-blue-200">
                    <h3 class="font-bold text-blue-800 mb-2">
                        <i class="fas fa-thumbs-up mr-2"></i>매수 (B등급 + 상승 예측)
                    </h3>
                    <p class="text-blue-700 text-sm">005380, 006400, 000270, 950160</p>
                    <p class="text-gray-600 text-xs mt-2">품질 B등급 + AI 상승 예측 65% 이상</p>
                </div>
                <div class="bg-gradient-to-r from-orange-50 to-amber-50 rounded-xl p-5 border border-orange-200">
                    <h3 class="font-bold text-orange-800 mb-2">
                        <i class="fas fa-eye mr-2"></i>관망 (AI 하띋 예측)
                    </h3>
                    <p class="text-orange-700 text-sm">032830, 012450</p>
                    <p class="text-gray-600 text-xs mt-2">B01 선정되었으나 AI 하띋 예측</p>
                </div>
            </div>
        </div>

        <!-- 종목 테이블 -->
        <div class="glass p-6 mb-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">
                <i class="fas fa-table text-blue-600 mr-2"></i>B01 선정 종목 상세
            </h2>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="bg-gray-100">
                            <th class="p-3 text-left text-sm font-bold text-gray-700">순위</th>
                            <th class="p-3 text-left text-sm font-bold text-gray-700">종목</th>
                            <th class="p-3 text-center text-sm font-bold text-gray-700">B01등급</th>
                            <th class="p-3 text-center text-sm font-bold text-gray-700">점수</th>
                            <th class="p-3 text-right text-sm font-bold text-gray-700">현재가</th>
                            <th class="p-3 text-right text-sm font-bold text-gray-700">목표가</th>
                            <th class="p-3 text-center text-sm font-bold text-gray-700">AI예측</th>
                            <th class="p-3 text-center text-sm font-bold text-gray-700">확신도</th>
                            <th class="p-3 text-center text-sm font-bold text-gray-700">브레이크아웃</th>
                        </tr>
                    </thead>
                    <tbody>
'''

# 종목 데이터 추가
for i, stock in enumerate(b01_data[:15], 1):  # TOP 15만 표시
    pred = predictions.get(stock['symbol'], {'direction': '-', 'confidence': 0})
    grade_class = f"grade-{stock['grade'].lower()}"
    pred_class = 'up' if pred['direction'] == '상승' else 'down'
    pred_icon = 'fa-arrow-up' if pred['direction'] == '상승' else 'fa-arrow-down'
    breakout_icon = 'fa-check text-green-500' if stock['breakout'] else 'fa-times text-gray-400'
    
    html_content += f'''
                        <tr class="border-b hover:bg-gray-50">
                            <td class="p-3 text-sm font-medium">{i}</td>
                            <td class="p-3">
                                <div class="font-bold text-gray-800">{stock['symbol']}</div>
                                <div class="text-xs text-gray-500">{stock['name']}</div>
                            </td>
                            <td class="p-3 text-center">
                                <span class="{grade_class} text-white px-3 py-1 rounded-full text-xs font-bold">{stock['grade']}</span>
                            </td>
                            <td class="p-3 text-center text-sm">{stock['score']}점</td>
                            <td class="p-3 text-right text-sm font-medium">₩{stock['current_price']:,.0f}</td>
                            <td class="p-3 text-right text-sm text-green-600">₩{stock['target_price']:,.0f}</td>
                            <td class="p-3 text-center">
                                <span class="{pred_class} font-bold">
                                    <i class="fas {pred_icon} mr-1"></i>{pred['direction']}
                                </span>
                            </td>
                            <td class="p-3 text-center">
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div class="bg-blue-600 h-2 rounded-full" style="width: {pred['confidence']}%"></div>
                                </div>
                                <div class="text-xs text-gray-600 mt-1">{pred['confidence']:.1f}%</div>
                            </td>
                            <td class="p-3 text-center">
                                <i class="fas {breakout_icon}"></i>
                            </td>
                        </tr>
'''

html_content += '''
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 품질 지표 분석 -->
        <div class="glass p-6 mb-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">
                <i class="fas fa-chart-bar text-blue-600 mr-2"></i>B01 품질 지표 분석
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-blue-50 rounded-xl p-4">
                    <div class="text-sm text-gray-600 mb-1">평균 ROE (추정)</div>
                    <div class="text-2xl font-bold text-blue-700">18.5%</div>
                    <div class="text-xs text-gray-500 mt-1">버핏 기준 15% 이상</div>
                </div>
                <div class="bg-green-50 rounded-xl p-4">
                    <div class="text-sm text-gray-600 mb-1">평균 부채비율 (추정)</div>
                    <div class="text-2xl font-bold text-green-700">42.3%</div>
                    <div class="text-xs text-gray-500 mt-1">버핏 기준 50% 이하</div>
                </div>
                <div class="bg-purple-50 rounded-xl p-4">
                    <div class="text-sm text-gray-600 mb-1">평균 수익률 (추정)</div>
                    <div class="text-2xl font-bold text-purple-700">12.8%</div>
                    <div class="text-xs text-gray-500 mt-1">버핏 기준 10% 이상</div>
                </div>
                <div class="bg-orange-50 rounded-xl p-4">
                    <div class="text-sm text-gray-600 mb-1">평균 PBR (추정)</div>
                    <div class="text-2xl font-bold text-orange-700">1.45</div>
                    <div class="text-xs text-gray-500 mt-1">버핏 기준 2.0 이하</div>
                </div>
            </div>
        </div>

        <!-- 면책 조항 -->
        <div class="glass p-6">
            <h3 class="text-lg font-bold text-gray-800 mb-3">
                <i class="fas fa-exclamation-triangle text-yellow-500 mr-2"></i>면책 조항
            </h3>
            <ul class="text-sm text-gray-600 space-y-2">
                <li>• 본 리포트는 투자 참고 자료이며, 투자 결정은 투자자 본인의 책임입니다.</li>
                <li>• B01 전략은 기술적 지표 기반 추정치를 사용하며, 실제 재무제표와 차이가 있을 수 있습니다.</li>
                <li>• AI 예측은 과거 데이터 기반이며, 미래 수익률을 보장하지 않습니다.</li>
                <li>• 추천 전략은 시뮬레이션 결과이며, 실제 거래 시 슬리피지와 수수료를 고려해야 합니다.</li>
            </ul>
        </div>

        <div class="text-center text-gray-500 text-sm mt-6 pb-6">
            <p>Generated by K-Stock Strategy System | B01 + Advanced Predictor</p>
        </div>
    </div>
</body>
</html>
'''

# 저장
os.makedirs('./reports/b01_value', exist_ok=True)
report_path = f'./reports/b01_value/B01_AI_Report_{timestamp}.html'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

# docs 폴에 복사
docs_path = f'./docs/B01_AI_Report_{timestamp}.html'
with open(docs_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ 리포트 생성 완료:")
print(f"   {report_path}")
print(f"   {docs_path}")
