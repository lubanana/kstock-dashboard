#!/usr/bin/env python3
"""
Daily Market Intelligence Scraper
==================================
매일 오전 5시 실행:
- jhnber-node.vercel.app (X-INTELLIGENCE)
- sovereignsky.ai (SOVEREIGN SKY)

저장: data/daily_intelligence/YYYY-MM-DD.json
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
import sys

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

# 저장 디렉토리
SAVE_DIR = './data/daily_intelligence'
os.makedirs(SAVE_DIR, exist_ok=True)

# 타겟 웹사이트
SITES = {
    'jhnber': {
        'url': 'https://jhnber-node.vercel.app',
        'name': 'X-INTELLIGENCE (JHONBER)'
    },
    'sovereignsky': {
        'url': 'https://sovereignsky.ai',
        'name': 'SOVEREIGN SKY'
    }
}


def scrape_jhnber():
    """jhnber-node.vercel.app 스크래핑"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(SITES['jhnber']['url'], headers=headers, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 텍스트 추출
        text = soup.get_text(separator='\n', strip=True)
        
        # 주요 섹션 파싱 (LIVE, TODAY, PEAK, TOTAL)
        data = {
            'timestamp': datetime.now().isoformat(),
            'url': SITES['jhnber']['url'],
            'title': 'X-INTELLIGENCE : JHONBER — NODE',
            'full_text': text,
            'sections': {}
        }
        
        # 시간 정보 추출 시도
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'LIVE' in line and i + 1 < len(lines):
                data['sections']['live'] = lines[i + 1].strip() if i + 1 < len(lines) else ''
            if 'TODAY' in line and i + 1 < len(lines):
                data['sections']['today'] = lines[i + 1].strip() if i + 1 < len(lines) else ''
            if 'PEAK' in line and i + 1 < len(lines):
                data['sections']['peak'] = lines[i + 1].strip() if i + 1 < len(lines) else ''
            if 'TOTAL' in line:
                data['sections']['total'] = lines[i + 1].strip() if i + 1 < len(lines) else ''
        
        return data
        
    except Exception as e:
        return {
            'timestamp': datetime.now().isoformat(),
            'url': SITES['jhnber']['url'],
            'error': str(e)
        }


def scrape_sovereignsky():
    """sovereignsky.ai 스크래핑"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(SITES['sovereignsky']['url'], headers=headers, timeout=30)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        
        # MARKET SUMMARY 데이터 추출
        data = {
            'timestamp': datetime.now().isoformat(),
            'url': SITES['sovereignsky']['url'],
            'title': 'SOVEREIGN SKY | ENGINE',
            'full_text': text,
            'indicators': {}
        }
        
        # 주요 지표 파싱
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            
            # RISK IDX (다음 줄에 숫자가 있는 경우)
            if 'RISK IDX' in line or 'RISK SNAPSHOT' in line:
                # 다음 줄들에서 숫자 찾기
                for j in range(i+1, min(i+5, len(lines))):
                    val = lines[j].strip()
                    if val and val.replace('.', '').isdigit():
                        data['indicators']['risk_idx'] = val
                        break
            
            # PRIMARY (주요 이벤트)
            if 'PRIMARY' in line or line.startswith('PRIMARY'):
                # 🔥 이모지 이후 텍스트 추출
                if '🔥' in line:
                    primary = line.split('🔥')[-1].strip()
                    data['indicators']['primary_event'] = primary
                else:
                    data['indicators']['primary_event'] = line.replace('PRIMARY', '').strip()
            
            # FLOW
            if line.startswith('FLOW'):
                data['indicators']['flow'] = line.replace('FLOW', '').strip()
            elif 'FLOW' in line and 'NEUTRAL' in line:
                data['indicators']['flow'] = 'NEUTRAL'
            elif 'FLOW' in line and 'BULLISH' in line:
                data['indicators']['flow'] = 'BULLISH'
            elif 'FLOW' in line and 'BEARISH' in line:
                data['indicators']['flow'] = 'BEARISH'
            
            # RISK INDEX 직접 파싱 (16.1 형식)
            if line.replace('.', '').isdigit() and '.' in line:
                num = float(line)
                if 0 < num < 100:  # RISK IDX 범위
                    data['indicators']['risk_idx'] = line
            
            # CONFIRMED
            if line == 'CONFIRMED':
                data['indicators']['status'] = 'CONFIRMED'
        
        return data
        
    except Exception as e:
        return {
            'timestamp': datetime.now().isoformat(),
            'url': SITES['sovereignsky']['url'],
            'error': str(e)
        }


def save_data(data):
    """데이터 저장"""
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'{SAVE_DIR}/intelligence_{today}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename


def save_raw_html(site_key, html_content):
    """원본 HTML 백업"""
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'{SAVE_DIR}/{site_key}_{today}.html'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return filename


def main():
    print("=" * 70)
    print("🔮 Daily Market Intelligence Scraper")
    print("=" * 70)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 결과 수집
    all_data = {
        'scraped_at': datetime.now().isoformat(),
        'sources': {}
    }
    
    # 1. jhnber 스크래핑
    print("📡 스크래핑: jhnber-node.vercel.app")
    jhnber_data = scrape_jhnber()
    all_data['sources']['jhnber'] = jhnber_data
    
    if 'error' in jhnber_data:
        print(f"   ❌ 오류: {jhnber_data['error']}")
    else:
        print(f"   ✅ 성공")
        print(f"   📄 제목: {jhnber_data.get('title', 'N/A')}")
        sections = jhnber_data.get('sections', {})
        for key, val in sections.items():
            if val:
                print(f"   • {key.upper()}: {val[:50]}...")
    
    print()
    
    # 2. sovereignsky 스크래핑
    print("📡 스크래핑: sovereignsky.ai")
    sky_data = scrape_sovereignsky()
    all_data['sources']['sovereignsky'] = sky_data
    
    if 'error' in sky_data:
        print(f"   ❌ 오류: {sky_data['error']}")
    else:
        print(f"   ✅ 성공")
        print(f"   📄 제목: {sky_data.get('title', 'N/A')}")
        indicators = sky_data.get('indicators', {})
        for key, val in indicators.items():
            print(f"   • {key}: {val}")
    
    print()
    
    # 저장
    today = datetime.now().strftime('%Y-%m-%d')
    saved_file = save_data(all_data)
    print(f"💾 데이터 저장: {saved_file}")
    
    # 최신 링크 업데이트
    latest_link = f'{SAVE_DIR}/latest.json'
    with open(latest_link, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 최신 데이터: {latest_link}")
    
    # GitHub 푸시 (옵션)
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'add', '-A'],
            cwd='/root/.openclaw/workspace/strg',
            capture_output=True,
            text=True
        )
        result = subprocess.run(
            ['git', 'commit', '-m', f'Daily intelligence data: {today}'],
            cwd='/root/.openclaw/workspace/strg',
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            result = subprocess.run(
                ['git', 'push', 'origin', 'main'],
                cwd='/root/.openclaw/workspace/strg',
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"📤 GitHub 푸시 완료")
            else:
                print(f"   ⚠️ GitHub 푸시 실패 (네트워크 등)")
        else:
            print(f"   ℹ️ GitHub: 변경사항 없음")
    except Exception as e:
        print(f"   ⚠️ GitHub 푸시 오류: {e}")
    
    print()
    print("=" * 70)
    print("✅ 스크래핑 완료")
    print("=" * 70)


if __name__ == '__main__':
    main()
