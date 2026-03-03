"""
EnrichmentService 단위 테스트

StockEnricherPort를 mock으로 주입하여 EnrichmentService 비즈니스 로직만 검증.
"""
import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock

from core.services.enrichment_service import EnrichmentService
from core.ports.enrichment_ports import StockEnricherPort
from core.ports.repository_ports import RepositoryPort


@pytest.fixture
def mock_enricher() -> StockEnricherPort:
    """StockEnricherPort mock — 구체 타입(StockPriceEnricher) 불필요"""
    return Mock(spec=StockEnricherPort)


@pytest.fixture
def mock_repository() -> RepositoryPort:
    return Mock(spec=RepositoryPort)


@pytest.fixture
def mock_logger():
    return Mock()


@pytest.fixture
def service(mock_enricher, mock_repository, mock_logger) -> EnrichmentService:
    return EnrichmentService(
        stock_enricher=mock_enricher,
        repository=mock_repository,
        logger=mock_logger,
    )


@pytest.fixture
def sample_yearly_data() -> dict:
    return {
        2024: pd.DataFrame({
            "종목명": ["주식A", "주식B"],
            "상장일": ["2024-01-15", "2024-02-20"],
            "확정공모가": [10000, 20000],
        })
    }


class TestEnrichmentService:

    def test_enricher_port_injected_not_concrete(self, mock_enricher):
        """EnrichmentService 생성자가 포트 인터페이스를 받아야 한다"""
        svc = EnrichmentService(
            stock_enricher=mock_enricher,  # StockEnricherPort mock
            repository=Mock(spec=RepositoryPort),
            logger=Mock(),
        )
        assert svc.stock_enricher is mock_enricher

    def test_enrich_data_calls_repository_save_per_year(
        self, service, mock_enricher, mock_repository, sample_yearly_data
    ):
        """연도별로 repository.save()가 1회씩 호출되어야 한다"""
        mock_enricher.get_market_data.return_value = {
            "시가": None, "고가": None, "저가": None, "종가": None, "수익률(%)": None
        }

        service.enrich_data(sample_yearly_data)

        mock_repository.save.assert_called_once()
        saved_year = mock_repository.save.call_args[0][0]
        assert saved_year == 2024

    def test_enrich_data_skips_empty_year(
        self, service, mock_enricher, mock_repository
    ):
        """빈 DataFrame 연도는 보강 없이 저장도 하지 않아야 한다"""
        yearly_data = {2024: pd.DataFrame()}
        service.enrich_data(yearly_data)
        mock_repository.save.assert_not_called()
        mock_enricher.get_market_data.assert_not_called()

    def test_enrich_data_updates_ohlc_columns(
        self, service, mock_enricher, mock_repository
    ):
        """get_market_data가 데이터를 반환하면 DataFrame에 반영되어야 한다"""
        mock_enricher.get_market_data.return_value = {
            "시가": 10000, "고가": 11000, "저가": 9500, "종가": 10500, "수익률(%)": 5.0
        }

        yearly_data = {
            2024: pd.DataFrame({
                "종목명": ["주식A"],
                "상장일": ["2024-01-15"],
                "확정공모가": [10000],
            })
        }

        service.enrich_data(yearly_data)

        # save 호출 인자에서 종가 검증
        saved_df = mock_repository.save.call_args[0][1]
        assert saved_df.iloc[0]["종가"] == 10500

    def test_enrich_data_handles_get_market_data_error_gracefully(
        self, service, mock_enricher, mock_repository, sample_yearly_data, mock_logger
    ):
        """get_market_data 도중 예외가 발생해도 나머지 종목을 계속 처리해야 한다"""
        mock_enricher.get_market_data.side_effect = Exception("API Error")

        # 예외가 전파되지 않아야 함
        service.enrich_data(sample_yearly_data)

        # 에러 로그는 찍혀야 함
        mock_logger.error.assert_called()
        # 저장은 여전히 호출되어야 함
        mock_repository.save.assert_called_once()

    def test_no_missing_stock_name_skips_silently(
        self, service, mock_enricher, mock_repository
    ):
        """종목명이 없는 행은 get_market_data를 호출하지 않고 건너뛰어야 한다"""
        yearly_data = {
            2024: pd.DataFrame({
                "종목명": [None, "주식A"],
                "상장일": ["2024-01-15", "2024-02-20"],
                "확정공모가": [None, 10000],
            })
        }
        mock_enricher.get_market_data.return_value = {
            "시가": None, "고가": None, "저가": None, "종가": None, "수익률(%)": None
        }

        service.enrich_data(yearly_data)

        # 종목명 없는 행 skip → 1번만 호출 (주식A 1건)
        assert mock_enricher.get_market_data.call_count == 1
