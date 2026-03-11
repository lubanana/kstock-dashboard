<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>O'Neil + Minervini Combined Strategy Report</title>
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }
        
        html {
            font-size: 16px;
        }
        
        @media (max-width: 480px) {
            html {
                font-size: 14px;
            }
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            padding: 0;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
        }
        
        @media (min-width: 768px) {
            .container {
                max-width: 1400px;
                border-radius: 20px;
                margin: 20px auto;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem 1rem;
            text-align: center;
        }
        
        .header h1 { 
            font-size: 1.8rem; 
            margin-bottom: 0.5rem;
            font-weight: 700;
        }
        
        .header p { 
            font-size: 1rem; 
            opacity: 0.9;
            margin-bottom: 0.3rem;
        }
        
        @media (min-width: 768px) {
            .header h1 {
                font-size: 2.5rem;
            }
            .header p {
                font-size: 1.2rem;
            }
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.8rem;
            padding: 1rem;
            background: #f8f9fa;
        }
        
        @media (min-width: 768px) {
            .stats-grid {
                grid-template-columns: repeat(4, 1fr);
                gap: 1.2rem;
                padding: 1.5rem;
            }
        }
        
        .stat-card {
            background: white;
            padding: 1rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .stat-card h3 { 
            color: #667eea; 
            font-size: 1.8rem; 
            margin-bottom: 0.3rem;
            font-weight: 700;
        }
        
        .stat-card p { 
            color: #666; 
            font-size: 0.85rem;
        }
        
        .stat-card.highlight {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        
        .stat-card.highlight h3 { 
            color: white; 
            font-size: 2rem;
        }
        
        .section { 
            padding: 1.2rem;
        }
        
        @media (min-width: 768px) {
            .section {
                padding: 1.5rem 2rem;
            }
        }
        
        .section h2 {
            color: #333;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 3px solid #667eea;
            font-size: 1.3rem;
        }
        
        @media (min-width: 768px) {
            .section h2 {
                font-size: 1.5rem;
            }
        }
        
        .methodology {
            background: #f8f9fa;
            padding: 1.2rem;
            border-radius: 12px;
            margin: 1rem 0;
        }
        
        .methodology h3 { 
            color: #667eea; 
            margin-bottom: 0.8rem;
            font-size: 1.1rem;
        }
        
        .methodology ul { 
            margin-left: 1.2rem; 
            line-height: 1.8; 
        }
        
        .methodology li {
            margin: 0.5rem 0;
            font-size: 0.95rem;
        }
        
        .combo-badge {
            display: inline-block;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 8px;
            font-size: 0.7rem;
            font-weight: bold;
            margin-left: 0.3rem;
            vertical-align: middle;
        }
        
        .table-container {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin: 1rem 0;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        table {
            width: 100%;
            min-width: 700px;
            border-collapse: collapse;
            font-size: 0.85rem;
            background: white;
        }
        
        @media (min-width: 768px) {
            table {
                font-size: 0.95rem;
            }
        }
        
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.8rem 0.5rem;
            text-align: left;
            font-weight: 600;
            white-space: nowrap;
            position: sticky;
            top: 0;
        }
        
        @media (min-width: 768px) {
            th {
                padding: 1rem 0.8rem;
            }
        }
        
        td { 
            padding: 0.7rem 0.5rem; 
            border-bottom: 1px solid #eee;
            white-space: nowrap;
        }
        
        @media (min-width: 768px) {
            td {
                padding: 0.8rem;
            }
        }
        
        tr:hover { 
            background: #f5f5f5; 
        }
        
        tr.combo { 
            background: #fff5f5;
        }
        
        .score-high { 
            color: #e74c3c; 
            font-weight: bold; 
        }
        
        .score-medium { 
            color: #f39c12; 
            font-weight: bold; 
        }
        
        .strategy-oneil { 
            color: #3498db; 
        }
        
        .strategy-minervini { 
            color: #9b59b6; 
        }
        
        .strategy-combo { 
            color: #e74c3c; 
            font-weight: bold; 
        }
        
        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.8rem;
            margin-bottom: 1rem;
            padding: 0.8rem;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 0.3rem;
            font-size: 0.85rem;
        }
        
        .legend-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .legend-dot.combo {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .legend-dot.oneil {
            background: #3498db;
        }
        
        .legend-dot.minervini {
            background: #9b59b6;
        }
        
        .footer {
            background: #f8f9fa;
            padding: 1.5rem 1rem;
            text-align: center;
            color: #666;
            font-size: 0.85rem;
        }
        
        .card-view {
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
        }
        
        @media (min-width: 768px) {
            .card-view {
                display: none;
            }
        }
        
        .stock-card {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        .stock-card.combo {
            border-left-color: #f5576c;
            background: #fff5f5;
        }
        
        .stock-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
        }
        
        .stock-card-header h3 {
            font-size: 1.1rem;
            margin: 0;
        }
        
        .stock-card-body {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
            font-size: 0.9rem;
        }
        
        .stock-card-body div {
            display: flex;
            justify-content: space-between;
        }
        
        .stock-card-body span:first-child {
            color: #666;
        }
        
        .table-view {
            display: none;
        }
        
        @media (min-width: 768px) {
            .table-view {
                display: block;
            }
        }
        
        .scroll-hint {
            text-align: center;
            padding: 0.5rem;
            color: #999;
            font-size: 0.8rem;
            display: block;
        }
        
        @media (min-width: 768px) {
            .scroll-hint {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Combined Strategy</h1>
            <p>O'Neil CANSLIM + Minervini SEPA</p>
            <p>{datetime.now().strftime('%Y-%m-%d')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{total}</h3>
                <p>총 신호</p>
            </div>
            <div class="stat-card highlight">
                <h3>{combo_count}</h3>
                <p>🔥 복합</p>
            </div>
            <div class="stat-card">
                <h3>{oneil_only}</h3>
                <p>오닐</p>
            </div>
            <div class="stat-card">
                <h3>{minervini_only}</h3>
                <p>미니버니</p>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 전략 설명</h2>
            
            <div class="methodology">
                <h3>🔵 O'Neil CANSLIM</h3>
                <ul>
                    <li>52주 신고가 + 거래량 급증</li>
                    <li>이동평균선 정렬</li>
                    <li>상대강도 상위 10%</li>
                </ul>
            </div>
            
            <div class="methodology">
                <h3>🟣 Minervini SEPA</h3>
                <ul>
                    <li>Trend Template 통과</li>
                    <li>VCP (변동성 수축)</li>
                    <li>박스권 돌파</li>
                </ul>
            </div>
        </div>
        
        <div class="section">
            <h2>🏆 TOP 50</h2>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-dot combo"></div>
                    <span>복합 전략</span>
                </div>
                <div class="legend-item">
                    <div class="legend-dot oneil"></div>
                    <span>오닐</span>
                </div>
                <div class="legend-item">
                    <div class="legend-dot minervini"></div>
                    <span>미니버니</span>
                </div>
            </div>
            
            <p class="scroll-hint">← 좌우로 스와이프하여 더 보기 →</p>
            
            <!-- 모바일 카드 뷰 -->
            <div class="card-view">
                {mobile_cards}
            </div>
            
            <!-- 데스크톱 테이블 뷰 -->
            <div class="table-view">
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>순위</th>
                                <th>종목</th>
                                <th>전략</th>
                                <th>점수</th>
                                <th>신호</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2026 KStock Analyzer</p>
            <p>⚠️ 투자 참고용 (본인 책임)</p>
        </div>
    </div>
</body>
</html>
