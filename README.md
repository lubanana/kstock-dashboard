# KStock Dashboard

📈 한국 주식 전략별 스캔 결과 대시보드

## 🌐 라이브 대시보드

**https://username.github.io/kstock-dashboard**

*(GitHub Pages 설정 후 위 URL에서 확인)*

## 📊 스캔 전략

| 전략 | 설명 | 파일 |
|------|------|------|
| **리버모어** | 52주 신고가 돌파 | `livermore_scanner.py` |
| **오닐** | 거래량 폭발 | `oneil_scanner.py` |
| **미너비니** | VCP 변동성 축소 | `minervini_scanner.py` |

## 🔄 자동 갱신

- **스캔 시간**: 매일 오전 7:00 (한국 시간)
- **배포 시간**: 매일 오전 7:30 (한국 시간)
- **데이터 소스**: Yahoo Finance

## 📁 폴더 구조

```
.
├── docs/                    # GitHub Pages 소스
│   └── index.html          # 대시보드 메인
├── data/                    # 스캔 결과 데이터
├── *.py                     # 스캐너 스크립트
└── .github/workflows/       # GitHub Actions
```

## 🚀 로컬 실행

```bash
# 스캐너 실행
python3 livermore_scanner.py
python3 oneil_scanner.py
python3 minervini_scanner.py

# 대시보드 생성
python3 generate_dashboard.py

# 로컬 서버로 확인
python3 -m http.server 8080 --directory docs
```

## ⚠️ 면책

이 프로젝트는 교육 목적으로 제작되었습니다. 투자 결정은 본인의 책임이며, 이 정보에 의존한 투자 결과에 대해 책임지지 않습니다.

## 📜 라이선스

MIT License
