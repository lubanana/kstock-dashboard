#!/usr/bin/env python3
"""
V-Series 종목 뉴스 수집기
선정된 7개 종목의 최신 뉴스 및 시장 상황 수집
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time

# 종목코드 -> 종목명 매핑
STOCK_NAMES = {
    '000660': 'SK하이닉스',
    '032830': '삼성생명',
    '004800': '현대해상',
    '006400': '삼성SDI',
    '005070': '코스모신소재',
    '001740': 'SK네트웍스',
    '003490': '대한항공'
}

def fetch_naver_news(symbol, name):
    """네이버 금융 뉴스 수집"""
    try:
        url = f"https://finance.naver.com/item/news_news.nhn?code={symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        news_list = []
        rows = soup.select('table.type5 tr')
        
        for row in rows[:5]:  # 최신 5개
            title_tag = row.select_one('td.title a')
            date_tag = row.select_one('td.date')
            info_tag = row.select_one('td.info')
            
            if title_tag and date_tag:
                news_list.append({
                    'title': title_tag.text.strip(),
                    'date': date_tag.text.strip(),
                    'source': info_tag.text.strip() if info_tag else '',
                    'link': 'https://finance.naver.com' + title_tag.get('href', '')
                })
        
        return news_list
    except Exception as e:
        return [{'error': str(e)}]

def fetch_market_sentiment():
    """시장 전체 정서 분석"""
    try:
        # 코스피/코스닥 지수
        url = "https://finance.naver.com/sise/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 코스피
        kospi = soup.select_one('#KOSPI_now')
        kospi_change = soup.select_one('#KOSPI_change')
        
        # 코스닥
        kosdaq = soup.select_one('#KOSDAQ_now')
        kosdaq_change = soup.select_one('#KOSDAQ_change')
        
        return {
            'kospi': {
                'price': kospi.text.strip() if kospi else 'N/A',
                'change': kospi_change.text.strip() if kospi_change else 'N/A'
            },
            'kosdaq': {
                'price': kosdaq.text.strip() if kosdaq else 'N/A',
                'change': kosdaq_change.text.strip() if kosdaq_change else 'N/A'
            }
        }
    except Exception as e:
        return {'error': str(e)}

def fetch_sector_news(sector):
    """섹터 뉴스 수집"""
    sector_keywords = {
        '반도체': ['SK하이닉스', '삼성전자', '반도체', 'HBM', '메모리'],
        '보험': ['삼성생명', '현대해상', '보험', '손핵'],
        '2차전지': ['삼성SDI', '2차전지', '배터리', 'EV'],
        '화학': ['코스모신소재', '화학', '소재'],
        '항공': ['대한항공', '항공', '여행', '화물'],
        '물류': ['SK네트웍스', '물류', '렌터카']
    }
    
    return sector_keywords.get(sector, [])

def main():
    print("📰 V-Series 종목 뉴스 수집 시작...")
    
    symbols = ['000660', '032830', '004800', '006400', '005070', '001740', '003490']
    
    results = {
        'scan_date': '2026-03-25',
        'collected_at': datetime.now().isoformat(),
        'market_sentiment': fetch_market_sentiment(),
        'stocks': {}
    }
    
    for symbol in symbols:
        name = STOCK_NAMES.get(symbol, symbol)
        print(f"  수집 중: {name} ({symbol})...")
        
        news = fetch_naver_news(symbol, name)
        results['stocks'][symbol] = {
            'name': name,
            'news': news
        }
        
        time.sleep(0.5)  # 예의있는 요청
    
    # 저장
    output_path = './reports/v_series/v_series_news_20260325.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\\n💾 저장 완료: {output_path}")
    return results

if __name__ == "__main__":
    main()
