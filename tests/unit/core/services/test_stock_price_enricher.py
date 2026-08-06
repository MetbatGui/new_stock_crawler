import pytest
from unittest.mock import Mock
from core.services.stock_price_enricher import StockPriceEnricher


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
            logger=mock_logger,
        )

    def test_get_market_data_success(
        self, enricher, mock_ticker_mapper, mock_market_data_provider
    ):
        # Given
        mock_ticker_mapper.get_ticker.return_value = "123456"
        mock_market_data_provider.get_ohlc.return_value = {
            "Open": 2000,
            "High": 2200,
            "Low": 1900,
            "Close": 2100,
        }

        # When
        result = enricher.get_market_data("TestStock", "2023.01.01", "1,500")

        # Then
        assert result["시가"] == 2000
        assert result["종가"] == 2100
        assert result["수익률(%)"] == 40.0
