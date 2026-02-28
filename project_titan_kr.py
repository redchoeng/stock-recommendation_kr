# -*- coding: utf-8 -*-
"""
Project Titan KR - 한국장 주식 의사결정 지원 시스템
KOSPI 200 + KOSDAQ 시총 상위 종목 대상
100점 스코어링 (펀더멘털 50 + 기술적 50) + ML 앙상블
"""

import time
from datetime import datetime
from tabulate import tabulate
import pytz
import os
import sys

from kr_data_provider import KRDataProvider

# ============================================================================
# 한국장 종목코드 (6자리)
# ============================================================================

# 성장주 (반도체, 2차전지, 바이오, 플랫폼, 방산, 조선, 자동차 등)
KR_GROWTH_CODES = [
    # ========== 반도체/AI (15) ==========
    '005930',  # 삼성전자
    '000660',  # SK하이닉스
    '042700',  # 한미반도체
    '403870',  # HPSP
    '058470',  # 리노공업
    '036930',  # 주성엔지니어링
    '025560',  # 미래산업
    '045660',  # 에이텍
    '357780',  # 솔브레인
    '005290',  # 동진쎄미켐
    '240810',  # 원익IPS
    '095340',  # ISC
    '098460',  # 고영
    '302920',  # 더블유에스아이
    '067160',  # 아프리카TV

    # ========== 2차전지/배터리 (10) ==========
    '373220',  # LG에너지솔루션
    '006400',  # 삼성SDI
    '051910',  # LG화학
    '247540',  # 에코프로비엠
    '086520',  # 에코프로
    '003670',  # 포스코퓨처엠
    '018260',  # 삼성에스디에스
    '361610',  # SK아이이테크놀로지
    '137400',  # 피엔티
    '108320',  # LX세미콘

    # ========== 바이오/헬스케어 (11) ==========
    '207940',  # 삼성바이오로직스
    '068270',  # 셀트리온
    '326030',  # SK바이오팜
    '145020',  # 휴젤
    '141080',  # 리가켐바이오
    '000100',  # 유한양행
    '128940',  # 한미약품
    '196170',  # 알테오젠
    '195940',  # HK이노엔
    '950160',  # 코오롱티슈진
    '328130',  # 루닛
    '006280',  # 녹십자

    # ========== K-플랫폼/IT서비스/게임 (14) ==========
    '035420',  # NAVER
    '035720',  # 카카오
    '259960',  # 크래프톤
    '352820',  # 하이브
    '263750',  # 펄어비스
    '112040',  # 위메이드
    '293490',  # 카카오게임즈
    '030200',  # KT
    '036570',  # 엔씨소프트
    '251270',  # 넷마블
    '377300',  # 카카오페이
    '323410',  # 카카오뱅크
    '017670',  # SK텔레콤
    '032640',  # LG유플러스

    # ========== 방산/우주 (8) ==========
    '012450',  # 한화에어로스페이스
    '079550',  # LIG넥스원
    '047810',  # 한국항공우주
    '272210',  # 한화시스템
    '064350',  # 현대로템
    '014970',  # 삼기오토모티브
    '006260',  # LS
    '103140',  # 풍산

    # ========== 조선/해양 (6) ==========
    '329180',  # HD현대중공업
    '009540',  # HD한국조선해양
    '042660',  # 한화오션
    '010620',  # HD현대미포
    '267250',  # HD현대
    '241560',  # 두산밥캣

    # ========== 자동차/모빌리티 (8) ==========
    '005380',  # 현대자동차
    '000270',  # 기아
    '012330',  # 현대모비스
    '018880',  # 한온시스템
    '161390',  # 한국타이어앤테크놀로지
    '298040',  # 효성중공업
    '009150',  # 삼성전기
]

# 가치주/배당주 (금융, 통신, 유틸리티, 건설, 에너지, 보험 등)
KR_VALUE_CODES = [
    # ========== 금융 - 은행 (10) ==========
    '105560',  # KB금융
    '055550',  # 신한지주
    '086790',  # 하나금융지주
    '316140',  # 우리금융지주
    '024110',  # 기업은행
    '138930',  # BNK금융지주
    '175330',  # JB금융지주
    '139130',  # DGB금융지주
    '071050',  # 한국금융지주
    '000810',  # 삼성화재

    # ========== 금융 - 보험/증권 (10) ==========
    '032830',  # 삼성생명
    '088350',  # 한화생명
    '005830',  # DB손해보험
    '001450',  # 현대해상
    '000815',  # 삼성화재우
    '039490',  # 키움증권
    '003540',  # 대신증권
    '006800',  # 미래에셋증권
    '016360',  # 삼성증권
    '030610',  # 교보증권

    # ========== 통신 (4) ==========
    '017670',  # SK텔레콤
    '030200',  # KT
    '032640',  # LG유플러스
    '034730',  # SK

    # ========== 유틸리티/에너지 (8) ==========
    '015760',  # 한국전력
    '034020',  # 두산에너빌리티
    '267250',  # HD현대
    '096770',  # SK이노베이션
    '010950',  # S-Oil
    '078930',  # GS
    '036460',  # 한국가스공사
    '051600',  # 한전KPS

    # ========== 건설/인프라 (8) ==========
    '000720',  # 현대건설
    '028260',  # 삼성물산
    '047040',  # 대우건설
    '006360',  # GS건설
    '002150',  # 도화엔지니어링
    '009830',  # 한화솔루션
    '011200',  # HMM
    '001040',  # CJ

    # ========== 소비재/유통 (12) ==========
    '051900',  # LG생활건강
    '090430',  # 아모레퍼시픽
    '004170',  # 신세계
    '023530',  # 롯데쇼핑
    '069960',  # 현대백화점
    '139480',  # 이마트
    '097950',  # CJ제일제당
    '271560',  # 오리온
    '280360',  # 롯데웰푸드
    '003230',  # 삼양식품
    '005180',  # 빙그레
    '002790',  # 아모레G

    # ========== 소재/화학 (10) ==========
    '051910',  # LG화학
    '010130',  # 고려아연
    '005490',  # POSCO홀딩스
    '004020',  # 현대제철
    '042670',  # 두산인프라코어
    '003490',  # 대한항공
    '000120',  # CJ대한통운
    '069620',  # 대웅제약
    '128940',  # 한미약품
    '006650',  # 대한유화

    # ========== 산업재/기계 (8) ==========
    '034220',  # LG디스플레이
    '066570',  # LG전자
    '003550',  # LG
    '000150',  # 두산
    '010140',  # 삼성중공업
    '001120',  # LX인터내셔널
    '001740',  # SK네트웍스
]


class TitanKRAnalyzer:
    # 필터링 기준 (한국장)
    MIN_MARKET_CAP = 1_000_000_000_000  # 1조원
    MIN_PRICE = 1000                     # ₩1,000
    MIN_AVG_VOLUME = 100_000            # 10만주

    # 섹터별 점수 - 성장주 (10pt 만점)
    SCORE_SECTOR_TIER1 = 10  # 반도체/AI, 2차전지
    SCORE_SECTOR_TIER2 = 8   # 바이오, K-플랫폼, 방산, 조선
    SCORE_SECTOR_TIER3 = 5   # 자동차, 화학, 철강, 건설
    SCORE_SECTOR_TIER4 = 3   # 유틸리티, 섬유, 음식료

    # 섹터별 점수 - 가치주 (10pt 만점)
    VALUE_SECTOR_TIER1 = 10  # 금융(은행/보험), 통신
    VALUE_SECTOR_TIER2 = 8   # 유틸리티, 보험
    VALUE_SECTOR_TIER3 = 5   # 건설, 에너지, 소재
    VALUE_SECTOR_TIER4 = 3   # 기술주(성장주 영역)

    # 한국 정책 보너스/페널티
    POLICY_BONUS = 3
    POLICY_PENALTY = -3

    # 섹터 순환매 분석용 ETF 매핑 (KOSPI 섹터 ETF)
    SECTOR_ETF_MAP = {
        'Technology': '091160.KS',           # KODEX 반도체
        'Financial Services': '091170.KS',   # KODEX 은행
        'Industrials': '091180.KS',          # KODEX 자동차
        'Healthcare': '244580.KS',           # KODEX 바이오
        'Basic Materials': '117680.KS',      # KODEX 철강
        'Energy': '117460.KS',              # KODEX 에너지화학
    }
    # 순환매 보너스 확대 (US v2.0 동기화)
    ROTATION_BONUS_INFLOW = 5       # 기존 3 → 5
    ROTATION_BONUS_TURNING = 7      # 기존 5 → 7
    ROTATION_BONUS_WATCHING = 2     # 기존 1 → 2
    ROTATION_PENALTY_OVERHEAT = -3  # 기존 -2 → -3
    ROTATION_PENALTY_COLD = -5      # 기존 -3 → -5

    # 한국 섹터별 ROE 기준 (한국장 하향 조정)
    SECTOR_ROE_THRESHOLDS = {
        '전기,전자': (15, 8),
        '전기전자': (15, 8),
        '반도체': (15, 8),
        '금융업': (10, 6),
        '은행': (10, 6),
        '보험': (10, 6),
        '증권': (10, 6),
        '유틸리티': (5, 2),
        '전기가스업': (5, 2),
        '전력': (5, 2),
        '조선': (10, 5),
        '운수장비': (10, 5),
        '건설업': (10, 5),
        '화학': (12, 6),
        '의약품': (12, 6),
        '바이오': (12, 6),
        '통신업': (10, 5),
        '서비스업': (12, 6),
        '음식료품': (12, 6),
        '유통업': (10, 5),
    }
    DEFAULT_ROE_THRESHOLD = (12, 6)

    # 한국 섹터별 OPM 기준
    SECTOR_OPM_THRESHOLDS = {
        '전기,전자': (15, 8),
        '전기전자': (15, 8),
        '반도체': (20, 10),
        '금융업': (20, 10),
        '은행': (20, 10),
        '유틸리티': (5, 1),
        '전기가스업': (3, 0),
        '전력': (3, 0),
        '조선': (5, 2),
        '운수장비': (8, 3),
        '건설업': (5, 2),
        '화학': (10, 5),
        '의약품': (15, 8),
        '바이오': (15, 8),
        '통신업': (15, 8),
        '음식료품': (8, 3),
        '유통업': (5, 2),
    }
    DEFAULT_OPM_THRESHOLD = (10, 5)

    # 한국 섹터별 매출성장률 기준
    SECTOR_REVENUE_GROWTH_THRESHOLDS = {
        '전기,전자': (20, 10),
        '전기전자': (20, 10),
        '금융업': (8, 3),
        '은행': (8, 3),
        '유틸리티': (5, 2),
        '전기가스업': (5, 2),
        '조선': (10, 5),
        '건설업': (10, 5),
        '화학': (10, 5),
        '의약품': (15, 8),
        '바이오': (20, 10),
        '통신업': (5, 2),
        '음식료품': (8, 3),
    }
    DEFAULT_REVENUE_GROWTH_THRESHOLD = (10, 5)

    # ===== 가치주 모드 전용 기준 =====
    # 배당수익률 기준 {sector: (excellent%, good%)} — 높을수록 좋음
    VALUE_DIVIDEND_THRESHOLDS = {
        '금융업': (5.0, 2.5),
        '은행': (5.0, 2.5),
        '보험': (4.0, 2.0),
        '증권': (3.0, 1.5),
        '통신업': (5.0, 3.0),
        '유틸리티': (5.0, 3.0),
        '전기가스업': (5.0, 3.0),
        '전력': (5.0, 3.0),
        '건설업': (3.0, 1.5),
        '화학': (3.0, 1.5),
        '음식료품': (3.0, 1.5),
        '유통업': (2.0, 1.0),
        '의약품': (2.0, 0.5),
        '전기,전자': (2.0, 0.5),
        '전기전자': (2.0, 0.5),
    }
    DEFAULT_VALUE_DIVIDEND_THRESHOLD = (3.0, 1.5)

    # PER 기준 (역방향: 낮을수록 좋음) {sector: (good_upper, fair_upper)}
    VALUE_PER_THRESHOLDS = {
        '금융업': (8, 15),
        '은행': (8, 15),
        '보험': (10, 18),
        '증권': (10, 18),
        '통신업': (12, 20),
        '유틸리티': (15, 25),
        '전기가스업': (15, 25),
        '건설업': (10, 18),
        '화학': (12, 20),
        '음식료품': (15, 25),
        '유통업': (12, 20),
        '의약품': (18, 30),
        '전기,전자': (15, 25),
        '전기전자': (15, 25),
    }
    DEFAULT_VALUE_PER_THRESHOLD = (12, 20)

    # 부채비율(D/E) 기준 (역방향: 낮을수록 좋음) {sector: (good_upper, fair_upper)}
    VALUE_DE_THRESHOLDS = {
        '금융업': (300, 600),
        '은행': (300, 600),
        '보험': (200, 400),
        '증권': (200, 400),
        '건설업': (150, 300),
        '유틸리티': (150, 250),
        '전기가스업': (150, 250),
        '통신업': (100, 200),
        '화학': (80, 150),
        '음식료품': (80, 150),
        '전기,전자': (50, 100),
        '전기전자': (50, 100),
    }
    DEFAULT_VALUE_DE_THRESHOLD = (80, 150)

    # EV/EBITDA 기준 (신규: PER 대안) {sector: (good_upper, fair_upper)}
    VALUE_EVEBITDA_THRESHOLDS = {
        '전기,전자': (12, 20),
        '전기전자': (12, 20),
        '금융업': (10, 16),
        '은행': (10, 16),
        '보험': (10, 16),
        '통신업': (8, 14),
        '유틸리티': (10, 16),
        '전기가스업': (10, 16),
        '건설업': (8, 13),
        '화학': (8, 13),
        '의약품': (14, 22),
        '음식료품': (14, 24),
        '유통업': (12, 20),
    }
    DEFAULT_VALUE_EVEBITDA_THRESHOLD = (12, 20)

    # P/B 기준 (금융/소재/에너지 전용)
    VALUE_PB_THRESHOLDS = {
        '금융업': (1.2, 1.8),
        '은행': (1.2, 1.8),
        '보험': (1.2, 1.8),
        '증권': (1.2, 1.8),
        '화학': (1.8, 2.8),
        '철강': (1.8, 2.8),
        '금속': (1.8, 2.8),
        'default': (2.5, 4.5),
    }

    # Beta 임계값 (가치주)
    VALUE_BETA_THRESHOLDS = (0.8, 1.2)

    # 한국 배당 귀족 (10년+ 연속 배당)
    KR_DIVIDEND_ARISTOCRATS = {
        '105560',  # KB금융
        '055550',  # 신한지주
        '086790',  # 하나금융지주
        '316140',  # 우리금융지주
        '000810',  # 삼성화재
        '005830',  # DB손해보험
        '000370',  # 한화손해보험
        '017670',  # SK텔레콤
        '030200',  # KT
        '032640',  # LG유플러스
        '034020',  # 두산에너빌리티
        '051900',  # LG생활건강
        '036570',  # 엔씨소프트
    }

    # 기술적 점수 (총 ~53점, US v2.0 동기화)
    # 1. 추세 (18점): MA120(2)+MA60(2)+MA20(2)+MA5(1)+MACD(4/2)+일목(3)+ADX(2)
    SCORE_MA120 = 2
    SCORE_MA60 = 2
    SCORE_MA20 = 2    # 3→2 (US 동기화)
    SCORE_MA5 = 1      # 2→1 (US 동기화)
    SCORE_MACD_BULLISH = 4
    SCORE_MACD_SIGNAL = 2
    SCORE_ICHIMOKU = 3   # 구름위(1)+TK크로스(1)+미래양운(1) — KR 고유 유지
    SCORE_ADX_STRONG = 2

    # 2. 모멘텀 (12점): RSI(5/3/2)+Stoch(5/2)+MFI(2)
    SCORE_RSI_OPTIMAL = 5
    SCORE_RSI_GOOD = 3
    SCORE_RSI_OVERSOLD = 2
    SCORE_STOCH_OPTIMAL = 5
    SCORE_STOCH_GOOD = 2     # 신규: stoch_k > stoch_d (>=80 포함)

    # 3. 거래량 (8점): Vol(4/3/2/1)+OBV(4)
    SCORE_VOLUME_EXTREME = 4
    SCORE_VOLUME_HIGH = 3
    SCORE_VOLUME_MODERATE = 2
    SCORE_VOLUME_NORMAL = 1
    SCORE_OBV_RISING = 4

    # 4. 변동성 (5점, 7→5 축소): BB(3)+ATR(2)
    SCORE_BB_POSITION = 3    # 4→3
    SCORE_ATR_EXPANSION = 2  # 3→2
    # 5. 패턴 (5점)
    SCORE_PRICE_POSITION = 5

    # 6. 상대강도 vs KOSPI (5점, 신규)
    SCORE_RS_STRONG = 5
    SCORE_RS_GOOD = 3
    SCORE_RS_NEUTRAL = 1

    # 거래대금 유동성 보너스
    TRADING_VALUE_HOT = 100_000_000_000       # 1000억원
    TRADING_VALUE_ACTIVE = 30_000_000_000     # 300억원
    TRADING_VALUE_NORMAL = 10_000_000_000     # 100억원
    BONUS_TRADING_HOT = 5
    BONUS_TRADING_ACTIVE = 3
    BONUS_TRADING_THIN = -3

    # Growth/Value 가중치
    GROWTH_FUND_WEIGHT = 0.8
    GROWTH_TECH_WEIGHT = 1.2
    VALUE_FUND_WEIGHT = 1.3
    VALUE_TECH_WEIGHT = 0.7

    RSI_OVERSOLD = 30
    RSI_OPTIMAL_MIN = 40
    RSI_OPTIMAL_MAX = 60
    RSI_GOOD_MAX = 70
    RSI_OVERBOUGHT = 70

    SCORE_OVERSOLD_QUALITY_BONUS = 10
    SCORE_OVERBOUGHT_PENALTY = -8  # -5→-8 (US v2.0 동기화)


    def __init__(self, dart_api_key=None):
        self.results = []
        self.analysis_mode = 'growth'
        self.data_provider = KRDataProvider(dart_api_key=dart_api_key)

    # ================================================================
    # 펀더멘털 점수 (50점 만점)
    # ================================================================
    def _get_fundamental_score(self, info):
        score = 0
        comments = []
        breakdown = {
            'roe_score': 0, 'roe_value': None,
            'opm_score': 0, 'opm_value': None,
            'revenue_growth_score': 0, 'revenue_growth_value': None,
            'sector_score': 0, 'sector_name': '',
            'peg_value': None, 'peg_score': 0,
            'fcf_margin_value': None, 'fcf_score': 0,
            # 가치주 전용 필드
            'dividend_yield_score': 0, 'dividend_yield_value': None,
            'dividend_growth_score': 0,
            'per_score': 0, 'per_value': None,
            'valuation_method': 'PER',
            'ev_ebitda_value': None,
            'debt_equity_score': 0, 'debt_equity_value': None,
            'fcf_yield_value': None,
            'beta_value': None, 'beta_score': 0,
        }

        try:
            sector = info.get('sector', '') or ''
            industry = info.get('industry', '') or ''

            # ===== 가치주 모드: 배당/저평가/안정성 중심 (50점) =====
            if self.analysis_mode == 'value':
                market_cap = info.get('marketCap', 0)
                stock_code = info.get('_code', '')
                is_aristocrat = stock_code in self.KR_DIVIDEND_ARISTOCRATS

                # [우량주 프리미엄 산정]
                premium_multiplier = 1.0
                roe_pre = info.get('returnOnEquity')
                if market_cap and market_cap >= 50_000_000_000_000:  # 50조원
                    premium_multiplier += 0.2
                if roe_pre and roe_pre >= 0.15:
                    premium_multiplier += 0.2
                if is_aristocrat:
                    premium_multiplier += 0.1
                premium_multiplier = min(premium_multiplier, 1.6)

                # 1. 배당수익률 (10점, 12→10: 배당성장률 5점 신설로 재배분)
                div_pct = None
                div_rate = info.get('dividendRate')
                price_now = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                if div_rate and div_rate > 0 and price_now and price_now > 0:
                    div_pct = div_rate / price_now * 100
                else:
                    div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
                    if div_yield and div_yield > 0:
                        div_pct = div_yield if div_yield <= 15 else div_yield / 100

                if div_pct and div_pct > 0:
                    breakdown['dividend_yield_value'] = round(div_pct, 2)
                    dy_exc, dy_good = self._get_sector_threshold(
                        sector, self.VALUE_DIVIDEND_THRESHOLDS, self.DEFAULT_VALUE_DIVIDEND_THRESHOLD)
                    dy_pts = self._calc_gradient_score(div_pct, dy_exc, dy_good, 10)

                    # 배당귀족/메가캡 최소 보장
                    if dy_pts < 4 and (is_aristocrat or (market_cap and market_cap >= 50_000_000_000_000)):
                        dy_pts = 4

                    # 배당성향 경고
                    payout = info.get('payoutRatio')
                    if payout and payout > 1.0:
                        dy_pts = int(dy_pts * 0.7)
                        comments.append(f"배당성향{payout*100:.0f}%⚠️")

                    score += dy_pts
                    breakdown['dividend_yield_score'] = dy_pts
                    if dy_pts >= 5:
                        comments.append(f"배당{div_pct:.1f}%")

                # 1.5. 배당 성장률 (5점, 신규)
                div_growth_pts = 0
                five_yr_avg_yield = info.get('fiveYearAvgDividendYield')
                earnings_growth = info.get('earningsGrowth')
                payout_for_growth = info.get('payoutRatio')

                if is_aristocrat:
                    div_growth_pts = 5
                elif div_pct and div_pct > 0:
                    if five_yr_avg_yield and five_yr_avg_yield > 0:
                        div_growth_pts += 2
                    if payout_for_growth and 0 < payout_for_growth < 0.7:
                        div_growth_pts += 1
                    if earnings_growth and earnings_growth > 0.05:
                        div_growth_pts += 1
                    if earnings_growth and earnings_growth > 0.10 and payout_for_growth and 0 < payout_for_growth < 0.6:
                        div_growth_pts += 1

                div_growth_pts = min(div_growth_pts, 5)
                score += div_growth_pts
                breakdown['dividend_growth_score'] = div_growth_pts
                if div_growth_pts >= 3:
                    comments.append(f"배당성장력{div_growth_pts}점")

                # 2. 밸류에이션 (12점): PER vs EV/EBITDA vs P/B 중 높은 쪽 채택
                per = info.get('trailingPE')
                ev_ebitda = info.get('enterpriseToEbitda')

                per_pts = 0
                if per and per > 0:
                    breakdown['per_value'] = per
                    per_good, per_fair = self._get_sector_threshold(
                        sector, self.VALUE_PER_THRESHOLDS, self.DEFAULT_VALUE_PER_THRESHOLD)
                    per_good *= premium_multiplier
                    per_fair *= premium_multiplier
                    per_pts = self._calc_inverse_gradient_score(per, per_good, per_fair, 12)

                ev_pts = 0
                is_financial = any(kw in (sector or '') for kw in ['금융', '은행', '보험', '증권'])
                if ev_ebitda and ev_ebitda > 0 and not is_financial:
                    breakdown['ev_ebitda_value'] = ev_ebitda
                    ev_good, ev_fair = self._get_sector_threshold(
                        sector, self.VALUE_EVEBITDA_THRESHOLDS, self.DEFAULT_VALUE_EVEBITDA_THRESHOLD)
                    ev_good *= premium_multiplier
                    ev_fair *= premium_multiplier
                    ev_pts = self._calc_inverse_gradient_score(ev_ebitda, ev_good, ev_fair, 12)

                pb_pts = 0
                if is_financial or any(kw in (sector or '') for kw in ['화학', '철강', '금속', '소재']):
                    pb = info.get('priceToBook')
                    if pb and pb > 0:
                        pb_good, pb_fair = self.VALUE_PB_THRESHOLDS.get(
                            sector, self.VALUE_PB_THRESHOLDS.get('default', (2.5, 4.5)))
                        # 섹터 부분 매칭
                        for key, val in self.VALUE_PB_THRESHOLDS.items():
                            if key != 'default' and (key in (sector or '') or (sector or '') in key):
                                pb_good, pb_fair = val
                                break
                        pb_good *= premium_multiplier
                        pb_fair *= premium_multiplier
                        pb_pts = self._calc_inverse_gradient_score(pb, pb_good, pb_fair, 12)

                val_pts = max(per_pts, ev_pts, pb_pts)
                if val_pts == pb_pts and pb_pts > 0:
                    breakdown['valuation_method'] = 'P/B'
                elif val_pts == ev_pts and ev_pts > 0:
                    breakdown['valuation_method'] = 'EV/EBITDA'
                else:
                    breakdown['valuation_method'] = 'PER'

                score += val_pts
                breakdown['per_score'] = val_pts
                if val_pts >= 6:
                    if ev_pts > per_pts and ev_ebitda:
                        comments.append(f"EV/EBITDA:{ev_ebitda:.1f}x")
                    elif per and per > 0:
                        comments.append(f"PER:{per:.1f}")

                # 3. ROE (8점, 가치주는 비중 축소)
                roe = info.get('returnOnEquity')
                roe_excellent, roe_good = self._get_sector_threshold(
                    sector, self.SECTOR_ROE_THRESHOLDS, self.DEFAULT_ROE_THRESHOLD)
                if roe is not None:
                    roe_pct = roe * 100
                    breakdown['roe_value'] = roe_pct
                    roe_score = self._calc_gradient_score(roe_pct, roe_excellent, roe_good, 8)
                    score += roe_score
                    breakdown['roe_score'] = roe_score
                    if roe_score >= 4:
                        comments.append(f"ROE:{roe_pct:.1f}%")

                # 4. 부채비율 D/E (8점, 역방향)
                de = info.get('debtToEquity')
                if de is not None and de >= 0:
                    breakdown['debt_equity_value'] = de
                    de_good, de_fair = self._get_sector_threshold(
                        sector, self.VALUE_DE_THRESHOLDS, self.DEFAULT_VALUE_DE_THRESHOLD)
                    de_good = int(de_good * premium_multiplier)
                    de_fair = int(de_fair * premium_multiplier)
                    de_pts = self._calc_inverse_gradient_score(de, de_good, de_fair, 8)
                    score += de_pts
                    breakdown['debt_equity_score'] = de_pts
                    if de_pts >= 4:
                        comments.append(f"D/E:{de:.0f}")
                elif is_financial:
                    de_pts = round(8 * 0.5)
                    score += de_pts
                    breakdown['debt_equity_score'] = de_pts

                # FCF Yield (5점, 배당 지속가능성 검증)
                fcf = info.get('freeCashflow')
                if fcf and market_cap and market_cap > 0:
                    fcf_yield = fcf / market_cap
                    breakdown['fcf_yield_value'] = round(fcf_yield * 100, 1)
                    if fcf_yield > 0.08:
                        fcf_pts = 5
                        comments.append("현금흐름최상위")
                    elif fcf_yield > 0.05:
                        fcf_pts = 4
                        comments.append("현금흐름우수")
                    elif fcf_yield > 0.03:
                        fcf_pts = 2
                    else:
                        fcf_pts = 0
                    score += fcf_pts
                    breakdown['fcf_score'] = fcf_pts

                # Beta (5점)
                beta = info.get('beta')
                if beta is not None:
                    breakdown['beta_value'] = beta
                    if beta <= 0.8:
                        beta_pts = 5
                        comments.append(f"LowBeta({beta:.2f})")
                    elif beta <= 1.0:
                        beta_pts = 4
                    elif beta <= 1.2:
                        beta_pts = 2
                    else:
                        beta_pts = 0
                    score += beta_pts
                    breakdown['beta_score'] = beta_pts

                # 5. 섹터 (10점)
                breakdown['sector_name'] = sector or industry or '기타'
                sector_score, sector_name, sector_comment = self._get_value_sector_score(sector, industry)
                score += sector_score
                breakdown['sector_score'] = sector_score
                breakdown['sector_name'] = sector_name
                if sector_comment:
                    comments.append(sector_comment)

                # 배당 귀족 보너스 (+4점)
                if is_aristocrat:
                    score += 4
                    breakdown['aristocrat_bonus'] = 4
                    comments.append("배당귀족")

                # 한국 정책 보너스
                policy_bonus, policy_comment = self._get_kr_policy_bonus(
                    sector, industry, info.get('shortName', ''))
                if policy_bonus != 0:
                    score += policy_bonus
                    breakdown['policy_bonus'] = policy_bonus
                    comments.append(policy_comment)

            # ===== 성장주 모드: ROE/OPM/FCF/매출성장 중심 (50점) =====
            else:
                market_cap = info.get('marketCap', 0)

                # 1. ROE (섹터별 차등, 15점)
                roe = info.get('returnOnEquity')
                roe_excellent, roe_good = self._get_sector_threshold(
                    sector, self.SECTOR_ROE_THRESHOLDS, self.DEFAULT_ROE_THRESHOLD)
                if roe is not None:
                    roe_pct = roe * 100
                    breakdown['roe_value'] = roe_pct
                    roe_score = self._calc_gradient_score(roe_pct, roe_excellent, roe_good, 15)
                    score += roe_score
                    breakdown['roe_score'] = roe_score
                    if roe_score >= 8:
                        comments.append(f"ROE:{roe_pct:.1f}%")

                # 2. OPM (섹터별 차등, 10점 — 15→10 축소, ROE와 중복 줄임)
                opm = info.get('operatingMargins')
                opm_excellent, opm_good = self._get_sector_threshold(
                    sector, self.SECTOR_OPM_THRESHOLDS, self.DEFAULT_OPM_THRESHOLD)
                if opm is not None:
                    opm_pct = opm * 100
                    breakdown['opm_value'] = opm_pct
                    opm_score = self._calc_gradient_score(opm_pct, opm_excellent, opm_good, 10)
                    score += opm_score
                    breakdown['opm_score'] = opm_score
                    if opm_score >= 5:
                        comments.append(f"OPM:{opm_pct:.1f}%")

                # 2.5. FCF Margin (10점, 신규: 현금창출력)
                fcf = info.get('freeCashflow')
                total_revenue = info.get('totalRevenue')
                if fcf and total_revenue and total_revenue > 0:
                    fcf_margin = fcf / total_revenue * 100
                    breakdown['fcf_margin_value'] = round(fcf_margin, 1)
                    # 한국 섹터별 FCF 기준
                    if any(kw in (sector or '') for kw in ['전기전자', '전자', '반도체']):
                        fcf_excellent, fcf_good = 20, 8
                    elif any(kw in (sector or '') for kw in ['바이오', '의약', '제약']):
                        fcf_excellent, fcf_good = 15, 5
                    elif any(kw in (sector or '') for kw in ['통신']):
                        fcf_excellent, fcf_good = 20, 8
                    else:
                        fcf_excellent, fcf_good = 10, 3
                    fcf_pts = self._calc_gradient_score(fcf_margin, fcf_excellent, fcf_good, 10)
                    score += fcf_pts
                    breakdown['fcf_score'] = fcf_pts
                    if fcf_pts >= 5:
                        comments.append(f"FCF:{fcf_margin:.0f}%")
                elif fcf and market_cap and market_cap > 0:
                    # FCF Yield 폴백 (매출 데이터 없을 때)
                    fcf_yield = fcf / market_cap * 100
                    breakdown['fcf_margin_value'] = None
                    breakdown['fcf_yield_value'] = round(fcf_yield, 1)
                    if fcf_yield > 5:
                        fcf_pts = 7
                    elif fcf_yield > 3:
                        fcf_pts = 4
                    elif fcf_yield > 1:
                        fcf_pts = 2
                    else:
                        fcf_pts = 0
                    score += fcf_pts
                    breakdown['fcf_score'] = fcf_pts

                # 3. 매출성장률 (10점)
                revenue_growth = info.get('revenueGrowth')
                rg_high, rg_good = self._get_sector_threshold(
                    sector, self.SECTOR_REVENUE_GROWTH_THRESHOLDS, self.DEFAULT_REVENUE_GROWTH_THRESHOLD)
                if revenue_growth is not None:
                    rg_pct = revenue_growth * 100
                    breakdown['revenue_growth_value'] = rg_pct
                    rg_score = self._calc_gradient_score(rg_pct, rg_high, rg_good, 10)
                    score += rg_score
                    breakdown['revenue_growth_score'] = rg_score

                # PEG Ratio (GARP 전략, 5점 보너스)
                peg = info.get('pegRatio')
                if peg and peg > 0:
                    breakdown['peg_value'] = peg
                    if peg < 1.0:
                        score += 5
                        breakdown['peg_score'] = 5
                        comments.append(f"PEG저평가({peg:.2f})")
                    elif peg < 1.5:
                        score += 3
                        breakdown['peg_score'] = 3

                # 3-1. 고성장 투자기업 보정
                if revenue_growth is not None and revenue_growth > 0.30:
                    roe_val = roe * 100 if roe else 0
                    opm_val = opm * 100 if opm else 0
                    if roe_val < 0 and breakdown['roe_score'] == 0:
                        bonus = round(15 * 0.4)
                        score += bonus
                        breakdown['roe_score'] = bonus
                        comments.append("성장투자")
                    if opm_val < 0 and breakdown['opm_score'] == 0:
                        bonus = round(10 * 0.4)
                        score += bonus
                        breakdown['opm_score'] = bonus

                # 4. 섹터 (라벨링만, 점수 0 — 순환매 보너스가 동적으로 대체)
                breakdown['sector_name'] = sector or industry or '기타'
                sector_score, sector_name, sector_comment = self._get_growth_sector_score(sector, industry, info.get('shortName', ''))
                breakdown['sector_score'] = 0  # 고정 섹터 점수 제거
                breakdown['sector_name'] = sector_name
                # sector_comment는 라벨링용으로 유지

                # 한국 정책 보너스
                policy_bonus, policy_comment = self._get_kr_policy_bonus(
                    sector, industry, info.get('shortName', ''))
                if policy_bonus != 0:
                    score += policy_bonus
                    breakdown['policy_bonus'] = policy_bonus
                    comments.append(policy_comment)

        except Exception:
            pass

        return score, comments, breakdown

    @staticmethod
    def _calc_gradient_score(value, excellent, good, max_pts):
        """선형 보간 점수 계산
        - value > excellent*1.3: max_pts (만점)
        - excellent ~ excellent*1.3: 80%~100% 보간
        - good ~ excellent: 40%~80% 보간
        - good*0.5 ~ good: 5%~40% 보간
        - < good*0.5: 0점
        """
        if value is None or value <= 0:
            return 0
        if excellent == 0 and good == 0:
            return 0

        fair = good * 0.5
        top = excellent * 1.3

        if value >= top:
            return max_pts
        elif value >= excellent:
            ratio = (value - excellent) / (top - excellent) if top > excellent else 1
            pts = max_pts * (0.8 + 0.2 * ratio)
        elif value >= good:
            ratio = (value - good) / (excellent - good) if excellent > good else 1
            pts = max_pts * (0.4 + 0.4 * ratio)
        elif value >= fair:
            ratio = (value - fair) / (good - fair) if good > fair else 1
            pts = max_pts * (0.05 + 0.35 * ratio)
        else:
            return 0

        return round(pts)

    @staticmethod
    def _calc_inverse_gradient_score(value, good_upper, fair_upper, max_pts):
        """역방향 선형 보간 (낮을수록 좋은 지표: PER, 부채비율)

        구간별 점수:
        - value <= good_upper * 0.6: max_pts (만점)
        - good_upper*0.6 ~ good_upper: 80%~100%
        - good_upper ~ fair_upper: 40%~80%
        - fair_upper ~ fair_upper*1.5: 5%~40%
        - > fair_upper*1.5: 0
        """
        if value is None or value <= 0:
            return 0

        excellent = good_upper * 0.6
        poor = fair_upper * 1.5

        if value <= excellent:
            return max_pts
        elif value <= good_upper:
            ratio = (good_upper - value) / (good_upper - excellent) if good_upper > excellent else 1
            return round(max_pts * (0.8 + 0.2 * ratio))
        elif value <= fair_upper:
            ratio = (fair_upper - value) / (fair_upper - good_upper) if fair_upper > good_upper else 1
            return round(max_pts * (0.4 + 0.4 * ratio))
        elif value <= poor:
            ratio = (poor - value) / (poor - fair_upper) if poor > fair_upper else 1
            return round(max_pts * (0.05 + 0.35 * ratio))
        else:
            return 0

    def _get_sector_threshold(self, sector, threshold_dict, default):
        """섹터명으로 임계값 찾기 (부분 매칭)"""
        if not sector:
            return default
        for key, val in threshold_dict.items():
            if key in sector or sector in key:
                return val
        return default

    # ================================================================
    # 성장주 섹터 점수
    # ================================================================
    def _get_growth_sector_score(self, sector, industry, name=""):
        """성장주 모드 섹터 점수"""
        s = (sector or '').lower()
        i = (industry or '').lower()
        n = (name or '').lower()

        # TIER 1 (10pt): 2차전지 (이름 기반, 전기전자보다 먼저 체크)
        if any(kw in n for kw in ['에너지솔루션', 'sdi', '에코프로', '포스코퓨처엠', '아이이테크']):
            return self.SCORE_SECTOR_TIER1, "2차전지", "2차전지"
        if any(kw in s+i+n for kw in ['2차전지', '배터리']):
            return self.SCORE_SECTOR_TIER1, "2차전지", "2차전지"

        # TIER 1 (10pt): 반도체/AI
        if any(kw in n for kw in ['삼성전자', 'sk하이닉스', '한미반도체', 'hpsp', '리노공업']):
            return self.SCORE_SECTOR_TIER1, "AI/반도체", "AI/반도체"
        if any(kw in s+i+n for kw in ['반도체', 'semiconductor']):
            return self.SCORE_SECTOR_TIER1, "AI/반도체", "AI/반도체"
        if any(kw in s+i for kw in ['전기전자', '전자']):
            return self.SCORE_SECTOR_TIER1, "전기전자", "전기전자"

        # TIER 2 (8pt): 바이오, 플랫폼, 방산, 조선
        if any(kw in s+i+n for kw in ['바이오', '의약', '제약', '헬스']):
            return self.SCORE_SECTOR_TIER2, "바이오", "바이오"
        if any(kw in n for kw in ['네이버', '카카오', '크래프톤', 'naver']):
            return self.SCORE_SECTOR_TIER2, "K-플랫폼", "K-플랫폼"
        if any(kw in s+i+n for kw in ['방산', '항공우주', '에어로', '넥스원', '한화시스템']):
            return self.SCORE_SECTOR_TIER2, "방산", "방산"
        if any(kw in s+i+n for kw in ['조선', '해양', '중공업', '한화오션']):
            return self.SCORE_SECTOR_TIER2, "조선", "조선"
        if any(kw in s+i+n for kw in ['게임', '엔씨', '넷마블', '펄어비스', '위메이드']):
            return self.SCORE_SECTOR_TIER2, "게임", "게임"

        # TIER 3 (5pt): 자동차, 화학, 철강, IT서비스
        if any(kw in s+i+n for kw in ['자동차', '모비스', '기아', '현대차']):
            return self.SCORE_SECTOR_TIER3, "자동차", "자동차"
        if any(kw in s+i for kw in ['화학', '소재']):
            return self.SCORE_SECTOR_TIER3, "화학/소재", "화학/소재"
        if any(kw in s+i for kw in ['철강', '금속']):
            return self.SCORE_SECTOR_TIER3, "철강", "철강"
        if any(kw in s+i for kw in ['소프트웨어', 'it서비스', '정보기술']):
            return self.SCORE_SECTOR_TIER3, "IT서비스", "IT서비스"
        if any(kw in s+i for kw in ['건설']):
            return self.SCORE_SECTOR_TIER3, "건설", "건설"
        if any(kw in s+i for kw in ['통신']):
            return self.SCORE_SECTOR_TIER3, "통신", "통신"

        # TIER 4 (3pt): 유틸리티, 식품, 섬유
        if any(kw in s+i for kw in ['유틸리티', '전력', '전기가스', '가스']):
            return self.SCORE_SECTOR_TIER4, "유틸리티", "유틸리티"
        if any(kw in s+i for kw in ['음식', '식품', '음료']):
            return self.SCORE_SECTOR_TIER4, "음식료", "음식료"
        if any(kw in s+i for kw in ['섬유', '의류', '패션']):
            return self.SCORE_SECTOR_TIER4, "섬유/의류", "섬유/의류"

        # 기타 (최소 1점 보장)
        return 1, sector or '기타', sector or ''

    # ================================================================
    # 가치주 섹터 점수
    # ================================================================
    def _get_value_sector_score(self, sector, industry):
        s = (sector or '').lower()
        i = (industry or '').lower()

        # TIER 1 (10pt): 금융, 통신
        if any(kw in s+i for kw in ['금융', '은행', '보험', '증권']):
            return self.VALUE_SECTOR_TIER1, "금융", "금융"
        if any(kw in s+i for kw in ['통신', '텔레콤']):
            return self.VALUE_SECTOR_TIER1, "통신", "통신"

        # TIER 2 (8pt): 유틸리티, 보험
        if any(kw in s+i for kw in ['유틸리티', '전력', '전기가스', '가스']):
            return self.VALUE_SECTOR_TIER2, "유틸리티", "유틸리티"

        # TIER 3 (5pt): 건설, 에너지, 소재
        if any(kw in s+i for kw in ['건설', '인프라']):
            return self.VALUE_SECTOR_TIER3, "건설", "건설"
        if any(kw in s+i for kw in ['에너지', '석유', '정유']):
            return self.VALUE_SECTOR_TIER3, "에너지", "에너지"
        if any(kw in s+i for kw in ['소재', '화학', '철강', '금속']):
            return self.VALUE_SECTOR_TIER3, "소재", "소재"
        if any(kw in s+i for kw in ['운수', '항공', '해운', '물류']):
            return self.VALUE_SECTOR_TIER3, "운수/물류", "운수/물류"
        if any(kw in s+i for kw in ['음식', '식품', '유통']):
            return self.VALUE_SECTOR_TIER3, "소비재", "소비재"

        # TIER 4 (3pt): 기술주
        if any(kw in s+i for kw in ['전자', '반도체', 'it', '소프트웨어', '게임']):
            return self.VALUE_SECTOR_TIER4, "기술주", "기술주"

        # 기타 (최소 1점 보장)
        return 1, sector or '기타', sector or ''

    # ================================================================
    # 한국 정책 보너스/페널티
    # ================================================================
    def _get_kr_policy_bonus(self, sector, industry, name=""):
        """한국 정부 정책 수혜/역풍

        수혜 (+3):
        - K-반도체: 삼성전자, SK하이닉스 (세제지원, 용인클러스터)
        - K-배터리: LG에너지솔루션, 삼성SDI (IRA/EU 보조금)
        - K-방산: 한화에어로, LIG넥스원 (수출 호조)
        - 조선: HD한국조선해양 (친환경 선박 교체)
        - 밸류업: 저PBR 금융주 (정부 밸류업 프로그램)

        역풍 (-3):
        - 중국 의존: 화장품(아모레), 면세점 등
        """
        s = (sector or '').lower()
        i = (industry or '').lower()
        n = (name or '').lower()

        # === 수혜 ===
        # K-반도체
        if any(kw in n for kw in ['삼성전자', 'sk하이닉스', '한미반도체', 'hpsp', '리노공업']):
            return self.POLICY_BONUS, "[Policy]K-반도체 정책수혜"
        if any(kw in s+i for kw in ['반도체']) and '장비' not in s+i:
            return self.POLICY_BONUS, "[Policy]K-반도체 정책수혜"

        # K-배터리
        if any(kw in n for kw in ['에너지솔루션', '삼성sdi', '에코프로', '포스코퓨처엠']):
            return self.POLICY_BONUS, "[Policy]K-배터리 정책수혜"
        if any(kw in s+i+n for kw in ['2차전지', '배터리']):
            return self.POLICY_BONUS, "[Policy]K-배터리 정책수혜"

        # K-방산
        if any(kw in n for kw in ['한화에어로', 'lig넥스원', '한국항공우주', '한화시스템', '현대로템', '풍산']):
            return self.POLICY_BONUS, "[Policy]K-방산 수출호조"
        if any(kw in s+i for kw in ['방산', '항공우주']):
            return self.POLICY_BONUS, "[Policy]K-방산 수출호조"

        # 조선
        if any(kw in n for kw in ['한국조선', 'hd현대중공업', '한화오션', 'hd현대미포']):
            return self.POLICY_BONUS, "[Policy]조선 친환경전환"
        if any(kw in s+i for kw in ['조선']):
            return self.POLICY_BONUS, "[Policy]조선 친환경전환"

        # 밸류업 (금융주)
        if any(kw in s+i for kw in ['금융', '은행', '보험', '증권']):
            return self.POLICY_BONUS, "[Policy]밸류업 프로그램"

        # === 역풍 ===
        # 중국 의존
        if any(kw in n for kw in ['아모레', '이니스프리', '면세']):
            return self.POLICY_PENALTY, "[Warning]중국 의존도 리스크"

        return 0, ""

    # ================================================================
    # 기술적 분석 (50점, US와 동일 알고리즘)
    # ================================================================
    def _get_technical_score(self, hist, current_price, kospi_hist=None):
        """기술적 분석 (최대 ~53점) — US v2.0 동기화"""
        from ta.trend import MACD, ADXIndicator
        from ta.momentum import RSIIndicator, StochasticOscillator
        from ta.volatility import BollingerBands, AverageTrueRange
        from ta.volume import OnBalanceVolumeIndicator, MFIIndicator

        score = 0
        comments = []
        breakdown = {
            'trend_score': 0, 'ma5': 0, 'ma20': 0, 'ma60': 0, 'ma120': 0,
            'macd_score': 0, 'adx_score': 0, 'adx_value': 0,
            'ichimoku_score': 0,
            'momentum_score': 0, 'rsi_value': 0, 'rsi_score': 0,
            'stoch_score': 0, 'stoch_k': 0, 'stoch_d': 0,
            'mfi_value': 0,
            'volume_score': 0, 'volume_ratio': 0, 'obv_score': 0,
            'volatility_score': 0, 'bb_position': 0, 'bb_upper': 0, 'bb_lower': 0, 'bb_mid': 0,
            'atr_score': 0, 'atr_value': 0,
            'pattern_score': 0, 'price_position': 0,
            'rs_score': 0, 'rs_ratio': 0,
        }

        try:
            if len(hist) < 120:
                return 0, ["데이터부족"], breakdown

            close = hist['Close']
            volume = hist['Volume']

            # 1. 추세 분석 (20점)
            trend_score = 0
            ma5 = close.rolling(window=5).mean().iloc[-1]
            ma20 = close.rolling(window=20).mean().iloc[-1]
            ma60 = close.rolling(window=60).mean().iloc[-1]
            ma120 = close.rolling(window=120).mean().iloc[-1]

            breakdown['ma5'] = ma5
            breakdown['ma20'] = ma20
            breakdown['ma60'] = ma60
            breakdown['ma120'] = ma120

            if current_price > ma120:
                trend_score += self.SCORE_MA120
                comments.append("MA120↑")
            if current_price > ma60:
                trend_score += self.SCORE_MA60
            if current_price > ma20:
                trend_score += self.SCORE_MA20
            if current_price > ma5:
                trend_score += self.SCORE_MA5

            # MACD
            macd = MACD(close=close)
            macd_line = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]

            if macd_line > macd_signal:
                if macd_line > 0:
                    trend_score += self.SCORE_MACD_BULLISH
                    comments.append("MACD골든")
                else:
                    trend_score += self.SCORE_MACD_SIGNAL
                breakdown['macd_score'] = self.SCORE_MACD_BULLISH if macd_line > 0 else self.SCORE_MACD_SIGNAL

            # 일목균형표 (Ichimoku Cloud) - 3점
            ichimoku_score = 0
            try:
                high_9 = hist['High'].rolling(9).max().iloc[-1]
                low_9 = hist['Low'].rolling(9).min().iloc[-1]
                tenkan = (high_9 + low_9) / 2

                high_26 = hist['High'].rolling(26).max().iloc[-1]
                low_26 = hist['Low'].rolling(26).min().iloc[-1]
                kijun = (high_26 + low_26) / 2

                high_52 = hist['High'].rolling(52).max().iloc[-1]
                low_52 = hist['Low'].rolling(52).min().iloc[-1]
                span_b = (high_52 + low_52) / 2
                span_a = (tenkan + kijun) / 2

                cloud_top = max(span_a, span_b)
                if current_price > cloud_top:
                    ichimoku_score += 1
                if tenkan > kijun:
                    ichimoku_score += 1
                if span_a > span_b:
                    ichimoku_score += 1

                trend_score += ichimoku_score
                breakdown['ichimoku_score'] = ichimoku_score
                if ichimoku_score >= 2:
                    comments.append(f"일목{ichimoku_score}/3")
            except Exception:
                pass

            # ADX
            adx = ADXIndicator(high=hist['High'], low=hist['Low'], close=close)
            adx_value = adx.adx().iloc[-1]
            breakdown['adx_value'] = adx_value
            if adx_value > 25:
                trend_score += self.SCORE_ADX_STRONG
                breakdown['adx_score'] = self.SCORE_ADX_STRONG
                comments.append(f"ADX:{adx_value:.0f}")

            breakdown['trend_score'] = trend_score
            score += trend_score

            is_downtrend = trend_score < 10

            # 2. 모멘텀 (10점)
            momentum_score = 0
            rsi_ind = RSIIndicator(close=close, window=14)
            rsi = rsi_ind.rsi().iloc[-1]
            breakdown['rsi_value'] = rsi

            if self.RSI_OPTIMAL_MIN <= rsi <= self.RSI_OPTIMAL_MAX:
                momentum_score += self.SCORE_RSI_OPTIMAL
                breakdown['rsi_score'] = self.SCORE_RSI_OPTIMAL
                comments.append(f"RSI:{rsi:.0f}*")
            elif self.RSI_OVERSOLD <= rsi < self.RSI_GOOD_MAX:
                momentum_score += self.SCORE_RSI_GOOD
                breakdown['rsi_score'] = self.SCORE_RSI_GOOD
                comments.append(f"RSI:{rsi:.0f}")
            elif rsi < self.RSI_OVERSOLD:
                if not is_downtrend:
                    momentum_score += self.SCORE_RSI_OVERSOLD
                    breakdown['rsi_score'] = self.SCORE_RSI_OVERSOLD
                    comments.append(f"RSI:{rsi:.0f}↓")
                else:
                    comments.append(f"RSI:{rsi:.0f}⚠")

            stoch = StochasticOscillator(high=hist['High'], low=hist['Low'], close=close)
            stoch_k = stoch.stoch().iloc[-1]
            stoch_d = stoch.stoch_signal().iloc[-1]
            breakdown['stoch_k'] = stoch_k
            breakdown['stoch_d'] = stoch_d

            if stoch_k > stoch_d and stoch_k < 80:
                momentum_score += self.SCORE_STOCH_OPTIMAL
                breakdown['stoch_score'] = self.SCORE_STOCH_OPTIMAL
                comments.append("Stoch골든")
            elif stoch_k > stoch_d:
                momentum_score += self.SCORE_STOCH_GOOD
                breakdown['stoch_score'] = self.SCORE_STOCH_GOOD

            # MFI (Money Flow Index)
            try:
                mfi = MFIIndicator(high=hist['High'], low=hist['Low'], close=close, volume=volume, window=14)
                mfi_val = mfi.money_flow_index().iloc[-1]
                breakdown['mfi_value'] = mfi_val
                if mfi_val < 20:
                    momentum_score += 2
                    comments.append("MFI바닥")
                elif mfi_val > 80 and is_downtrend:
                    comments.append("MFI과열")
            except Exception:
                pass

            breakdown['momentum_score'] = momentum_score
            score += momentum_score

            # 3. 거래량 (8점)
            volume_score = 0
            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            current_volume = volume.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            breakdown['volume_ratio'] = volume_ratio

            if volume_ratio >= 3.0:
                volume_score += self.SCORE_VOLUME_EXTREME
                comments.append(f"거래량{volume_ratio:.1f}x")
            elif volume_ratio >= 2.0:
                volume_score += self.SCORE_VOLUME_HIGH
                comments.append(f"거래량{volume_ratio:.1f}x")
            elif volume_ratio >= 1.5:
                volume_score += self.SCORE_VOLUME_MODERATE
            elif volume_ratio >= 1.2:
                volume_score += self.SCORE_VOLUME_NORMAL

            obv = OnBalanceVolumeIndicator(close=close, volume=volume)
            obv_values = obv.on_balance_volume()
            obv_ma = obv_values.rolling(window=20).mean()
            if len(obv_values) >= 20 and obv_values.iloc[-1] > obv_ma.iloc[-1]:
                volume_score += self.SCORE_OBV_RISING
                breakdown['obv_score'] = self.SCORE_OBV_RISING
                comments.append("OBV↑")

            breakdown['volume_score'] = volume_score
            score += volume_score

            # 4. 변동성 (5점, 7→5 축소)
            volatility_score = 0
            bb = BollingerBands(close=close)
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]
            bb_mid = bb.bollinger_mavg().iloc[-1]
            bb_position = (current_price - bb_low) / (bb_high - bb_low) if (bb_high - bb_low) > 0 else 0.5
            breakdown['bb_position'] = bb_position
            breakdown['bb_upper'] = float(bb_high)
            breakdown['bb_lower'] = float(bb_low)
            breakdown['bb_mid'] = float(bb_mid)

            if 0.3 <= bb_position <= 0.7:
                volatility_score += self.SCORE_BB_POSITION
            elif bb_position < 0.3:
                if not is_downtrend:
                    volatility_score += 3
                    comments.append("BB하단")

            atr = AverageTrueRange(high=hist['High'], low=hist['Low'], close=close)
            atr_current = atr.average_true_range().iloc[-1]
            atr_avg = atr.average_true_range().rolling(window=14).mean().iloc[-1]
            if atr_current > atr_avg:
                volatility_score += self.SCORE_ATR_EXPANSION
                breakdown['atr_score'] = self.SCORE_ATR_EXPANSION

            breakdown['atr_value'] = float(atr_current)
            breakdown['volatility_score'] = volatility_score
            score += volatility_score

            # 5. 가격 패턴 (5점)
            pattern_score = 0
            high_52w = close.rolling(window=252).max().iloc[-1] if len(close) >= 252 else close.max()
            low_52w = close.rolling(window=252).min().iloc[-1] if len(close) >= 252 else close.min()
            price_position = (current_price - low_52w) / (high_52w - low_52w) if (high_52w - low_52w) > 0 else 0.5
            breakdown['price_position'] = price_position

            if price_position >= 0.9:
                pattern_score += self.SCORE_PRICE_POSITION
                comments.append("52주고점근처")
            elif price_position >= 0.7:
                pattern_score += 3
            elif 0.5 <= price_position < 0.7:
                pattern_score += 2

            breakdown['pattern_score'] = pattern_score
            score += pattern_score

            # 6. 상대강도 vs KOSPI (5점, 신규)
            rs_score = 0
            if kospi_hist is not None and len(kospi_hist) >= 60 and len(close) >= 60:
                try:
                    kospi_close = kospi_hist['Close']
                    stock_return_3m = (close.iloc[-1] / close.iloc[-63] - 1) if len(close) >= 63 else (close.iloc[-1] / close.iloc[0] - 1)
                    kospi_return_3m = (kospi_close.iloc[-1] / kospi_close.iloc[-63] - 1) if len(kospi_close) >= 63 else (kospi_close.iloc[-1] / kospi_close.iloc[0] - 1)
                    rs_ratio = stock_return_3m - kospi_return_3m

                    breakdown['rs_ratio'] = round(rs_ratio * 100, 1)

                    if rs_ratio > 0.15:
                        rs_score = self.SCORE_RS_STRONG
                        comments.append(f"RS강세+{rs_ratio*100:.0f}%")
                    elif rs_ratio > 0.05:
                        rs_score = self.SCORE_RS_GOOD
                        comments.append(f"RS양호+{rs_ratio*100:.0f}%")
                    elif rs_ratio > -0.05:
                        rs_score = self.SCORE_RS_NEUTRAL
                except Exception:
                    pass

            breakdown['rs_score'] = rs_score
            score += rs_score

            breakdown['is_downtrend'] = is_downtrend
            if is_downtrend:
                comments.append("⚠하락추세")

        except Exception as e:
            print(f"Technical analysis error: {e}")

        return score, comments, breakdown

    # ================================================================
    # 거래대금 유동성 보너스
    # ================================================================
    def _get_trading_value_bonus(self, info):
        """거래대금 유동성 티어 보너스"""
        trading_value = info.get('tradingValue', 0)
        if not trading_value:
            trading_value = info.get('currentPrice', 0) * info.get('averageVolume', 0)

        if trading_value >= self.TRADING_VALUE_HOT:
            return self.BONUS_TRADING_HOT, "Hot"
        elif trading_value >= self.TRADING_VALUE_ACTIVE:
            return self.BONUS_TRADING_ACTIVE, "Active"
        elif trading_value >= self.TRADING_VALUE_NORMAL:
            return 0, "Normal"
        else:
            return self.BONUS_TRADING_THIN, "Thin"

    # ================================================================
    # 판정
    # ================================================================
    def _get_verdict(self, total_score, market_regime='neutral'):
        if market_regime == 'bull':
            strong_buy_threshold = 85
            buy_threshold = 75
            hold_threshold = 65
        elif market_regime == 'bear':
            strong_buy_threshold = 75
            buy_threshold = 65
            hold_threshold = 55
        else:
            strong_buy_threshold = 80
            buy_threshold = 70
            hold_threshold = 60

        if total_score >= strong_buy_threshold:
            return "Strong Buy ★"
        elif total_score >= buy_threshold:
            return "Buy"
        elif total_score >= hold_threshold:
            return "Hold"
        else:
            return "Avoid"

    # ================================================================
    # 섹터 순환매 분석 (KOSPI 섹터 ETF 기반)
    # ================================================================
    def _analyze_sector_rotation(self):
        """섹터 순환매 분석 — 섹터 ETF 모멘텀 기반"""
        try:
            import yfinance as yf
            etf_tickers = list(self.SECTOR_ETF_MAP.values())
            data = yf.download(etf_tickers, period='1mo', progress=False)

            if data.empty:
                return {}

            results = {}
            for sector, etf in self.SECTOR_ETF_MAP.items():
                try:
                    if len(self.SECTOR_ETF_MAP) > 1:
                        close = data['Close'][etf].dropna()
                    else:
                        close = data['Close'].dropna()
                    if len(close) < 10:
                        continue

                    week_return = (close.iloc[-1] / close.iloc[-5] - 1) * 100
                    recent_5d = (close.iloc[-1] / close.iloc[-5] - 1) * 100
                    prev_5d = (close.iloc[-6] / close.iloc[-10] - 1) * 100
                    acceleration = recent_5d - prev_5d

                    results[sector] = {
                        'etf': etf,
                        'week_return': round(week_return, 2),
                        'acceleration': round(acceleration, 2),
                    }
                except Exception:
                    continue

            if not results:
                return {}

            sorted_sectors = sorted(results.items(), key=lambda x: x[1]['week_return'], reverse=True)
            total = len(sorted_sectors)
            top_cutoff = max(total // 3, 1)
            bottom_cutoff = total - top_cutoff

            for rank, (sector, info) in enumerate(sorted_sectors):
                info['rank'] = rank + 1
                acc = info['acceleration']

                if rank < top_cutoff:
                    if acc > 0:
                        info['rotation_bonus'] = self.ROTATION_BONUS_INFLOW
                        info['phase'] = '수급유입'
                    else:
                        info['rotation_bonus'] = self.ROTATION_PENALTY_OVERHEAT
                        info['phase'] = '과열주의'
                elif rank >= bottom_cutoff:
                    if acc > 0:
                        info['rotation_bonus'] = self.ROTATION_BONUS_TURNING
                        info['phase'] = '순환매 기대'
                    else:
                        info['rotation_bonus'] = self.ROTATION_PENALTY_COLD
                        info['phase'] = '소외 지속'
                else:
                    if acc > 0.5:
                        info['rotation_bonus'] = self.ROTATION_BONUS_WATCHING
                        info['phase'] = '관심'
                    else:
                        info['rotation_bonus'] = 0
                        info['phase'] = '중립'

            return dict(sorted_sectors)

        except Exception as e:
            print(f"  ⚠️ 섹터 순환매 분석 실패: {e}")
            return {}

    # ================================================================
    # 시장 레짐 감지 (KOSPI 기반)
    # ================================================================
    def _detect_market_regime(self):
        try:
            from ta.trend import ADXIndicator

            hist = self.data_provider.get_market_index(period='1y')
            if len(hist) < 120:
                return 'neutral', {}, "데이터 부족"

            close = hist['Close']
            current_price = close.iloc[-1]

            ma60 = close.rolling(window=60).mean().iloc[-1]
            ma120 = close.rolling(window=120).mean().iloc[-1]

            price_3m_ago = close.iloc[-63] if len(close) >= 63 else close.iloc[0]
            trend_3m = (current_price - price_3m_ago) / price_3m_ago

            price_6m_ago = close.iloc[-126] if len(close) >= 126 else close.iloc[0]
            trend_6m = (current_price - price_6m_ago) / price_6m_ago

            adx = ADXIndicator(high=hist['High'], low=hist['Low'], close=close)
            adx_value = adx.adx().iloc[-1]

            bull_signals = 0
            bear_signals = 0

            if current_price > ma120:
                bull_signals += 1
            else:
                bear_signals += 1
            if ma60 > ma120:
                bull_signals += 1
            else:
                bear_signals += 1
            if trend_3m > 0.05:
                bull_signals += 1
            elif trend_3m < -0.05:
                bear_signals += 1
            if trend_6m > 0.10:
                bull_signals += 1
            elif trend_6m < -0.10:
                bear_signals += 1

            if adx_value < 20:
                regime = 'sideways'
                regime_kr = '횡보장'
                regime_emoji = '↔️'
            elif bull_signals >= 3:
                regime = 'bull'
                regime_kr = '상승장'
                regime_emoji = '📈'
            elif bear_signals >= 3:
                regime = 'bear'
                regime_kr = '하락장'
                regime_emoji = '📉'
            else:
                regime = 'neutral'
                regime_kr = '중립'
                regime_emoji = '➡️'

            details = {
                'current': current_price,
                'ma60': ma60,
                'ma120': ma120,
                'trend_3m': trend_3m * 100,
                'trend_6m': trend_6m * 100,
                'adx': adx_value,
                'bull_signals': bull_signals,
                'bear_signals': bear_signals
            }

            description = f"{regime_emoji} {regime_kr} (KOSPI: {current_price:,.0f}, 3개월: {trend_3m*100:+.1f}%, ADX: {adx_value:.0f})"
            return regime, details, description

        except Exception as e:
            print(f"Market regime detection error: {e}")
            return 'neutral', {}, "감지 실패"

    def _apply_regime_adjustment(self, tech_score, fund_score, regime, is_downtrend=False, tech_breakdown=None):
        # 하락추세 페널티 (펀더멘털 품질 차등)
        trend_penalty_applied = False
        if is_downtrend and tech_score > 0:
            if fund_score >= 40:
                penalty = 0.9 if regime == 'bear' else 0.85
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}% (우량주 경감)"
            elif fund_score >= 30:
                penalty = 0.8 if regime == 'bear' else 0.7
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}%"
            else:
                penalty = 0.7 if regime == 'bear' else 0.5
                trend_penalty_msg = f"하락추세 페널티 -{int((1-penalty)*100)}% (펀더 약세 강화)"
            tech_score = int(tech_score * penalty)
            trend_penalty_applied = True
        else:
            trend_penalty_msg = ""

        # Growth/Value 기본 가중치
        if self.analysis_mode == 'growth':
            base_fund_w = self.GROWTH_FUND_WEIGHT   # 0.8
            base_tech_w = self.GROWTH_TECH_WEIGHT   # 1.2
        elif self.analysis_mode == 'value':
            base_fund_w = self.VALUE_FUND_WEIGHT    # 1.3
            base_tech_w = self.VALUE_TECH_WEIGHT    # 0.7
        else:
            base_fund_w, base_tech_w = 1.0, 1.0

        # 시장상태 가중치
        if regime == 'bull':
            regime_fund_w, regime_tech_w = 0.8, 1.2
            adjustment = "상승장: 기술↑ 펀더↓"
        elif regime == 'bear':
            regime_fund_w, regime_tech_w = 1.2, 0.8
            adjustment = "하락장: 기술↓ 펀더↑"
        elif regime == 'sideways':
            regime_fund_w, regime_tech_w = 1.0, 1.0
            adjustment = "횡보장: 균등"
        else:
            regime_fund_w, regime_tech_w = 1.0, 1.0
            adjustment = "중립"

        # 통합 가중치 (평균으로 합산 → 총합 보존)
        final_fund_w = (base_fund_w + regime_fund_w) / 2
        final_tech_w = (base_tech_w + regime_tech_w) / 2

        fund_score = int(fund_score * final_fund_w)
        tech_score = int(tech_score * final_tech_w)

        # 상한선
        fund_score = min(fund_score, 65)
        tech_score = min(tech_score, 65)

        mode_label = "성장" if self.analysis_mode == 'growth' else "가치"
        adjustment = f"{mode_label}({base_fund_w}/{base_tech_w}) + {adjustment}"

        if trend_penalty_applied:
            adjustment = f"{trend_penalty_msg} + {adjustment}"

        return tech_score, fund_score, adjustment

    # ================================================================
    # 역발상 + 스마트 진입/청산
    # ================================================================
    def _apply_contrarian_adjustment(self, fund_score, tech_breakdown, sector_name):
        """하이브리드 전략: 과매도 우량주 보너스, 과열주 감점 (US v2.0 강화)"""
        adjustment = 0
        contrarian_comment = ""
        rsi = tech_breakdown.get('rsi_value', 50)
        volume_ratio = tech_breakdown.get('volume_ratio', 1.0)

        quality_sectors = [
            'AI/반도체', '전기전자', '2차전지', '바이오', 'K-플랫폼', '방산', '조선',
            # 가치주 방어 섹터 (포트폴리오 헤징 역할)
            '금융', '통신', '유틸리티',
        ]

        # 과매도 조건 강화: Fund≥35 (기존 30), 거래량 폭증 시 추가 보너스
        if rsi < self.RSI_OVERSOLD:
            if fund_score >= 35:
                if sector_name in quality_sectors:
                    adjustment = self.SCORE_OVERSOLD_QUALITY_BONUS
                    if volume_ratio >= 2.0:
                        adjustment += 2  # 항복매도(Capitulation) 거래량 동반
                    contrarian_comment = "🎯저가매수기회"
                else:
                    adjustment = self.SCORE_OVERSOLD_QUALITY_BONUS // 2
                    contrarian_comment = "💎저평가"
            elif fund_score >= 25:
                adjustment = 3
                contrarian_comment = "💎약한저평가"
        # 과열 조건 강화: RSI>75 → 더 강한 감점
        elif rsi > 75:
            adjustment = self.SCORE_OVERBOUGHT_PENALTY  # -8
            if volume_ratio < 1.0:
                adjustment -= 2  # 거래량 감소 동반 과열 = 추가 감점
            contrarian_comment = "⚠️과열주의"
        elif rsi > self.RSI_OVERBOUGHT:  # 70-75 구간: 경미한 감점
            adjustment = -3
            contrarian_comment = "⚡과열경계"

        return adjustment, contrarian_comment

    # ================================================================
    # 스윙 저점/고점 탐지 (US v2.0 동기화)
    # ================================================================
    def _find_swing_lows(self, hist, lookback=60, order=5):
        """최근 N일 로우에서 스윙 저점(지지선) 탐지"""
        lows = hist['Low'].iloc[-lookback:]
        swing_lows = []
        for i in range(order, len(lows) - order):
            if all(lows.iloc[i] <= lows.iloc[i - j] for j in range(1, order + 1)) and \
               all(lows.iloc[i] <= lows.iloc[i + j] for j in range(1, order + 1)):
                swing_lows.append(float(lows.iloc[i]))
        return sorted(set(swing_lows))

    def _find_swing_highs(self, hist, lookback=60, order=5):
        """최근 N일 하이에서 스윙 고점(저항선) 탐지"""
        highs = hist['High'].iloc[-lookback:]
        swing_highs = []
        for i in range(order, len(highs) - order):
            if all(highs.iloc[i] >= highs.iloc[i - j] for j in range(1, order + 1)) and \
               all(highs.iloc[i] >= highs.iloc[i + j] for j in range(1, order + 1)):
                swing_highs.append(float(highs.iloc[i]))
        return sorted(set(swing_highs))

    @staticmethod
    def _nearest_below(levels, price):
        """현재가 아래 가장 가까운 레벨"""
        candidates = [l for l in levels if l < price]
        return max(candidates) if candidates else None

    @staticmethod
    def _nearest_above(levels, price):
        """현재가 위 가장 가까운 레벨"""
        candidates = [l for l in levels if l > price]
        return min(candidates) if candidates else None

    def _validate_risk_reward(self, buy_price, target_price, stop_loss, atr, swing_highs):
        """R:R >= 2.0 보장, 최대 손절 7%"""
        max_stop = buy_price * 0.93
        if stop_loss < max_stop:
            stop_loss = max_stop

        risk = buy_price - stop_loss
        reward = target_price - buy_price
        if risk > 0 and reward / risk < 2.0:
            farther = [r for r in swing_highs if r > target_price]
            if farther:
                target_price = min(farther)
            elif atr > 0:
                target_price = buy_price + (3.0 * atr)
            else:
                target_price = buy_price * 1.12

        return target_price, stop_loss

    def _calculate_smart_entry_exit(self, current_price, contrarian_adj, hist, tech_breakdown):
        """스윙매매 특화 진입/청산 전략 (기술적 레벨 기반, US v2.0 동기화)"""
        try:
            if len(hist) < 20:
                return None, None, None, "데이터 부족"

            ma20 = tech_breakdown.get('ma20', 0)
            ma60 = tech_breakdown.get('ma60', 0)
            bb_upper = tech_breakdown.get('bb_upper', 0)
            bb_lower = tech_breakdown.get('bb_lower', 0)
            atr = tech_breakdown.get('atr_value', 0)

            swing_lows = self._find_swing_lows(hist)
            swing_highs = self._find_swing_highs(hist)
            nearest_support = self._nearest_below(swing_lows, current_price)
            nearest_resistance = self._nearest_above(swing_highs, current_price)

            # ========== Tier 1: 역발상 매수 (과매도 우량주) ==========
            if contrarian_adj > 0:
                if bb_lower > 0 and bb_lower >= current_price * 0.97:
                    buy_price = bb_lower
                else:
                    buy_price = current_price

                if nearest_resistance and nearest_resistance > buy_price * 1.03:
                    target_price = nearest_resistance
                elif bb_upper > 0 and bb_upper > buy_price * 1.03:
                    target_price = bb_upper
                else:
                    target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.08

                atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                struct_stop = nearest_support * 0.99 if nearest_support else atr_stop
                stop_loss = max(atr_stop, struct_stop)
                if stop_loss > buy_price * 0.98:
                    stop_loss = buy_price * 0.98
                if stop_loss >= buy_price:
                    stop_loss = buy_price * 0.95

                target_price, stop_loss = self._validate_risk_reward(
                    buy_price, target_price, stop_loss, atr, swing_highs)
                strategy = "🎯 역발상매수(기술적지지)"

            # ========== Tier 2: 조정대기 (과열주) ==========
            elif contrarian_adj < 0:
                candidates = []
                if ma20 > 0 and ma20 < current_price:
                    candidates.append(ma20)
                if nearest_support and nearest_support < current_price:
                    candidates.append(nearest_support)
                if atr > 0:
                    candidates.append(current_price - (2.0 * atr))

                buy_price = max(candidates) if candidates else current_price * 0.95

                if nearest_resistance and nearest_resistance > buy_price * 1.03:
                    target_price = nearest_resistance
                elif bb_upper > 0:
                    target_price = bb_upper
                else:
                    target_price = buy_price * 1.08

                atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                struct_stop = nearest_support * 0.99 if nearest_support else atr_stop
                stop_loss = max(atr_stop, struct_stop)
                if stop_loss >= buy_price:
                    stop_loss = buy_price * 0.95

                target_price, stop_loss = self._validate_risk_reward(
                    buy_price, target_price, stop_loss, atr, swing_highs)
                strategy = "⚠️ 조정대기(진입조건가)"

            # ========== Tier 3: 세분화 전략 (일반종목) ==========
            else:
                rsi = tech_breakdown.get('rsi_value', 50)
                ma120 = tech_breakdown.get('ma120', 0)

                uptrend = (ma20 > 0 and ma60 > 0 and ma20 > ma60)
                price_above_ma20 = (ma20 > 0 and current_price > ma20)
                sideways = (ma20 > 0 and ma60 > 0 and abs(ma20 - ma60) / ma60 < 0.02)
                weak = (ma60 > 0 and current_price < ma60) or rsi < 40

                # --- Tier 3A: 추세추종 ---
                if uptrend and price_above_ma20 and rsi >= 50:
                    buy_price = current_price
                    if nearest_resistance and nearest_resistance > current_price * 1.02:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price * 1.02:
                        target_price = bb_upper
                    else:
                        target_price = current_price + (2.0 * atr) if atr > 0 else current_price * 1.08
                    atr_stop = current_price - (2.0 * atr) if atr > 0 else current_price * 0.95
                    ma20_stop = ma20 * 0.99 if ma20 > 0 else atr_stop
                    stop_loss = max(atr_stop, ma20_stop)
                    if stop_loss > current_price * 0.98:
                        stop_loss = current_price * 0.98
                    if stop_loss >= current_price:
                        stop_loss = current_price * 0.95
                    target_price, stop_loss = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = "📈 추세추종(MA20↑)"

                # --- Tier 3B: 풀백매수 ---
                elif uptrend and not price_above_ma20:
                    support_candidates = []
                    if ma20 > 0 and ma20 < current_price * 1.03:
                        support_candidates.append(('MA20', ma20))
                    if bb_lower > 0 and bb_lower < current_price:
                        support_candidates.append(('BB하단', bb_lower))
                    if nearest_support and nearest_support < current_price:
                        support_candidates.append(('스윙저점', nearest_support))
                    if support_candidates:
                        best_label, best_support = max(support_candidates, key=lambda x: x[1])
                        buy_price = best_support
                        strategy_suffix = best_label
                    else:
                        buy_price = ma20 if ma20 > 0 else current_price
                        strategy_suffix = "MA20"
                    if nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price:
                        target_price = bb_upper
                    else:
                        target_price = buy_price + (2.0 * atr) if atr > 0 else buy_price * 1.08
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.98:
                        stop_loss = buy_price * 0.98
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"📊 풀백매수({strategy_suffix})"

                # --- Tier 3C: 박스권하단 ---
                elif sideways or (not uptrend and not weak):
                    support_candidates = []
                    if bb_lower > 0 and bb_lower < current_price:
                        support_candidates.append(('BB하단', bb_lower))
                    if nearest_support and nearest_support < current_price:
                        support_candidates.append(('스윙저점', nearest_support))
                    if ma60 > 0 and ma60 < current_price:
                        support_candidates.append(('MA60', ma60))
                    if support_candidates:
                        best_label, best_support = max(support_candidates, key=lambda x: x[1])
                        buy_price = best_support
                        strategy_suffix = best_label
                    else:
                        buy_price = current_price * 0.97
                        strategy_suffix = "지지선"
                    if nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    elif bb_upper > 0 and bb_upper > current_price:
                        target_price = bb_upper
                    else:
                        target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.06
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (2.0 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.98:
                        stop_loss = buy_price * 0.98
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"📦 박스권하단({strategy_suffix})"

                # --- Tier 3D: 반등대기 ---
                else:
                    support_candidates = []
                    if nearest_support and nearest_support < current_price:
                        support_candidates.append(('스윙저점', nearest_support))
                    if ma120 > 0 and ma120 < current_price:
                        support_candidates.append(('MA120', ma120))
                    if bb_lower > 0 and bb_lower < current_price:
                        support_candidates.append(('BB하단', bb_lower))
                    if support_candidates:
                        best_label, best_support = max(support_candidates, key=lambda x: x[1])
                        buy_price = best_support
                        strategy_suffix = best_label
                    else:
                        buy_price = current_price * 0.95
                        strategy_suffix = "지지확인"
                    if ma60 > 0 and ma60 > current_price:
                        target_price = ma60
                    elif nearest_resistance and nearest_resistance > current_price:
                        target_price = nearest_resistance
                    else:
                        target_price = buy_price + (1.5 * atr) if atr > 0 else buy_price * 1.06
                    supports_below = [l for l in swing_lows if l < buy_price]
                    struct_stop = max(supports_below) * 0.99 if supports_below else buy_price * 0.95
                    atr_stop = buy_price - (1.5 * atr) if atr > 0 else buy_price * 0.95
                    stop_loss = max(atr_stop, struct_stop)
                    if stop_loss > buy_price * 0.97:
                        stop_loss = buy_price * 0.97
                    if stop_loss >= buy_price:
                        stop_loss = buy_price * 0.95
                    target_price, stop_loss = self._validate_risk_reward(
                        buy_price, target_price, stop_loss, atr, swing_highs)
                    strategy = f"🔄 반등대기({strategy_suffix})"

            return buy_price, target_price, stop_loss, strategy

        except Exception:
            return None, None, None, "계산 실패"

    def _get_current_price(self, info, hist):
        return info.get('currentPrice') or info.get('regularMarketPrice') or (int(hist['Close'].iloc[-1]) if not hist.empty else 0)

    def _get_market_status_and_prices(self, info):
        """시장 상태 (한국장: KST 09:00-15:30, 프리/애프터 없음)"""
        try:
            kst = pytz.timezone('Asia/Seoul')
            now_kst = datetime.now(kst)
            hour = now_kst.hour
            minute = now_kst.minute

            if (hour == 9 and minute >= 0) or (9 < hour < 15) or (hour == 15 and minute <= 30):
                market_status = 'regular'
            else:
                market_status = 'closed'

            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            previous_close = info.get('previousClose', 0)

            return {
                'status': market_status,
                'current_price': current_price,
                'previous_close': previous_close
            }
        except Exception:
            return {
                'status': 'unknown',
                'current_price': info.get('currentPrice', 0),
                'previous_close': info.get('previousClose', 0)
            }

    # ================================================================
    # 개별 종목 분석
    # ================================================================
    def _analyze_single_stock(self, code, kospi_hist=None):
        info = self.data_provider.get_info(code)
        # 가치주 모드에서 배당귀족 판별용 코드 삽입
        info['_code'] = code
        hist = self.data_provider.get_history(code, period='1y')

        if hist.empty or len(hist) < 20:
            return None

        current_price = self._get_current_price(info, hist)

        fund_score, fund_comments, fund_breakdown = self._get_fundamental_score(info)
        tech_score, tech_comments, tech_breakdown = self._get_technical_score(hist, current_price, kospi_hist)

        contrarian_adj, contrarian_comment = self._apply_contrarian_adjustment(
            fund_score, tech_breakdown, fund_breakdown.get('sector_name', ''))

        # 거래대금 보너스
        trading_bonus, trading_tier = self._get_trading_value_bonus(info)

        total_score = fund_score + tech_score + contrarian_adj + trading_bonus

        # 스마트 진입/청산 전략 (US v2.0)
        buy_price, target, stop_loss, strategy = self._calculate_smart_entry_exit(
            current_price, contrarian_adj, hist, tech_breakdown)

        market_info = self._get_market_status_and_prices(info)
        verdict = self._get_verdict(total_score)

        all_comments = fund_comments + tech_comments
        if contrarian_comment:
            all_comments.insert(0, contrarian_comment)
        if trading_bonus != 0:
            all_comments.append(f"유동성:{trading_tier}({'+' if trading_bonus > 0 else ''}{trading_bonus})")
        comment = ", ".join(all_comments[:4]) if all_comments else "-"

        result = {
            'ticker': code,
            'company_name': info.get('shortName', ''),
            'score': total_score,
            'fund_score': fund_score,
            'tech_score': tech_score,
            'contrarian_adjustment': contrarian_adj,
            'trading_bonus': trading_bonus,
            'trading_tier': trading_tier,
            'fund_breakdown': fund_breakdown,
            'tech_breakdown': tech_breakdown,
            'verdict': verdict,
            'price': current_price,
            'market_info': market_info,
            'buy_price': buy_price,
            'buy_strategy': strategy,
            'target': target,
            'stop_loss': stop_loss,
            'comment': comment
        }

        # 애널리스트 코멘트 생성
        result['analyst_comment'] = self._generate_analyst_comment(result)

        return result

    def _generate_analyst_comment(self, stock_data):
        """Titan 분석 데이터 기반 애널리스트 톤 코멘트 생성"""
        parts = []
        fund_bd = stock_data.get('fund_breakdown', {})
        tech_bd = stock_data.get('tech_breakdown', {})

        # 1) 펀더멘털 요약
        roe = fund_bd.get('roe_value', 0)
        opm = fund_bd.get('opm_value', 0)
        rev_growth = fund_bd.get('revenue_growth_value')

        fund_parts = []
        if roe >= 20:
            fund_parts.append(f"ROE {roe:.1f}%로 수익성 최상위권")
        elif roe >= 10:
            fund_parts.append(f"ROE {roe:.1f}%로 양호한 수익성")
        elif roe > 0:
            fund_parts.append(f"ROE {roe:.1f}%로 수익성 보통")

        if opm >= 25:
            fund_parts.append(f"영업이익률 {opm:.1f}%의 고마진 구조")
        elif opm >= 15:
            fund_parts.append(f"영업이익률 {opm:.1f}%로 안정적")

        if rev_growth is not None:
            if rev_growth >= 30:
                fund_parts.append(f"매출 YoY +{rev_growth:.0f}% 고성장")
            elif rev_growth >= 10:
                fund_parts.append(f"매출 YoY +{rev_growth:.0f}% 성장세")

        if fund_parts:
            parts.append(". ".join(fund_parts) + ".")

        # 2) 기술적 요약
        rsi = tech_bd.get('rsi_value', 50)
        ma20 = tech_bd.get('ma20', 0)
        ma60 = tech_bd.get('ma60', 0)
        price = stock_data.get('price', 0)

        tech_parts = []
        if ma20 and ma60:
            if ma20 > ma60 and price > ma20:
                tech_parts.append("MA20>MA60 정배열 상태로 상승 추세 진행 중")
            elif ma20 > ma60:
                tech_parts.append("MA20>MA60 정배열이나 단기 조정 구간")
            elif ma20 < ma60 and price < ma20:
                tech_parts.append("MA20<MA60 역배열로 약세 흐름")
            else:
                tech_parts.append("이동평균 수렴 구간으로 방향성 탐색 중")

        if rsi <= 30:
            tech_parts.append(f"RSI {rsi:.0f}으로 과매도 영역 → 반등 가능성")
        elif rsi >= 70:
            tech_parts.append(f"RSI {rsi:.0f}으로 과매수 영역 → 단기 조정 유의")
        elif rsi >= 50:
            tech_parts.append(f"RSI {rsi:.0f}으로 매수세 우위")
        else:
            tech_parts.append(f"RSI {rsi:.0f}으로 매도세 우위")

        if tech_parts:
            parts.append(". ".join(tech_parts) + ".")

        # 3) 전략 제안
        strategy = stock_data.get('buy_strategy', '')
        contrarian = stock_data.get('contrarian_adjustment', 0)

        if contrarian > 0:
            parts.append("역발상 매수 시그널 감지 → 저가 매수 기회로 판단.")
        elif '추세추종' in strategy:
            parts.append("상승 추세 지속 중으로 추세 추종 매매가 유효.")
        elif '풀백매수' in strategy:
            parts.append("상승 추세 내 조정 구간으로 분할 매수 접근 권장.")
        elif '박스권' in strategy:
            parts.append("횡보 구간 하단 접근 중으로 지지선 확인 후 매수 검토.")
        elif '반등대기' in strategy:
            parts.append("하락 추세로 반등 신호 확인 전까지 관망 권장.")
        elif '⚠️' in strategy:
            parts.append("과열 구간으로 신규 진입보다 조정 후 재진입 권장.")

        return " ".join(parts) if parts else ""

    def _save_score_cache(self, results, report_type):
        """Titan 분석 점수를 JSON 캐시로 저장 (검색 기능용)"""
        import json
        cache_type = 'growth' if 'Growth' in report_type else 'value'
        cache_file = f"titan_kr_scores_{cache_type}.json"
        cache = {}
        for r in results:
            fund_bd = r.get('fund_breakdown', {})
            tech_bd = r.get('tech_breakdown', {})
            cache[r['ticker']] = {
                'score': r.get('score', 0),
                'fund_score': r.get('fund_score', 0),
                'tech_score': r.get('tech_score', 0),
                'price': r.get('price', 0),
                'company_name': r.get('company_name', ''),
                'verdict': r.get('verdict', ''),
                'buy_price': r.get('buy_price'),
                'target_price': r.get('target'),
                'stop_loss': r.get('stop_loss'),
                'strategy': r.get('buy_strategy', ''),
                'comment': r.get('comment', ''),
                'contrarian_adjustment': r.get('contrarian_adjustment', 0),
                'trading_bonus': r.get('trading_bonus', 0),
                'trading_tier': r.get('trading_tier', ''),
                'rotation_bonus': r.get('rotation_bonus', 0),
                'rotation_phase': r.get('rotation_phase', ''),
                'sector_name': fund_bd.get('sector_name', ''),
                'roe_value': fund_bd.get('roe_value'),
                'opm_value': fund_bd.get('opm_value'),
                'revenue_growth_value': fund_bd.get('revenue_growth_value'),
                'peg_value': fund_bd.get('peg_value'),
                'fcf_margin_value': fund_bd.get('fcf_margin_value'),
                'fcf_score': fund_bd.get('fcf_score', 0),
                'dividend_yield_value': fund_bd.get('dividend_yield_value'),
                'dividend_growth_score': fund_bd.get('dividend_growth_score', 0),
                'valuation_method': fund_bd.get('valuation_method', 'PER'),
                'ev_ebitda_value': fund_bd.get('ev_ebitda_value'),
                'per_value': fund_bd.get('per_value'),
                'debt_equity_value': fund_bd.get('debt_equity_value'),
                'beta_value': fund_bd.get('beta_value'),
                'beta_score': fund_bd.get('beta_score', 0),
                'fcf_yield_value': fund_bd.get('fcf_yield_value'),
                'rsi_value': tech_bd.get('rsi_value'),
                'mfi_value': tech_bd.get('mfi_value'),
                'atr_value': tech_bd.get('atr_value'),
                'rs_score': tech_bd.get('rs_score', 0),
                'rs_ratio': tech_bd.get('rs_ratio', 0),
                'ma5': tech_bd.get('ma5'),
                'ma20': tech_bd.get('ma20'),
                'ma60': tech_bd.get('ma60'),
                'ma120': tech_bd.get('ma120'),
                'analyst_comment': r.get('analyst_comment', ''),
            }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        print(f"💾 Titan KR 점수 캐시 저장: {cache_file} ({len(cache)}개 종목)")

    # ================================================================
    # 2단계: 정밀 분석
    # ================================================================
    def stage2_deep_analysis(self, codes):
        print("=" * 70)
        print("📊 STAGE 2: 정밀 분석 (Fundamental + Technical)")
        print("=" * 70)

        print("\n🌍 시장 상태 감지 중...")
        market_regime, regime_details, regime_desc = self._detect_market_regime()
        print(f"   {regime_desc}\n")

        # 🔄 섹터 순환매 분석
        print("🔄 섹터 순환매 분석 중...")
        self.sector_rotation = self._analyze_sector_rotation()
        if self.sector_rotation:
            phases = {}
            for sector, info in self.sector_rotation.items():
                phase = info.get('phase', '중립')
                if phase not in phases:
                    phases[phase] = []
                phases[phase].append(f"{sector}({info['week_return']:+.1f}%)")

            icons = {'수급유입': '🔥', '과열주의': '⚠️', '순환매 기대': '⚡', '소외 지속': '❄️', '관심': '👀', '중립': '➖'}
            for phase in ['수급유입', '순환매 기대', '관심', '중립', '과열주의', '소외 지속']:
                if phase in phases:
                    print(f"   {icons.get(phase, '')} {phase}: {', '.join(phases[phase])}")
            print()

        # KOSPI 히스토리 (RS vs KOSPI용)
        print("📈 KOSPI 지수 로딩 중...")
        kospi_hist = self.data_provider.get_market_index(period='1y')
        if not kospi_hist.empty:
            print(f"   KOSPI: {kospi_hist['Close'].iloc[-1]:,.0f} ({len(kospi_hist)}일)")
        else:
            print("   ⚠️ KOSPI 데이터 없음 (RS 분석 생략)")
        print()

        results = []
        total = len(codes)

        for i, code in enumerate(codes, 1):
            try:
                print(f"분석 중: {i}/{total} - {code}")
                result = self._analyze_single_stock(code, kospi_hist=kospi_hist)
                if result:
                    is_downtrend = result.get('tech_breakdown', {}).get('is_downtrend', False)
                    tech_adjusted, fund_adjusted, adjustment_msg = self._apply_regime_adjustment(
                        result['tech_score'], result['fund_score'],
                        market_regime, is_downtrend=is_downtrend)

                    # 🔄 섹터 순환매 보너스
                    sector_name = result.get('fund_breakdown', {}).get('sector_name', '')
                    # KR 섹터명 → ETF 섹터 매핑
                    kr_sector_to_etf = {
                        'AI/반도체': 'Technology', '전기전자': 'Technology', '2차전지': 'Technology',
                        '금융': 'Financial Services', '은행': 'Financial Services', '보험': 'Financial Services',
                        '자동차': 'Industrials', '기계': 'Industrials', '조선': 'Industrials',
                        '바이오': 'Healthcare', '의약품': 'Healthcare',
                        '화학': 'Basic Materials', '철강': 'Basic Materials', '소재': 'Basic Materials',
                        '에너지': 'Energy', '정유': 'Energy',
                    }
                    etf_sector = ''
                    for kw, mapped in kr_sector_to_etf.items():
                        if kw in sector_name:
                            etf_sector = mapped
                            break
                    rotation_info = self.sector_rotation.get(etf_sector, {})
                    rotation_bonus = rotation_info.get('rotation_bonus', 0)
                    rotation_phase = rotation_info.get('phase', '중립')
                    result['rotation_bonus'] = rotation_bonus
                    result['rotation_phase'] = rotation_phase

                    total_score_adjusted = fund_adjusted + tech_adjusted + result['contrarian_adjustment'] + result.get('trading_bonus', 0) + rotation_bonus

                    result['market_regime'] = market_regime
                    result['regime_description'] = regime_desc
                    result['regime_adjustment'] = adjustment_msg
                    result['tech_score_original'] = result['tech_score']
                    result['fund_score_original'] = result['fund_score']
                    result['tech_score'] = tech_adjusted
                    result['fund_score'] = fund_adjusted
                    result['score'] = total_score_adjusted
                    result['verdict'] = self._get_verdict(total_score_adjusted, market_regime)

                    results.append(result)

                time.sleep(0.3)
            except Exception as e:
                print(f"  ⚠️  {code} 분석 실패: {e}")

        print(f"\n✅ 2단계 완료: {len(results)}개 종목 분석 완료")
        print(f"📊 시장 상태: {regime_desc}\n")
        return results

    # ================================================================
    # 결과 출력
    # ================================================================
    def display_results(self, results, min_score=60):
        print("=" * 100)
        print(f"🎯 PROJECT TITAN KR - 최종 결과 (Score >= {min_score})")
        print(f"📅 분석 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)

        filtered = [r for r in results if r['score'] >= min_score]
        filtered.sort(key=lambda x: x['score'], reverse=True)

        if not filtered:
            print(f"⚠️  Score >= {min_score} 이상인 종목이 없습니다.")
            return

        table_data = []
        for r in filtered:
            table_data.append([
                f"{r['ticker']} {r['company_name']}",
                r['score'],
                r['verdict'],
                f"₩{r['price']:,}",
                f"₩{int(r['buy_price']):,}" if r.get('buy_price') else "N/A",
                f"₩{int(r['stop_loss']):,}" if r['stop_loss'] else "N/A",
                r['comment']
            ])

        headers = ['종목', 'Score', 'Verdict', '현재가', '매수신호가', '손절가', 'Comment']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print(f"\n📊 총 {len(filtered)}개 유망 종목 발견")

    # ================================================================
    # HTML 리포트 생성
    # ================================================================
    def generate_html_report(self, results, report_type="KOSPI Growth", filename="report.html", min_score=50):
        filtered = [r for r in results if r['score'] >= min_score]
        filtered.sort(key=lambda x: x['score'], reverse=True)

        _kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(_kst)

        market_regime = filtered[0].get('market_regime', 'neutral') if filtered else 'neutral'
        if market_regime == 'bull':
            strong_buy_threshold = 85
            buy_threshold = 75
        elif market_regime == 'bear':
            strong_buy_threshold = 75
            buy_threshold = 65
        else:
            strong_buy_threshold = 80
            buy_threshold = 70

        if "Growth" in report_type:
            primary_color = "#E85D75"
            emoji = "🚀"
        elif "Value" in report_type:
            primary_color = "#E8A838"
            emoji = "💰"
        else:
            primary_color = "#7B68EE"
            emoji = "⭐"

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_type} - Titan KR - {now.strftime("%Y-%m-%d")}</title>
    <link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
    <link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
    <style>
        :root {{
            --bg: #f7f8fa;
            --surface: #ffffff;
            --text: #191f28;
            --text-sub: #8b95a1;
            --text-muted: #b0b8c1;
            --border: #e5e8eb;
            --accent: {primary_color};
            --accent-light: {('#edf2ff' if 'E85D75' in primary_color else '#fff8e1' if 'E8A838' in primary_color else '#f3f0ff')};
            --green: #20c997;
            --red: #f06595;
            --radius: 16px;
            --shadow: 0 2px 8px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
            --shadow-hover: 0 8px 24px rgba(0,0,0,0.08);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Pretendard Variable', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 20px;
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        .market-switcher {{
            display: flex; justify-content: center; gap: 4px; margin-bottom: 20px;
            background: var(--surface); border-radius: 12px; padding: 4px;
            box-shadow: var(--shadow); width: fit-content; margin-left: auto; margin-right: auto;
        }}
        .market-btn {{
            padding: 10px 24px; font-size: 0.9em; font-weight: 600; font-family: inherit;
            border: none; border-radius: 10px; cursor: pointer; transition: all 0.2s;
            text-decoration: none; color: var(--text-sub); display: flex; align-items: center; gap: 6px; background: transparent;
        }}
        .market-btn.active {{ background: var(--accent); color: white; }}
        .market-btn:not(.active):hover {{ background: var(--accent-light); color: var(--accent); }}
        .back-link {{
            display: block; text-align: center; margin-bottom: 16px;
            color: var(--text-sub); text-decoration: none; font-weight: 600; font-size: 0.9em;
        }}
        .back-link:hover {{ color: var(--accent); }}
        .header {{
            background: var(--surface);
            border-radius: var(--radius);
            padding: 32px;
            margin-bottom: 20px;
            box-shadow: var(--shadow);
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, var(--accent), {('#7c3aed' if 'E85D75' in primary_color else '#f59f00' if 'E8A838' in primary_color else '#9775fa')});
        }}
        .header h1 {{ color: var(--text); font-size: 1.6em; font-weight: 800; margin-top: 8px; letter-spacing: -0.02em; }}
        .header .subtitle {{ color: var(--text-sub); margin-top: 8px; font-size: 0.95em; }}
        .header .date {{ color: var(--text-muted); margin-top: 8px; font-size: 0.85em; }}
        .titan-badge {{
            display: inline-block; background: var(--accent); color: white;
            padding: 4px 12px; border-radius: 8px; font-size: 0.7em; margin-left: 8px; font-weight: 700;
        }}
        .summary {{
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px; margin-bottom: 20px;
        }}
        .summary-card {{
            background: var(--surface); border-radius: var(--radius); padding: 18px;
            box-shadow: var(--shadow); text-align: center;
        }}
        .summary-card .label {{ color: var(--text-sub); margin-bottom: 6px; font-size: 0.85em; }}
        .summary-card .value {{ color: var(--accent); font-size: 1.5em; font-weight: 700; }}
        .stock-card {{
            background: var(--surface); border-radius: var(--radius); padding: 24px;
            margin-bottom: 12px; box-shadow: var(--shadow); position: relative;
            transition: box-shadow 0.2s;
        }}
        .stock-card:hover {{ box-shadow: var(--shadow-hover); }}
        .stock-card .rank {{
            position: absolute; top: 12px; left: 12px;
            background: var(--accent); color: white;
            width: 36px; height: 36px; border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 0.9em;
        }}
        .stock-card h2 {{ color: var(--text); margin-bottom: 8px; padding-left: 48px; font-size: 1.2em; font-weight: 700; }}
        .stock-card .ticker {{ color: var(--accent); font-weight: 700; font-size: 1.05em; }}
        .stock-card .info {{ margin-top: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; }}
        .stock-card .info-item {{ padding: 10px; background: var(--bg); border-radius: 12px; }}
        .stock-card .info-label {{ font-size: 0.8em; color: var(--text-sub); }}
        .stock-card .info-value {{ font-weight: 700; color: var(--text); margin-top: 2px; }}
        .score-badge {{
            background: var(--accent); color: white; padding: 6px 16px; border-radius: 10px;
            float: right; font-weight: 700; font-size: 1em;
        }}
        .score-badge.high {{ background: var(--green); }}
        .score-badge.strong {{ background: #f76707; }}
        .verdict {{
            display: inline-block; padding: 4px 14px; border-radius: 8px;
            font-size: 0.85em; font-weight: 700; margin-top: 8px;
        }}
        .verdict.strong-buy {{ background: #e6fcf5; color: #0ca678; }}
        .verdict.buy {{ background: #e6fcf5; color: var(--green); }}
        .verdict.hold {{ background: #fff9db; color: #e67700; }}
        .comment {{
            margin-top: 12px; padding: 12px 14px; background: var(--bg);
            border-left: 3px solid var(--accent); border-radius: 8px;
            font-size: 0.88em; color: var(--text); line-height: 1.6;
        }}
        .detail-toggle {{
            display: inline-block; margin-top: 10px; padding: 6px 16px;
            background: var(--bg); color: var(--text-sub); border: 1px solid var(--border);
            border-radius: 10px; font-size: 0.84em; font-weight: 600;
            cursor: pointer; transition: all 0.2s; font-family: inherit;
        }}
        .detail-toggle:hover {{ background: var(--accent-light); color: var(--accent); border-color: var(--accent); }}
        .score-breakdown {{ margin: 14px 0; padding: 16px; background: var(--bg); border-radius: 12px; border: 1px solid var(--border); display: none; }}
        .score-breakdown.open {{ display: block; }}
        .score-breakdown h3 {{ color: var(--text); margin-bottom: 12px; font-size: 0.95em; }}
        .breakdown-section {{ margin-bottom: 12px; }}
        .breakdown-title {{ font-weight: 700; color: var(--accent); margin-bottom: 8px; font-size: 0.9em; }}
        .breakdown-items {{ display: grid; gap: 4px; }}
        .breakdown-item {{
            display: grid; grid-template-columns: 1fr auto auto; gap: 10px;
            padding: 8px 12px; background: var(--surface); border-radius: 8px;
            align-items: center; font-size: 0.84em;
        }}
        .breakdown-item .criterion {{ color: var(--text); font-weight: 500; }}
        .breakdown-item .criterion-value {{ color: var(--text-sub); text-align: right; }}
        .breakdown-item .criterion-score {{ color: var(--accent); font-weight: 700; text-align: right; min-width: 50px; }}
        .scoring-btn {{
            display: inline-block; margin-top: 12px; padding: 8px 20px;
            background: var(--text); color: white; border: none; border-radius: 10px;
            font-size: 0.85em; font-weight: 600; cursor: pointer; transition: all 0.2s; font-family: inherit;
        }}
        .scoring-btn:hover {{ opacity: 0.85; transform: translateY(-1px); }}
        .scoring-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; justify-content: center; align-items: center; backdrop-filter: blur(4px); }}
        .scoring-overlay.active {{ display: flex; }}
        .scoring-modal {{ width: 95%; max-width: 1200px; height: 90vh; border-radius: var(--radius); overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3); position: relative; }}
        .scoring-modal iframe {{ width: 100%; height: 100%; border: none; }}
        .scoring-close {{ position: absolute; top: 12px; right: 16px; width: 36px; height: 36px; background: rgba(0,0,0,0.6); color: #fff; border: none; border-radius: 10px; font-size: 1.2em; cursor: pointer; z-index: 10; display: flex; align-items: center; justify-content: center; }}
        .scoring-close:hover {{ background: rgba(240,101,149,0.8); }}
        .analyst-view {{
            margin-top: 14px; padding: 18px 20px;
            background: var(--bg); border: 1px solid var(--border); border-radius: 12px;
        }}
        .analyst-header {{
            font-weight: 700; font-size: 0.92em; color: var(--text);
            margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid var(--border);
        }}
        .analyst-comment {{
            font-size: 0.86em; color: var(--text); line-height: 1.8;
            padding: 12px 14px; background: var(--surface); border-radius: 10px;
            border-left: 3px solid var(--accent);
        }}
        .footer {{
            background: var(--surface); border-radius: var(--radius); padding: 20px;
            text-align: center; color: var(--text-muted); margin-top: 24px;
            box-shadow: var(--shadow); font-size: 0.85em; line-height: 1.7;
        }}
        @media (max-width: 768px) {{
            body {{ padding: 12px; }}
            .header {{ padding: 24px 16px; }}
            .header h1 {{ font-size: 1.25em; }}
            .titan-badge {{ display: block; margin: 8px auto 0; width: fit-content; }}
            .summary {{ grid-template-columns: repeat(2, 1fr); gap: 8px; }}
            .summary-card {{ padding: 14px 8px; }}
            .summary-card .value {{ font-size: 1.2em; }}
            .stock-card {{ padding: 18px 14px; }}
            .stock-card .rank {{ width: 30px; height: 30px; font-size: 0.85em; border-radius: 8px; }}
            .stock-card h2 {{ padding-left: 40px; font-size: 1.05em; padding-right: 70px; }}
            .score-badge {{ padding: 5px 12px; font-size: 0.9em; }}
            .stock-card .info {{ grid-template-columns: repeat(2, 1fr); gap: 6px; }}
            .breakdown-item {{ grid-template-columns: 1fr auto; gap: 4px; font-size: 0.8em; }}
            .breakdown-item .criterion-value {{ display: none; }}
            .comment {{ font-size: 0.82em; }}
            .analyst-comment {{ font-size: 0.82em; padding: 10px 12px; }}
            .scoring-modal {{ width: 100%; height: 95vh; border-radius: 10px; }}
        }}
        @media (max-width: 400px) {{
            .header h1 {{ font-size: 1.1em; }}
            .summary {{ grid-template-columns: 1fr 1fr; gap: 6px; }}
            .stock-card h2 {{ font-size: 0.95em; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="market-switcher">
            <a href="https://redchoeng.github.io/stock-recommendation_2.0/" class="market-btn">US</a>
            <span class="market-btn active">KR</span>
        </div>
        <a href="index.html" class="back-link">&larr; 메인으로</a>
        <div class="header">
            <h1>{report_type} <span class="titan-badge">TITAN KR</span></h1>
            <div class="subtitle">Fundamental + Technical 기반 한국 주식 분석</div>
            <div class="date">{now.strftime("%Y-%m-%d %H:%M")} KST 업데이트</div>
            <button class="scoring-btn" onclick="document.getElementById('scoringOverlay').classList.add('active')">📐 점수 체계 보기</button>
        </div>
        <div id="scoringOverlay" class="scoring-overlay" onclick="if(event.target===this)this.classList.remove('active')">
            <div class="scoring-modal">
                <button class="scoring-close" onclick="document.getElementById('scoringOverlay').classList.remove('active')">&times;</button>
                <iframe src="scoring_system_kr.html"></iframe>
            </div>
        </div>
        <div class="summary">
            <div class="summary-card">
                <div class="label">분석 종목</div>
                <div class="value">{len(results)}개</div>
            </div>
            <div class="summary-card">
                <div class="label">추천 종목 (&ge;{min_score}점)</div>
                <div class="value">{len(filtered)}개</div>
            </div>
            <div class="summary-card">
                <div class="label">Strong Buy (&ge;{strong_buy_threshold}점)</div>
                <div class="value">{len([r for r in filtered if r['score'] >= strong_buy_threshold])}개</div>
            </div>
            <div class="summary-card">
                <div class="label">평균 점수</div>
                <div class="value">{sum(r['score'] for r in filtered) / len(filtered) if filtered else 0:.0f}점</div>
            </div>
            <div class="summary-card" style="grid-column: 1 / -1; background: var(--accent); color: white;">
                <div class="label" style="color: rgba(255,255,255,0.8);">시장 상태 및 평가 기준</div>
                <div class="value" style="font-size: 1em; color: white;">{filtered[0].get('regime_description', 'N/A') if filtered else 'N/A'}<br>
                <span style="font-size: 0.8em; opacity: 0.85;">Strong Buy &ge;{strong_buy_threshold}점 | Buy &ge;{buy_threshold}점</span></div>
            </div>
        </div>
'''

        for idx, stock in enumerate(filtered[:20], 1):
            score_class = 'strong' if stock['score'] >= strong_buy_threshold else ('high' if stock['score'] >= buy_threshold else '')
            verdict_class = stock['verdict'].lower().replace(' ', '-').replace('★', '').strip()

            fund_bd = stock.get('fund_breakdown', {})
            tech_bd = stock.get('tech_breakdown', {})
            market_info = stock.get('market_info', {})

            roe_value = fund_bd.get('roe_value')
            roe_display = f"{roe_value:.1f}%" if roe_value is not None else "N/A"
            opm_value = fund_bd.get('opm_value')
            opm_display = f"{opm_value:.1f}%" if opm_value is not None else "N/A"
            rg_value = fund_bd.get('revenue_growth_value')
            rg_display = f"{rg_value:.1f}%" if rg_value is not None else "N/A"
            is_value_mode = fund_bd.get('dividend_yield_value') is not None or 'Value' in report_type

            html += f'''
        <div class="stock-card">
            <div class="rank">#{idx}</div>
            <span class="score-badge {score_class}">{stock['score']}점</span>
            <h2><span class="ticker">{stock['ticker']}</span> <span style="font-size:0.7em; color:#7B6B4F; font-weight:normal;">{stock.get('company_name', '')}</span></h2>
            <span class="verdict {verdict_class}">{stock['verdict']}</span>

            <button class="detail-toggle" onclick="toggleDetail({idx})">상세 분석 ▼</button>
            <div class="score-breakdown" id="detail-{idx}">
                <h3>📊 점수 상세 분석</h3>
                <div class="breakdown-section">
                    <div class="breakdown-title">펀더멘털 점수: {stock.get('fund_score', 0)}점 / 50점</div>
                    <div class="breakdown-items">''' + (f'''
                        <div class="breakdown-item">
                            <span class="criterion">배당수익률</span>
                            <span class="criterion-value">{(fund_bd.get('dividend_yield_value') or 0):.2f}%</span>
                            <span class="criterion-score">+{fund_bd.get('dividend_yield_score', 0)}점 /10</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">배당 성장력</span>
                            <span class="criterion-value">{'배당귀족' if fund_bd.get('aristocrat_bonus', 0) > 0 else '지속성 평가'}</span>
                            <span class="criterion-score">+{fund_bd.get('dividend_growth_score', 0)}점 /5</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">{"EV/EBITDA" if fund_bd.get("valuation_method") == "EV/EBITDA" else "P/B" if fund_bd.get("valuation_method") == "P/B" else "PER"} (저평가)</span>
                            <span class="criterion-value">{fund_bd.get("valuation_method", "PER")} 지표</span>
                            <span class="criterion-score">+{fund_bd.get('per_score', 0)}점 /12</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">ROE (수익성)</span>
                            <span class="criterion-value">{roe_display}</span>
                            <span class="criterion-score">+{fund_bd.get('roe_score', 0)}점 /8</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">부채비율 (D/E)</span>
                            <span class="criterion-value">{"N/A" if fund_bd.get('debt_equity_value') is None else f"{fund_bd.get('debt_equity_value', 0):.0f}%"}</span>
                            <span class="criterion-score">+{fund_bd.get('debt_equity_score', 0)}점 /8</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">FCF Yield</span>
                            <span class="criterion-value">{"N/A" if fund_bd.get('fcf_yield_value') is None else f"{fund_bd.get('fcf_yield_value', 0):.1f}%"}</span>
                            <span class="criterion-score">+{fund_bd.get('fcf_score', 0)}점 /5</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">Beta (시장민감도)</span>
                            <span class="criterion-value">{"N/A" if fund_bd.get('beta_value') is None else f"{fund_bd.get('beta_value', 0):.2f}"}</span>
                            <span class="criterion-score">+{fund_bd.get('beta_score', 0)}점 /5</span>
                        </div>''' if is_value_mode else f'''
                        <div class="breakdown-item">
                            <span class="criterion">ROE (자기자본이익률)</span>
                            <span class="criterion-value">{roe_display}</span>
                            <span class="criterion-score">+{fund_bd.get('roe_score', 0)}점 /15</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">OPM (영업이익률)</span>
                            <span class="criterion-value">{opm_display}</span>
                            <span class="criterion-score">+{fund_bd.get('opm_score', 0)}점 /10</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">FCF Margin (현금창출)</span>
                            <span class="criterion-value">{"N/A" if fund_bd.get('fcf_margin_value') is None else f"{fund_bd.get('fcf_margin_value', 0):.1f}%"}</span>
                            <span class="criterion-score">+{fund_bd.get('fcf_score', 0)}점 /10</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">매출성장률</span>
                            <span class="criterion-value">{rg_display}</span>
                            <span class="criterion-score">+{fund_bd.get('revenue_growth_score', 0)}점 /10</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">PEG (성장가치)</span>
                            <span class="criterion-value">{"N/A" if fund_bd.get('peg_value') is None else f"{fund_bd.get('peg_value', 0):.2f}"}</span>
                            <span class="criterion-score">+{fund_bd.get('peg_score', 0)}점</span>
                        </div>''') + f'''
                        <div class="breakdown-item">
                            <span class="criterion">섹터</span>
                            <span class="criterion-value">{fund_bd.get('sector_name', 'N/A')}</span>
                            <span class="criterion-score">+{fund_bd.get('sector_score', 0)}점</span>
                        </div>
                        {"" if fund_bd.get('policy_bonus', 0) == 0 else f"""<div class="breakdown-item" style="background: rgba({'76,175,80' if fund_bd.get('policy_bonus',0) > 0 else '244,67,54'}, 0.08);">
                            <span class="criterion">🇰🇷 정책</span>
                            <span class="criterion-value">{'수혜' if fund_bd.get('policy_bonus',0) > 0 else '역풍'}</span>
                            <span class="criterion-score">{'+' if fund_bd.get('policy_bonus',0) > 0 else ''}{fund_bd.get('policy_bonus',0)}점</span>
                        </div>"""}
                    </div>
                </div>
                <div class="breakdown-section">
                    <div class="breakdown-title">기술적 점수: {stock.get('tech_score', 0)}점</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(103, 126, 234, 0.05);">
                            <span class="criterion">📈 추세 분석</span>
                            <span class="criterion-value">MA5/20/60/120, MACD, 일목({tech_bd.get('ichimoku_score', 0)}/3), ADX</span>
                            <span class="criterion-score">+{tech_bd.get('trend_score', 0)}점 /18</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(76, 175, 80, 0.05);">
                            <span class="criterion">⚡ 모멘텀</span>
                            <span class="criterion-value">RSI:{tech_bd.get('rsi_value', 0):.0f}, Stoch, MFI:{tech_bd.get('mfi_value', 0):.0f}</span>
                            <span class="criterion-score">+{tech_bd.get('momentum_score', 0)}점 /12</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(255, 152, 0, 0.05);">
                            <span class="criterion">📊 거래량</span>
                            <span class="criterion-value">{tech_bd.get('volume_ratio', 0):.1f}x, OBV</span>
                            <span class="criterion-score">+{tech_bd.get('volume_score', 0)}점 /8</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(156, 39, 176, 0.05);">
                            <span class="criterion">🌊 변동성</span>
                            <span class="criterion-value">BB, ATR</span>
                            <span class="criterion-score">+{tech_bd.get('volatility_score', 0)}점 /5</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(244, 67, 54, 0.05);">
                            <span class="criterion">🎯 가격 패턴</span>
                            <span class="criterion-value">52주 {tech_bd.get('price_position', 0):.0%}</span>
                            <span class="criterion-score">+{tech_bd.get('pattern_score', 0)}점 /5</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(33, 150, 243, 0.05);">
                            <span class="criterion">💪 상대강도 vs KOSPI</span>
                            <span class="criterion-value">{"N/A" if tech_bd.get('rs_ratio', 0) == 0 else f"{tech_bd.get('rs_ratio', 0):+.1f}%"}</span>
                            <span class="criterion-score">+{tech_bd.get('rs_score', 0)}점 /5</span>
                        </div>
                    </div>
                </div>'''

            regime_adjustment = stock.get('regime_adjustment', '')
            if regime_adjustment and regime_adjustment != '중립: 조정 없음':
                html += f'''
                <div class="breakdown-section" style="border-top: 2px dashed #E85D75; padding-top: 10px; margin-top: 10px;">
                    <div class="breakdown-title" style="color: #E85D75;">🌍 {regime_adjustment}</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(232, 93, 117, 0.05);">
                            <span class="criterion">원래 기술 점수</span>
                            <span class="criterion-value">{stock.get('tech_score_original', 0)}점</span>
                            <span class="criterion-score">&rarr; {stock.get('tech_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(232, 93, 117, 0.05);">
                            <span class="criterion">원래 펀더 점수</span>
                            <span class="criterion-value">{stock.get('fund_score_original', 0)}점</span>
                            <span class="criterion-score">&rarr; {stock.get('fund_score', 0)}점</span>
                        </div>
                    </div>
                </div>'''

            contrarian_adj = stock.get('contrarian_adjustment', 0)
            trading_bonus = stock.get('trading_bonus', 0)
            bonus_parts = []
            if contrarian_adj != 0:
                adj_sign = '+' if contrarian_adj > 0 else ''
                adj_color = '#4CAF50' if contrarian_adj > 0 else '#F44336'
                adj_label = '🎯 역발상 보너스' if contrarian_adj > 0 else '⚠️ 과열 감점'
                bonus_parts.append(f"{adj_sign}{contrarian_adj}")
                html += f'''
                <div class="breakdown-section" style="border-top: 2px solid {primary_color}; padding-top: 10px; margin-top: 10px;">
                    <div class="breakdown-title" style="color: {adj_color};">{adj_label}: {adj_sign}{contrarian_adj}점</div>
                </div>'''

            if trading_bonus != 0:
                tb_sign = '+' if trading_bonus > 0 else ''
                tb_color = '#4CAF50' if trading_bonus > 0 else '#F44336'
                bonus_parts.append(f"{tb_sign}{trading_bonus}")
                html += f'''
                <div class="breakdown-section" style="padding-top: 5px;">
                    <div class="breakdown-title" style="color: {tb_color};">💰 거래대금 유동성 ({stock.get('trading_tier', '')}): {tb_sign}{trading_bonus}점</div>
                </div>'''

            # 🔄 섹터 순환매 표시
            rot_bonus = stock.get('rotation_bonus', 0)
            rot_phase = stock.get('rotation_phase', '')
            if rot_phase and rot_phase != '중립':
                rot_sign = '+' if rot_bonus >= 0 else ''
                phase_colors = {'수급유입': '#FF6B35', '순환매 기대': '#27AE60', '관심': '#3498DB', '과열주의': '#E67E22', '소외 지속': '#E74C3C'}
                phase_icons = {'수급유입': '🔥', '순환매 기대': '⚡', '관심': '👀', '과열주의': '⚠️', '소외 지속': '❄️'}
                rot_color = phase_colors.get(rot_phase, '#7B6B4F')
                rot_icon = phase_icons.get(rot_phase, '🔄')
                bonus_parts.append(f"{rot_sign}{rot_bonus}")
                html += f'''
                <div class="breakdown-section" style="padding-top: 5px;">
                    <div class="breakdown-title" style="color: {rot_color};">{rot_icon} 섹터 순환매: {rot_phase} ({rot_sign}{rot_bonus}점)</div>
                </div>'''

            if bonus_parts:
                bonus_str = ' '.join(bonus_parts)
                html += f'''
                <div class="breakdown-section" style="border-top: 1px solid #E0E0E0; padding-top: 8px; margin-top: 5px;">
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(76, 175, 80, 0.1);">
                            <span class="criterion">최종 점수</span>
                            <span class="criterion-value">{stock.get('fund_score', 0)} + {stock.get('tech_score', 0)} {bonus_str}</span>
                            <span class="criterion-score" style="color: #E85D75; font-size: 1.1em;">{stock['score']}점</span>
                        </div>
                    </div>
                </div>'''

            html += '''
            </div>
            <div class="info">'''

            current_price = stock['price']
            prev_close = market_info.get('previous_close', 0)
            change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            change_color = '#4CAF50' if change_pct >= 0 else '#F44336'
            change_sign = '+' if change_pct >= 0 else ''

            html += f'''
                <div class="info-item" style="background: #4CAF50; color: white;">
                    <div class="info-label" style="color: rgba(255,255,255,0.9);">현재가</div>
                    <div class="info-value" style="font-size: 1.2em;">₩{current_price:,}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">전일대비</div>
                    <div class="info-value" style="color: {change_color}; font-weight: bold;">{change_sign}{change_pct:.2f}%</div>
                </div>'''

            if stock.get('buy_price') is not None:
                html += f'''
                <div class="info-item">
                    <div class="info-label">{stock.get('buy_strategy', '')}</div>
                    <div class="info-value">₩{int(stock['buy_price']):,}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">목표가</div>
                    <div class="info-value">₩{int(stock['target']):,}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">손절가</div>
                    <div class="info-value" style="color: #F44336;">₩{int(stock['stop_loss']):,}</div>
                </div>'''

            analyst_comment = stock.get('analyst_comment', '')
            analyst_view_html = ''
            if analyst_comment:
                analyst_view_html = f'''
            <div class="analyst-view">
                <div class="analyst-header">📝 Titan 애널리스트 뷰</div>
                <div class="analyst-comment">{analyst_comment}</div>
            </div>'''

            html += f'''
            </div>
            <div class="comment">{stock['comment']}</div>{analyst_view_html}
        </div>
'''

        html += f'''
        <div class="footer">
            <p>Project Titan KR &middot; 한국장 AI 분석 시스템</p>
            <p style="margin-top: 4px;">본 분석은 알고리즘 기반 투자 참고 자료이며, 투자 책임은 본인에게 있습니다.</p>
        </div>
    </div>
    <script>
    function toggleDetail(id) {{
        var el = document.getElementById('detail-' + id);
        var btn = el.previousElementSibling;
        if (el.classList.contains('open')) {{
            el.classList.remove('open');
            btn.textContent = '상세 분석 ▼';
        }} else {{
            el.classList.add('open');
            btn.textContent = '상세 분석 ▲';
        }}
    }}
    </script>
</body>
</html>'''

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        # scoring_system_kr.html 복사
        try:
            import shutil
            scoring_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scoring_system_kr.html')
            scoring_dst = os.path.join(os.path.dirname(os.path.abspath(filename)), 'scoring_system_kr.html')
            if os.path.exists(scoring_src) and scoring_src != scoring_dst:
                shutil.copy2(scoring_src, scoring_dst)
        except Exception:
            pass

        print(f"📄 리포트 저장: {filename}")
        return filename


# ============================================================================
# 텔레그램 알림
# ============================================================================
def send_push_alert(results, market='kr'):
    """Supabase에서 사용자별 보유종목 조회 후 Web Push 알림 전송"""
    import requests as _req
    import json as _json
    from collections import defaultdict

    sb_url = os.environ.get('SUPABASE_URL', '')
    sb_key = os.environ.get('SUPABASE_SERVICE_KEY', '')
    vapid_private = os.environ.get('VAPID_PRIVATE_KEY', '')
    vapid_email = os.environ.get('VAPID_EMAIL', 'mailto:admin@titan.com')

    if not sb_url or not sb_key or not vapid_private:
        _send_telegram_fallback(results, market)
        return

    headers = {
        'apikey': sb_key,
        'Authorization': f'Bearer {sb_key}',
        'Content-Type': 'application/json'
    }

    try:
        resp = _req.get(
            f'{sb_url}/rest/v1/alert_holdings?market=eq.{market}&select=*',
            headers=headers, timeout=15
        )
        all_holdings = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"⚠️  보유종목 조회 실패: {e}")
        _send_telegram_fallback(results, market)
        return

    all_holdings = [h for h in all_holdings if float(h.get('qty', 0)) > 0]
    if not all_holdings:
        print("ℹ️  등록된 보유종목 없음")
        return

    user_ids = list(set(h['user_id'] for h in all_holdings))
    user_id_csv = ','.join(user_ids)
    try:
        resp2 = _req.get(
            f'{sb_url}/rest/v1/push_subscriptions?user_id=in.({user_id_csv})&select=*',
            headers=headers, timeout=15
        )
        subs = resp2.json() if resp2.status_code == 200 else []
    except Exception:
        subs = []

    user_subs = defaultdict(list)
    for s in subs:
        user_subs[s['user_id']].append(s)

    user_holdings = defaultdict(list)
    for h in all_holdings:
        user_holdings[h['user_id']].append(h)

    lookup = {r['ticker']: r for r in results}
    is_kr = (market == 'kr')
    kst = pytz.timezone('Asia/Seoul')

    def fmt(v):
        if not v:
            return '-'
        return f"₩{int(v):,}" if is_kr else f"${v:,.2f}"

    tag = 'KR' if is_kr else 'US'
    total_alerts = 0

    for user_id, holdings in user_holdings.items():
        subscriptions = user_subs.get(user_id, [])
        if not subscriptions:
            continue

        alerts = []
        for h in holdings:
            r = lookup.get(h['ticker'])
            if not r:
                continue

            price = r.get('price', 0)
            target = r.get('target') or r.get('target_price', 0)
            stop = r.get('stop_loss', 0)
            avg = float(h.get('avg_price', 0))
            qty = float(h.get('qty', 0))
            name = h.get('name', h['ticker'])
            pnl_pct = ((price - avg) / avg * 100) if avg else 0

            if price and target and price >= target:
                alerts.append({
                    'title': f'🟢 목표가 도달: {name}',
                    'body': f'{fmt(price)} ≥ 목표 {fmt(target)} | {pnl_pct:+.1f}%',
                    'tag': f'target-{h["ticker"]}'
                })
            if price and stop and price <= stop:
                alerts.append({
                    'title': f'🔴 손절가 도달: {name}',
                    'body': f'{fmt(price)} ≤ 손절 {fmt(stop)} | {pnl_pct:+.1f}%',
                    'tag': f'stop-{h["ticker"]}'
                })

        if not alerts:
            continue

        for alert in alerts:
            for sub_info in subscriptions:
                _send_webpush(sub_info, alert, vapid_private, vapid_email, sb_url, sb_key, headers)
                time.sleep(0.05)
            total_alerts += 1

    print(f"📨 [{tag}] Web Push 알림 {total_alerts}건 전송 ({len(user_holdings)}명)")


def _send_webpush(sub_info, payload, vapid_private, vapid_email, sb_url, sb_key, headers):
    """단일 Web Push 전송"""
    try:
        from pywebpush import webpush
        import json as _json

        subscription_info = {
            'endpoint': sub_info['endpoint'],
            'keys': {
                'p256dh': sub_info['p256dh'],
                'auth': sub_info['auth']
            }
        }
        webpush(
            subscription_info=subscription_info,
            data=_json.dumps(payload),
            vapid_private_key=vapid_private,
            vapid_claims={'sub': vapid_email}
        )
    except Exception as e:
        err_str = str(e)
        if '410' in err_str or 'Gone' in err_str:
            try:
                import requests as _req
                _req.delete(
                    f'{sb_url}/rest/v1/push_subscriptions?id=eq.{sub_info["id"]}',
                    headers=headers, timeout=10
                )
            except Exception:
                pass
        else:
            print(f"⚠️  Push 전송 실패: {err_str[:80]}")


def _send_telegram_fallback(results, market='kr'):
    """Supabase 미설정 시 기존 텔레그램 폴백"""
    import json as _json
    import requests as _req

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        print("⚠️  텔레그램/Supabase 설정 없음 — 알림 건너뜀")
        return

    try:
        with open('my_holdings.json', 'r', encoding='utf-8') as f:
            holdings = _json.load(f).get('holdings', [])
    except (FileNotFoundError, _json.JSONDecodeError):
        return

    holdings = [h for h in holdings if h.get('qty', 0) > 0]
    if not holdings:
        return

    lookup = {r['ticker']: r for r in results}
    is_kr = (market == 'kr')
    kst = pytz.timezone('Asia/Seoul')
    now_str = datetime.now(kst).strftime('%m/%d %H:%M')

    def fmt(v):
        if not v:
            return '-'
        return f"₩{int(v):,}" if is_kr else f"${v:,.2f}"

    alerts = []
    summary_lines = []

    for h in holdings:
        r = lookup.get(h['ticker'])
        if not r:
            continue

        price = r.get('price', 0)
        target = r.get('target') or r.get('target_price', 0)
        stop = r.get('stop_loss', 0)
        avg = h.get('avg_price', 0)
        qty = h.get('qty', 0)
        name = h.get('name', h['ticker'])
        pnl_pct = ((price - avg) / avg * 100) if avg else 0

        if price and target and price >= target:
            alerts.append(f"🟢 목표가 도달: {name} ({h['ticker']})\n현재 {fmt(price)} ≥ 목표 {fmt(target)}\n보유 {qty}주 · 평단 {fmt(avg)} · 수익 {pnl_pct:+.1f}%")
        if price and stop and price <= stop:
            alerts.append(f"🔴 손절가 도달: {name} ({h['ticker']})\n현재 {fmt(price)} ≤ 손절 {fmt(stop)}\n보유 {qty}주 · 평단 {fmt(avg)} · 손실 {pnl_pct:+.1f}%")
        summary_lines.append(f"  {name}: {fmt(price)} ({pnl_pct:+.1f}%)\n    목표 {fmt(target)} | 손절 {fmt(stop)}")

    def send_tg(text):
        try:
            _req.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={'chat_id': chat_id, 'text': text}, timeout=10)
        except Exception:
            pass

    for a in alerts:
        send_tg(a)
    if summary_lines:
        tag = 'KR' if is_kr else 'US'
        send_tg(f"📊 [{tag}] 보유종목 현황 ({now_str} KST)\n\n" + "\n\n".join(summary_lines))


def _fetch_user_holding_codes(market='kr'):
    """Supabase에서 사용자 보유종목 코드를 가져와 분석 대상에 추가"""
    import requests as _req
    sb_url = os.environ.get('SUPABASE_URL', '')
    sb_key = os.environ.get('SUPABASE_SERVICE_KEY', '')
    if not sb_url or not sb_key:
        return []
    try:
        headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}
        resp = _req.get(
            f"{sb_url}/rest/v1/alert_holdings?market=eq.{market}&select=ticker",
            headers=headers, timeout=10
        )
        if resp.status_code == 200:
            codes = list(set(h['ticker'] for h in resp.json()))
            if codes:
                print(f"📌 보유종목 {len(codes)}개 추가 분석 대상에 포함")
            return codes
    except Exception as e:
        print(f"⚠️  보유종목 조회 실패: {e}")
    return []


# ============================================================================
# 메인 실행
# ============================================================================
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     PROJECT TITAN KR - 한국장 주식 의사결정 지원 시스템      ║
    ║        KOSPI 200 + KOSDAQ 시총 상위 분석                   ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    mode = 'growth'
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    analyzer = TitanKRAnalyzer()
    holding_codes = _fetch_user_holding_codes(market='kr')

    if mode == 'value':
        print("💰 가치주 모드 (금융/통신/유틸리티/건설)")
        analyzer.analysis_mode = 'value'
        codes = list(dict.fromkeys(KR_VALUE_CODES + holding_codes))
        report_type = "KOSPI Value"
        filename = "titan_kr_value_report.html"
    else:
        print("🚀 성장주 모드 (반도체/2차전지/바이오/방산/조선)")
        analyzer.analysis_mode = 'growth'
        codes = list(dict.fromkeys(KR_GROWTH_CODES + holding_codes))
        report_type = "KOSPI Growth"
        filename = "titan_kr_growth_report.html"

    print(f"📊 분석 대상: {len(codes)}개 종목\n")

    results = analyzer.stage2_deep_analysis(codes)

    analyzer.display_results(results, min_score=50)

    report_path = analyzer.generate_html_report(
        results, report_type=report_type, filename=filename, min_score=50)

    analyzer._save_score_cache(results, report_type)

    # 보유종목 알림 (Web Push / 텔레그램 폴백)
    send_push_alert(results, market='kr')

    # 마지막 업데이트 시간 저장 (index.html에서 표시용)
    import json as _json
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    with open('last_updated.json', 'w', encoding='utf-8') as _f:
        _json.dump({
            'timestamp': now_kst.strftime('%Y-%m-%d %H:%M'),
            'timezone': 'KST',
            'mode': mode
        }, _f)

    print(f"\n✅ 분석 완료!")
    print(f"📄 리포트: {report_path}")
