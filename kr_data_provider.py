# -*- coding: utf-8 -*-
"""
KR Data Provider - 한국 주식 데이터 추상화 레이어
pykrx + FinanceDataReader + OpenDartReader 통합

yfinance 호환 인터페이스로 한국 데이터 제공
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# pykrx
try:
    from pykrx import stock as krx
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    print("⚠️ pykrx 미설치: pip install pykrx")

# FinanceDataReader
try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    FDR_AVAILABLE = False
    print("⚠️ FinanceDataReader 미설치: pip install FinanceDataReader")

# OpenDartReader
try:
    import OpenDartReader
    DART_AVAILABLE = True
except ImportError:
    DART_AVAILABLE = False
    print("ℹ️ OpenDartReader 미설치 (DART 재무제표 미사용)")

# yfinance (한국 종목 재무제표 조회용 .KS/.KQ)
try:
    import yfinance as yf
    import logging
    logging.getLogger('yfinance').setLevel(logging.CRITICAL)
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False


class KRDataProvider:
    """한국 주식 데이터 통합 제공자

    pykrx: OHLCV, PER/PBR/DIV, 시가총액
    FinanceDataReader: 종목 리스트, Sector/Industry
    OpenDartReader: ROE, OPM, 매출성장률 (DART 재무제표)
    """

    def __init__(self, dart_api_key=None):
        self._fundamental_cache = {}   # {date_str: DataFrame}
        self._market_cap_cache = {}    # {date_str: DataFrame}
        self._stock_listing_cache = {} # {'KOSPI': df, 'KOSDAQ': df}
        self._dart = None
        self._dart_cache = {}          # {code: {roe, opm, revenue_growth}}
        self._naver_enabled = True     # NAVER 스크래핑 활성 (실패 시 자동 비활성)
        self._naver_fail_count = 0
        self._yf_enabled = True        # yfinance 활성 (연속 실패 시 자동 비활성)
        self._yf_fail_count = 0

        if dart_api_key and DART_AVAILABLE:
            try:
                self._dart = OpenDartReader.OpenDartReader(dart_api_key)
                print("✅ DART API 연결 완료")
            except Exception as e:
                print(f"⚠️ DART API 연결 실패: {e}")

    # ================================================================
    # 영업일 탐색
    # ================================================================
    def _find_latest_trading_date(self, max_lookback=10):
        """가장 최근 영업일 찾기 (주말/공휴일/장 시작 전 대응)"""
        if hasattr(self, '_cached_trading_date') and self._cached_trading_date:
            return self._cached_trading_date

        today = datetime.now()
        for i in range(max_lookback):
            date = today - timedelta(days=i)
            # 주말 건너뛰기 (API 호출 절약)
            if date.weekday() >= 5:
                continue
            date_str = date.strftime('%Y%m%d')
            try:
                df = krx.get_market_ohlcv(date_str, market='KOSPI')
                if df is not None and not df.empty and df['종가'].sum() > 0:
                    self._cached_trading_date = date_str
                    return date_str
            except Exception:
                continue
        fallback = (today - timedelta(days=1)).strftime('%Y%m%d')
        self._cached_trading_date = fallback
        return fallback

    # ================================================================
    # 유니버스 (종목 리스트)
    # ================================================================
    def get_universe(self, kosdaq_top_n=100):
        """KOSPI 200 + KOSDAQ 시총 상위 N개 유니버스

        Returns:
            list of dict: [{code, name, market, sector, industry}, ...]
        """
        if not PYKRX_AVAILABLE:
            print("❌ pykrx 필요")
            return []

        date_str = self._find_latest_trading_date()
        universe = []

        # --- KOSPI 200 ---
        try:
            kospi200_codes = krx.get_index_portfolio_deposit_file('1028')
            print(f"✅ KOSPI 200: {len(kospi200_codes)}개 로드")
            for code in kospi200_codes:
                name = krx.get_market_ticker_name(code)
                universe.append({
                    'code': code,
                    'name': name or code,
                    'market': 'KOSPI',
                })
        except Exception as e:
            print(f"⚠️ KOSPI 200 로드 실패: {e}")

        # --- KOSDAQ 시총 상위 ---
        try:
            kosdaq_cap = krx.get_market_cap(date_str, market='KOSDAQ')
            if kosdaq_cap is not None and not kosdaq_cap.empty:
                kosdaq_top = kosdaq_cap.nlargest(kosdaq_top_n, '시가총액')
                print(f"✅ KOSDAQ 시총 상위 {len(kosdaq_top)}개 로드")
                for code in kosdaq_top.index:
                    name = krx.get_market_ticker_name(code)
                    universe.append({
                        'code': code,
                        'name': name or code,
                        'market': 'KOSDAQ',
                    })
        except Exception as e:
            print(f"⚠️ KOSDAQ 로드 실패: {e}")

        # --- Sector/Industry 매핑 (KRX 업종 인덱스) ---
        self._enrich_sector_info(universe)

        print(f"📊 전체 유니버스: {len(universe)}개 종목")
        return universe

    # KRX 업종 인덱스 → 섹터명 매핑
    KRX_SECTOR_INDICES = {
        '1005': '음식료품',
        '1006': '섬유의류',
        '1007': '종이목재',
        '1008': '화학',
        '1009': '의약품',
        '1010': '비금속',
        '1011': '금속',
        '1012': '기계장비',
        '1013': '전기전자',
        '1014': '의료정밀기기',
        '1015': '운수장비',
        '1016': '유통업',
        '1017': '전기가스업',
        '1018': '건설업',
        '1019': '운수창고',
        '1020': '통신업',
        '1021': '금융업',
        '1024': '증권',
        '1025': '보험',
        '1026': '서비스업',
    }

    def _build_sector_map(self):
        """KRX 업종 인덱스에서 종목코드→섹터 매핑 구축"""
        if hasattr(self, '_sector_map') and self._sector_map:
            return self._sector_map

        self._sector_map = {}
        for idx_code, sector_name in self.KRX_SECTOR_INDICES.items():
            try:
                codes = krx.get_index_portfolio_deposit_file(idx_code)
                if codes:
                    for code in codes:
                        self._sector_map[code] = sector_name
            except Exception:
                continue

        return self._sector_map

    def _enrich_sector_info(self, universe):
        """KRX 업종 인덱스로 섹터 정보 보강"""
        try:
            sector_map = self._build_sector_map()
            for item in universe:
                code = item['code']
                sector = sector_map.get(code, '')
                item['sector'] = sector
                item['industry'] = sector  # KRX는 sector=industry
        except Exception as e:
            print(f"⚠️ 섹터 정보 보강 실패: {e}")
            for item in universe:
                item.setdefault('sector', '')
                item.setdefault('industry', '')

    # ================================================================
    # 벌크 데이터 (캐시)
    # ================================================================
    def _get_bulk_fundamentals(self, date_str):
        """벌크 PER/PBR/DIV 데이터 (캐시)"""
        if date_str not in self._fundamental_cache:
            try:
                df_kospi = krx.get_market_fundamental(date_str, market='KOSPI')
                df_kosdaq = krx.get_market_fundamental(date_str, market='KOSDAQ')
                combined = pd.concat([df_kospi, df_kosdaq])
                self._fundamental_cache[date_str] = combined
            except Exception as e:
                print(f"⚠️ 펀더멘털 벌크 로드 실패: {e}")
                self._fundamental_cache[date_str] = pd.DataFrame()
        return self._fundamental_cache[date_str]

    def _get_bulk_market_cap(self, date_str):
        """벌크 시가총액 데이터 (캐시)"""
        if date_str not in self._market_cap_cache:
            try:
                df_kospi = krx.get_market_cap(date_str, market='KOSPI')
                df_kosdaq = krx.get_market_cap(date_str, market='KOSDAQ')
                combined = pd.concat([df_kospi, df_kosdaq])
                self._market_cap_cache[date_str] = combined
            except Exception as e:
                print(f"⚠️ 시총 벌크 로드 실패: {e}")
                self._market_cap_cache[date_str] = pd.DataFrame()
        return self._market_cap_cache[date_str]

    # ================================================================
    # 개별 종목 정보 (yfinance ticker.info 호환)
    # ================================================================
    def get_info(self, code, date_str=None):
        """종목 정보 (yfinance info 호환 딕셔너리)

        Returns:
            dict with keys: currentPrice, marketCap, averageVolume,
                           PER, PBR, dividendYield, returnOnEquity,
                           operatingMargins, revenueGrowth,
                           sector, industry, shortName
        """
        if date_str is None:
            date_str = self._find_latest_trading_date()

        info = {
            'currentPrice': 0,
            'regularMarketPrice': 0,
            'marketCap': 0,
            'averageVolume': 0,
            'trailingPE': 0,
            'forwardPE': 0,
            'priceToBook': 0,
            'dividendYield': 0,
            'returnOnEquity': None,
            'operatingMargins': None,
            'revenueGrowth': None,
            'sector': '',
            'industry': '',
            'shortName': '',
            'previousClose': 0,
        }

        try:
            # 이름
            name = krx.get_market_ticker_name(code)
            info['shortName'] = name or code

            # 시가총액 + 거래량
            cap_df = self._get_bulk_market_cap(date_str)
            if not cap_df.empty and code in cap_df.index:
                row = cap_df.loc[code]
                info['marketCap'] = int(row.get('시가총액', 0))
                info['averageVolume'] = int(row.get('거래량', 0))
                info['tradingValue'] = int(row.get('거래대금', 0))

            # PER/PBR/DIV
            fund_df = self._get_bulk_fundamentals(date_str)
            if not fund_df.empty and code in fund_df.index:
                row = fund_df.loc[code]
                per = row.get('PER', 0)
                pbr = row.get('PBR', 0)
                div_yield = row.get('DIV', 0)

                info['trailingPE'] = float(per) if per and per > 0 else 0
                info['forwardPE'] = float(per) if per and per > 0 else 0
                info['priceToBook'] = float(pbr) if pbr and pbr > 0 else 0
                info['dividendYield'] = float(div_yield) / 100 if div_yield and div_yield > 0 else 0

            # 현재가 (벌크 시총 데이터에서 종가 추출, 개별 API 호출 회피)
            if not cap_df.empty and code in cap_df.index:
                row = cap_df.loc[code]
                close_price = row.get('종가', 0)
                if close_price and close_price > 0:
                    info['currentPrice'] = int(close_price)
                    info['regularMarketPrice'] = info['currentPrice']
                    info['previousClose'] = info['currentPrice']  # 근사치

            # 벌크에 종가 없으면 개별 호출 (fallback)
            if info['currentPrice'] == 0:
                try:
                    ohlcv = krx.get_market_ohlcv(date_str, date_str, code)
                    if ohlcv is not None and not ohlcv.empty:
                        info['currentPrice'] = int(ohlcv['종가'].iloc[-1])
                        info['regularMarketPrice'] = info['currentPrice']
                        info['previousClose'] = int(ohlcv['시가'].iloc[-1])
                except Exception:
                    pass

            # 섹터/업종 (KRX 업종 인덱스)
            self._fill_sector_info(code, info)

            # DART 재무제표 (ROE, OPM, 매출성장률)
            self._fill_dart_financials(code, info)

        except Exception as e:
            print(f"⚠️ {code} info 로드 실패: {e}")

        return info

    def _fill_sector_info(self, code, info):
        """종목의 섹터 정보 채우기 (캐시된 sector_map 또는 이름 기반)"""
        try:
            # sector_map이 이미 구축되어 있으면 사용 (get_universe 경로)
            if hasattr(self, '_sector_map') and self._sector_map:
                sector = self._sector_map.get(code, '')
                if sector:
                    info['sector'] = sector
                    info['industry'] = sector
                    return
            # sector_map 없으면 (개별 종목 분석 경로) → 이름 기반 추론
            # project_titan_kr.py의 _get_growth_sector_score()가 이름으로 매칭하므로
            # 여기서는 빈 값으로 두어도 됨 (API 16회 호출 회피)
        except Exception:
            pass

    def _fill_dart_financials(self, code, info):
        """DART 재무제표에서 ROE, OPM, 매출성장률 계산"""
        # 캐시 확인
        if code in self._dart_cache:
            cached = self._dart_cache[code]
            info['returnOnEquity'] = cached.get('roe')
            info['operatingMargins'] = cached.get('opm')
            info['revenueGrowth'] = cached.get('revenue_growth')
            return

        roe = None
        opm = None
        revenue_growth = None

        if self._dart is not None:
            try:
                # 최근 사업보고서 (연간)
                current_year = datetime.now().year
                fs = None

                # 최근 연도부터 시도
                for yr in [current_year - 1, current_year - 2]:
                    try:
                        fs = self._dart.finstate(code, yr, reprt_code='11011')  # 사업보고서
                        if fs is not None and not fs.empty:
                            break
                    except Exception:
                        continue

                if fs is not None and not fs.empty:
                    # 매출액 찾기 (다양한 계정명 대응)
                    revenue_names = ['매출액', '수익(매출액)', '영업수익', '매출', '순매출액']
                    revenue = self._find_account(fs, revenue_names)

                    # 영업이익
                    op_names = ['영업이익', '영업이익(손실)']
                    operating_profit = self._find_account(fs, op_names)

                    # 당기순이익
                    ni_names = ['당기순이익', '당기순이익(손실)', '분기순이익']
                    net_income = self._find_account(fs, ni_names)

                    # 자본총계
                    equity_names = ['자본총계', '자본 총계']
                    equity = self._find_account(fs, equity_names)

                    # ROE 계산
                    if net_income and equity and equity != 0:
                        roe = net_income / equity
                        info['returnOnEquity'] = roe

                    # OPM 계산
                    if operating_profit and revenue and revenue != 0:
                        opm = operating_profit / revenue
                        info['operatingMargins'] = opm

                    # 매출성장률 (전년도 대비)
                    try:
                        fs_prev = None
                        for yr in [current_year - 2, current_year - 3]:
                            try:
                                fs_prev = self._dart.finstate(code, yr, reprt_code='11011')
                                if fs_prev is not None and not fs_prev.empty:
                                    break
                            except Exception:
                                continue

                        if fs_prev is not None and not fs_prev.empty:
                            prev_revenue = self._find_account(fs_prev, revenue_names)
                            if prev_revenue and prev_revenue != 0 and revenue:
                                revenue_growth = (revenue - prev_revenue) / abs(prev_revenue)
                                info['revenueGrowth'] = revenue_growth
                    except Exception:
                        pass

            except Exception as e:
                # DART 실패 시 조용히 넘어감
                pass

        # yfinance 한국 종목 (.KS/.KQ) - DART 실패 시 기본 대안
        # 연속 10회 네트워크/API 오류 시 자동 비활성 (데이터 없음은 오류로 안 침)
        if (roe is None or opm is None or revenue_growth is None) and YF_AVAILABLE and self._yf_enabled:
            try:
                for suffix in ['.KS', '.KQ']:
                    try:
                        yf_ticker = yf.Ticker(f"{code}{suffix}")
                        yf_info = yf_ticker.info
                        if not yf_info or not isinstance(yf_info, dict):
                            continue
                        # 종목 존재 여부 확인 (regularMarketPrice 대신 quoteType/shortName 확인)
                        if not yf_info.get('quoteType') and not yf_info.get('shortName'):
                            continue
                        if roe is None and yf_info.get('returnOnEquity') is not None:
                            roe = yf_info['returnOnEquity']
                            info['returnOnEquity'] = roe
                        if opm is None and yf_info.get('operatingMargins') is not None:
                            opm = yf_info['operatingMargins']
                            info['operatingMargins'] = opm
                        if revenue_growth is None and yf_info.get('revenueGrowth') is not None:
                            revenue_growth = yf_info['revenueGrowth']
                            info['revenueGrowth'] = revenue_growth
                        # 유효한 종목 찾았으면 (데이터 유무와 무관) 성공으로 처리
                        self._yf_fail_count = 0
                        break
                    except Exception:
                        continue
            except Exception:
                # 네트워크/API 오류만 실패로 카운트
                self._yf_fail_count += 1
            if self._yf_fail_count >= 10:
                self._yf_enabled = False
                print("   yfinance 자동 비활성화 (연속 10회 API 오류)", flush=True)

        # NAVER Finance 스크래핑 (yfinance도 실패 시 대안, 자동 비활성화 지원)
        if (roe is None or opm is None or revenue_growth is None) and self._naver_enabled:
            naver_data = self._fetch_naver_financials(code)
            if naver_data:
                if roe is None and naver_data.get('roe') is not None:
                    roe = naver_data['roe']
                    info['returnOnEquity'] = roe
                if opm is None and naver_data.get('opm') is not None:
                    opm = naver_data['opm']
                    info['operatingMargins'] = opm
                if revenue_growth is None and naver_data.get('revenue_growth') is not None:
                    revenue_growth = naver_data['revenue_growth']
                    info['revenueGrowth'] = revenue_growth

        # pykrx에서 PER/PBR로 대략적 추정 (DART + NAVER 모두 실패 시)
        if roe is None and info.get('trailingPE', 0) > 0 and info.get('priceToBook', 0) > 0:
            # ROE ≈ PBR / PER (근사치)
            per = info['trailingPE']
            pbr = info['priceToBook']
            if per > 0:
                roe_approx = pbr / per
                info['returnOnEquity'] = roe_approx
                roe = roe_approx

        # 캐시 저장
        self._dart_cache[code] = {
            'roe': roe,
            'opm': opm,
            'revenue_growth': revenue_growth,
        }

    def _fetch_naver_financials(self, code):
        """NAVER Finance에서 재무지표 스크래핑 (DART API 없을 때 대안)

        연속 3회 실패 시 자동 비활성화 (GitHub Actions 등 해외 서버 대응)

        Returns:
            dict: {roe, opm, revenue_growth} or None
        """
        try:
            import requests

            url = f"https://finance.naver.com/item/main.naver?code={code}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=3)
            resp.encoding = 'euc-kr'

            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}")

            tables = pd.read_html(resp.text, encoding='euc-kr')
            if not tables:
                return None

            result = {}

            for table in tables:
                table_str = table.to_string()

                # 재무비율 테이블 (영업이익률, ROE 포함)
                if '영업이익률' in table_str or 'ROE' in table_str:
                    for idx, row in table.iterrows():
                        row_label = str(row.iloc[0]) if len(row) > 0 else ''

                        if '영업이익률' in row_label and 'opm' not in result:
                            val = self._extract_naver_number(row)
                            if val is not None:
                                result['opm'] = val / 100

                        if 'ROE' in row_label.upper() and 'roe' not in result:
                            val = self._extract_naver_number(row)
                            if val is not None:
                                result['roe'] = val / 100

                # 매출액 테이블에서 성장률 계산
                if '매출액' in table_str and 'revenue_growth' not in result:
                    for idx, row in table.iterrows():
                        row_label = str(row.iloc[0]) if len(row) > 0 else ''
                        if '매출액' in row_label and '증가' not in row_label and '률' not in row_label:
                            revenues = []
                            for val in row.iloc[1:]:
                                try:
                                    v = float(str(val).replace(',', ''))
                                    if not pd.isna(v) and v != 0:
                                        revenues.append(v)
                                except (ValueError, TypeError):
                                    continue
                            if len(revenues) >= 2 and revenues[-2] != 0:
                                result['revenue_growth'] = (revenues[-1] - revenues[-2]) / abs(revenues[-2])
                            break

            if result:
                self._naver_fail_count = 0  # 성공 시 카운터 리셋
            return result if result else None

        except Exception:
            self._naver_fail_count += 1
            if self._naver_fail_count >= 3:
                self._naver_enabled = False
                print("   NAVER Finance 스크래핑 비활성화 (연속 실패, PBR/PER 추정 사용)", flush=True)
            return None

    def _extract_naver_number(self, row):
        """NAVER 테이블 row에서 가장 최근 유효 숫자 추출"""
        # 뒤에서부터 탐색 (최신 데이터 우선, 단 추정치(E) 제외)
        for val in reversed(list(row.iloc[1:])):
            try:
                s = str(val).replace(',', '').replace('%', '').strip()
                if s == '' or s == 'nan' or s == 'N/A':
                    continue
                v = float(s)
                if not pd.isna(v):
                    return v
            except (ValueError, TypeError):
                continue
        return None

    def _find_account(self, fs, account_names):
        """재무제표에서 계정 찾기 (fuzzy match)"""
        try:
            # account_nm 컬럼명 확인
            name_col = None
            for col in ['account_nm', 'sj_nm', 'account_nm']:
                if col in fs.columns:
                    name_col = col
                    break
            if name_col is None:
                return None

            # 금액 컬럼
            amount_col = None
            for col in ['thstrm_amount', 'thstrm_dt', 'amount']:
                if col in fs.columns:
                    amount_col = col
                    break
            if amount_col is None:
                return None

            for name in account_names:
                matches = fs[fs[name_col].str.contains(name, na=False, regex=False)]
                if not matches.empty:
                    # 연결재무제표 우선
                    for _, row in matches.iterrows():
                        val = row[amount_col]
                        if val and str(val).strip() and str(val).strip() != '':
                            try:
                                return float(str(val).replace(',', ''))
                            except (ValueError, TypeError):
                                continue
        except Exception:
            pass
        return None

    # ================================================================
    # OHLCV 히스토리 (yfinance history 호환)
    # ================================================================
    def get_history(self, code, period='1y'):
        """OHLCV DataFrame (yfinance history 호환)

        Args:
            code: 종목코드 (6자리)
            period: '1y', '2y', '6mo', '3mo'

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        end_date = datetime.now()
        period_map = {
            '3mo': 90,
            '6mo': 180,
            '1y': 365,
            '2y': 730,
            '3y': 1095,
        }
        days = period_map.get(period, 365)
        start_date = end_date - timedelta(days=days)

        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')

        try:
            df = krx.get_market_ohlcv(start_str, end_str, code)
            if df is None or df.empty:
                return pd.DataFrame()

            # 한글 컬럼명 → 영문 변환
            df = df.rename(columns={
                '시가': 'Open',
                '고가': 'High',
                '저가': 'Low',
                '종가': 'Close',
                '거래량': 'Volume',
            })

            # 필요한 컬럼만
            cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            available_cols = [c for c in cols if c in df.columns]
            df = df[available_cols]

            # 0 거래량 행 제거 (거래정지일)
            df = df[df['Volume'] > 0]

            return df

        except Exception as e:
            print(f"⚠️ {code} 히스토리 로드 실패: {e}")
            return pd.DataFrame()

    # ================================================================
    # 시장 지수 (KOSPI)
    # ================================================================
    def get_market_index(self, period='1y'):
        """KOSPI 지수 OHLCV (시장 레짐 감지용)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        if not PYKRX_AVAILABLE:
            return pd.DataFrame()

        end_date = datetime.now()
        period_map = {'6mo': 180, '1y': 365, '2y': 730}
        days = period_map.get(period, 365)
        start_date = end_date - timedelta(days=days)

        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')

        try:
            # KOSPI 지수 (1001)
            df = krx.get_index_ohlcv(start_str, end_str, '1001')
            if df is None or df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                '시가': 'Open',
                '고가': 'High',
                '저가': 'Low',
                '종가': 'Close',
                '거래량': 'Volume',
            })

            cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            available_cols = [c for c in cols if c in df.columns]
            return df[available_cols]

        except Exception as e:
            print(f"⚠️ KOSPI 지수 로드 실패: {e}")
            return pd.DataFrame()


# ================================================================
# 테스트
# ================================================================
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 60)
    print("🇰🇷 KR Data Provider 테스트")
    print("=" * 60)

    provider = KRDataProvider()

    # 1. 삼성전자 테스트
    print("\n--- 삼성전자 (005930) 정보 ---")
    info = provider.get_info('005930')
    print(f"  이름: {info['shortName']}")
    print(f"  현재가: ₩{info['currentPrice']:,}")
    print(f"  시가총액: ₩{info['marketCap']:,}")
    print(f"  PER: {info['trailingPE']:.1f}")
    print(f"  PBR: {info['priceToBook']:.2f}")
    print(f"  배당률: {info['dividendYield']*100:.1f}%")
    if info['returnOnEquity']:
        print(f"  ROE: {info['returnOnEquity']*100:.1f}%")
    if info['operatingMargins']:
        print(f"  OPM: {info['operatingMargins']*100:.1f}%")
    print(f"  섹터: {info['sector']}")
    print(f"  업종: {info['industry']}")

    # 2. 히스토리 테스트
    print("\n--- 삼성전자 1년 히스토리 ---")
    hist = provider.get_history('005930', '1y')
    if not hist.empty:
        print(f"  기간: {hist.index[0]} ~ {hist.index[-1]}")
        print(f"  데이터: {len(hist)}일")
        print(f"  최근 종가: ₩{int(hist['Close'].iloc[-1]):,}")

    # 3. KOSPI 지수
    print("\n--- KOSPI 지수 ---")
    kospi = provider.get_market_index('1y')
    if not kospi.empty:
        print(f"  기간: {kospi.index[0]} ~ {kospi.index[-1]}")
        print(f"  현재: {kospi['Close'].iloc[-1]:,.2f}")

    # 4. 유니버스
    print("\n--- 유니버스 (상위 5개) ---")
    universe = provider.get_universe(kosdaq_top_n=50)
    for item in universe[:5]:
        print(f"  {item['code']} {item['name']} ({item['market']}) - {item.get('sector', 'N/A')}")
    print(f"  ... 총 {len(universe)}개")
