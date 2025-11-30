import pytest
from unittest.mock import Mock
from datetime import date
from core.services.stock_price_enricher import StockPriceEnricher
from core.domain.models import StockInfo

class TestStockPriceEnricher:
    @pytest.fixture
    def mock_ticker_mapper(self):
        return Mock()

    @pytest.fixture
    def mock_market_data_provider(self):
        return Mock()

    @pytest.fixture
    def mock_logger(self):
        return Mock()

    @pytest.fixture
    def enricher(self, mock_ticker_mapper, mock_market_data_provider, mock_logger):
        return StockPriceEnricher(
            ticker_mapper=mock_ticker_mapper,
            market_data_provider=mock_market_data_provider,
            logger=mock_logger
        )

    @pytest.fixture
    def sample_stock(self):
        return StockInfo(
            name="TestStock",
            url="http://test.com",
            market_segment="KOSPI",
            sector="Tech",
            revenue=100,
            profit_pre_tax=10,
            net_profit=8,
            capital=50,
            total_shares=1000,
            par_value=500,
            desired_price_range="1000-2000",
            confirmed_price=1500,
            offering_amount=1500000,
            underwriter="TestSec",
            listing_date="2023.01.01",
            competition_rate="100:1",
            emp_shares=100,
            inst_shares=500,
            retail_shares=400,
            tradable_shares_count="200",
            tradable_shares_percent="20%"
        )

    def test_enrich_stock_info_success(self, enricher, mock_ticker_mapper, mock_market_data_provider, sample_stock):
        # Given
        mock_ticker_mapper.get_ticker.return_value = "123456"
        mock_market_data_provider.get_ohlc.return_value = {
            "Open": 2000, "High": 2200, "Low": 1900, "Close": 2100
        }

        # When
        result = enricher.enrich_stock_info(sample_stock)

        # Then
        assert result.open_price == 2000
        assert result.close_price == 2100
        # Growth rate: (2100 - 1500) / 1500 * 100 = 600 / 1500 * 100 = 40.0
        assert result.growth_rate == 40.0
        
        mock_ticker_mapper.get_ticker.assert_called_with("TestStock")
        mock_market_data_provider.get_ohlc.assert_called()

    def test_enrich_stock_info_no_ticker(self, enricher, mock_ticker_mapper, sample_stock):
        # Given
        mock_ticker_mapper.get_ticker.return_value = None

        # When
        result = enricher.enrich_stock_info(sample_stock)

        # Then
        assert result.open_price is None
        assert result.growth_rate is None

    def test_get_market_data_success(self, enricher, mock_ticker_mapper, mock_market_data_provider):
        # Given
        mock_ticker_mapper.get_ticker.return_value = "123456"
        mock_market_data_provider.get_ohlc.return_value = {
            "Open": 2000, "High": 2200, "Low": 1900, "Close": 2100
        }

        # When
        result = enricher.get_market_data("TestStock", "2023.01.01", "1,500")

        # Then
        assert result['시가'] == 2000
        assert result['종가'] == 2100
        assert result['수익률'] == 40.0
