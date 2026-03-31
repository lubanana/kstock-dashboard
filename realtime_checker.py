#!/usr/bin/env python3
"""
실시간 종목 상황 체크 + 최종 판단 모듈
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

class RealTimeChecker:
    """실시간 종목 상황 체커"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def check_stock_situation(self, symbol, name):
        """
        종목의 현재 시점 상황 체크
        """
        try:
            url = f"https://finance.naver.com/item/main.naver?code={symbol}"
            response = self.session.get(url, timeout=10)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result = {
                'current_price': None,
                'price_change': None,
                'price_change_pct': None,
                'volume': None,
                'vs_prev_day': None,  # 전일대비
                'rsi_status': None,
                'alerts': [],
                'recommendation': None
            }
            
            # 현재가
            try:
                price_elem = soup.select_one('.no_today .blind')
                if price_elem:
                    price_text = price_elem.text.strip().replace(',', '')
                    result['current_price'] = int(price_text)
            except:
                pass
            
            # 등락률 파싱
            try:
                # no_exday 안의 모든 em 태그 찾기
                em_tags = soup.select('.no_exday em')
                for em in em_tags:
                    # %가 포함된 텍스트 찾기
                    text = em.get_text()
                    if '%' in text:
                        # 숫자 추출
                        import re
                        match = re.search(r'([+-]?)([\d.]+)%', text)
                        if match:
                            sign = -1 if '-' in text or 'no_down' in str(em) else 1
                            result['price_change_pct'] = float(match.group(2)) * sign
                            break
                
                # 등락가
                change_span = soup.select_one('.no_exday .blind')
                if change_span:
                    change_text = change_span.text.strip().replace(',', '')
                    try:
                        result['price_change'] = int(change_text)
                    except:
                        pass
                        
            except Exception as e:
                print(f"등락률 파싱 오류: {e}")
            
            # 거래량
            try:
                volume_table = soup.select('table td span')
                for span in volume_table:
                    if '거래대금' in str(span.parent) or '거래량' in str(span.parent):
                        volume_text = span.text.strip()
                        result['volume'] = volume_text
                        break
            except:
                pass
            
            # 분석 및 알림
            if result['price_change_pct'] is not None:
                if result['price_change_pct'] > 5:
                    result['alerts'].append(f"⚠️ 급등 (+{result['price_change_pct']:.1f}%) - 진입 시점 놓침 가능성")
                    result['vs_prev_day'] = '급등'
                elif result['price_change_pct'] > 2:
                    result['alerts'].append(f"△ 상승 중 (+{result['price_change_pct']:.1f}%)")
                    result['vs_prev_day'] = '상승'
                elif result['price_change_pct'] < -5:
                    result['alerts'].append(f"✓ 추가 하락 (-{abs(result['price_change_pct']):.1f}%) - 더 좋은 진입가")
                    result['vs_prev_day'] = '급락'
                elif result['price_change_pct'] < -2:
                    result['alerts'].append(f"○ 하락 중 ({result['price_change_pct']:.1f}%)")
                    result['vs_prev_day'] = '하락'
                else:
                    result['alerts'].append(f"→ 보합 ({result['price_change_pct']:+.1f}%)")
                    result['vs_prev_day'] = '보합'
            
            # 최종 추천
            if result['vs_prev_day'] == '급락':
                result['recommendation'] = '매수 적기 (추가 하락으로 진입가 개선)'
            elif result['vs_prev_day'] == '하락':
                result['recommendation'] = '분할 매수 시작 고려'
            elif result['vs_prev_day'] == '보합':
                result['recommendation'] = '시장가 매수 가능'
            elif result['vs_prev_day'] == '상승':
                result['recommendation'] = '관망 또는 소액 매수'
            elif result['vs_prev_day'] == '급등':
                result['recommendation'] = '진입 시점 놓침 - 다음 기회 대기'
            
            return result
            
        except Exception as e:
            return {
                'current_price': None,
                'price_change': None,
                'price_change_pct': None,
                'volume': None,
                'vs_prev_day': '확인 불가',
                'alerts': ['⚠️ 데이터 확인 불가'],
                'recommendation': '수동 확인 필요'
            }


def generate_realtime_judgment(stock, realtime_data):
    """실시간 데이터를 반영한 최종 판단"""
    
    judgments = stock.get('judgments', [])
    realtime_notes = []
    
    # 실시간 등락 반영
    if realtime_data.get('price_change_pct') is not None:
        change = realtime_data['price_change_pct']
        
        if change > 5:
            realtime_notes.append({
                'type': 'warning',
                'text': f'⚠️ 오늘 급등 +{change:.1f}% - 어제 스캔가 대비 상승'
            })
            # 급등 시 등급 조정
            if stock.get('grade') == 'S':
                adjusted_grade = 'A'
                reason = '급등으로 진입 시점 놓침'
            else:
                adjusted_grade = stock.get('grade')
                reason = '상승 후 진입 권장하지 않음'
                
        elif change > 2:
            realtime_notes.append({
                'type': 'neutral',
                'text': f'△ 오늘 +{change:.1f}% 상승 중'
            })
            adjusted_grade = stock.get('grade')
            reason = '상승 중이나 진입 가능'
            
        elif change < -5:
            realtime_notes.append({
                'type': 'positive',
                'text': f'✓ 오늘 추가 하락 {change:.1f}% - 더 좋은 진입기회'
            })
            # 추가 하락 시 등급 상향
            if stock.get('grade') == 'A':
                adjusted_grade = 'S'
                reason = '추가 하락으로 진입가 개선'
            else:
                adjusted_grade = stock.get('grade')
                reason = '추가 하락 - 분할 매수 적기'
                
        elif change < -2:
            realtime_notes.append({
                'type': 'positive',
                'text': f'○ 오늘 {change:.1f}% 하락 - 진입 적기'
            })
            adjusted_grade = stock.get('grade')
            reason = '하락 중 진입 권장'
            
        else:
            realtime_notes.append({
                'type': 'neutral',
                'text': f'→ 오늘 {change:+.1f}% - 보합권'
            })
            adjusted_grade = stock.get('grade')
            reason = '시장가 진입 가능'
    else:
        adjusted_grade = stock.get('grade')
        reason = '실시간 데이터 없음'
    
    return {
        'adjusted_grade': adjusted_grade,
        'adjustment_reason': reason,
        'realtime_notes': realtime_notes,
        'realtime_data': realtime_data
    }


if __name__ == "__main__":
    checker = RealTimeChecker()
    
    # TOP 5 종목 실시간 체크
    top_stocks = [
        ('013520', '화승코퍼레이션'),
        ('263860', '지니언스'),
        ('110990', '디아이티'),
        ('003350', '한국화장품제조'),
        ('095610', '테스'),
    ]
    
    print("🔍 실시간 종목 상황 체크 (2026-03-31 기준)")
    print("="*70)
    
    for symbol, name in top_stocks:
        print(f"\n📊 {name} ({symbol})")
        print("-"*70)
        
        result = checker.check_stock_situation(symbol, name)
        
        if result['current_price']:
            print(f"   현재가: {result['current_price']:,}원")
        
        if result['price_change_pct'] is not None:
            change_symbol = '🟥' if result['price_change_pct'] > 0 else '🟩' if result['price_change_pct'] < 0 else '➖'
            print(f"   등락률: {change_symbol} {result['price_change_pct']:+.2f}%")
        
        print(f"   상태: {result['vs_prev_day']}")
        
        for alert in result['alerts']:
            print(f"   {alert}")
        
        print(f"   💡 실시간 추천: {result['recommendation']}")
