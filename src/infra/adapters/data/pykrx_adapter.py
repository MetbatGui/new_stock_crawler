from pykrx import stock
from typing import Optional, Dict
from datetime import date
import pandas as pd

from core.ports.enrichment_ports import TickerMapperPort, MarketDataProviderPort

class PyKrxAdapter(TickerMapperPort, MarketDataProviderPort):
    """
    PyKrx를 사용한 데이터 제공 어댑터
    (KRX 공식 데이터를 스크래핑하여 제공)
    """
    
    def get_ticker(self, stock_name: str) -> Optional[str]:
        """
        종목명으로 티커 조회
        (KOSPI, KOSDAQ, KONEX 순차 검색)
        """
        # 기준일은 오늘로 설정 (최신 종목 검색)
        today = date.today().strftime("%Y%m%d")
        
        # 검색할 시장 목록
        markets = ["KOSPI", "KOSDAQ", "KONEX"]
        
        # 1. 정확히 일치하는 경우 검색
        for market in markets:
            try:
                tickers = stock.get_market_ticker_list(today, market=market)
                for ticker in tickers:
                    name = stock.get_market_ticker_name(ticker)
                    if name == stock_name:
                        return ticker
            except Exception:
                continue
                
        # 2. (주) 제거 등 간단한 정제 후 재검색
        cleaned_name = stock_name.replace("(주)", "").strip()
        if cleaned_name != stock_name:
            for market in markets:
                try:
                    tickers = stock.get_market_ticker_list(today, market=market)
                    for ticker in tickers:
                        name = stock.get_market_ticker_name(ticker)
                        if name == cleaned_name:
                            return ticker
                except Exception:
                    continue
                    
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
