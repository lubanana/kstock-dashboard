# TradingView Lightweight Charts 적용 가이드

## 📊 라이브러리 특징

| 특징 | 설명 |
|:---|:---|
| **용량** | ~40KB (이미지 수준) |
| **성능** | HTML5 Canvas 기반, 고성능 |
| **최적화** | 금융 데이터 전용 |
| **플러그인** | 커스텀 플러그인 지원 |

## 🚀 설치 방법

### CDN (권장)
```html
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
```

### NPM
```bash
npm install lightweight-charts
```

## 📈 기본 사용법

### 1. 캔들스틱 차트
```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
    <div id="chart" style="width: 800px; height: 400px;"></div>
    
    <script>
        const chart = LightweightCharts.createChart(document.getElementById('chart'), {
            layout: {
                background: { color: '#1a1a2e' },
                textColor: '#d1d4dc',
            },
            grid: {
                vertLines: { color: '#2a2a3e' },
                horzLines: { color: '#2a2a3e' },
            },
            rightPriceScale: {
                borderColor: '#2a2a3e',
            },
            timeScale: {
                borderColor: '#2a2a3e',
            },
        });
        
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        
        // 데이터 설정
        candlestickSeries.setData([
            { time: '2024-01-01', open: 100, high: 105, low: 98, close: 103 },
            { time: '2024-01-02', open: 103, high: 108, low: 102, close: 106 },
            // ... 더 많은 데이터
        ]);
        
        chart.timeScale().fitContent();
    </script>
</body>
</html>
```

### 2. 라인 차트 + 볼륨
```javascript
const chart = LightweightCharts.createChart(container, {
    layout: { background: { color: '#ffffff' }, textColor: '#333' },
});

// 라인 시리즈
const lineSeries = chart.addLineSeries({
    color: '#2962FF',
    lineWidth: 2,
});

// 볼륨 히스토그램
const volumeSeries = chart.addHistogramSeries({
    color: '#26a69a',
    priceFormat: { type: 'volume' },
    priceScaleId: '',
});

volumeSeries.priceScale().applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
});
```

### 3. 목표가/손절가 표시
```javascript
// 수평선 플러그인으로 목표가/손절가 표시
const targetPriceLine = lineSeries.createPriceLine({
    price: 150000,  // 목표가
    color: '#26a69a',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'Target',
});

const stopLossLine = lineSeries.createPriceLine({
    price: 120000,  // 손절가
    color: '#ef5350',
    lineWidth: 2,
    lineStyle: LightweightCharts.LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'Stop Loss',
});
```

## 🎨 테마 설정

### 다크 테마
```javascript
const darkTheme = {
    layout: {
        background: { type: 'solid', color: '#131722' },
        textColor: '#d1d4dc',
    },
    grid: {
        vertLines: { color: '#2a2e39' },
        horzLines: { color: '#2a2e39' },
    },
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
    },
    rightPriceScale: {
        borderColor: '#2a2e39',
    },
    timeScale: {
        borderColor: '#2a2e39',
    },
};
```

### 라이트 테마
```javascript
const lightTheme = {
    layout: {
        background: { type: 'solid', color: '#ffffff' },
        textColor: '#333',
    },
    grid: {
        vertLines: { color: '#e0e0e0' },
        horzLines: { color: '#e0e0e0' },
    },
};
```

## 📊 한국 주식 데이터 포맷

```javascript
// KRX 데이터 포맷 변환
function convertKRXData(krxData) {
    return krxData.map(d => ({
        time: d.date.replace(/-/g, ''),  // 2024-01-01 → 20240101
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
        volume: d.volume,
    }));
}

// 예시 데이터
const sampleData = [
    { time: '20260409', open: 70200, high: 71100, low: 69800, close: 70800, volume: 12500000 },
    { time: '20260408', open: 69800, high: 70500, low: 69500, close: 70200, volume: 11800000 },
    // ...
];
```

## 🔧 실전 적용 예시

### 스캐너 리포트 통합
```html
<!-- 종목 카드 클릭 시 모달 차트 -->
<div id="stock-modal" class="modal">
    <div class="modal-content">
        <div id="chart-container"></div>
        <div class="target-levels">
            <span class="target">Target: 85,000 (+20%)</span>
            <span class="stop-loss">Stop: 62,000 (-12%)</span>
        </div>
    </div>
</div>

<script>
function showStockChart(stockCode, stockData) {
    const container = document.getElementById('chart-container');
    container.innerHTML = '';  // 기존 차트 제거
    
    const chart = LightweightCharts.createChart(container, {
        width: 700,
        height: 400,
        ...darkTheme,
    });
    
    const series = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
    });
    
    series.setData(stockData);
    
    // 목표가/손절가 라인
    const entryPrice = stockData[stockData.length - 1].close;
    const targetPrice = entryPrice * 1.20;
    const stopPrice = entryPrice * 0.88;
    
    series.createPriceLine({
        price: targetPrice,
        color: '#26a69a',
        lineWidth: 2,
        title: 'Target +20%',
    });
    
    series.createPriceLine({
        price: stopPrice,
        color: '#ef5350',
        lineWidth: 2,
        title: 'Stop -12%',
    });
    
    series.createPriceLine({
        price: entryPrice,
        color: '#ffd700',
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dotted,
        title: 'Entry',
    });
    
    chart.timeScale().fitContent();
}
</script>
```

## 📈 고급 기능

### 1. 마커 표시 (매수/매도 신호)
```javascript
series.setMarkers([
    {
        time: '20260401',
        position: 'belowBar',
        color: '#26a69a',
        shape: 'arrowUp',
        text: 'BUY',
        size: 2,
    },
    {
        time: '20260405',
        position: 'aboveBar',
        color: '#ef5350',
        shape: 'arrowDown',
        text: 'SELL',
        size: 2,
    },
]);
```

### 2. 복수 시리즈 (이동평균선)
```javascript
// 캔들스틱
const candleSeries = chart.addCandlestickSeries();
candleSeries.setData(candleData);

// 20일 이동평균
const ma20Series = chart.addLineSeries({
    color: '#2962FF',
    lineWidth: 1,
    title: 'MA20',
});
ma20Series.setData(ma20Data);

// 60일 이동평균
const ma60Series = chart.addLineSeries({
    color: '#FF6D00',
    lineWidth: 1,
    title: 'MA60',
});
ma60Series.setData(ma60Data);
```

### 3. 실시간 업데이트
```javascript
// 새 데이터 도착 시
series.update({
    time: '20260409',
    open: 70200,
    high: 71100,
    low: 69800,
    close: 70800,
});
```

## 🎯 현재 프로젝트 적용 계획

### 1단계: 기본 통합
- `mv_integrated_report.py`에 차트 라이브러리 교체
- 캔들스틱 + 볼륨 차트 구현

### 2단계: 고급 기능
- 목표가/손절가 수평선 표시
- 이동평균선 오버레이
- 매수/매도 마커 표시

### 3단계: 실시간 차트
- WebSocket 연동
- 실시간 가격 업데이트

## 📚 참고 자료

- [공식 문서](https://tradingview.github.io/lightweight-charts/)
- [예제 모음](https://tradingview.github.io/lightweight-charts/plugin-examples/)
- [GitHub](https://github.com/tradingview/lightweight-charts)
