#!/bin/bash
# TradingView Lightweight Charts 설치 스크립트
# =============================================

echo "=========================================="
echo "📦 TradingView Lightweight Charts 설치"
echo "=========================================="

# 1. Node.js 버전 확인
echo -e "\n1️⃣ Node.js 버전 확인..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js가 설치되어 있지 않습니다"
    echo "   설치 방법: https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "   ✅ Node.js 버전: $NODE_VERSION"

# 2. npm 버전 확인
echo -e "\n2️⃣ npm 버전 확인..."
NPM_VERSION=$(npm --version)
echo "   ✅ npm 버전: $NPM_VERSION"

# 3. 프로젝트 폴더 생성
echo -e "\n3️⃣ 프로젝트 폴더 생성..."
PROJECT_DIR="tv-charts-project"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

echo "   ✅ 폴더 생성: $PROJECT_DIR/"

# 4. package.json 생성
echo -e "\n4️⃣ package.json 생성..."
cat > package.json << 'EOF'
{
  "name": "tv-charts-project",
  "version": "1.0.0",
  "description": "TradingView Lightweight Charts Project",
  "main": "index.js",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "serve": "python3 -m http.server 8080"
  },
  "dependencies": {
    "lightweight-charts": "^4.1.0"
  },
  "devDependencies": {
    "vite": "^5.0.0"
  }
}
EOF
echo "   ✅ package.json 생성 완료"

# 5. 라이브러리 설치
echo -e "\n5️⃣ TradingView Lightweight Charts 설치..."
npm install
echo "   ✅ 설치 완료"

# 6. 기본 파일 구조 생성
echo -e "\n6️⃣ 프로젝트 구조 생성..."

# src 폴더
mkdir -p src

# 메인 JS 파일
cat > src/main.js << 'EOF'
import { createChart, CandlestickSeries, LineSeries } from 'lightweight-charts';

// 차트 생성
const chart = createChart(document.getElementById('chart'), {
    layout: {
        background: { color: '#131722' },
        textColor: '#d1d4dc',
    },
    grid: {
        vertLines: { color: '#2a2e39' },
        horzLines: { color: '#2a2e39' },
    },
    width: 800,
    height: 400,
});

// 캔들스틱 시리즈
const candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
});

// 샘플 데이터 (KRX 형식)
const data = [
    { time: '20260401', open: 65000, high: 66500, low: 64500, close: 66000 },
    { time: '20260402', open: 66000, high: 67800, low: 65500, close: 67500 },
    { time: '20260403', open: 67500, high: 68200, low: 66800, close: 67000 },
    { time: '20260404', open: 67000, high: 69500, low: 66500, close: 69000 },
    { time: '20260407', open: 69000, high: 71200, low: 68500, close: 70800 },
    { time: '20260408', open: 70800, high: 72500, low: 70200, close: 72000 },
    { time: '20260409', open: 72000, high: 73500, low: 71500, close: 73000 },
];

candleSeries.setData(data);

// 목표가/손절가 라인
const entryPrice = 70200;
const targetPrice = 85000;
const stopPrice = 62000;

candleSeries.createPriceLine({
    price: entryPrice,
    color: '#ffd700',
    lineWidth: 1,
    lineStyle: 2, // Dashed
    axisLabelVisible: true,
    title: `Entry ${entryPrice.toLocaleString()}`,
});

candleSeries.createPriceLine({
    price: targetPrice,
    color: '#26a69a',
    lineWidth: 2,
    lineStyle: 2,
    axisLabelVisible: true,
    title: `Target ${targetPrice.toLocaleString()}`,
});

candleSeries.createPriceLine({
    price: stopPrice,
    color: '#ef5350',
    lineWidth: 2,
    lineStyle: 2,
    axisLabelVisible: true,
    title: `Stop ${stopPrice.toLocaleString()}`,
});

chart.timeScale().fitContent();

console.log('✅ TradingView chart loaded');
EOF

# HTML 파일
cat > index.html << 'EOF'
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradingView Charts - Sample</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #131722;
            color: #d1d4dc;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            padding: 20px;
            border-bottom: 1px solid #2a2e39;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .chart-container {
            background: #1a1d29;
            border: 1px solid #2a2e39;
            border-radius: 8px;
            padding: 20px;
            margin: 0 auto;
            max-width: 900px;
        }
        
        #chart {
            width: 100%;
            height: 400px;
        }
        
        .levels {
            display: flex;
            gap: 20px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #2a2e39;
        }
        
        .level {
            padding: 10px 20px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
        }
        
        .level.entry {
            background: rgba(255, 215, 0, 0.2);
            color: #ffd700;
        }
        
        .level.target {
            background: rgba(38, 166, 154, 0.2);
            color: #26a69a;
        }
        
        .level.stop {
            background: rgba(239, 83, 80, 0.2);
            color: #ef5350;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📈 TradingView Lightweight Charts</h1>
        <p>Sample Chart with Target/Stop Loss Lines</p>
    </div>
    
    <div class="chart-container">
        <div id="chart"></div>
        <div class="levels">
            <span class="level entry">Entry: 70,200</span>
            <span class="level target">Target: 85,000 (+21.1%)</span>
            <span class="level stop">Stop: 62,000 (-11.7%)</span>
        </div>
    </div>
    
    <script type="module" src="/src/main.js"></script>
</body>
</html>
EOF

# Vite 설정
cat > vite.config.js << 'EOF'
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
EOF

echo "   ✅ 프로젝트 구조 생성 완료"

# 7. 완료 메시지
echo -e "\n=========================================="
echo "✅ 설치 완료!"
echo "=========================================="
echo -e "\n📂 프로젝트 위치: $(pwd)"
echo -e "\n🚀 실행 방법:"
echo "   1. 개발 서버: npm run dev"
echo "   2. 정적 서버: npm run serve"
echo "   3. 프로덕션 빌드: npm run build"
echo -e "\n📚 파일 구조:"
tree -L 2 2>/dev/null || find . -maxdepth 2 -type f | head -20
echo -e "\n💡 다음 단계:"
echo "   cd $PROJECT_DIR"
echo "   npm run dev"
echo "=========================================="
