"""
데이터 보강 포트
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import date

from core.domain.models import StockInfo


class TickerMapperPort(ABC):
    """종목명으로 티커(종목코드)를 조회하는 포트"""
    @abstractmethod
    def get_ticker(self, stock_name: str) -> Optional[str]:
        pass


class MarketDataProviderPort(ABC):
    """시세 데이터를 조회하는 포트"""
    @abstractmethod
    def get_ohlc(self, ticker: str, target_date: date) -> Optional[Dict[str, int]]:
        """
        특정 날짜의 OHLC(시가, 고가, 저가, 종가) 데이터를 조회
        Returns:
            {"Open": 1000, "High": 1100, "Low": 900, "Close": 1050}
        """
        pass


class StockEnricherPort(ABC):
    """
    주가 보강 서비스 포트

    `EnrichmentService`가 `StockPriceEnricher` 구체 타입 대신
    이 인터페이스를 의존함으로써 코어 레이어와 인프라를 분리합니다.
    """

    @abstractmethod
    def enrich_stock_info(self, stock: StockInfo) -> StockInfo:
        """StockInfo에 OHLC 및 수익률 보강 후 반환"""
        pass

    @abstractmethod
    def get_market_data(
        self,
        stock_name: str,
        listing_date_val: Any,
        confirmed_price_val: Any,
    ) -> Dict[str, Any]:
        """
        종목명·상장일·공모가를 받아 OHLC 및 수익률 딕셔너리 반환

        Returns:
            {'\uc2dc\uac00': ..., '\uace0\uac00': ..., '\uc800\uac00': ..., '\uc885\uac00': ..., '\uc218\uc775\ub960(%)': ...}
        """
        pass
