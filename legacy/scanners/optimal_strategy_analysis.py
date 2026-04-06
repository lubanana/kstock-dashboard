#!/usr/bin/env python3
"""
실제 페이퍼트레이딩 결과 기반 최적 전략 도출
"""

import json

# 실제 페이퍼트레이딩 결과
trades = [
    {'name': '제룡전기', 'return': -4.01, 'exit': '보유만기'},
    {'name': '파크시스템스', 'return': -3.04, 'exit': '보유만기'},
    {'name': '넥스틴', 'return': -0.61, 'exit': '보유만기'},
    {'name': '서부T&D', 'return': -3.20, 'exit': '보유만기'},
    {'name': '삼보산업', 'return': -5.72, 'exit': '보유만기'},
    {'name': '삼미금속', 'return': +11.18, 'exit': '보유만기'},
    {'name': '아난티', 'return': -1.22, 'exit': '보유만기'},
    {'name': '한미반도체', 'return': +12.41, 'exit': '보유만기'},
]

print("=" * 70)
print("🔥 실제 페이퍼트레이딩 분석 - 최적 전략 도출")
print("=" * 70)

# 현재 결과 분석
wins = [t for t in trades if t['return'] > 0]
losses = [t for t in trades if t['return'] <= 0]

print("\n📊 현재 결과 (7일 보유, 고정 손절 없음)")
print(f"   승률: {len(wins)}/{len(trades)} = {len(wins)/len(trades)*100:.1f}%")
print(f"   수익 종목: {[t['name'] for t in wins]}")
print(f"   손실 종목: {[t['name'] for t in losses]}")

# 시뮬레이션: 다양한 전략 적용
print("\n" + "=" * 70)
print("📊 전략별 시뮬레이션")
print("=" * 70)

strategies = [
    {
        'name': '전략A: 고정 손절 -5%',
        'stop': -5.0,
        'target': None,
        'early_exit': True
    },
    {
        'name': '전략B: 트레일링 스톱 (수익 50% 보장)',
        'stop': None,
        'trail': 0.5,
        'early_exit': False
    },
    {
        'name': '전략C: 분할 익절 (5% 익절 50%, 나머지 보유)',
        'partial': 5.0,
        'early_exit': True
    },
    {
        'name': '전략D: 목표가 10% 도달 시 트레일링',
        'target': 10.0,
        'trail_after_target': True,
        'early_exit': True
    },
    {
        'name': '전략E: 3일 단기 보유',
        'hold_days': 3,
        'early_exit': False
    },
]

results = []

for strat in strategies:
    print(f"\n📈 {strat['name']}")
    print("-" * 50)
    
    simulated = []
    
    for trade in trades:
        original_return = trade['return']
        
        # 시뮬레이션 로직
        if 'stop' in strat and strat['stop'] is not None:
            # 고정 손절
            if original_return <= strat['stop']:
                new_return = strat['stop']
                reason = '손절'
            else:
                new_return = original_return
                reason = trade['exit']
        
        elif 'trail' in strat:
            # 트레일링 스톱
            if original_return > 0:
                # 수익 시 본전 + 50% 보장
                new_return = max(original_return * strat['trail'], 0)
                reason = '트레일링'
            else:
                new_return = original_return
                reason = trade['exit']
        
        elif 'partial' in strat:
            # 분할 익절
            if original_return >= strat['partial']:
                # 50%는 5%에서 익절, 나머지 50%는 보유
                new_return = (strat['partial'] * 0.5) + (original_return * 0.5)
                reason = '분할익절'
            elif original_return <= -5:
                new_return = -5
                reason = '손절'
            else:
                new_return = original_return
                reason = trade['exit']
        
        elif 'target' in strat:
            # 목표가 도달 후 트레일링
            if original_return >= strat['target']:
                new_return = strat['target'] + (original_return - strat['target']) * 0.3
                reason = '목표+트레일'
            else:
                new_return = original_return
                reason = trade['exit']
        
        elif 'hold_days' in strat:
            # 단기 보유
            # 3일 후 수익률 (실제 7일의 절반으로 가정)
            new_return = original_return * 0.6  # 단기는 변동성 작음
            reason = f"{strat['hold_days']}일청산"
        
        else:
            new_return = original_return
            reason = trade['exit']
        
        simulated.append({
            'name': trade['name'],
            'original': original_return,
            'simulated': round(new_return, 2),
            'reason': reason
        })
    
    # 통계
    sim_returns = [s['simulated'] for s in simulated]
    sim_wins = [r for r in sim_returns if r > 0]
    
    win_rate = len(sim_wins) / len(sim_returns) * 100
    total = sum(sim_returns)
    avg = sum(sim_returns) / len(sim_returns)
    
    print(f"   승률: {win_rate:.1f}%")
    print(f"   총수익: {total:+.2f}%")
    print(f"   평균: {avg:+.2f}%")
    
    for s in simulated:
        emoji = '📈' if s['simulated'] > 0 else '📉' if s['simulated'] < 0 else '➖'
        print(f"      {emoji} {s['name']}: {s['simulated']:+.2f}% (원래 {s['original']:+.2f}%, {s['reason']})")
    
    results.append({
        'name': strat['name'],
        'win_rate': win_rate,
        'total_return': total,
        'avg_return': avg,
        'details': simulated
    })

# 최종 비교
print("\n" + "=" * 70)
print("📊 전략별 비교표")
print("=" * 70)

results.sort(key=lambda x: x['total_return'], reverse=True)

print(f"\n{'순위':<4} {'전략명':<30} {'승률':<8} {'평균':<10} {'총수익':<10}")
print("-" * 70)

for i, r in enumerate(results, 1):
    medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else '  '
    print(f"{medal} {i:<2} {r['name']:<30} {r['win_rate']:<8.1f} {r['avg_return']:<10.2f} {r['total_return']:<10.2f}")

# 원래 결과도 표시
original_total = sum(t['return'] for t in trades)
original_avg = original_total / len(trades)
print(f"\n📌 원래 결과 (7일 보유, 무조건 보유)")
print(f"   승률: {len(wins)/len(trades)*100:.1f}%")
print(f"   평균: {original_avg:+.2f}%")
print(f"   총수익: {original_total:+.2f}%")

# 최종 권장
print("\n" + "=" * 70)
print("💡 최종 권장 전략")
print("=" * 70)

if results:
    best = results[0]
    print(f"\n🏆 추천: {best['name']}")
    print(f"   - 총 수익률: {best['total_return']:+.2f}%")
    print(f"   - 승률: {best['win_rate']:.1f}%")
    print(f"   - 거래 횟수: 8회")

print("\n📋 다중 전략 병행 제안:")
print("""
[포트폴리오 구성 - 월간 리밸런싱]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 추세 추종 (40%): 7일 보유, -5% 손절, 1:3 목표
   → MA 크로스, ATR 브레이크아웃
   
2. 고승률 반등 (30%): 5일 보유, -3% 손절, 1:1.5 목표  
   → RSI2 과매도 반등
   
3. 단타 모멘텀 (20%): 3일 보유, -4% 손절, 1:2 목표
   → 15분봉 120선 전환존
   
4. 장기 추세 (10%): 15일 보유, -7% 손절, 1:5 목표
   → 돈키안 채널 돌파
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[리스크 관리]
- 포지션당 최대 15% (총 5종목)
- 일일 손실 한도: -2%
- 연속 3회 손실 시 해당 전략 일시 중단
""")

# 저장
with open('docs/optimal_strategy_recommendation.json', 'w', encoding='utf-8') as f:
    json.dump({
        'paper_trading_results': trades,
        'strategy_simulations': results,
        'recommendation': {
            'best_strategy': results[0]['name'] if results else None,
            'portfolio_allocation': {
                'trend_following': 0.4,
                'mean_reversion': 0.3,
                'short_term_momentum': 0.2,
                'long_term_trend': 0.1
            }
        }
    }, f, ensure_ascii=False, indent=2)

print("\n✅ 결과 저장: docs/optimal_strategy_recommendation.json")
