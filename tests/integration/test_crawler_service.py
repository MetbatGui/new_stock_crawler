"""
CrawlerService 통합 테스트
새로운 아키텍처가 제대로 동작하는지 검증
"""
import pytest
from unittest.mock import Mock
from datetime import date

from core.services.crawler_service import CrawlerService
from core.domain.models import ScrapeReport, StockInfo


class TestCrawlerService:
    """CrawlerService 통합 테스트"""

    @pytest.fixture
    def mock_dependencies(self):
        """모든 의존성 모킹"""
        return {
            'page_provider': Mock(),
            'calendar_scraper': Mock(),
            'detail_scraper': Mock(),
            'data_mapper': Mock(),
            'repository': Mock(),       # data_exporter → repository
            'date_calculator': Mock(),
            'stock_enricher': Mock(),
            'logger': Mock(),
        }

    @pytest.fixture
    def crawler_service(self, mock_dependencies):
        """CrawlerService 인스턴스 생성"""
        return CrawlerService(**mock_dependencies)

    def test_service_initialization(self, crawler_service, mock_dependencies):
        """서비스가 모든 의존성을 제대로 주입받는지 확인"""
        assert crawler_service.page_provider == mock_dependencies['page_provider']
        assert crawler_service.calendar_scraper == mock_dependencies['calendar_scraper']
        assert crawler_service.detail_scraper == mock_dependencies['detail_scraper']
        assert crawler_service.data_mapper == mock_dependencies['data_mapper']
        assert crawler_service.repository == mock_dependencies['repository']
        assert crawler_service.stock_enricher == mock_dependencies['stock_enricher']
        assert crawler_service.logger == mock_dependencies['logger']

    def test_run_with_single_year(self, crawler_service, mock_dependencies):
        """단일 연도 크롤링이 제대로 동작하는지 확인"""
        # Given: 날짜 계산기가 2024년 범위를 반환
        mock_date_range = Mock(start_month=1, end_month=12, day_limit=31)
        mock_dependencies['date_calculator'].calculate.return_value = {2024: mock_date_range}

        mock_page = Mock()
        mock_dependencies['page_provider'].get_page.return_value = mock_page

        stock_tuple = ("테스트종목", "http://example.com")
        mock_report = ScrapeReport(final_stock_count=1, spack_filtered_count=0, results=[stock_tuple])
        mock_dependencies['calendar_scraper'].scrape_calendar.return_value = mock_report

        mock_stock = _make_stock("테스트종목", "2024-12-01")
        mock_dependencies['detail_scraper'].scrape_details.return_value = [mock_stock]
        mock_dependencies['stock_enricher'].enrich_stock_info.return_value = mock_stock

        import pandas as pd
        mock_df = pd.DataFrame([{'name': '테스트종목'}])
        mock_dependencies['data_mapper'].to_dataframe.return_value = mock_df

        # When
        crawler_service.run(start_year=2024)

        # Then
        mock_dependencies['calendar_scraper'].scrape_calendar.assert_called_once()
        mock_dependencies['detail_scraper'].scrape_details.assert_called_once()
        mock_dependencies['repository'].save.assert_called_once_with(2024, mock_df)

    def test_run_with_no_results(self, crawler_service, mock_dependencies):
        """결과가 없을 때 저장하지 않는지 확인"""
        mock_date_range = Mock(start_month=1, end_month=12, day_limit=31)
        mock_dependencies['date_calculator'].calculate.return_value = {2024: mock_date_range}

        mock_page = Mock()
        mock_dependencies['page_provider'].get_page.return_value = mock_page

        empty_report = ScrapeReport(final_stock_count=0, spack_filtered_count=5, results=[])
        mock_dependencies['calendar_scraper'].scrape_calendar.return_value = empty_report

        crawler_service.run(start_year=2024)

        mock_dependencies['repository'].save.assert_not_called()

    def test_run_with_multiple_years(self, crawler_service, mock_dependencies):
        """여러 연도 크롤링이 제대로 동작하는지 확인"""
        mock_dependencies['date_calculator'].calculate.return_value = {
            2023: Mock(start_month=1, end_month=12, day_limit=31),
            2024: Mock(start_month=1, end_month=11, day_limit=26),
        }

        mock_page = Mock()
        mock_dependencies['page_provider'].get_page.return_value = mock_page

        mock_dependencies['calendar_scraper'].scrape_calendar.return_value = ScrapeReport(
            final_stock_count=1, spack_filtered_count=0, results=[("종목", "http://test.com")]
        )
        mock_dependencies['detail_scraper'].scrape_details.return_value = [Mock(spec=StockInfo)]
        mock_dependencies['stock_enricher'].enrich_stock_info.side_effect = lambda x: x

        import pandas as pd
        mock_dependencies['data_mapper'].to_dataframe.return_value = pd.DataFrame([{'name': 'test'}])

        crawler_service.run(start_year=2023)

        assert mock_dependencies['calendar_scraper'].scrape_calendar.call_count == 2
        assert mock_dependencies['repository'].save.call_count == 2

    def test_run_full_coverage(self, crawler_service, mock_dependencies):
        """run() 메서드 기본 흐름 커버리지"""
        mock_dependencies['date_calculator'].calculate.return_value = {
            2024: Mock(start_month=1, end_month=12, day_limit=31)
        }
        mock_page = Mock()
        mock_dependencies['page_provider'].get_page.return_value = mock_page

        stock_tuple = ("종목", "url")
        mock_dependencies['calendar_scraper'].scrape_calendar.return_value = ScrapeReport(
            final_stock_count=1, spack_filtered_count=0, results=[stock_tuple]
        )

        mock_stock = _make_stock("종목", "2024-01-01")
        mock_dependencies['detail_scraper'].scrape_details.return_value = [mock_stock]
        mock_dependencies['stock_enricher'].enrich_stock_info.return_value = mock_stock

        import pandas as pd
        mock_df = pd.DataFrame([{'name': '종목'}])
        mock_dependencies['data_mapper'].to_dataframe.return_value = mock_df

        result = crawler_service.run(2024)

        assert 2024 in result
        mock_dependencies['repository'].save.assert_called_once_with(2024, mock_df)

    def test_run_daily_no_results(self, crawler_service, mock_dependencies):
        """run_scheduled() 결과 없음 케이스"""
        mock_page = Mock()
        mock_dependencies['page_provider'].get_page.return_value = mock_page

        empty_report = ScrapeReport(final_stock_count=0, spack_filtered_count=3, results=[])
        mock_dependencies['calendar_scraper'].scrape_calendar.return_value = empty_report

        result = crawler_service.run_scheduled(start_date=date(2024, 11, 26), days_ahead=0)
        assert result == {}
        mock_dependencies['repository'].save.assert_not_called()


def _make_stock(name: str, listing_date: str) -> StockInfo:
    return StockInfo(
        name=name, url="http://example.com", market_segment="KOSPI", sector="IT",
        revenue=1000, profit_pre_tax=100, net_profit=80, capital=500,
        total_shares=1000000, par_value=500, desired_price_range="10000-12000",
        confirmed_price=11000, offering_amount=11000000000, underwriter="테스트증권",
        listing_date=listing_date, competition_rate="100:1",
        emp_shares=10000, inst_shares=50000, retail_shares=40000,
        tradable_shares_count="900000", tradable_shares_percent="90%",
    )
