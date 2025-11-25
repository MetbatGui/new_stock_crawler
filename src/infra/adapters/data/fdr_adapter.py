import FinanceDataReader as fdr
from typing import Optional, Dict
from datetime import date
import pandas as pd

from core.ports.enrichment_ports import TickerMapperPort, MarketDataProviderPort

class FDRAdapter(TickerMapperPort, MarketDataProviderPort):
    """
    FinanceDataReader를 사용한 데이터 제공 어댑터
    """
    def __init__(self):
        self._krx_listing = None
        
    def _load_listing(self):
        """KRX 종목 리스트 로드 (Lazy Loading)"""
        if self._krx_listing is None:
            # KRX 전체 종목 리스트 (상장폐지 종목 포함 여부는 옵션 확인 필요, 기본은 현재 상장)
            # FDR의 StockListing('KRX')는 현재 상장 종목만 가져옴.
            # 상장폐지된 종목의 과거 데이터를 위해서는 'KRX-DELISTING'도 확인해야 할 수 있음.
            # 우선은 'KRX'로 진행.
            self._krx_listing = fdr.StockListing('KRX')
            
    def get_ticker(self, stock_name: str) -> Optional[str]:
        self._load_listing()
        
        # 1. 정확히 일치하는 경우
        row = self._krx_listing[self._krx_listing['Name'] == stock_name]
        if not row.empty:
            return str(row.iloc[0]['Code'])
        
        # 2. 스팩 종목 처리 (예: "엔에이치스팩19호" -> "NH스팩19호" 등 변환 필요할 수 있음)
        # 우선 간단한 정제만 수행
        cleaned_name = stock_name.replace("(주)", "").strip()
        row = self._krx_listing[self._krx_listing['Name'] == cleaned_name]
        if not row.empty:
            return str(row.iloc[0]['Code'])
            
        return None

    def get_ohlc(self, ticker: str, target_date: date) -> Optional[Dict[str, int]]:
        try:
            # FDR은 문자열 날짜나 datetime 객체 모두 수용
            # start와 end를 같게 하여 1일치 데이터 조회
            df = fdr.DataReader(ticker, target_date, target_date)
            
            if df.empty:
                return None
            
            row = df.iloc[0]
            return {
                "Open": int(row['Open']),
                "High": int(row['High']),
                "Low": int(row['Low']),
                "Close": int(row['Close'])
            }
        except Exception:
            return None
