"""
V2 Core - Report Engine
HTML 리포트 생성기
"""
from datetime import datetime
from typing import List, Dict, Any, Optional


class Signal:
    """Dummy Signal class for type hints (actual implementation in strategy_base)"""
    pass


class ReportEngine:
    """HTML 리포트 생성 엔진"""
    
    # 테마 색상
    COLORS = {
        'primary': '#e94560',
        'secondary': '#0f3460',
        'accent': '#533483',
        'success': '#4ecca3',
        'warning': '#ffaa00',
        'danger': '#ff4444',
        'bg_dark': '#1a1a2e',
        'bg_card': 'rgba(255,255,255,0.05)',
        'text': '#eee',
        'text_secondary': '#aaa'
    }
    
    def __init__(self, title: str = "스캔 리포트"):
        self.title = title
    
    def generate(self, 
                strategies: List[Dict[str, Any]],
                date: str,
                summary_stats: Dict[str, Any]) -> str:
        """
        통합 리포트 생성
        
        Args:
            strategies: [{'name': str, 'signals': List[Signal], 'stats': dict}, ...]
            date: 기준일
            summary_stats: 종합 통계
        """
        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title} - {date}</title>
    <style>{self._get_css()}</style>
</head>
<body>
    <div class="container">
        {self._render_header(date, summary_stats)}
        {self._render_summary_cards(summary_stats)}
        {self._render_strategies(strategies)}
        {self._render_footer()}
    </div>
</body>
</html>"""
        return html
    
    def _get_css(self) -> str:
        """CSS 스타일"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(90deg, #0f3460, #533483);
            border-radius: 15px;
            margin-bottom: 30px;
        }
        h1 { font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { font-size: 1.2em; opacity: 0.9; }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card-value { font-size: 2.5em; font-weight: bold; color: #e94560; margin: 10px 0; }
        .card-label { color: #aaa; font-size: 0.9em; }
        .section {
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .section h2 { color: #e94560; margin-bottom: 20px; border-bottom: 2px solid #e94560; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.95em; }
        th { background: rgba(233, 69, 96, 0.2); padding: 12px; text-align: left; border-bottom: 2px solid #e94560; }
        td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        tr:hover { background: rgba(255,255,255,0.05); }
        .badge { display: inline-block; padding: 5px 12px; border-radius: 15px; font-size: 0.85em; font-weight: bold; }
        .badge-buy { background: #4ecca3; color: #1a1a2e; }
        .badge-hold { background: #ffaa00; color: #1a1a2e; }
        .badge-sell { background: #ff4444; color: white; }
        .change-up { color: #4ecca3; font-weight: bold; }
        .change-down { color: #ff4444; font-weight: bold; }
        .score-high { color: #4ecca3; font-weight: bold; }
        .score-med { color: #ffaa00; }
        .score-low { color: #aaa; }
        .strategy-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .footer { text-align: center; padding: 30px; color: #888; border-top: 1px solid rgba(255,255,255,0.1); margin-top: 30px; }
        """
    
    def _render_header(self, date: str, stats: Dict) -> str:
        """헤더 렌더링"""
        return f"""
        <header>
            <h1>📊 {self.title}</h1>
            <div class="subtitle">{date} | KOSPI/KOSDAQ 시장 분석</div>
        </header>
        """
    
    def _render_summary_cards(self, stats: Dict) -> str:
        """요약 카드 렌더링"""
        cards = [
            ('분석 종목', stats.get('total_stocks', 0)),
            ('총 신호', stats.get('total_signals', 0)),
            ('매수 신호', stats.get('buy_signals', 0)),
            ('평균 점수', f"{stats.get('avg_score', 0):.1f}")
        ]
        
        html = '<div class="summary-cards">'
        for label, value in cards:
            html += f'''
            <div class="card">
                <div class="card-label">{label}</div>
                <div class="card-value">{value}</div>
            </div>
            '''
        html += '</div>'
        return html
    
    def _render_strategies(self, strategies: List[Dict]) -> str:
        """전략별 섹션 렌더링"""
        html = ""
        for strat in strategies:
            name = strat['name']
            signals = strat['signals']
            stats = strat['stats']
            
            html += f'<div class="section"><h2>🎯 {name}</h2>'
            html += f'<p>총 {len(signals)}개 신호 | 평균 점수: {stats.get("avg_score", 0):.1f}</p>'
            
            if signals:
                html += self._render_signal_table(signals)
            else:
                html += '<p>선정된 종목이 없습니다.</p>'
            
            html += '</div>'
        
        return html
    
    def _render_signal_table(self, signals: List[Signal]) -> str:
        """신호 테이블 렌더링"""
        html = """
        <table>
            <thead>
                <tr>
                    <th>순위</th>
                    <th>종목</th>
                    <th>신호</th>
                    <th>점수</th>
                    <th>주요 사유</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for i, sig in enumerate(signals[:20], 1):  # Top 20
            badge_class = f"badge-{sig.signal_type}"
            score_class = "score-high" if sig.score >= 80 else "score-med" if sig.score >= 60 else "score-low"
            reason_text = sig.reason[0] if sig.reason else ""
            
            html += f"""
            <tr>
                <td>{i}</td>
                <td><strong>{sig.name}</strong> ({sig.code})</td>
                <td><span class="badge {badge_class}">{sig.signal_type.upper()}</span></td>
                <td class="{score_class}">{sig.score:.1f}</td>
                <td>{reason_text}</td>
            </tr>
            """
        
        html += "</tbody></table>"
        return html
    
    def _render_footer(self) -> str:
        """푸터 렌더링"""
        return f"""
        <div class="footer">
            <p>{self.title} | 생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                본 리포트는 투자 참고 자료이며, 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.
            </p>
        </div>
        """
