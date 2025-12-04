"""
웹 스크래핑 관련 포트 인터페이스
"""
from abc import ABC, abstractmethod
from typing import List, Tuple
from playwright.sync_api import Page
from core.domain.models import ScrapeReport, StockInfo


class PageProvider(ABC):
    """
    Playwright Page 객체 제공 포트
    
    책임: 브라우저 생명주기 관리
    """
    
    @abstractmethod
    def setup(self) -> None:
        """브라우저 초기화"""
        pass
    
    @abstractmethod
    def get_page(self) -> Page:
        """Page 객체 반환"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """리소스 정리"""
        pass


class CalendarScraperPort(ABC):
    """
    캘린더 페이지 스크래핑 포트
    
    책임: IPO 목록 수집
    """
    
    @abstractmethod
    def scrape_calendar(
        self,
        page: Page,
        year: int,
        start_month: int,
        end_month: int,
        today_day: int,
        start_day: int = 1
    ) -> ScrapeReport:
        """캘린더에서 IPO 목록 추출"""
        pass


class DetailScraperPort(ABC):
    """
    상세 정보 페이지 스크래핑 포트
    
    책임: 종목별 상세 정보 수집
    """
    
    @abstractmethod
    def scrape_details(
        self,
        page: Page,
        stocks: List[Tuple[str, str]]
    ) -> List[StockInfo]:
        """종목 상세 정보 추출"""
        pass
