#!/usr/bin/env python3
"""
KOSPI 마스터 파일 파서
DWS 마스터 파일에서 종목 코드와 이름 추출
"""

import os
import json
import re
from datetime import datetime


def parse_kospi_master_line(line: str) -> dict:
    """
    한 줄 파싱 - 개선된 버전
    """
    try:
        # 처음 6자리가 종목코드
        code = line[0:6].strip()
        
        if not code.isdigit() or len(code) != 6:
            return None
        
        # ISIN 코드 찾기
        isin_match = re.search(r'(KR7\d{9})', line)
        isin = isin_match.group(1) if isin_match else ''
        
        # 종목명 추출 (ISIN 이후)
        name = ""
        if isin:
            isin_pos = line.find(isin)
            if isin_pos > 0:
                after_isin = line[isin_pos + len(isin):]
                
                # 첫 번째 한글 단어 추출
                # 패턴: 한글로 시작하고, 한글/영문/숫자/- 포함
                name_match = re.search(r'^[^가-힣]*([가-힣][가-힣A-Za-z0-9\-]{1,20})', after_isin)
                if name_match:
                    name = name_match.group(1).strip()
                    
                    # 후처리: ST, NN 등 코드 제거
                    name = re.sub(r'(ST|NN|NY|YN|AY|YA)[0-9YNS]+$', '', name).strip()
        
        if not name or len(name) < 2:
            return None
        
        # 펀드/ETF 등 필터링
        exclude_keywords = ['펀드', 'Fund', 'FUND', '스팩', 'SPAC', 'ETF', 'ETN', '신탁', '리츠', 'REITs', '채권', '1호', '2호', '3호', '4호', '5호']
        if any(e in name for e in exclude_keywords):
            return None
        
        return {
            'code': code,
            'name': name,
            'isin': isin,
            'symbol': f"{code}.KS",
            'market': 'KOSPI'
        }
        
    except Exception as e:
        return None


def parse_kospi_master(file_path: str) -> list:
    """
    마스터 파일 파싱
    """
    stocks = []
    seen_codes = set()
    
    with open(file_path, 'rb') as f:
        content = f.read().decode('cp949', errors='ignore')
        lines = content.split('\n')
    
    for line in lines:
        if len(line) < 50:
            continue
        
        stock = parse_kospi_master_line(line)
        if stock and stock['code'] not in seen_codes:
            stocks.append(stock)
            seen_codes.add(stock['code'])
    
    return stocks


def main():
    print("=" * 70)
    print("📊 KOSPI Master Parser v3")
    print("=" * 70)
    
    master_file = '/home/programs/kstock_analyzer/data/kospi_code.mst'
    
    if not os.path.exists(master_file):
        print(f"❌ File not found: {master_file}")
        return
    
    print(f"📂 Loading: {master_file}")
    
    stocks = parse_kospi_master(master_file)
    
    print(f"\n📈 Total stocks: {len(stocks)}")
    
    if stocks:
        # Sort by code
        stocks.sort(key=lambda x: x['code'])
        
        # Show samples
        print("\n📋 Sample stocks:")
        samples = [s for s in stocks if any(k in s['name'] for k in ['삼성', '현대', 'SK', 'NAVER', '카카오', 'LG', '기아'])]
        if not samples:
            samples = stocks[:30]
        
        for stock in samples[:30]:
            print(f"  • [{stock['code']}] {stock['name']}")
        
        if len(samples) > 30:
            print(f"  ... and {len(samples) - 30} more")
        
        # Save
        output_file = '/home/programs/kstock_analyzer/data/kospi_stocks.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'count': len(stocks),
                'updated_at': datetime.now().isoformat(),
                'source': 'Korea Investment DWS Master',
                'stocks': stocks
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Saved to {output_file}")
        
        # Also save simple list
        list_file = '/home/programs/kstock_analyzer/data/kospi_stock_list.txt'
        with open(list_file, 'w', encoding='utf-8') as f:
            for s in stocks:
                f.write(f"{s['code']},{s['name']}\n")
        print(f"✅ Saved list to {list_file}")


if __name__ == '__main__':
    main()
