from pykrx import stock
from typing import Optional, Dict
from datetime import date
import pandas as pd

from core.ports.enrichment_ports import TickerMapperPort, MarketDataProviderPort


class PyKrxAdapter(TickerMapperPort, MarketDataProviderPort):
    """
    PyKrx를 사용한 데이터 제공 어댑터
    (KRX 공식 데이터를 스크래핑하여 제공)

    성능:
        get_ticker()는 세션 최초 호출 시 전체 종목명→티커 캐시를 1회 로드합니다.
        이후 호출은 캐시에서 O(1)로 조회합니다.
    """

    def __init__(self) -> None:
        # {종목명: 티커} 캐시 — 세션 내 KRX 서버를 1회만 호출
        self._ticker_cache: Dict[str, str] = {}

    def _load_ticker_cache(self) -> None:
        """KOSPI, KOSDAQ, KONEX 전체 종목 캐시를 한 번만 로드"""
        if self._ticker_cache:
            return

        today = date.today().strftime("%Y%m%d")
        for market in ["KOSPI", "KOSDAQ", "KONEX"]:
            try:
                tickers = stock.get_market_ticker_list(today, market=market)
                for ticker in tickers:
                    name = stock.get_market_ticker_name(ticker)
                    if name and name not in self._ticker_cache:
                        self._ticker_cache[name] = ticker
            except Exception:
                continue

    def get_ticker(self, stock_name: str) -> Optional[str]:
        """
        종목명으로 티커 조회 (캐시 기반, 세션당 1회 KRX 로드)

        Args:
            stock_name: 검색할 종목명

        Returns:
            티커 문자열 또는 None
        """
        self._load_ticker_cache()

        # 1. 정확히 일치하는 경우
        if stock_name in self._ticker_cache:
            return self._ticker_cache[stock_name]

        # 2. (주) 제거 후 재검색
        cleaned_name = stock_name.replace("(주)", "").strip()
        if cleaned_name != stock_name and cleaned_name in self._ticker_cache:
            return self._ticker_cache[cleaned_name]

        return None


    def get_ohlc(self, ticker: str, target_date: date) -> Optional[Dict[str, int]]:
        """
        특정 날짜의 OHLC 데이터 조회
        """
        try:
            # 날짜 포맷 변환 (YYYYMMDD)
            date_str = target_date.strftime("%Y%m%d")
            
            # 해당 날짜의 데이터 조회 (시작일=종료일)
            df = stock.get_market_ohlcv(date_str, date_str, ticker)
            
            if df.empty:
                return None
            
            # 첫 번째 행 사용
            row = df.iloc[0]
            
            # 0원인 경우 데이터 없음으로 간주 (거래 정지 등)
            if row['시가'] == 0 and row['종가'] == 0:
                return None
                
            return {
                "Open": int(row['시가']),
                "High": int(row['고가']),
                "Low": int(row['저가']),
                "Close": int(row['종가'])
            }
        except Exception:
            return None
