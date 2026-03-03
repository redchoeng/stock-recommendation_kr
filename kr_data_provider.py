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
        # 삼성전자 개별 OHLCV로 최근 영업일 탐색 (벌크 API 장애 대응)
        try:
            start_str = (today - timedelta(days=max_lookback)).strftime('%Y%m%d')
            end_str = today.strftime('%Y%m%d')
            df = krx.get_market_ohlcv(start_str, end_str, '005930')
            if df is not None and not df.empty:
                last_date = df.index[-1]
                if hasattr(last_date, 'strftime'):
                    date_str = last_date.strftime('%Y%m%d')
                else:
                    date_str = str(last_date).replace('-', '')[:8]
                self._cached_trading_date = date_str
                return date_str
        except Exception:
            pass

        # fallback: 주말 건너뛴 어제
        for i in range(max_lookback):
            date = today - timedelta(days=i)
            if date.weekday() < 5:
                fallback = date.strftime('%Y%m%d')
                self._cached_trading_date = fallback
                return fallback
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
        date_str = self._find_latest_trading_date()
        universe = []

        # --- 방법 1: pykrx KOSPI 200 인덱스 ---
        kospi200_loaded = False
        if PYKRX_AVAILABLE:
            try:
                kospi200_codes = krx.get_index_portfolio_deposit_file('1028')
                if kospi200_codes and len(kospi200_codes) > 0:
                    print(f"✅ KOSPI 200: {len(kospi200_codes)}개 로드 (pykrx)")
                    for code in kospi200_codes:
                        name = krx.get_market_ticker_name(code)
                        universe.append({
                            'code': code,
                            'name': name or code,
                            'market': 'KOSPI',
                        })
                    kospi200_loaded = True
            except Exception:
                pass

        # --- 방법 2: FDR fallback (pykrx 벌크 API 장애 시) ---
        if not kospi200_loaded and FDR_AVAILABLE:
            try:
                all_stocks = self._get_fdr_stock_listing()
                if all_stocks is not None and not all_stocks.empty:
                    # KOSPI 주요 종목: 시총 기준으로 상위 200개 선택
                    # FDR에는 시총이 없으므로 yfinance로 시총 상위 추정
                    kospi_stocks = all_stocks[all_stocks['Market'] == 'KOSPI']
                    # KOSPI 전체에서 상위 200개 (이름순 대신 코드 기반)
                    # 시총 정보 없이는 전체 KOSPI를 가져와야 함
                    kospi_codes = kospi_stocks['Code'].tolist()[:200]
                    print(f"✅ KOSPI 상위: {len(kospi_codes)}개 로드 (FDR fallback)")
                    for _, row in kospi_stocks.head(200).iterrows():
                        universe.append({
                            'code': row['Code'],
                            'name': row['Name'],
                            'market': 'KOSPI',
                            'sector': row.get('Sector', ''),
                            'industry': row.get('Industry', ''),
                        })
                    kospi200_loaded = True
            except Exception as e:
                print(f"⚠️ FDR KOSPI 로드 실패: {e}")

        # --- KOSDAQ 시총 상위 ---
        kosdaq_loaded = False
        if PYKRX_AVAILABLE:
            try:
                kosdaq_cap = krx.get_market_cap(date_str, market='KOSDAQ')
                if kosdaq_cap is not None and not kosdaq_cap.empty:
                    kosdaq_top = kosdaq_cap.nlargest(kosdaq_top_n, '시가총액')
                    print(f"✅ KOSDAQ 시총 상위 {len(kosdaq_top)}개 로드 (pykrx)")
                    for code in kosdaq_top.index:
                        name = krx.get_market_ticker_name(code)
                        universe.append({
                            'code': code,
                            'name': name or code,
                            'market': 'KOSDAQ',
                        })
                    kosdaq_loaded = True
            except Exception:
                pass

        if not kosdaq_loaded and FDR_AVAILABLE:
            try:
                all_stocks = self._get_fdr_stock_listing()
                if all_stocks is not None and not all_stocks.empty:
                    kosdaq_stocks = all_stocks[all_stocks['Market'] == 'KOSDAQ']
                    kosdaq_top = kosdaq_stocks.head(kosdaq_top_n)
                    print(f"✅ KOSDAQ 상위: {len(kosdaq_top)}개 로드 (FDR fallback)")
                    for _, row in kosdaq_top.iterrows():
                        universe.append({
                            'code': row['Code'],
                            'name': row['Name'],
                            'market': 'KOSDAQ',
                            'sector': row.get('Sector', ''),
                            'industry': row.get('Industry', ''),
                        })
            except Exception as e:
                print(f"⚠️ FDR KOSDAQ 로드 실패: {e}")

        # --- Sector/Industry 매핑 ---
        self._enrich_sector_info(universe)

        print(f"📊 전체 유니버스: {len(universe)}개 종목")
        return universe

    def _get_fdr_stock_listing(self):
        """FDR 종목 리스트 (캐시)"""
        if not hasattr(self, '_fdr_listing_cache') or self._fdr_listing_cache is None:
            try:
                import FinanceDataReader as fdr
                self._fdr_listing_cache = fdr.StockListing('KRX-DESC')
            except Exception:
                self._fdr_listing_cache = pd.DataFrame()
        return self._fdr_listing_cache

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
        """종목코드→섹터 매핑 구축 (KRX 인덱스 → FDR fallback)"""
        if hasattr(self, '_sector_map') and self._sector_map:
            return self._sector_map

        self._sector_map = {}

        # 방법 1: pykrx KRX 업종 인덱스
        if PYKRX_AVAILABLE:
            try:
                for idx_code, sector_name in self.KRX_SECTOR_INDICES.items():
                    try:
                        codes = krx.get_index_portfolio_deposit_file(idx_code)
                        if codes:
                            for code in codes:
                                self._sector_map[code] = sector_name
                    except Exception:
                        continue
                if self._sector_map:
                    return self._sector_map
            except Exception:
                pass

        # 방법 2: FDR fallback (KRX API 장애 시)
        if FDR_AVAILABLE:
            try:
                all_stocks = self._get_fdr_stock_listing()
                if all_stocks is not None and not all_stocks.empty:
                    # FDR Sector를 KRX 업종명으로 근사 매핑
                    for _, row in all_stocks.iterrows():
                        code = row.get('Code', '')
                        sector = row.get('Sector', '')
                        if code and sector:
                            # FDR 세부 업종 → KRX 대분류 근사 매핑
                            mapped = self._map_fdr_sector_to_krx(sector)
                            self._sector_map[code] = mapped
            except Exception:
                pass

        return self._sector_map

    # FDR 세부 업종 → KRX 대분류 매핑
    FDR_TO_KRX_SECTOR = {
        '반도체': '전기전자', '전자부품': '전기전자', '통신': '전기전자',
        '디스플레이': '전기전자', '컴퓨터': '전기전자', '소프트웨어': '서비스업',
        '의약품': '의약품', '바이오': '의약품', '기초 의약': '의약품',
        '자동차': '운수장비', '조선': '운수장비', '항공': '운수창고',
        '화학': '화학', '석유': '화학', '플라스틱': '화학',
        '철강': '금속', '비철금속': '금속', '금속': '금속',
        '기계': '기계장비', '건설': '건설업', '전기': '전기가스업',
        '가스': '전기가스업', '유틸리티': '전기가스업',
        '은행': '금융업', '보험': '보험', '증권': '증권', '금융': '금융업',
        '유통': '유통업', '음식': '음식료품', '식품': '음식료품',
        '섬유': '섬유의류', '의류': '섬유의류',
        '통신': '통신업', '방송': '통신업',
        '운수': '운수창고', '물류': '운수창고', '해운': '운수창고',
        '의료': '의료정밀기기', '종이': '종이목재', '목재': '종이목재',
        '비금속': '비금속', '세라믹': '비금속', '유리': '비금속',
    }

    def _map_fdr_sector_to_krx(self, fdr_sector):
        """FDR 세부 업종명 → KRX 대분류 매핑"""
        if not fdr_sector:
            return ''
        for keyword, krx_sector in self.FDR_TO_KRX_SECTOR.items():
            if keyword in fdr_sector:
                return krx_sector
        return fdr_sector  # 매핑 실패 시 원본 반환

    def _enrich_sector_info(self, universe):
        """섹터 정보 보강 (KRX 인덱스 or FDR)"""
        try:
            sector_map = self._build_sector_map()
            for item in universe:
                code = item['code']
                # 이미 섹터 정보가 있으면 (FDR에서 가져온 경우) 스킵
                if item.get('sector'):
                    # FDR 세부 업종 → KRX 대분류로 변환
                    item['sector'] = self._map_fdr_sector_to_krx(item['sector'])
                    item['industry'] = item['sector']
                    continue
                sector = sector_map.get(code, '')
                item['sector'] = sector
                item['industry'] = sector
        except Exception as e:
            print(f"⚠️ 섹터 정보 보강 실패: {e}")
            for item in universe:
                item.setdefault('sector', '')
                item.setdefault('industry', '')

    # ================================================================
    # 벌크 데이터 (캐시)
    # ================================================================
    def _get_bulk_fundamentals(self, date_str):
        """벌크 PER/PBR/DIV 데이터 (캐시, KRX API 장애 시 빈 DataFrame)"""
        if date_str not in self._fundamental_cache:
            if PYKRX_AVAILABLE:
                try:
                    df_kospi = krx.get_market_fundamental(date_str, market='KOSPI')
                    df_kosdaq = krx.get_market_fundamental(date_str, market='KOSDAQ')
                    combined = pd.concat([df_kospi, df_kosdaq])
                    if not combined.empty:
                        self._fundamental_cache[date_str] = combined
                        return combined
                except Exception:
                    pass  # KRX API 장애 → yfinance fallback
            self._fundamental_cache[date_str] = pd.DataFrame()
        return self._fundamental_cache[date_str]

    def _get_bulk_market_cap(self, date_str):
        """벌크 시가총액 데이터 (캐시, KRX API 장애 시 빈 DataFrame)"""
        if date_str not in self._market_cap_cache:
            if PYKRX_AVAILABLE:
                try:
                    df_kospi = krx.get_market_cap(date_str, market='KOSPI')
                    df_kosdaq = krx.get_market_cap(date_str, market='KOSDAQ')
                    combined = pd.concat([df_kospi, df_kosdaq])
                    if not combined.empty:
                        self._market_cap_cache[date_str] = combined
                        return combined
                except Exception:
                    pass  # KRX API 장애 → yfinance fallback
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
            'dividendRate': None,
            'returnOnEquity': None,
            'operatingMargins': None,
            'revenueGrowth': None,
            'freeCashflow': None,
            'totalRevenue': None,
            'enterpriseToEbitda': None,
            'debtToEquity': None,
            'beta': None,
            'pegRatio': None,
            'payoutRatio': None,
            'earningsGrowth': None,
            'fiveYearAvgDividendYield': None,
            'sector': '',
            'industry': '',
            'shortName': '',
            'previousClose': 0,
        }

        try:
            # 이름
            try:
                name = krx.get_market_ticker_name(code) if PYKRX_AVAILABLE else None
            except Exception:
                name = None
            info['shortName'] = name or code

            # --- pykrx 벌크 API (시총/PER/PBR/DIV) ---
            # KRX API 장애 시 빈 DataFrame 반환 → yfinance fallback
            cap_df = self._get_bulk_market_cap(date_str)
            if not cap_df.empty and code in cap_df.index:
                row = cap_df.loc[code]
                info['marketCap'] = int(row.get('시가총액', 0))
                info['averageVolume'] = int(row.get('거래량', 0))
                info['tradingValue'] = int(row.get('거래대금', 0))

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

            # --- 현재가 + 전일종가 (pykrx 개별 OHLCV, 아직 작동) ---
            try:
                end_date = datetime.strptime(date_str, '%Y%m%d')
                start_lookback = (end_date - timedelta(days=10)).strftime('%Y%m%d')
                ohlcv = krx.get_market_ohlcv(start_lookback, date_str, code) if PYKRX_AVAILABLE else None
                if ohlcv is not None and not ohlcv.empty and len(ohlcv) >= 1:
                    ohlcv = ohlcv[ohlcv['거래량'] > 0]
                    if len(ohlcv) >= 1:
                        info['currentPrice'] = int(ohlcv['종가'].iloc[-1])
                        info['regularMarketPrice'] = info['currentPrice']
                        if len(ohlcv) >= 2:
                            info['previousClose'] = int(ohlcv['종가'].iloc[-2])
                        else:
                            info['previousClose'] = info['currentPrice']
            except Exception:
                pass

            # --- yfinance fallback (pykrx 벌크 API 장애 대응) ---
            # marketCap, PER, PBR, DIV, previousClose 등이 0이면 yfinance로 보완
            needs_yf = (info['marketCap'] == 0 or info['trailingPE'] == 0
                        or info['currentPrice'] == 0)
            if needs_yf and YF_AVAILABLE and self._yf_enabled:
                self._fill_from_yfinance(code, info)

            # 섹터/업종
            self._fill_sector_info(code, info)

            # DART 재무제표 (ROE, OPM, 매출성장률)
            self._fill_dart_financials(code, info)

            # PBR 추정 (yfinance에서 PBR 없는 경우: PBR ≈ PER × ROE)
            if info['priceToBook'] == 0 and info['trailingPE'] > 0 and info.get('returnOnEquity'):
                roe = info['returnOnEquity']
                if roe and roe > 0:
                    info['priceToBook'] = round(info['trailingPE'] * roe, 2)

        except Exception as e:
            print(f"⚠️ {code} info 로드 실패: {e}")

        return info

    def _get_yf_info(self, code):
        """yfinance info 캐시 (중복 호출 방지)"""
        if not hasattr(self, '_yf_info_cache'):
            self._yf_info_cache = {}
        if code in self._yf_info_cache:
            return self._yf_info_cache[code]

        yf_info = None
        for suffix in ['.KS', '.KQ']:
            try:
                yf_ticker = yf.Ticker(f"{code}{suffix}")
                candidate = yf_ticker.info
                if not candidate or not isinstance(candidate, dict):
                    continue
                if not candidate.get('quoteType') and not candidate.get('shortName'):
                    continue
                yf_info = candidate
                self._yf_fail_count = 0
                break
            except Exception:
                continue

        self._yf_info_cache[code] = yf_info
        return yf_info

    def _fill_from_yfinance(self, code, info):
        """yfinance로 누락 데이터 보완 (pykrx 벌크 API 장애 fallback)"""
        try:
            yf_info = self._get_yf_info(code)
            if not yf_info:
                return

            # 현재가
            if info['currentPrice'] == 0:
                price = yf_info.get('currentPrice') or yf_info.get('regularMarketPrice', 0)
                if price and price > 0:
                    info['currentPrice'] = int(price)
                    info['regularMarketPrice'] = int(price)

            # 전일종가
            if info['previousClose'] == 0 or info['previousClose'] == info['currentPrice']:
                prev = yf_info.get('previousClose', 0)
                if prev and prev > 0:
                    info['previousClose'] = int(prev)

            # 시가총액
            if info['marketCap'] == 0:
                mcap = yf_info.get('marketCap', 0)
                if mcap and mcap > 0:
                    info['marketCap'] = int(mcap)

            # 거래량
            if info['averageVolume'] == 0:
                vol = yf_info.get('averageVolume') or yf_info.get('volume', 0)
                if vol and vol > 0:
                    info['averageVolume'] = int(vol)

            # PER
            if info['trailingPE'] == 0:
                pe = yf_info.get('trailingPE') or yf_info.get('forwardPE', 0)
                if pe and pe > 0:
                    info['trailingPE'] = float(pe)
                    info['forwardPE'] = float(pe)

            # PBR
            if info['priceToBook'] == 0:
                pbr = yf_info.get('priceToBook', 0)
                if pbr and pbr > 0:
                    info['priceToBook'] = float(pbr)

            # 배당수익률
            if info['dividendYield'] == 0:
                dy = yf_info.get('dividendYield', 0)
                if dy and dy > 0:
                    info['dividendYield'] = float(dy) if dy < 1 else float(dy) / 100

            # 이름 보완
            if info['shortName'] == code:
                name = yf_info.get('shortName') or yf_info.get('longName', '')
                if name:
                    info['shortName'] = name

            # 추가 필드 일괄 보완 (ROE, OPM, FCF 등)
            for key in ['returnOnEquity', 'operatingMargins', 'revenueGrowth',
                        'freeCashflow', 'totalRevenue', 'enterpriseToEbitda',
                        'debtToEquity', 'beta', 'pegRatio', 'payoutRatio',
                        'earningsGrowth', 'fiveYearAvgDividendYield', 'dividendRate']:
                if info.get(key) is None and yf_info.get(key) is not None:
                    info[key] = yf_info[key]

        except Exception:
            self._yf_fail_count += 1
            if self._yf_fail_count >= 10:
                self._yf_enabled = False
                print("   yfinance 자동 비활성화 (연속 10회 API 오류)", flush=True)

    def _fill_sector_info(self, code, info):
        """종목의 섹터 정보 채우기 (캐시된 sector_map 또는 이름 기반)"""
        try:
            if hasattr(self, '_sector_map') and self._sector_map:
                sector = self._sector_map.get(code, '')
                if sector:
                    info['sector'] = sector
                    info['industry'] = sector
                    return
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

        # yfinance 한국 종목 (.KS/.KQ) - DART 실패 시 대안 (캐시된 yf_info 재사용)
        if (roe is None or opm is None or revenue_growth is None) and YF_AVAILABLE and self._yf_enabled:
            try:
                yf_info = self._get_yf_info(code)
                if yf_info:
                    if roe is None and yf_info.get('returnOnEquity') is not None:
                        roe = yf_info['returnOnEquity']
                        info['returnOnEquity'] = roe
                    if opm is None and yf_info.get('operatingMargins') is not None:
                        opm = yf_info['operatingMargins']
                        info['operatingMargins'] = opm
                    if revenue_growth is None and yf_info.get('revenueGrowth') is not None:
                        revenue_growth = yf_info['revenueGrowth']
                        info['revenueGrowth'] = revenue_growth
                    # 추가 필드 (이미 _fill_from_yfinance에서 채워졌을 수 있지만, 호출 순서에 따라 보완)
                    for key in ['freeCashflow', 'totalRevenue', 'enterpriseToEbitda',
                                'debtToEquity', 'beta', 'pegRatio', 'payoutRatio',
                                'earningsGrowth', 'fiveYearAvgDividendYield', 'dividendRate']:
                        if info.get(key) is None and yf_info.get(key) is not None:
                            info[key] = yf_info[key]
            except Exception:
                pass

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
        # 방법 1: pykrx (KRX API)
        if PYKRX_AVAILABLE:
            end_date = datetime.now()
            period_map = {'6mo': 180, '1y': 365, '2y': 730}
            days = period_map.get(period, 365)
            start_date = end_date - timedelta(days=days)
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            try:
                df = krx.get_index_ohlcv(start_str, end_str, '1001')
                if df is not None and not df.empty:
                    df = df.rename(columns={
                        '시가': 'Open', '고가': 'High',
                        '저가': 'Low', '종가': 'Close', '거래량': 'Volume',
                    })
                    cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    available_cols = [c for c in cols if c in df.columns]
                    return df[available_cols]
            except Exception:
                pass

        # 방법 2: yfinance fallback (^KS11)
        if YF_AVAILABLE:
            try:
                kospi = yf.Ticker('^KS11')
                df = kospi.history(period=period)
                if df is not None and not df.empty:
                    # yfinance 컬럼: Open, High, Low, Close, Volume, Dividends, Stock Splits
                    cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    available_cols = [c for c in cols if c in df.columns]
                    df = df[available_cols]
                    # timezone-aware index → naive (pykrx 호환)
                    if df.index.tz is not None:
                        df.index = df.index.tz_localize(None)
                    return df
            except Exception as e:
                print(f"⚠️ KOSPI 지수 yfinance 로드 실패: {e}")

        print(f"⚠️ KOSPI 지수 로드 실패 (pykrx + yfinance 모두 실패)")
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
