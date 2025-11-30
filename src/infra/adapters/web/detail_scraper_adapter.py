"""
상세 정보 스크래핑 어댑터 구현
"""
import time
import traceback
import pandas as pd

from typing import List, Tuple, Optional
from playwright.sync_api import Page, Locator

from core.ports.web_scraping_ports import DetailScraperPort
from core.domain.models import StockInfo
from infra.adapters.parsing.text import parsers as text_parsers
from infra.adapters.parsing.html.table_grid_builder import TableGridBuilder
from infra.adapters.parsing.html.strategies import (
    TableFinderStrategy,
    TitleSiblingTableFinder,
    TitleFollowingTableFinder,
    HeaderContentTableFinder,
    RowContentTableFinder
)


class DetailScraperAdapter(DetailScraperPort):
    """
    종목 상세 정보 스크래핑 어댑터
    
    원칙 준수:
    - 다른 어댑터를 모름 ✅
    - Page 객체만 사용
    """
    
    def __init__(self, logger=None):
        self.grid_builder = TableGridBuilder()
        self.logger = logger
        self.table_strategies: List[TableFinderStrategy] = [
            TitleSiblingTableFinder(),
            TitleFollowingTableFinder(),
            HeaderContentTableFinder(),
            RowContentTableFinder()
        ]
    
    def scrape_details(
        self,
        page: Page,
        stocks: List[Tuple[str, str]]
    ) -> List[StockInfo]:
        """여러 종목 스크래핑"""
        results = []
        
        for name, href in stocks:
            if stock := self._scrape_single(page, name, href):
                results.append(stock)
                if self.logger:
                    self.logger.info(f"   ✅ 수집 완료: {stock.name} (공모가: {stock.confirmed_price:,}원, 경쟁률: {stock.competition_rate})")
            time.sleep(0.3)
        
        return results
    
    def _scrape_single(
        self, page: Page, name: str, href: str
    ) -> Optional[StockInfo]:
        """단일 종목 스크래핑"""
        try:
            page.goto(href)
            page.wait_for_load_state("networkidle")
            
            company_info = self._parse_company_info(page)
            offering_info = self._parse_offering_info(page)
            schedule_info = self._parse_schedule_info(page)
            tradable_info = self._parse_shareholder_table(page)
            
            return self._create_stock_info(
                name, href, company_info, offering_info, schedule_info, tradable_info
            )
        except Exception:
            # 로깅은 서비스 계층에서 처리하거나, 필요시 에러 로거 주입
            return None

    def _get_value(self, table: Locator, key_text: str) -> str:
        """키-값 테이블에서 값 추출"""
        try:
            key_cell = table.locator(
                f'//*[self::td or self::th][contains(normalize-space(.), "{key_text}")]'
            )
            value_cell = key_cell.locator("xpath=./following-sibling::td[1]")
            
            if value_cell.is_visible(timeout=1000):
                return value_cell.inner_text().replace("\u00a0", " ").strip()
            
            key_cell = key_cell.first
            value_cell = key_cell.locator("xpath=./following-sibling::td[1]")
            
            if value_cell.is_visible(timeout=1000):
                return value_cell.inner_text().replace("\u00a0", " ").strip()
            
            return "N/A"
        except Exception:
            return "N/A"

    def _parse_company_info(self, page: Page) -> dict:
        """기업개요 파싱"""
        table = page.locator('table[summary="기업개요"]')
        return {
            "market": self._get_value(table, "시장구분"),
            "sector": self._get_value(table, "업종"),
            "revenue": self._get_value(table, "매출액"),
            "profit_pre_tax": self._get_value(table, "법인세비용차감전"),
            "net_profit": self._get_value(table, "순이익"),
            "capital": self._get_value(table, "자본금"),
        }

    def _parse_offering_info(self, page: Page) -> dict:
        """공모정보 파싱"""
        table = page.locator('table[summary="공모정보"]')
        return {
            "total_shares": self._get_value(table, "총공모주식수"),
            "par_value": self._get_value(table, "액면가"),
            "desired_price": self._get_value(table, "희망공모가액"),
            "confirmed_price": self._get_value(table, "확정공모가"),
            "offering_amount": self._get_value(table, "공모금액"),
            "underwriter": self._get_value(table, "주간사"),
        }

    def _parse_schedule_info(self, page: Page) -> dict:
        """공모청약일정 파싱"""
        table = page.locator('table[summary="공모청약일정"]')
        
        listing_date = self._get_value(table, "신규상장일")
        if listing_date == "N/A":
            listing_date = self._get_value(table, "(상장일")
        
        competition_rate_raw = self._get_value(table, "기관경쟁률")
        
        return {
            "listing_date": listing_date,
            "competition_rate": text_parsers.format_competition_rate(competition_rate_raw),
            "emp_shares": text_parsers.extract_share_count(
                self._get_value(table, "우리사주조합")
            ),
            "inst_shares": text_parsers.extract_share_count(
                self._get_value(table, "기관투자자등")
            ),
            "retail_shares": text_parsers.extract_share_count(
                self._get_value(table, "일반청약자")
            ),
        }

    def _create_stock_info(
        self, name: str, href: str, company_info: dict, offering_info: dict, 
        schedule_info: dict, tradable_info: Tuple[str, str]
    ) -> StockInfo:
        """StockInfo 객체 생성"""
        return StockInfo(
            name=name,
            url=href,
            market_segment=company_info["market"],
            sector=company_info["sector"],
            revenue=text_parsers.parse_to_int(company_info["revenue"], f"{name} - revenue"),
            profit_pre_tax=text_parsers.parse_to_int(company_info["profit_pre_tax"], f"{name} - profit_pre_tax"),
            net_profit=text_parsers.parse_to_int(company_info["net_profit"], f"{name} - net_profit"),
            capital=text_parsers.parse_to_int(company_info["capital"], f"{name} - capital"),
            total_shares=text_parsers.parse_to_int(offering_info["total_shares"], f"{name} - total_shares"),
            par_value=text_parsers.parse_to_int(offering_info["par_value"], f"{name} - par_value"),
            desired_price_range=offering_info["desired_price"],
            confirmed_price=text_parsers.parse_to_int(offering_info["confirmed_price"], f"{name} - confirmed_price"),
            offering_amount=text_parsers.parse_to_int(offering_info["offering_amount"], f"{name} - offering_amount"),
            underwriter=offering_info["underwriter"],
            listing_date=schedule_info["listing_date"],
            competition_rate=schedule_info["competition_rate"],
            emp_shares=text_parsers.parse_to_int(schedule_info["emp_shares"], f"{name} - emp_shares"),
            inst_shares=text_parsers.parse_to_int(schedule_info["inst_shares"], f"{name} - inst_shares"),
            retail_shares=text_parsers.parse_to_int(schedule_info["retail_shares"], f"{name} - retail_shares"),
            tradable_shares_count=tradable_info[0],
            tradable_shares_percent=tradable_info[1],
        )


    def _parse_shareholder_table(self, page: Page) -> Tuple[str, str]:
        """주주현황 파싱"""
        try:
            table = self._find_shareholder_table(page)
            if table is None:
                return "N/A", "N/A"
            
            grid = self.grid_builder.build_grid(table)
            if not grid:
                return "N/A", "N/A"
            
            tradable_cols = self._find_tradable_columns(grid)
            if not tradable_cols:
                return "N/A", "N/A"
            
            return self._extract_tradable_values(grid, tradable_cols)
        except Exception:
            return "N/A", "N/A"

    def _find_shareholder_table(self, page: Page) -> Optional[Locator]:
        """주주현황 테이블 찾기"""
        for strategy in self.table_strategies:
            if table := strategy.find_table(page):
                return table
        return None

    def _find_tradable_columns(self, grid: List[List[str]]) -> List[int]:
        """유통가능물량 열 찾기"""
        header_col = self._find_tradable_column_in_header(grid)
        
        if header_col is None:
            return []
        
        for row_idx in range(min(5, len(grid))):
            if "유통가능" in grid[row_idx][header_col] and "물량" in grid[row_idx][header_col]:
                return self._find_sub_columns(grid, row_idx, header_col)
        
        return [header_col, header_col + 1]

    def _find_tradable_column_in_header(self, grid: List[List[str]]) -> Optional[int]:
        """헤더에서 유통가능물량 열 인덱스 찾기"""
        for row_idx in range(min(5, len(grid))):
            for col_idx, cell_text in enumerate(grid[row_idx]):
                if "유통가능" in cell_text and "물량" in cell_text:
                    return col_idx
        return None

    def _calculate_colspan_range(self, grid: List[List[str]], row_idx: int, col_idx: int) -> int:
        """colspan 범위 계산"""
        colspan_end = col_idx
        cell_value = grid[row_idx][col_idx]
        
        while colspan_end < len(grid[row_idx]) - 1 and grid[row_idx][colspan_end + 1] == cell_value:
            colspan_end += 1
        return colspan_end

    def _find_sub_columns(self, grid: List[List[str]], row_idx: int, col_idx: int) -> List[int]:
        """하위 컬럼(주식수, 비율) 찾기"""
        colspan_end = self._calculate_colspan_range(grid, row_idx, col_idx)
        
        # 바로 아래 행에서 하위 헤더 찾기
        next_row = row_idx + 1
        if next_row >= len(grid):
            return [col_idx, col_idx + 1]

        share_col = -1
        percent_col = -1

        for c in range(col_idx, colspan_end + 1):
            text = grid[next_row][c]
            if "주식수" in text:
                share_col = c
            elif "비율" in text or "지분율" in text:
                percent_col = c
        
        if share_col != -1 and percent_col != -1:
            return [share_col, percent_col]
            
        return [col_idx, col_idx + 1]

    def _extract_tradable_values(
        self, grid: List[List[str]], cols: List[int]
    ) -> Tuple[str, str]:
        """값 추출"""
        share_col, percent_col = cols[0], cols[1]
        
        # 마지막 행(계) 또는 그 위 행에서 값 찾기
        for row_idx in range(len(grid) - 1, -1, -1):
            row = grid[row_idx]
            if len(row) <= max(share_col, percent_col):
                continue
                
            share_val = row[share_col].strip()
            percent_val = row[percent_col].strip()
            
            # 유효한 숫자가 있는 행 찾기
            if share_val and share_val != "-" and any(c.isdigit() for c in share_val):
                return text_parsers.clean_tradable_values(share_val, percent_val)
                
        return "N/A", "N/A"
