#!/usr/bin/env python3
"""
LazyAlpha 스타일 섹터 강도 분석 모듈
- 섹터 강도 = 진입×1.2 + 워치×0.4 − 청산
- 5일 워치 누적 스코어
- 실시간 섹터 랭킹
"""

import json
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import sys

sys.path.insert(0, '/root/.openclaw/workspace/strg')


class SectorStrengthAnalyzer:
    """
    LazyAlpha 스타일 섹터 강도 분석기
    """
    
    def __init__(self, db_path='/root/.openclaw/workspace/strg/data/sector_signals.db'):
        self.db_path = db_path
        self.init_db()
        
        # LazyAlpha 가중치
        self.weights = {
            'entry': 1.2,   # 진입 가중치
            'watch': 0.4,   # 워치 가중치
            'exit': -1.0    # 청산 가중치 (음수)
        }
    
    def init_db(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 시그널 이력 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sector_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                sector TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,  -- 'entry', 'watch', 'exit'
                score REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 5일 누적 워치 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watch_accumulation (
                symbol TEXT PRIMARY KEY,
                sector TEXT NOT NULL,
                watch_count INTEGER DEFAULT 0,
                last_watch_date TEXT,
                accumulated_score REAL DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_signal(self, sector, symbol, signal_type, score=0):
        """시그널 추가"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 시그널 저장
        cursor.execute('''
            INSERT INTO sector_signals (date, sector, symbol, signal_type, score)
            VALUES (?, ?, ?, ?, ?)
        ''', (today, sector, symbol, signal_type, score))
        
        # 워치인 경우 누적 업데이트
        if signal_type == 'watch':
            cursor.execute('''
                INSERT INTO watch_accumulation (symbol, sector, watch_count, last_watch_date, accumulated_score)
                VALUES (?, ?, 1, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    watch_count = watch_count + 1,
                    last_watch_date = ?,
                    accumulated_score = accumulated_score + ?
            ''', (symbol, sector, today, score, today, score))
        
        conn.commit()
        conn.close()
    
    def calculate_sector_strength(self, date=None):
        """
        섹터별 시그널 강도 계산
        공식: 진입×1.2 + 워치×0.4 − 청산
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 해당 날짜의 시그널 조회
        cursor.execute('''
            SELECT sector, signal_type, COUNT(*) as count
            FROM sector_signals
            WHERE date = ?
            GROUP BY sector, signal_type
        ''', (date,))
        
        results = cursor.fetchall()
        conn.close()
        
        # 섹터별 집계
        sector_data = defaultdict(lambda: {'entry': 0, 'watch': 0, 'exit': 0})
        for sector, signal_type, count in results:
            sector_data[sector][signal_type] = count
        
        # 강도 계산
        sector_strength = {}
        for sector, counts in sector_data.items():
            strength = (
                counts['entry'] * self.weights['entry'] +
                counts['watch'] * self.weights['watch'] +
                counts['exit'] * self.weights['exit']
            )
            sector_strength[sector] = {
                'strength': round(strength, 2),
                'entry': counts['entry'],
                'watch': counts['watch'],
                'exit': counts['exit']
            }
        
        # 강도순 정렬
        return dict(sorted(
            sector_strength.items(),
            key=lambda x: x[1]['strength'],
            reverse=True
        ))
    
    def get_watch_accumulated_score(self, symbol, days=5):
        """
        5일 워치 누적 점수 조회
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 해당 심볼의 누적 점수
        cursor.execute('''
            SELECT accumulated_score, watch_count, last_watch_date
            FROM watch_accumulation
            WHERE symbol = ?
        ''', (symbol,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            accumulated_score, watch_count, last_date = result
            
            # 5일 이상 지난 데이터는 제외
            if last_date:
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
                if (datetime.now() - last_dt).days > days:
                    return 0, 0
            
            return accumulated_score, watch_count
        
        return 0, 0
    
    def calculate_candidate_score(self, sector, symbol, base_score):
        """
        진입 후보 점수 계산
        공식: 기본점수 + 섹터강도 + 시총가중치 + 5일워치누적
        """
        # 1. 기본 점수 (0-100)
        score = base_score
        
        # 2. 섹터 강도 반영
        today = datetime.now().strftime('%Y-%m-%d')
        sector_strength = self.calculate_sector_strength(today)
        
        if sector in sector_strength:
            # 섹터 강도를 0-20점으로 변환
            strength = sector_strength[sector]['strength']
            sector_bonus = min(max(strength * 2, 0), 20)
            score += sector_bonus
        
        # 3. 5일 워치 누적 반영
        watch_score, watch_count = self.get_watch_accumulated_score(symbol)
        # 누적 워치 별 추가 점수
        watch_bonus = min(watch_count * 3, 15)  # 최대 15점
        score += watch_bonus
        
        return {
            'total_score': round(score, 1),
            'base_score': base_score,
            'sector_bonus': round(sector_bonus if sector in sector_strength else 0, 1),
            'watch_bonus': watch_bonus,
            'watch_count': watch_count
        }
    
    def get_grade(self, score):
        """점수별 등급 산정 (LazyAlpha 기준)"""
        if score >= 90:
            return '핵심 후보', '#00ff88'  # 초록
        elif score >= 70:
            return '관심', '#4dabf7'      # 파랑
        else:
            return '참고', '#868e96'       # 회색
    
    def generate_report(self, date=None):
        """섹터 강도 리포트 생성"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        sector_strength = self.calculate_sector_strength(date)
        
        report = []
        report.append("=" * 60)
        report.append("📊 LazyAlpha 스타일 섹터 강도 분석")
        report.append("=" * 60)
        report.append(f"공식: 진입×1.2 + 워치×0.4 − 청산 | 날짜: {date}")
        report.append("-" * 60)
        report.append(f"{'순위':<4} {'섹터':<15} {'강도':<8} {'진입':<6} {'워치':<6} {'청산':<6}")
        report.append("-" * 60)
        
        for i, (sector, data) in enumerate(sector_strength.items(), 1):
            strength_color = '🟢' if data['strength'] > 0 else '🔴' if data['strength'] < 0 else '⚪'
            report.append(
                f"{i:<4} {sector:<15} {strength_color} {data['strength']:<5.1f} "
                f"{data['entry']:<6} {data['watch']:<6} {data['exit']:<6}"
            )
        
        if not sector_strength:
            report.append("(데이터 없음)")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def cleanup_old_data(self, days=30):
        """오래된 데이터 정리"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        cursor.execute('DELETE FROM sector_signals WHERE date < ?', (cutoff_date,))
        cursor.execute('DELETE FROM watch_accumulation WHERE last_watch_date < ?', (cutoff_date,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ {days}일 이전 데이터 정리 완료")


# 통합 스캐너 연동 함수
def enhance_scanner_with_sector_strength(scanner_results, analyzer):
    """
    기존 스캐너 결과에 섹터 강도 점수 추가
    """
    enhanced_results = []
    
    for stock in scanner_results:
        symbol = stock['symbol']
        name = stock['name']
        sector = stock.get('sector', '기타')  # 섹터 정보 필요
        base_score = stock.get('final_score', stock.get('quality_score', 0))
        
        # LazyAlpha 스타일 점수 계산
        candidate_score = analyzer.calculate_candidate_score(
            sector, symbol, base_score
        )
        
        # 등급 산정
        grade, color = analyzer.get_grade(candidate_score['total_score'])
        
        # 결과 병합
        enhanced = {
            **stock,
            'lazyalpha_score': candidate_score['total_score'],
            'lazyalpha_grade': grade,
            'score_breakdown': candidate_score,
            'grade_color': color
        }
        
        enhanced_results.append(enhanced)
    
    # 점수순 정렬
    return sorted(enhanced_results, key=lambda x: x['lazyalpha_score'], reverse=True)


if __name__ == "__main__":
    # 테스트
    analyzer = SectorStrengthAnalyzer()
    
    # 샘플 시그널 추가
    test_signals = [
        ('반도체', '042700', 'entry', 80),
        ('반도체', '058470', 'watch', 75),
        ('반도체', '092130', 'entry', 70),
        ('바이오', '068270', 'watch', 65),
        ('바이오', '207940', 'exit', 60),
        ('2차전지', '051910', 'entry', 85),
        ('반도체', '005930', 'watch', 72),
        ('반도체', '000660', 'entry', 78),
    ]
    
    print("📝 샘플 시그널 추가 중...")
    for sector, symbol, signal_type, score in test_signals:
        analyzer.add_signal(sector, symbol, signal_type, score)
    
    # 리포트 출력
    print("\n" + analyzer.generate_report())
    
    # 진입 후보 점수 계산 예시
    print("\n" + "=" * 60)
    print("🎯 진입 후보 점수 계산 예시")
    print("=" * 60)
    
    test_candidates = [
        ('반도체', '042700', 75),
        ('반도체', '058470', 70),
        ('2차전지', '051910', 80),
    ]
    
    for sector, symbol, base_score in test_candidates:
        score_data = analyzer.calculate_candidate_score(sector, symbol, base_score)
        grade, color = analyzer.get_grade(score_data['total_score'])
        
        print(f"\n{symbol} ({sector}):")
        print(f"  기본점수: {score_data['base_score']}")
        print(f"  섹터병점수: +{score_data['sector_bonus']}")
        print(f"  워치누적({score_data['watch_count']}회): +{score_data['watch_bonus']}")
        print(f"  총점: {score_data['total_score']} → {grade}")
    
    # 데이터 정리
    analyzer.cleanup_old_data(days=7)
