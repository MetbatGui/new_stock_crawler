"""
CLI 의존성 주입 모듈
"""
from typing import Any, Dict

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
# from infra.adapters.data.fdr_adapter import FDRAdapter
from infra.adapters.data.pykrx_adapter import PyKrxAdapter
from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter

def build_dependencies(headless: bool = True) -> Dict[str, Any]:
    """
    의존성 주입 컨테이너 역할
    
    Args:
        headless: 브라우저 헤드리스 모드 여부
        
    Returns:
        Dict: 구성된 서비스 및 어댑터 모음
    """
    # 1. 어댑터 생성
    logger = ConsoleLogger()
    date_calculator = DateCalculator()
    
    # 2. Data
    # fdr_adapter = FDRAdapter()
    pykrx_adapter = PyKrxAdapter()
    data_mapper = DataFrameMapper()
    data_exporter = ExcelExporter()
    
    # 3. Storage
    storage = GoogleDriveAdapter()

    # 3.5 Enrichment
    stock_enricher = StockPriceEnricher(
        ticker_mapper=pykrx_adapter,
        market_data_provider=pykrx_adapter,
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
        'exporter': data_exporter,
        'storage': storage,
    }
