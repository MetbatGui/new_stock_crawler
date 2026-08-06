"""
CLI 의존성 주입 모듈
"""

from typing import Any, Dict

from core.services.crawler_service import CrawlerService
from core.services.stock_price_enricher import StockPriceEnricher
from core.services.enrichment_service import EnrichmentService
from infra.adapters.utils.console_logger import ConsoleLogger
from infra.adapters.utils.date_calculator import DateCalculator
from infra.adapters.web.playwright_page_provider import PlaywrightPageProvider
from infra.adapters.web.calendar_scraper_adapter import CalendarScraperAdapter
from infra.adapters.web.detail_scraper_adapter import DetailScraperAdapter
from infra.adapters.data.dataframe_mapper import DataFrameMapper
from infra.adapters.data.sqlite_repository import SqliteRepository
from infra.adapters.data.krx_native_adapter import KrxNativeAdapter


def build_dependencies(headless: bool = True) -> Dict[str, Any]:
    """
    의존성 주입 컨테이너

    Args:
        headless: 브라우저 헤드리스 모드 여부

    Returns:
        Dict: 구성된 서비스 및 어댑터 모음
    """
    # 1. 공통 유틸리티
    logger = ConsoleLogger()
    date_calculator = DateCalculator()

    # 2. 데이터 어댑터
    krx_adapter = KrxNativeAdapter()
    data_mapper = DataFrameMapper()

    # 3. 저장소 (SQLite)
    repository = SqliteRepository()

    # 4. OHLC 보강
    stock_enricher = StockPriceEnricher(
        ticker_mapper=krx_adapter,
        market_data_provider=krx_adapter,
        logger=logger,
    )
    enrichment_service = EnrichmentService(
        stock_enricher=stock_enricher,
        repository=repository,
        logger=logger,
    )

    # 5. 웹 스크래핑
    page_provider = PlaywrightPageProvider(headless=headless)
    calendar_scraper = CalendarScraperAdapter()
    detail_scraper = DetailScraperAdapter(logger=logger)

    # 6. 크롤러 서비스 (수집 전담 — OHLC 보강은 enrichment_service가 별도 백필 단계에서 수행)
    crawler_service = CrawlerService(
        page_provider=page_provider,
        calendar_scraper=calendar_scraper,
        detail_scraper=detail_scraper,
        data_mapper=data_mapper,
        repository=repository,
        date_calculator=date_calculator,
        logger=logger,
    )

    return {
        "crawler": crawler_service,
        "enrichment": enrichment_service,
        "page_provider": page_provider,
        "logger": logger,
        "repository": repository,
    }
