# LazyAlpha (딥다이브) 분석 리포트

**URL:** https://deepdive.ai.kr/lazyalpha/  
**운영자:** @deepdive_kr  
**분석일:** 2026-03-31

---

## 📊 플랫폼 개요

LazyAlpha는 국내 주식 시장을 대상으로 한 **AI 기반 알고리즘 트레이딩 시그널 플랫폼**입니다. 실시간으로 4시간봉 기준 매매 시그널을 제공하며, 섹터 로테이션과 시그널 강도를 결합한 독자적인 스코어링 시스템을 사용합니다.

---

## 🔑 핵심 기능 분석

### 1. 4H 시그널 (4시간봉 시그널)
- **타임프레임:** 4시간봉 기준
- **시그널 유형:** 진입(Entry) / 워치(Watch) / 청산(Exit)
- **업데이트:** 12초 자동 갱신
- **장세 판단:** 
  - 중립 장세
  - 혼조 (섹터 강도 + 액션 분포 함께 확인 필요)

### 2. 섹터별 시그널 강도 (Sector Signal Strength)
```
섹터 강도 = 진입×1.2 + 워치×0.4 − 청산
```
- **진입(Entry):** 1.2배 가중치
- **워치(Watch):** 0.4배 가중치  
- **청산(Exit):** 마이너스 가중치

**활용 아이디어:**
- 우리 스캐너에도 비슷한 가중치 시스템 적용 가능
- 예: BUY 시그널 × 1.5 + WATCH × 0.5 - SELL × 1.0

### 3. 진입 상위 후보 스코어링
```
점수 = 당일 시그널 + 섹터 강도 + 시총 + 5일 워치 누적

등급:
- 90점 이상 = 핵심 후보 (Core Candidate)
- 70~89점 = 관심 (Interest)
- 70점 미만 = 참고 (Reference)
```

**활용 아이디어:**
- 우리 통합 스캐너의 점수 체계와 유사
- 5일 누적 워치 개념 추가 → 추적 관찰 기능

---

## 💡 우리 시스템에 적용 가능한 기능

### 1. 섹터 강도 모듈 추가
```python
class SectorStrengthCalculator:
    def calculate(self, sector_signals):
        '''
        섹터 강도 = 진입×1.2 + 워치×0.4 − 청산
        '''
        entry_weight = 1.2
        watch_weight = 0.4
        exit_weight = -1.0
        
        strength = (
            sector_signals['entry'] * entry_weight +
            sector_signals['watch'] * watch_weight +
            sector_signals['exit'] * exit_weight
        )
        return strength
```

### 2. 멀티타임프레임 시그널 통합
- 현재: 일봉 기준
- 추가: 4H봉 시그널
- 최종 점수에 시간프레임 가중치 부여

### 3. 워치리스트 추적 시스템
```python
class WatchlistTracker:
    def __init__(self):
        self.watch_history = {}  # 5일 누적 저장
    
    def add_watch(self, symbol):
        if symbol not in self.watch_history:
            self.watch_history[symbol] = []
        self.watch_history[symbol].append({
            'date': datetime.now(),
            'score': self.calculate_score(symbol)
        })
        # 5일 이상 데이터는 제거
        self.watch_history[symbol] = [
            x for x in self.watch_history[symbol] 
            if (datetime.now() - x['date']).days <= 5
        ]
    
    def get_accumulated_score(self, symbol):
        # 5일 워치 누적 점수 계산
        if symbol not in self.watch_history:
            return 0
        return sum(x['score'] for x in self.watch_history[symbol])
```

### 4. 실시간 대시보드 개선
LazyAlpha의 UI/UX 참고:
- 12초 자동 갱신
- 섹터별 색상 구분
- 시그널 피드 실시간 스트리밍

---

## 🎯 적용 우선순위

### 즉시 적용 가능 (Low Effort, High Impact)
1. **섹터 강도 계산식** - 기존 데이터로 계산 가능
2. **점수 등급 체계** - 90/70 기준 명확화
3. **워치리스트 5일 누적** - DB에 저장 후 활용

### 중기 적용 (Medium Effort)
1. **4H 시그널 연동** - FinanceDataReader 4H 데이터 확인
2. **실시간 자동 갱신** - WebSocket 또는 폴링 구현
3. **섹터별 시각화** - 차트에 섹터 색상 표시

### 장기 적용 (High Effort)
1. **웹훅 알림 시스템** - 텔레그램/슬랙 연동
2. **AI 예측 모델** - 머신러닝 기반 시그널 예측
3. **백테스트 엔진** - 과거 시그널 검증

---

## 📋 기능 비교표

| 기능 | LazyAlpha | 우리 스캐너 | 적용 가능성 |
|:---|:---|:---|:---:|
| **4H 시그널** | ◎ | △ (일봉) | 중 |
| **섹터 강도** | ◎ | ✗ | **상** |
| **워치리스트** | ◎ (5일 누적) | △ (단일) | **상** |
| **실시간 갱신** | ◎ (12초) | ✗ (수동) | 중 |
| **재무 분석** | ? | ◎ (DART) | - |
| **웹 정보** | ? | ◎ (네이버) | - |
| **최종 판단** | ? | ◎ (S/A/B/C) | - |

**◎ = 강점, △ = 부분적, ✗ = 없음, ? = 확인 불가**

---

## 🔧 코드 스니펫: 섹터 강도 모듈

```python
# sector_strength.py
import pandas as pd
from datetime import datetime, timedelta

class SectorStrengthAnalyzer:
    '''
    LazyAlpha 스타일 섹터 강도 분석기
    '''
    
    def __init__(self):
        self.sector_weights = {
            'entry': 1.2,   # 진입 가중치
            'watch': 0.4,   # 워치 가중치
            'exit': -1.0    # 청산 가중치 (음수)
        }
    
    def calculate_sector_strength(self, signals_df):
        '''
        섹터별 시그널 강도 계산
        
        Args:
            signals_df: DataFrame with columns [sector, symbol, signal_type, date]
                signal_type: 'entry', 'watch', 'exit'
        
        Returns:
            sector_strength: {sector: strength_score}
        '''
        sector_strength = {}
        
        for sector in signals_df['sector'].unique():
            sector_data = signals_df[signals_df['sector'] == sector]
            
            # 오늘 날짜 기준
            today = datetime.now().date()
            today_data = sector_data[sector_data['date'].dt.date == today]
            
            # 시그널 카운트
            entry_count = len(today_data[today_data['signal_type'] == 'entry'])
            watch_count = len(today_data[today_data['signal_type'] == 'watch'])
            exit_count = len(today_data[today_data['signal_type'] == 'exit'])
            
            # 강도 계산
            strength = (
                entry_count * self.sector_weights['entry'] +
                watch_count * self.sector_weights['watch'] +
                exit_count * self.sector_weights['exit']
            )
            
            sector_strength[sector] = {
                'strength': round(strength, 2),
                'entry': entry_count,
                'watch': watch_count,
                'exit': exit_count
            }
        
        # 강도순 정렬
        return dict(sorted(
            sector_strength.items(), 
            key=lambda x: x[1]['strength'], 
            reverse=True
        ))
    
    def get_top_sectors(self, sector_strength, top_n=5):
        '''상위 N개 섹터 반환'''
        return dict(list(sector_strength.items())[:top_n])
    
    def generate_sector_report(self, sector_strength):
        '''섹터 강도 리포트 생성'''
        report = []
        report.append("=" * 50)
        report.append("📊 섹터별 시그널 강도")
        report.append("=" * 50)
        report.append(f"{'순위':<4} {'섹터':<15} {'강도':<8} {'진입':<6} {'워치':<6} {'청산':<6}")
        report.append("-" * 50)
        
        for i, (sector, data) in enumerate(sector_strength.items(), 1):
            report.append(
                f"{i:<4} {sector:<15} {data['strength']:<8.1f} "
                f"{data['entry']:<6} {data['watch']:<6} {data['exit']:<6}"
            )
        
        return "\n".join(report)


# 사용 예시
if __name__ == "__main__":
    # 샘플 데이터
    sample_data = pd.DataFrame({
        'sector': ['반도체', '반도체', '반도체', '바이오', '바이오', '2차전지'],
        'symbol': ['042700', '058470', '092130', '068270', '207940', '051910'],
        'signal_type': ['entry', 'watch', 'entry', 'watch', 'exit', 'entry'],
        'date': pd.to_datetime(['2026-03-31'] * 6)
    })
    
    analyzer = SectorStrengthAnalyzer()
    strength = analyzer.calculate_sector_strength(sample_data)
    print(analyzer.generate_sector_report(strength))
```

---

## 📌 결론 및 추천사항

### 핵심 인사이트
1. **섹터 로테이션 전략** - LazyAlpha의 가장 큰 특징
2. **가중치 기반 스코어링** - 단순 카운트가 아닌 가중합
3. **멀티타임프레임** - 4H + 일봉 동시 활용
4. **누적 추적** - 5일 워치 누적 → 추세 확인

### 우리 시스템 개선 방향
1. **단기:** 섹터 강도 계산식 도입 (진입×1.2 + 워치×0.4 − 청산)
2. **중기:** 4H 시그널 추가, 워치리스트 5일 누적 기능
3. **장기:** 실시간 대시보드, 웹훅 알림 시스템

### 기대 효과
- **섹터 로테이션 타이밍** 포착
- **시그널 신뢰도** 향상 (누적 스코어)
- **실시간 대응** 능력 강화

---

**LazyAlpha는 섹터 기반 알고리즘 트레이딩의 좋은 참고 모델입니다. 특히 섹터 강도 계산식과 5일 누적 워치 개념을 우리 스캐너에 적용하면 시그널의 질을 크게 높일 수 있습니다.**
