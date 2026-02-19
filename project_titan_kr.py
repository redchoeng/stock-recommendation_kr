# -*- coding: utf-8 -*-
"""
Project Titan KR - 한국장 주식 의사결정 지원 시스템
KOSPI 200 + KOSDAQ 시총 상위 종목 대상
100점 스코어링 (펀더멘털 50 + 기술적 50) + ML 앙상블
"""

import pandas as pd
import time
from datetime import datetime
from tabulate import tabulate
from ta.momentum import RSIIndicator
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

    # ========== 2차전지/배터리 (12) ==========
    '373220',  # LG에너지솔루션
    '006400',  # 삼성SDI
    '051910',  # LG화학
    '247540',  # 에코프로비엠
    '086520',  # 에코프로
    '003670',  # 포스코퓨처엠
    '012450',  # 한화에어로스페이스 (방산이지만 배터리도)
    '064350',  # 현대로템
    '018260',  # 삼성에스디에스
    '361610',  # SK아이이테크놀로지
    '137400',  # 피엔티
    '108320',  # LX세미콘

    # ========== 바이오/헬스케어 (15) ==========
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
    '352820',  # 하이브
    '263750',  # 펄어비스
    '112040',  # 위메이드
    '293490',  # 카카오게임즈

    # ========== K-플랫폼/IT서비스 (10) ==========
    '035420',  # NAVER
    '035720',  # 카카오
    '259960',  # 크래프톤
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
    '006280',  # 녹십자
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

    # ========== 통신 (5) ==========
    '017670',  # SK텔레콤
    '030200',  # KT
    '032640',  # LG유플러스
    '036570',  # 엔씨소프트
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
    '042670',  # 두산인프라코어
    '001120',  # LX인터내셔널
    '001740',  # SK네트웍스
]


class TitanKRAnalyzer:
    # 필터링 기준 (한국장)
    MIN_MARKET_CAP = 500_000_000_000    # 5000억원
    MIN_PRICE = 1000                     # ₩1,000
    MIN_AVG_VOLUME = 100_000            # 10만주

    # 점수 임계값
    SCORE_STRONG_BUY = 80
    SCORE_BUY = 60
    SCORE_HOLD = 40

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

    # 기술적 점수 (총 50점, US와 동일)
    SCORE_MA200 = 3
    SCORE_MA50 = 3
    SCORE_MA20 = 2
    SCORE_MACD_BULLISH = 4
    SCORE_MACD_SIGNAL = 2
    SCORE_ADX_STRONG = 3

    SCORE_RSI_OPTIMAL = 6
    SCORE_RSI_GOOD = 4
    SCORE_RSI_OVERSOLD = 2
    SCORE_STOCH_OPTIMAL = 6
    SCORE_STOCH_GOOD = 3

    SCORE_VOLUME_EXTREME = 6
    SCORE_VOLUME_HIGH = 4
    SCORE_VOLUME_MODERATE = 3
    SCORE_VOLUME_NORMAL = 2
    SCORE_OBV_RISING = 4

    SCORE_BB_POSITION = 5
    SCORE_ATR_EXPANSION = 3
    SCORE_PRICE_POSITION = 5

    RSI_OVERSOLD = 30
    RSI_OPTIMAL_MIN = 40
    RSI_OPTIMAL_MAX = 60
    RSI_GOOD_MAX = 70
    RSI_OVERBOUGHT = 70

    SCORE_OVERSOLD_QUALITY_BONUS = 10
    SCORE_OVERBOUGHT_PENALTY = -5

    VOLUME_SURGE_MULTIPLIER = 1.2
    STOP_LOSS_RATIO = 0.97

    def __init__(self, dart_api_key=None):
        self.K_FACTOR = 0.5
        self.results = []
        self.analysis_mode = 'growth'
        self.data_provider = KRDataProvider(dart_api_key=dart_api_key)

    # ================================================================
    # 1단계: 빠른 스크리닝
    # ================================================================
    def _meets_stage1_criteria(self, info):
        market_cap = info.get('marketCap', 0)
        current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        avg_volume = info.get('averageVolume', 0)

        return (market_cap and market_cap > self.MIN_MARKET_CAP and
                current_price and current_price > self.MIN_PRICE and
                avg_volume and avg_volume > self.MIN_AVG_VOLUME)

    def stage1_quick_filter(self, codes):
        """1단계: 빠른 스크리닝 (시가총액, 거래량, 가격)"""
        print("=" * 70)
        print(f"🔍 STAGE 1: 빠른 스크리닝 (시총 > ₩{self.MIN_MARKET_CAP/1e8:.0f}억, "
              f"거래량 > {self.MIN_AVG_VOLUME/1e4:.0f}만주)")
        print("=" * 70)

        filtered = []
        total = len(codes)

        for i, code in enumerate(codes, 1):
            try:
                if i % 50 == 0 or i == total:
                    print(f"진행: {i}/{total} ({i/total*100:.1f}%)")

                info = self.data_provider.get_info(code)
                if self._meets_stage1_criteria(info):
                    filtered.append(code)

                if i % 10 == 0:
                    time.sleep(0.1)
            except Exception:
                pass

        print(f"\n✅ 1단계 완료: {len(filtered)}개 종목 선정 (원본 {total}개)\n")
        return filtered

    # ================================================================
    # 펀더멘털 점수 (50점 만점)
    # ================================================================
    def _get_fundamental_score(self, info):
        score = 0
        comments = []
        breakdown = {
            'roe_score': 0, 'roe_value': 0,
            'opm_score': 0, 'opm_value': 0,
            'revenue_growth_score': 0, 'revenue_growth_value': None,
            'sector_score': 0, 'sector_name': ''
        }

        try:
            sector = info.get('sector', '') or ''
            industry = info.get('industry', '') or ''

            # 1. ROE (섹터별 차등, 선형 보간)
            roe = info.get('returnOnEquity')
            roe_excellent, roe_good = self._get_sector_threshold(
                sector, self.SECTOR_ROE_THRESHOLDS, self.DEFAULT_ROE_THRESHOLD)
            if roe:
                roe_pct = roe * 100
                breakdown['roe_value'] = roe_pct
                roe_score = self._calc_gradient_score(roe_pct, roe_excellent, roe_good, 15)
                score += roe_score
                breakdown['roe_score'] = roe_score
                if roe_score > 0:
                    comments.append(f"ROE:{roe_pct:.1f}%")

            # 2. OPM (섹터별 차등, 선형 보간)
            opm = info.get('operatingMargins')
            opm_excellent, opm_good = self._get_sector_threshold(
                sector, self.SECTOR_OPM_THRESHOLDS, self.DEFAULT_OPM_THRESHOLD)
            if opm:
                opm_pct = opm * 100
                breakdown['opm_value'] = opm_pct
                opm_score = self._calc_gradient_score(opm_pct, opm_excellent, opm_good, 15)
                score += opm_score
                breakdown['opm_score'] = opm_score
                if opm_score > 0:
                    comments.append(f"OPM:{opm_pct:.1f}%")

            # 3. 매출성장률 (섹터별 차등, 선형 보간)
            revenue_growth = info.get('revenueGrowth')
            rg_high, rg_good = self._get_sector_threshold(
                sector, self.SECTOR_REVENUE_GROWTH_THRESHOLDS, self.DEFAULT_REVENUE_GROWTH_THRESHOLD)
            if revenue_growth:
                rg_pct = revenue_growth * 100
                breakdown['revenue_growth_value'] = rg_pct
                rg_score = self._calc_gradient_score(rg_pct, rg_high, rg_good, 10)
                score += rg_score
                breakdown['revenue_growth_score'] = rg_score

            # 3-1. 고성장 투자기업 보정 (매출 30%+ & ROE/OPM 적자)
            if revenue_growth and revenue_growth > 0.30:
                roe_val = roe * 100 if roe else 0
                opm_val = opm * 100 if opm else 0
                if roe_val < 0 and breakdown['roe_score'] == 0:
                    bonus = round(15 * 0.4)  # 40% of max (6점)
                    score += bonus
                    breakdown['roe_score'] = bonus
                    comments.append("성장투자")
                if opm_val < 0 and breakdown['opm_score'] == 0:
                    bonus = round(15 * 0.4)  # 40% of max (6점)
                    score += bonus
                    breakdown['opm_score'] = bonus

            # 4. 섹터 & 정책 보너스
            breakdown['sector_name'] = sector or industry or '기타'

            if self.analysis_mode == 'value':
                sector_score, sector_name, sector_comment = self._get_value_sector_score(sector, industry)
                score += sector_score
                breakdown['sector_score'] = sector_score
                breakdown['sector_name'] = sector_name
                if sector_comment:
                    comments.append(sector_comment)

                # 한국 정책 보너스 (가치주)
                policy_bonus, policy_comment = self._get_kr_policy_bonus(
                    sector, industry, info.get('shortName', ''))
                if policy_bonus != 0:
                    score += policy_bonus
                    breakdown['policy_bonus'] = policy_bonus
                    comments.append(policy_comment)
            else:
                sector_score, sector_name, sector_comment = self._get_growth_sector_score(sector, industry, info.get('shortName', ''))
                score += sector_score
                breakdown['sector_score'] = sector_score
                breakdown['sector_name'] = sector_name
                if sector_comment:
                    comments.append(sector_comment)

                # 한국 정책 보너스 (성장주)
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
        if value is None:
            return 0
        if excellent == 0 and good == 0:
            return 0

        top = excellent * 1.3
        bottom = good * 0.5

        if value >= top:
            return max_pts
        elif value >= excellent:
            ratio = 0.8 + 0.2 * (value - excellent) / (top - excellent) if top != excellent else 1.0
            return round(max_pts * ratio, 1)
        elif value >= good:
            ratio = 0.4 + 0.4 * (value - good) / (excellent - good) if excellent != good else 0.8
            return round(max_pts * ratio, 1)
        elif value >= bottom:
            ratio = 0.05 + 0.35 * (value - bottom) / (good - bottom) if good != bottom else 0.05
            return round(max_pts * ratio, 1)
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
    def _get_technical_score(self, hist, current_price):
        from ta.trend import MACD, ADXIndicator
        from ta.momentum import RSIIndicator, StochasticOscillator
        from ta.volatility import BollingerBands, AverageTrueRange
        from ta.volume import OnBalanceVolumeIndicator

        score = 0
        comments = []
        breakdown = {
            'trend_score': 0, 'ma20': 0, 'ma50': 0, 'ma200': 0,
            'macd_score': 0, 'adx_score': 0,
            'momentum_score': 0, 'rsi_value': 0, 'rsi_score': 0,
            'stoch_score': 0, 'stoch_k': 0, 'stoch_d': 0,
            'volume_score': 0, 'volume_ratio': 0, 'obv_score': 0,
            'volatility_score': 0, 'bb_position': 0, 'atr_score': 0,
            'pattern_score': 0, 'price_position': 0
        }

        try:
            if len(hist) < 200:
                return 0, ["데이터부족"], breakdown

            close = hist['Close']
            volume = hist['Volume']

            # 1. 추세 분석 (15점)
            trend_score = 0
            ma20 = close.rolling(window=20).mean().iloc[-1]
            ma50 = close.rolling(window=50).mean().iloc[-1]
            ma200 = close.rolling(window=200).mean().iloc[-1]

            breakdown['ma20'] = ma20
            breakdown['ma50'] = ma50
            breakdown['ma200'] = ma200

            if current_price > ma200:
                trend_score += self.SCORE_MA200
                comments.append("MA200↑")
            if current_price > ma50:
                trend_score += self.SCORE_MA50
            if current_price > ma20:
                trend_score += self.SCORE_MA20

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

            adx = ADXIndicator(high=hist['High'], low=hist['Low'], close=close)
            adx_value = adx.adx().iloc[-1]
            if adx_value > 25:
                trend_score += self.SCORE_ADX_STRONG
                breakdown['adx_score'] = self.SCORE_ADX_STRONG
                comments.append(f"ADX:{adx_value:.0f}")

            breakdown['trend_score'] = trend_score
            score += trend_score

            is_downtrend = trend_score < 8

            # 2. 모멘텀 (12점)
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

            breakdown['momentum_score'] = momentum_score
            score += momentum_score

            # 3. 거래량 (10점)
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

            # 4. 변동성 (8점)
            volatility_score = 0
            bb = BollingerBands(close=close)
            bb_high = bb.bollinger_hband().iloc[-1]
            bb_low = bb.bollinger_lband().iloc[-1]
            bb_position = (current_price - bb_low) / (bb_high - bb_low) if (bb_high - bb_low) > 0 else 0.5
            breakdown['bb_position'] = bb_position

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

            breakdown['volatility_score'] = volatility_score
            score += volatility_score

            # 5. 가격 패턴 (5점)
            pattern_score = 0
            high_52w = close.rolling(window=252).max().iloc[-1]
            low_52w = close.rolling(window=252).min().iloc[-1]
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

            breakdown['is_downtrend'] = is_downtrend
            if is_downtrend:
                comments.append("⚠하락추세")

        except Exception as e:
            print(f"Technical analysis error: {e}")

        return score, comments, breakdown

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
    # 시장 레짐 감지 (KOSPI 기반)
    # ================================================================
    def _detect_market_regime(self):
        try:
            from ta.trend import ADXIndicator

            hist = self.data_provider.get_market_index(period='1y')
            if len(hist) < 200:
                return 'neutral', {}, "데이터 부족"

            close = hist['Close']
            current_price = close.iloc[-1]

            ma50 = close.rolling(window=50).mean().iloc[-1]
            ma200 = close.rolling(window=200).mean().iloc[-1]

            price_3m_ago = close.iloc[-63] if len(close) >= 63 else close.iloc[0]
            trend_3m = (current_price - price_3m_ago) / price_3m_ago

            price_6m_ago = close.iloc[-126] if len(close) >= 126 else close.iloc[0]
            trend_6m = (current_price - price_6m_ago) / price_6m_ago

            adx = ADXIndicator(high=hist['High'], low=hist['Low'], close=close)
            adx_value = adx.adx().iloc[-1]

            bull_signals = 0
            bear_signals = 0

            if current_price > ma200:
                bull_signals += 1
            else:
                bear_signals += 1
            if ma50 > ma200:
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
                'ma50': ma50,
                'ma200': ma200,
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
        original_tech = tech_score
        original_fund = fund_score

        trend_penalty_applied = False
        if is_downtrend and tech_score > 0:
            if regime == 'bear':
                tech_score = int(tech_score * 0.8)
                trend_penalty_msg = "하락추세 페널티 -20% (하락장 완화)"
            else:
                tech_score = int(tech_score * 0.6)
                trend_penalty_msg = "하락추세 페널티 -40%"
            trend_penalty_applied = True
        else:
            trend_penalty_msg = ""

        if regime == 'bull':
            tech_score = int(tech_score * 1.2)
            fund_score = int(fund_score * 0.8)
            adjustment = "상승장: 기술60% : 펀더40%"
        elif regime == 'bear':
            tech_score = int(tech_score * 0.8)
            fund_score = int(fund_score * 1.2)
            adjustment = "하락장: 기술40% : 펀더60%"
        elif regime == 'sideways':
            adjustment = "횡보장: 기술50% : 펀더50%"
        else:
            adjustment = "중립: 조정 없음"

        if regime == 'bull':
            tech_score = min(tech_score, 60)
            fund_score = min(fund_score, 50)
        elif regime == 'bear':
            tech_score = min(tech_score, 50)
            fund_score = min(fund_score, 65)
        else:
            tech_score = min(tech_score, 55)
            fund_score = min(fund_score, 55)

        if trend_penalty_applied:
            adjustment = f"{trend_penalty_msg} + {adjustment}"

        return tech_score, fund_score, adjustment

    # ================================================================
    # 역발상 + 스마트 진입/청산
    # ================================================================
    def _apply_contrarian_adjustment(self, fund_score, tech_breakdown, sector_name):
        adjustment = 0
        contrarian_comment = ""
        rsi = tech_breakdown.get('rsi_value', 50)

        quality_sectors = ['AI/반도체', '전기전자', '2차전지', '바이오', 'K-플랫폼', '방산', '조선']

        if rsi < self.RSI_OVERSOLD:
            if fund_score >= 30:
                if sector_name in quality_sectors:
                    adjustment = self.SCORE_OVERSOLD_QUALITY_BONUS
                    contrarian_comment = "🎯저가매수기회"
                else:
                    adjustment = self.SCORE_OVERSOLD_QUALITY_BONUS // 2
                    contrarian_comment = "💎저평가"
        elif rsi > self.RSI_OVERBOUGHT:
            adjustment = self.SCORE_OVERBOUGHT_PENALTY
            contrarian_comment = "⚠️과열주의"

        return adjustment, contrarian_comment

    def _calculate_volatility_breakout(self, hist):
        try:
            if len(hist) < 2:
                return None, None, None
            prev_high = hist['High'].iloc[-2]
            prev_low = hist['Low'].iloc[-2]
            today_open = hist['Open'].iloc[-1]
            range_val = prev_high - prev_low
            breakout_price = today_open + (range_val * self.K_FACTOR)
            target_price = breakout_price + range_val
            stop_loss = breakout_price * self.STOP_LOSS_RATIO
            return breakout_price, target_price, stop_loss
        except Exception:
            return None, None, None

    def _calculate_smart_entry_exit(self, current_price, contrarian_adj, hist, ma20):
        try:
            if len(hist) < 2:
                return None, None, None, "데이터 부족"
            if contrarian_adj > 0:
                buy_price = current_price
                target_price = current_price * 1.10
                stop_loss = current_price * 0.95
                strategy = "🎯 즉시매수"
            elif contrarian_adj < 0:
                buy_price = None
                target_price = None
                stop_loss = None
                strategy = "⚠️ 조정대기"
            else:
                if ma20 and ma20 > 0:
                    buy_price = ma20 * 1.01
                    target_price = buy_price * 1.08
                    stop_loss = ma20 * 0.97
                    strategy = "📊 MA20풀백"
                else:
                    buy_price = current_price
                    target_price = current_price * 1.08
                    stop_loss = current_price * 0.97
                    strategy = "📊 현재가"
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
                'pre_market_price': None,
                'post_market_price': None,
                'previous_close': previous_close
            }
        except Exception:
            return {
                'status': 'unknown',
                'current_price': info.get('currentPrice', 0),
                'pre_market_price': None,
                'post_market_price': None,
                'previous_close': info.get('previousClose', 0)
            }

    # ================================================================
    # 개별 종목 분석
    # ================================================================
    def _analyze_single_stock(self, code):
        info = self.data_provider.get_info(code)
        hist = self.data_provider.get_history(code, period='1y')

        if hist.empty or len(hist) < 20:
            return None

        current_price = self._get_current_price(info, hist)

        fund_score, fund_comments, fund_breakdown = self._get_fundamental_score(info)
        tech_score, tech_comments, tech_breakdown = self._get_technical_score(hist, current_price)

        contrarian_adj, contrarian_comment = self._apply_contrarian_adjustment(
            fund_score, tech_breakdown, fund_breakdown.get('sector_name', ''))

        total_score = fund_score + tech_score + contrarian_adj

        ma20 = tech_breakdown.get('ma20', 0)
        buy_price, target, stop_loss, strategy = self._calculate_smart_entry_exit(
            current_price, contrarian_adj, hist, ma20)

        breakout, _, _ = self._calculate_volatility_breakout(hist)

        market_info = self._get_market_status_and_prices(info)
        verdict = self._get_verdict(total_score)

        all_comments = fund_comments + tech_comments
        if contrarian_comment:
            all_comments.insert(0, contrarian_comment)
        comment = ", ".join(all_comments[:3]) if all_comments else "-"

        return {
            'ticker': code,
            'company_name': info.get('shortName', ''),
            'score': total_score,
            'fund_score': fund_score,
            'tech_score': tech_score,
            'contrarian_adjustment': contrarian_adj,
            'fund_breakdown': fund_breakdown,
            'tech_breakdown': tech_breakdown,
            'verdict': verdict,
            'price': current_price,
            'market_info': market_info,
            'buy_price': buy_price,
            'buy_strategy': strategy,
            'breakout': breakout,
            'target': target,
            'stop_loss': stop_loss,
            'comment': comment
        }

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

        results = []
        total = len(codes)

        for i, code in enumerate(codes, 1):
            try:
                print(f"분석 중: {i}/{total} - {code}")
                result = self._analyze_single_stock(code)
                if result:
                    is_downtrend = result.get('tech_breakdown', {}).get('is_downtrend', False)
                    tech_adjusted, fund_adjusted, adjustment_msg = self._apply_regime_adjustment(
                        result['tech_score'], result['fund_score'],
                        market_regime, is_downtrend=is_downtrend)

                    total_score_adjusted = fund_adjusted + tech_adjusted + result['contrarian_adjustment']

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
                f"₩{int(r['breakout']):,}" if r['breakout'] else "N/A",
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

        now = datetime.now()

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
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            background: linear-gradient(180deg, #87CEEB 0%, #98D8C8 30%, #F7DC6F 70%, #FADBD8 100%);
            background-attachment: fixed;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: white;
            border-radius: 30px;
            padding: 35px;
            margin-bottom: 25px;
            box-shadow: 0 8px 0 {primary_color};
            border: 4px solid #5D4E37;
            text-align: center;
        }}
        .header h1 {{ color: #5D4E37; font-size: 2em; margin-top: 10px; }}
        .header .subtitle {{ color: {primary_color}; margin-top: 10px; font-size: 1.1em; }}
        .header .date {{ color: #7B6B4F; margin-top: 10px; font-size: 0.9em; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .summary-card {{
            background: linear-gradient(180deg, #FFF8DC, #FAEBD7);
            border-radius: 20px;
            padding: 20px;
            border: 3px solid #5D4E37;
            text-align: center;
        }}
        .summary-card .label {{ color: #7B6B4F; margin-bottom: 8px; }}
        .summary-card .value {{ color: #FF6B35; font-size: 1.8em; font-weight: bold; }}
        .stock-card {{
            background: white;
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 15px;
            border: 3px solid #5D4E37;
            box-shadow: 0 5px 0 {primary_color};
            position: relative;
        }}
        .stock-card .rank {{
            position: absolute; top: 10px; left: 10px;
            background: #FFD700; color: #5D4E37;
            width: 40px; height: 40px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 1.2em; border: 2px solid #5D4E37;
        }}
        .stock-card h2 {{ color: #5D4E37; margin-bottom: 10px; padding-left: 50px; }}
        .stock-card .ticker {{ color: {primary_color}; font-weight: bold; font-size: 1.1em; }}
        .stock-card .info {{ margin-top: 15px; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
        .stock-card .info-item {{ padding: 8px; background: #F5F5F5; border-radius: 10px; }}
        .stock-card .info-label {{ font-size: 0.85em; color: #7B6B4F; }}
        .stock-card .info-value {{ font-weight: bold; color: #5D4E37; margin-top: 3px; }}
        .score-badge {{ background: {primary_color}; color: white; padding: 8px 20px; border-radius: 20px; float: right; font-weight: bold; font-size: 1.1em; }}
        .score-badge.high {{ background: #4CAF50; }}
        .score-badge.strong {{ background: #FF6B35; }}
        .verdict {{ display: inline-block; padding: 5px 15px; border-radius: 15px; font-size: 0.9em; font-weight: bold; margin-top: 10px; }}
        .verdict.strong-buy {{ background: #4CAF50; color: white; }}
        .verdict.buy {{ background: #8BC34A; color: white; }}
        .verdict.hold {{ background: #FFC107; color: #5D4E37; }}
        .comment {{ margin-top: 10px; padding: 10px; background: #FFF9E6; border-left: 4px solid {primary_color}; border-radius: 5px; font-size: 0.9em; color: #5D4E37; }}
        .back-link {{ display: block; text-align: center; margin-bottom: 20px; color: #5D4E37; text-decoration: none; font-weight: bold; }}
        .back-link:hover {{ color: {primary_color}; }}
        .footer {{ background: rgba(255,255,255,0.9); border-radius: 20px; padding: 20px; text-align: center; color: #7B6B4F; margin-top: 30px; }}
        .titan-badge {{ display: inline-block; background: linear-gradient(135deg, #E85D75 0%, #FF6B35 100%); color: white; padding: 5px 15px; border-radius: 15px; font-size: 0.8em; margin-left: 10px; font-weight: bold; }}
        .score-breakdown {{ margin: 15px 0; padding: 15px; background: #F8F9FA; border-radius: 10px; border: 2px solid #E0E0E0; }}
        .score-breakdown h3 {{ color: #5D4E37; margin-bottom: 12px; font-size: 1em; }}
        .breakdown-section {{ margin-bottom: 12px; }}
        .breakdown-title {{ font-weight: bold; color: {primary_color}; margin-bottom: 8px; font-size: 0.95em; }}
        .breakdown-items {{ display: grid; gap: 6px; }}
        .breakdown-item {{ display: grid; grid-template-columns: 1fr auto auto; gap: 10px; padding: 6px 10px; background: white; border-radius: 6px; align-items: center; font-size: 0.85em; }}
        .breakdown-item .criterion {{ color: #5D4E37; font-weight: 500; }}
        .breakdown-item .criterion-value {{ color: #7B6B4F; text-align: right; }}
        .breakdown-item .criterion-score {{ color: {primary_color}; font-weight: bold; text-align: right; min-width: 50px; }}
        .scoring-btn {{ display: inline-block; margin-top: 12px; padding: 8px 22px; background: linear-gradient(135deg, #5D4E37, #7B6B4F); color: #FFF8DC; border: 2px solid #5D4E37; border-radius: 20px; font-size: 0.9em; font-weight: 600; cursor: pointer; transition: all 0.3s; }}
        .scoring-btn:hover {{ background: linear-gradient(135deg, #7B6B4F, #9B8B6F); transform: translateY(-1px); }}
        .scoring-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 9999; justify-content: center; align-items: center; }}
        .scoring-overlay.active {{ display: flex; }}
        .scoring-modal {{ width: 95%; max-width: 1400px; height: 92vh; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.5); position: relative; }}
        .scoring-modal iframe {{ width: 100%; height: 100%; border: none; }}
        .scoring-close {{ position: absolute; top: 12px; right: 16px; width: 36px; height: 36px; background: rgba(0,0,0,0.7); color: #fff; border: none; border-radius: 50%; font-size: 1.3em; cursor: pointer; z-index: 10; display: flex; align-items: center; justify-content: center; }}
        .scoring-close:hover {{ background: rgba(200,0,0,0.8); }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back-link">&larr; 메인으로</a>
        <div class="header">
            <div style="font-size: 3em;">{emoji}</div>
            <h1>{report_type} <span class="titan-badge">TITAN KR v1.0</span></h1>
            <div class="subtitle">한국장 Fundamental + Technical Analysis</div>
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
            <div class="summary-card" style="grid-column: 1 / -1; background: linear-gradient(135deg, #E85D75 0%, #FF6B35 100%); color: white;">
                <div class="label" style="color: rgba(255,255,255,0.9);">🌍 시장 상태 및 평가 기준</div>
                <div class="value" style="font-size: 1.1em;">{filtered[0].get('regime_description', 'N/A') if filtered else 'N/A'}<br>
                <span style="font-size: 0.85em; opacity: 0.9;">Strong Buy &ge;{strong_buy_threshold}점 | Buy &ge;{buy_threshold}점</span></div>
            </div>
        </div>
'''

        for idx, stock in enumerate(filtered[:20], 1):
            score_class = 'strong' if stock['score'] >= strong_buy_threshold else ('high' if stock['score'] >= buy_threshold else '')
            verdict_class = stock['verdict'].lower().replace(' ', '-').replace('★', '').strip()

            fund_bd = stock.get('fund_breakdown', {})
            tech_bd = stock.get('tech_breakdown', {})
            market_info = stock.get('market_info', {})

            rg_value = fund_bd.get('revenue_growth_value')
            rg_display = f"{rg_value:.1f}%" if rg_value is not None else "N/A"

            html += f'''
        <div class="stock-card">
            <div class="rank">#{idx}</div>
            <span class="score-badge {score_class}">{stock['score']}점</span>
            <h2><span class="ticker">{stock['ticker']}</span> <span style="font-size:0.7em; color:#7B6B4F; font-weight:normal;">{stock.get('company_name', '')}</span></h2>
            <span class="verdict {verdict_class}">{stock['verdict']}</span>

            <div class="score-breakdown">
                <h3>📊 점수 상세 분석</h3>
                <div class="breakdown-section">
                    <div class="breakdown-title">펀더멘털 점수: {stock.get('fund_score', 0)}점 / 50점</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item">
                            <span class="criterion">ROE (자기자본이익률)</span>
                            <span class="criterion-value">{fund_bd.get('roe_value', 0):.1f}%</span>
                            <span class="criterion-score">+{fund_bd.get('roe_score', 0)}점</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="criterion">OPM (영업이익률)</span>
                            <span class="criterion-value">{fund_bd.get('opm_value', 0):.1f}%</span>
                            <span class="criterion-score">+{fund_bd.get('opm_score', 0)}점</span>
                        </div>
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
                        <div class="breakdown-item">
                            <span class="criterion">매출성장률</span>
                            <span class="criterion-value">{rg_display}</span>
                            <span class="criterion-score">+{fund_bd.get('revenue_growth_score', 0)}점</span>
                        </div>
                    </div>
                </div>
                <div class="breakdown-section">
                    <div class="breakdown-title">기술적 점수: {stock.get('tech_score', 0)}점 / 50점</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(103, 126, 234, 0.05);">
                            <span class="criterion">📈 추세 분석</span>
                            <span class="criterion-value">MA20/50/200, MACD, ADX</span>
                            <span class="criterion-score">+{tech_bd.get('trend_score', 0)}점 /15</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(76, 175, 80, 0.05);">
                            <span class="criterion">⚡ 모멘텀</span>
                            <span class="criterion-value">RSI:{tech_bd.get('rsi_value', 0):.0f}, Stoch</span>
                            <span class="criterion-score">+{tech_bd.get('momentum_score', 0)}점 /12</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(255, 152, 0, 0.05);">
                            <span class="criterion">📊 거래량</span>
                            <span class="criterion-value">{tech_bd.get('volume_ratio', 0):.1f}x, OBV</span>
                            <span class="criterion-score">+{tech_bd.get('volume_score', 0)}점 /10</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(156, 39, 176, 0.05);">
                            <span class="criterion">🌊 변동성</span>
                            <span class="criterion-value">BB, ATR</span>
                            <span class="criterion-score">+{tech_bd.get('volatility_score', 0)}점 /8</span>
                        </div>
                        <div class="breakdown-item" style="background: rgba(244, 67, 54, 0.05);">
                            <span class="criterion">🎯 가격 패턴</span>
                            <span class="criterion-value">52주 {tech_bd.get('price_position', 0):.0%}</span>
                            <span class="criterion-score">+{tech_bd.get('pattern_score', 0)}점 /5</span>
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
            if contrarian_adj != 0:
                adj_sign = '+' if contrarian_adj > 0 else ''
                adj_color = '#4CAF50' if contrarian_adj > 0 else '#F44336'
                adj_label = '🎯 역발상 보너스' if contrarian_adj > 0 else '⚠️ 과열 감점'
                html += f'''
                <div class="breakdown-section" style="border-top: 2px solid {primary_color}; padding-top: 10px; margin-top: 10px;">
                    <div class="breakdown-title" style="color: {adj_color};">{adj_label}: {adj_sign}{contrarian_adj}점</div>
                    <div class="breakdown-items">
                        <div class="breakdown-item" style="background: rgba(76, 175, 80, 0.1);">
                            <span class="criterion">최종 점수</span>
                            <span class="criterion-value">{stock.get('fund_score', 0)} + {stock.get('tech_score', 0)} {adj_sign}{contrarian_adj}</span>
                            <span class="criterion-score" style="color: {adj_color}; font-size: 1.1em;">{stock['score']}점</span>
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
                    <div class="info-label">매수가 {stock.get('buy_strategy', '')}</div>
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

            html += f'''
            </div>
            <div class="comment">{stock['comment']}</div>
        </div>
'''

        html += f'''
        <div class="footer">
            <p>🤖 Project Titan KR v1.0 | 한국장 AI 분석 시스템</p>
            <p style="margin-top: 5px; font-size: 0.85em;">⚠️ 본 분석은 투자 참고용이며, 투자 책임은 본인에게 있습니다.</p>
        </div>
    </div>
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
# 메인 실행
# ============================================================================
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')

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

    if mode == 'value':
        print("💰 가치주 모드 (금융/통신/유틸리티/건설)")
        analyzer.analysis_mode = 'value'
        codes = list(set(KR_VALUE_CODES))
        report_type = "KOSPI Value"
        filename = "titan_kr_value_report.html"
    else:
        print("🚀 성장주 모드 (반도체/2차전지/바이오/방산/조선)")
        analyzer.analysis_mode = 'growth'
        codes = list(set(KR_GROWTH_CODES))
        report_type = "KOSPI Growth"
        filename = "titan_kr_growth_report.html"

    print(f"📊 분석 대상: {len(codes)}개 종목\n")

    results = analyzer.stage2_deep_analysis(codes)

    analyzer.display_results(results, min_score=50)

    report_path = analyzer.generate_html_report(
        results, report_type=report_type, filename=filename, min_score=50)

    print(f"\n✅ 분석 완료!")
    print(f"📄 리포트: {report_path}")
