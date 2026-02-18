# -*- coding: utf-8 -*-
"""
균형 포트폴리오 ML 분석 (한국장)
Titan KR 분석 결과에서 자동으로 70점+ 종목을 추출하여 ML 예측 실행
"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

from ml_predictor import EnsemblePredictor, train_and_predict, set_kr_provider
from project_titan_kr import TitanKRAnalyzer, KR_GROWTH_CODES, KR_VALUE_CODES
from kr_data_provider import KRDataProvider

# 한국장 최소 점수 (US 75 → KR 70)
MIN_SCORE = 70

# KRDataProvider 초기화 (DART API 키가 있으면 환경변수에서 읽기)
dart_key = os.environ.get('DART_API_KEY', None)
provider = KRDataProvider(dart_api_key=dart_key)
set_kr_provider(provider)


def scan_titan_scores(min_score=MIN_SCORE):
    """Titan KR 분석으로 70점+ 종목 자동 추출 (Growth/Value 분리)"""
    analyzer = TitanKRAnalyzer(dart_api_key=dart_key)
    analyzer.data_provider = provider  # 프로바이더 공유
    growth_list = []
    value_list = []

    # 성장주 스캔
    codes_growth = list(set(KR_GROWTH_CODES))
    print(f"📊 Titan 성장주 스캔 중... ({len(codes_growth)}개)")
    analyzer.analysis_mode = 'growth'
    for i, code in enumerate(codes_growth):
        try:
            r = analyzer._analyze_single_stock(code)
            if r and r['score'] >= min_score:
                growth_list.append((code, r['score']))
        except:
            pass
        if i % 30 == 0 and i > 0:
            print(f"   ... {i}/{len(codes_growth)} 스캔 완료")

    # 가치주 스캔
    codes_value = list(set(KR_VALUE_CODES))
    print(f"📊 Titan 가치주 스캔 중... ({len(codes_value)}개)")
    analyzer.analysis_mode = 'value'
    for i, code in enumerate(codes_value):
        try:
            r = analyzer._analyze_single_stock(code)
            if r and r['score'] >= min_score:
                value_list.append((code, r['score']))
        except:
            pass
        if i % 30 == 0 and i > 0:
            print(f"   ... {i}/{len(codes_value)} 스캔 완료")

    growth_list.sort(key=lambda x: x[1], reverse=True)
    value_list.sort(key=lambda x: x[1], reverse=True)

    g_codes = [c for c, s in growth_list]
    v_codes = [c for c, s in value_list]

    print(f"\n✅ Titan 스캔 완료:")
    print(f"   Growth 70+: {len(g_codes)}개 - {g_codes[:10]}{'...' if len(g_codes) > 10 else ''}")
    print(f"   Value  70+: {len(v_codes)}개 - {v_codes[:10]}{'...' if len(v_codes) > 10 else ''}")

    return g_codes, v_codes


# === Titan 스캔으로 70+ 종목 자동 추출 ===
GROWTH_70_PLUS, VALUE_70_PLUS = scan_titan_scores()
ALL_70_PLUS = GROWTH_70_PLUS + VALUE_70_PLUS

print("\n" + "=" * 70)
print("🚀 균형 포트폴리오 ML 분석 (Titan KR 자동 연동)")
print(f"📊 분석 대상: {len(ALL_70_PLUS)}개 종목 (70점+)")
print(f"   - Growth: {len(GROWTH_70_PLUS)}개 (기술적 분석)")
print(f"   - Value: {len(VALUE_70_PLUS)}개 (펀더멘털 + 기술적 분석)")
print("=" * 70)

# ML 예측 실행 - 성장주와 가치주 분리
print("\n📈 성장주 ML 분석 중...")
growth_results = train_and_predict(GROWTH_70_PLUS, value_mode=False)

print("\n💎 가치주 ML 분석 중 (펀더멘털 피처 포함)...")
value_results = train_and_predict(VALUE_70_PLUS, value_mode=True)

# 결과 병합
results = growth_results + value_results

# 결과 정렬 (신뢰도 기준)
results_sorted = sorted(results, key=lambda x: x.get('confidence', 0), reverse=True)

print("\n" + "=" * 70)
print("📊 ML 예측 결과 (신뢰도 순)")
print("=" * 70)
print(f"{'종목':<10} {'현재가':>12} {'Signal':<18} {'Conf':>8} {'Type':<7} {'PER':>7} {'DIV':>6} {'Value':>6}")
print("-" * 85)

strong_buy = []
buy = []
hold = []
avoid = []

for r in results_sorted:
    code = r['ticker']
    price = r.get('price', 0)
    signal = r.get('signal', 'N/A')
    conf = r.get('confidence', 0)
    category = "Growth" if code in GROWTH_70_PLUS else "Value"

    pe_ratio = r.get('pe_ratio', 0) or 0
    div_yield = r.get('dividend_yield', 0) or 0
    value_score = r.get('value_score', 0) or 0

    pe_str = f"{pe_ratio:.1f}" if pe_ratio > 0 else "-"
    if div_yield > 1:
        div_str = f"{div_yield:.1f}%"
    elif div_yield > 0:
        div_str = f"{div_yield*100:.1f}%"
    else:
        div_str = "-"
    val_str = f"{value_score:.2f}" if value_score > 0 else "-"

    print(f"{code:<10} ₩{int(price):>10,} {signal:<18} {conf:>7.1%} {category:<7} {pe_str:>7} {div_str:>6} {val_str:>6}")

    if 'Strong' in signal or 'Buy' in signal:
        if conf >= 0.7:
            strong_buy.append(r)
        elif conf >= 0.5:
            buy.append(r)
        else:
            hold.append(r)
    elif 'Hold' in signal:
        hold.append(r)
    else:
        avoid.append(r)

print("\n" + "=" * 70)
print("🎯 공격적 포트폴리오 추천 (ML 기반)")
print("=" * 70)

print(f"\n✅ Strong Buy (신뢰도 70%+): {len(strong_buy)}개")
for r in strong_buy:
    print(f"   - {r['ticker']}: ₩{int(r['price']):,} | {r['signal']} | 신뢰도 {r['confidence']:.1%}")

print(f"\n📈 Buy (신뢰도 50-70%): {len(buy)}개")
for r in buy:
    print(f"   - {r['ticker']}: ₩{int(r['price']):,} | {r['signal']} | 신뢰도 {r['confidence']:.1%}")

print(f"\n⏸️ Hold: {len(hold)}개")
for r in hold:
    print(f"   - {r['ticker']}: ₩{int(r['price']):,} | {r['signal']} | 신뢰도 {r['confidence']:.1%}")

print(f"\n❌ Avoid: {len(avoid)}개")
for r in avoid:
    print(f"   - {r['ticker']}: ₩{int(r['price']):,} | {r['signal']} | 신뢰도 {r['confidence']:.1%}")

# 포트폴리오 구성 제안
print("\n" + "=" * 70)
print("💼 균형 포트폴리오 구성 제안 (Growth + Value)")
print("=" * 70)

all_non_avoid = strong_buy + buy + hold
growth_all = [r for r in all_non_avoid if r['ticker'] in GROWTH_70_PLUS]
value_all = [r for r in all_non_avoid if r['ticker'] in VALUE_70_PLUS]

growth_all.sort(key=lambda x: x['confidence'], reverse=True)
value_all.sort(key=lambda x: x['confidence'], reverse=True)

print(f"\n📈 Growth 후보 ({len(growth_all)}개):")
for r in growth_all[:5]:
    name = provider.get_info(r['ticker']).get('shortName', r['ticker'])
    signal_emoji = "🚀" if r['confidence'] >= 0.65 else "📈" if r['confidence'] >= 0.5 else "➡️"
    print(f"   {signal_emoji} {r['ticker']} {name}: ₩{int(r['price']):,} | 신뢰도 {r['confidence']:.1%}")

print(f"\n💎 Value 후보 ({len(value_all)}개):")
for r in value_all[:5]:
    name = provider.get_info(r['ticker']).get('shortName', r['ticker'])
    div_yield = r.get('dividend_yield', 0) or 0
    pe_ratio = r.get('pe_ratio', 0) or 0
    div_pct = div_yield if div_yield > 1 else div_yield * 100
    signal_emoji = "🚀" if r['confidence'] >= 0.65 else "📈" if r['confidence'] >= 0.5 else "➡️"
    extra = f"PER:{pe_ratio:.1f} DIV:{div_pct:.1f}%" if pe_ratio > 0 else ""
    print(f"   {signal_emoji} {r['ticker']} {name}: ₩{int(r['price']):,} | 신뢰도 {r['confidence']:.1%} | {extra}")

# === 균형 포트폴리오 구성 ===
growth_picks = growth_all[:2]
value_picks = value_all[:2]
final_picks = growth_picks + value_picks

if final_picks:
    print(f"\n🏆 최종 균형 포트폴리오 (Growth 2 + Value 2):")
    print("-" * 60)

    growth_weight = 50 / len(growth_picks) if growth_picks else 0
    value_weight = 50 / len(value_picks) if value_picks else 0
    total_conf = sum(r['confidence'] for r in final_picks)

    for r in final_picks:
        is_value = r['ticker'] in VALUE_70_PLUS
        base_weight = value_weight if is_value else growth_weight
        conf_adj = (r['confidence'] / total_conf * len(final_picks) - 1) * 5
        weight = base_weight + conf_adj

        name = provider.get_info(r['ticker']).get('shortName', r['ticker'])

        if is_value:
            div_yield = r.get('dividend_yield', 0) or 0
            pe_ratio = r.get('pe_ratio', 0) or 0
            div_pct = div_yield if div_yield > 1 else div_yield * 100
            extra = f"[Value] PER:{pe_ratio:.1f} DIV:{div_pct:.1f}%"
        else:
            extra = "[Growth]"

        signal_emoji = "🚀" if r['confidence'] >= 0.65 else "📈" if r['confidence'] >= 0.5 else "➡️"
        print(f"   ⭐ {r['ticker']} {name}: 비중 {weight:.1f}% | ₩{int(r['price']):,} | {signal_emoji} {r['confidence']:.1%} {extra}")

    print(f"\n📊 포트폴리오 요약:")
    avg_conf = sum(r['confidence'] for r in final_picks) / len(final_picks)
    avg_div = sum((r.get('dividend_yield', 0) or 0) for r in value_picks) / len(value_picks) if value_picks else 0
    avg_div_pct = avg_div if avg_div > 1 else avg_div * 100
    print(f"   평균 신뢰도: {avg_conf:.1%}")
    print(f"   Value 평균 배당률: {avg_div_pct:.2f}%")
    print(f"   Growth/Value 비율: {len(growth_picks)*25}% / {len(value_picks)*25}%")
else:
    print("\n⚠️ 추천 가능한 종목이 없습니다. 시장 타이밍을 기다리세요.")
