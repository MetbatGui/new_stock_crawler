"""
CLI 의존성 주입 모듈
"""
from config import config
from core.services.crawler_service import CrawlerService
from core.services.stock_price_enricher import StockPriceEnricher
from infra.adapters.utils.console_logger import ConsoleLogger
from infra.adapters.utils.date_calculator import DateCalculator
from infra.adapters.web.playwright_page_provider import PlaywrightPageProvider
from infra.adapters.web.calendar_scraper_adapter import CalendarScraperAdapter
from infra.adapters.web.detail_scraper_adapter import DetailScraperAdapter
from infra.adapters.data.dataframe_mapper import DataFrameMapper
from infra.adapters.data.excel_exporter import ExcelExporter
from infra.adapters.data.fdr_adapter import FDRAdapter
from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter

def build_dependencies(headless: bool = config.HEADLESS):
    """
    의존성 조립 (DI Container 역할)
    
    Args:
        headless: Playwright 헤드리스 모드
        
    Returns:
        dict: 조립된 의존성 객체들
    """
    # 1. 유틸리티
    logger = ConsoleLogger()
    date_calculator = DateCalculator()
    
    # 2. Data
    fdr_adapter = FDRAdapter()
    data_mapper = DataFrameMapper()
    data_exporter = ExcelExporter()  # config 사용
    
    # 3. Storage
    storage_adapter = GoogleDriveAdapter()

    # 3.5 Enrichment
    stock_enricher = StockPriceEnricher(
        ticker_mapper=fdr_adapter,
        market_data_provider=fdr_adapter,
        logger=logger
    )
    
    # 4. Web Scraping
    page_provider = PlaywrightPageProvider(headless=headless)
    calendar_scraper = CalendarScraperAdapter()
    detail_scraper = DetailScraperAdapter(
        logger=logger
    )
    
    # 5. Service
    crawler_service = CrawlerService(
        page_provider=page_provider,
        calendar_scraper=calendar_scraper,
        detail_scraper=detail_scraper,
        data_mapper=data_mapper,
        data_exporter=data_exporter,
        date_calculator=date_calculator,
        stock_enricher=stock_enricher,
        logger=logger
    )
    
    return {
        'crawler': crawler_service,
        'page_provider': page_provider,
        'logger': logger,
        'fdr': fdr_adapter,
        'exporter': data_exporter,
        'storage': storage_adapter,
    }
