# src/domain/ports.py
from abc import ABC, abstractmethod
from typing import Generator, Tuple, List, Dict 
from playwright.sync_api import Page
from .models import ScrapeReport, StockInfo  # [수정] StockInfo 임포트
import pandas as pd

class IPOInfoPort(ABC):
    
    @abstractmethod
    def setup(self) -> None:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass

    @abstractmethod
    def test_navigation(self, year: int, start_month: int, end_month: int) -> None:
        pass

    @abstractmethod
    def get_ipos_for_period(
        self, year: int, start_month: int, end_month: int, today_day: int
    ) -> ScrapeReport:
        """
        지정된 기간 동안의 IPO 목록을 스크랩하고 ScrapeReport를 반환합니다.
        """
        pass

    # ▼ [수정] 반환 타입이 None -> List[StockInfo] 로 변경
    @abstractmethod
    def scrape_stock_details(self, stocks: List[Tuple[str, str]]) -> List[StockInfo]:
        """
        수집된 (종목명, href) 리스트를 받아 세부 정보를 스크랩하고
        StockInfo 객체 리스트를 반환합니다.
        """
        pass


class PersistencePort(ABC):
    """
    데이터 저장을 위한 아웃바운드 포트 (인터페이스)
    """
    
    @abstractmethod
    def save_report(self, data: Dict[int, pd.DataFrame]) -> None:
        """
        스크래핑 리포트(DataFrame) 딕셔너리를 저장합니다.
        
        Args:
            data (Dict[int, pd.DataFrame]): {연도: DataFrame} 형태의 
                                            전체 데이터 딕셔너리.
        """
        pass