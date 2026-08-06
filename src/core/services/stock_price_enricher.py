"""
주가 정보 보강 서비스
"""

from typing import Optional, Dict
import pandas as pd

from core.ports.enrichment_ports import (
    TickerMapperPort,
    MarketDataProviderPort,
    StockEnricherPort,
)
from core.ports.utility_ports import LoggerPort


class StockPriceEnricher(StockEnricherPort):
    """
    주가 정보(OHLC) 및 수익률 계산 로직을 담당하는 도메인 서비스
    """

    def __init__(
        self,
        ticker_mapper: TickerMapperPort,
        market_data_provider: MarketDataProviderPort,
        logger: LoggerPort,
    ):
        self.ticker_mapper = ticker_mapper
        self.market_data_provider = market_data_provider
        self.logger = logger

    def get_market_data(
        self, stock_name: str, listing_date_val: str, confirmed_price_val: str
    ) -> Dict:
        """
        종목명, 상장일, 공모가를 받아 OHLC 및 수익률 딕셔너리 반환 (EnrichmentService용)
        """
        result = {
            "시가": None,
            "고가": None,
            "저가": None,
            "종가": None,
            "수익률(%)": None,
        }

        try:
            # 1. 상장일 파싱
            if not listing_date_val or listing_date_val == "N/A":
                self.logger.info(f"    - [SKIP] 상장일 정보 없음: {stock_name}")
                return result

            try:
                listing_date_str = str(listing_date_val).replace(".", "-")
                listing_date = pd.to_datetime(listing_date_str).date()
            except Exception as e:
                self.logger.info(
                    f"    - [SKIP] 날짜 변환 실패: {stock_name} ({listing_date_val}) - {e}"
                )
                return result

            # 2. OHLC 조회 (이름으로 직접 조회)
            ohlc = self.market_data_provider.get_ohlc(
                name=stock_name, target_date=listing_date
            )

            if not ohlc:
                # Fallback: Ticker로 시도
                ticker = self.ticker_mapper.get_ticker(stock_name)
                if ticker:
                    ohlc = self.market_data_provider.get_ohlc(
                        ticker=ticker, target_date=listing_date
                    )

            if not ohlc:
                self.logger.info(
                    f"    - [SKIP] OHLC 데이터 없음: {stock_name} ({listing_date})"
                )
                return result

            result["시가"] = ohlc["Open"]
            result["고가"] = ohlc["High"]
            result["저가"] = ohlc["Low"]
            result["종가"] = ohlc["Close"]

            # 3. 수익률 계산
            confirmed_price = self._parse_price(confirmed_price_val)
            if confirmed_price:
                growth_rate = self._calculate_growth_rate(
                    ohlc["Close"], confirmed_price
                )
                result["수익률(%)"] = growth_rate
                self.logger.info(f"    - [OK] {stock_name}: 수익률 {growth_rate}%")
            else:
                self.logger.info(
                    f"    - [WARN] 공모가 변환 실패: {stock_name} ({confirmed_price_val})"
                )

            return result

        except Exception as e:
            self.logger.error(f"    - [ERROR] {stock_name} 처리 중 오류: {e}")
            return result

    def _calculate_growth_rate(
        self, close_price: int, confirmed_price: Optional[int]
    ) -> Optional[float]:
        """수익률 계산"""
        if confirmed_price and confirmed_price > 0:
            growth_rate = (close_price - confirmed_price) / confirmed_price * 100
            return round(growth_rate, 2)
        return None

    def _parse_price(self, price_val: str) -> Optional[int]:
        """가격 문자열 파싱"""
        if pd.notna(price_val) and price_val != "":
            try:
                return int(float(str(price_val).replace(",", "")))
            except ValueError:
                return None
        return None
