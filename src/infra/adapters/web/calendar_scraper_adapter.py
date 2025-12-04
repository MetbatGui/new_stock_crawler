"""
캘린더 스크래핑 어댑터 구현
"""
from typing import List, Tuple, Optional
from playwright.sync_api import Page, Locator

from core.ports.web_scraping_ports import CalendarScraperPort
from core.domain.models import ScrapeReport
from infra.adapters.parsing.text import parsers as text_parsers
from config import config


class CalendarScraperAdapter(CalendarScraperPort):
    """
    38.co.kr 캘린더 스크래핑 어댑터
    
    원칙 준수:
    - 다른 어댑터를 모름 ✅
    - Page 객체만 사용
    """
    
    BASE_URL = config.BASE_URL
    SCHEDULE_URL = f"{BASE_URL}/html/ipo/ipo_schedule.php"
    
    def scrape_calendar(
        self,
        page: Page,
        year: int,
        start_month: int,
        end_month: int,
        today_day: int,
        start_day: int = 1
    ) -> ScrapeReport:
        """캘린더 스크래핑 (기존 CalendarParser 로직)"""
        total_spacs = 0
        total_results = []
        
        for month in range(start_month, end_month + 1):
            is_current = (month == end_month)
            
            # 월별 페이지 이동
            self._goto_month(page, year, month)
            
            # 파싱
            spacs, results = self._parse_table(page, month, today_day, start_day, is_current)
            total_spacs += spacs
            total_results.extend(results)
        
        return ScrapeReport(
            final_stock_count=len(total_results),
            spack_filtered_count=total_spacs,
            results=total_results
        )
    
    def _goto_month(self, page: Page, year: int, month: int) -> None:
        """월별 페이지 이동"""
        month_str = f"{month:02d}"
        url = f"{self.SCHEDULE_URL}?mode=goMonth&o=s&month={month_str}&year={year}"
        page.goto(url)
        page.wait_for_load_state("networkidle")
    
    def _parse_table(
        self, page: Page, month: int, today_day: int, start_day: int, is_current: bool
    ) -> Tuple[int, List[Tuple[str, str]]]:
        """테이블 파싱"""
        calendar_table = page.locator('table[summary="증시캘린더"]')
        
        if not calendar_table.is_visible():
            return 0, []
        
        cells = calendar_table.locator("tbody > tr > td")
        spacks_total = 0
        results_total = []
        
        for i in range(cells.count()):
            spack_count, cell_results = self._parse_cell(
                cells.nth(i), month, today_day, start_day, is_current
            )
            spacks_total += spack_count
            results_total.extend(cell_results)
        
        return spacks_total, results_total

    def _parse_cell(
        self, cell: Locator, current_month: int, today_day: int, start_day: int, is_current_month: bool
    ) -> Tuple[int, List[Tuple[str, str]]]:
        """단일 셀 파싱"""
        day = self._extract_day(cell)
        if day is None:
            return 0, []
        
        if self._should_skip(day, today_day, start_day, is_current_month):
            return 0, []
        
        try:
            return self._extract_links(cell)
        except Exception:
            return 0, []

    def _extract_day(self, cell: Locator) -> Optional[int]:
        """날짜 추출"""
        day_locator = cell.locator("table tr:first-child td:first-child b").first
        if not day_locator.is_visible():
            return None
        
        try:
            return int(day_locator.inner_text().strip())
        except ValueError:
            return None

    def _should_skip(self, day: int, today_day: int, start_day: int, is_current_month: bool) -> bool:
        """스킵 여부 결정"""
        # 현재 월인 경우: start_day보다 작거나, today_day보다 크면 스킵
        # today_day 포함 (>)
        if is_current_month:
            if day < start_day:
                return True
            if day > today_day:
                return True
        return False

    def _extract_links(self, cell: Locator) -> Tuple[int, List[Tuple[str, str]]]:
        """링크 추출"""
        spacks_filtered = 0
        results = []
        
        links = cell.locator("table tr:nth-child(2) td a")
        
        for i in range(links.count()):
            link = links.nth(i)
            name_raw = link.inner_text().strip().replace("\n", " ")
            
            if "(상장)" not in name_raw:
                continue
            
            if text_parsers.is_spac_stock(name_raw):
                spacks_filtered += 1
                continue
            
            name_cleaned = text_parsers.clean_stock_name(name_raw)
            
            if href := link.get_attribute("href"):
                href_full = f"{self.BASE_URL}{href}"
                results.append((name_cleaned, href_full))
        
        return spacks_filtered, results
