# TradingView Lightweight Charts 빠른 시작

## 🚀 설치 방법 (3가지 옵션)

### 옵션 1: 자동 설치 스크립트 (권장)
```bash
# 프로젝트 폴더에서 실행
cd /root/.openclaw/workspace/strg
./install-tv-charts.sh

# 생성된 프로젝트로 이동
cd tv-charts-project
npm run dev
```

### 옵션 2: 수동 설치
```bash
# 1. 폴터 생성
mkdir my-chart-project
cd my-chart-project

# 2. npm 초기화
npm init -y

# 3. 라이브러리 설치
npm install lightweight-charts

# 4. Vite 설치 (개발 서버용)
npm install -D vite
```

### 옵션 3: CDN 직접 사용 (가장 빠름)
```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
    <div id="chart" style="width: 800px; height: 400px;"></div>
    <script>
        const chart = LightweightCharts.createChart(document.getElementById('chart'));
        const series = chart.addCandlestickSeries();
        series.setData([
            { time: '20260401', open: 100, high: 105, low: 98, close: 103 },
            { time: '20260402', open: 103, high: 108, low: 102, close: 106 },
        ]);
    </script>
</body>
</html>
```

---

## 📂 생성되는 프로젝트 구조

```
tv-charts-project/
├── node_modules/          # 설치된 패키지
├── src/
│   └── main.js           # 메인 차트 코드
├── index.html            # HTML 템플릿
├── package.json          # 프로젝트 설정
├── vite.config.js        # Vite 설정
└── README.md             # 프로젝트 문서
```

---

## 🎯 주요 명령어

| 명령어 | 설명 |
|:---|:---|
| `npm run dev` | 개발 서버 실행 (http://localhost:3000) |
| `npm run build` | 프로덕션 빌드 |
| `npm run preview` | 빌드 결과 미리보기 |
| `npm run serve` | 정적 파일 서버 |

---

## 💻 사용 예시

### 기본 캔들스틱 차트
```javascript
import { createChart, CandlestickSeries } from 'lightweight-charts';

const chart = createChart(document.getElementById('chart'), {
    width: 800,
    height: 400,
    layout: {
        background: { color: '#131722' },
        textColor: '#d1d4dc',
    },
});

const series = chart.addSeries(CandlestickSeries, {
    upColor: '#26a69a',
    downColor: '#ef5350',
});

series.setData([
    { time: '20260401', open: 65000, high: 66500, low: 64500, close: 66000 },
    { time: '20260402', open: 66000, high: 67800, low: 65500, close: 67500 },
]);
```

### 목표가/손절가 라인
```javascript
// 진입가
series.createPriceLine({
    price: 70200,
    color: '#ffd700',
    lineWidth: 2,
    title: 'Entry',
});

// 목표가
series.createPriceLine({
    price: 85000,
    color: '#26a69a',
    lineWidth: 2,
    title: 'Target +21%',
});

// 손절가
series.createPriceLine({
    price: 62000,
    color: '#ef5350',
    lineWidth: 2,
    title: 'Stop -12%',
});
```

---

## 🎨 테마 변경

### 다크 테마 (기본)
```javascript
const darkTheme = {
    layout: {
        background: { color: '#131722' },
        textColor: '#d1d4dc',
    },
    grid: {
        vertLines: { color: '#2a2e39' },
        horzLines: { color: '#2a2e39' },
    },
};
```

### 라이트 테마
```javascript
const lightTheme = {
    layout: {
        background: { color: '#ffffff' },
        textColor: '#333333',
    },
    grid: {
        vertLines: { color: '#e0e0e0' },
        horzLines: { color: '#e0e0e0' },
    },
};
```

---

## 📚 추가 자료

- [공식 문서](https://tradingview.github.io/lightweight-charts/)
- [GitHub 저장소](https://github.com/tradingview/lightweight-charts)
- [플러그인 예제](https://tradingview.github.io/lightweight-charts/plugin-examples/)

---

## ❓ 문제 해결

### "Cannot find module 'lightweight-charts'"
```bash
npm install lightweight-charts
```

### 차트가 표시되지 않음
- 브라우저 콘솔 확인 (F12)
- 컨테이너 크기 확인 (width/height)
- 데이터 형식 확인 (time: 'YYYYMMDD')

### CORS 에러
```bash
# 로컬 서버 사용
npm run serve
# 또는
python3 -m http.server 8080
```
