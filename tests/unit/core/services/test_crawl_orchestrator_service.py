"""
CrawlOrchestratorService 단위 테스트

CrawlerService/EnrichmentService/RepositoryPort를 mock으로 격리해
오케스트레이션 로직(호출 순서, changed_years 계산)만 검증.
"""

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from core.services.crawl_orchestrator_service import CrawlOrchestratorService


@pytest.fixture
def mock_crawler():
    return MagicMock()


@pytest.fixture
def mock_enrichment():
    return MagicMock()


@pytest.fixture
def mock_repository():
    return MagicMock()


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def orchestrator(mock_crawler, mock_enrichment, mock_repository, mock_logger):
    return CrawlOrchestratorService(
        crawler=mock_crawler,
        enrichment=mock_enrichment,
        repository=mock_repository,
        logger=mock_logger,
    )


class TestRunFull:
    def test_backfills_entire_saved_history_and_merges_changed_years(
        self, orchestrator, mock_crawler, mock_enrichment, mock_repository
    ):
        """전체 연도(load_all) 대상으로 백필하고, 크롤링/백필 변경 연도를 합쳐 반환해야 한다"""
        mock_crawler.run.return_value = {
            2024: pd.DataFrame({"종목명": ["주식A", "주식B"]})
        }
        mock_repository.load_all.return_value = {
            2023: pd.DataFrame(),
            2024: pd.DataFrame(),
        }
        mock_enrichment.enrich_data.return_value = {2023}

        result = orchestrator.run_full(start_year=2020)

        mock_crawler.run.assert_called_once_with(start_year=2020)
        mock_enrichment.enrich_data.assert_called_once_with(
            mock_repository.load_all.return_value
        )
        assert result.collected_count == 2
        assert result.changed_years == {2023, 2024}

    def test_no_crawl_or_enrich_results_yields_empty_result(
        self, orchestrator, mock_crawler, mock_enrichment, mock_repository
    ):
        mock_crawler.run.return_value = {}
        mock_repository.load_all.return_value = {}
        mock_enrichment.enrich_data.return_value = set()

        result = orchestrator.run_full(start_year=2020)

        assert result.collected_count == 0
        assert result.changed_years == set()


class TestRunDaily:
    def test_backfills_current_year_only_outside_january(
        self, orchestrator, mock_crawler, mock_enrichment, mock_repository
    ):
        mock_crawler.run_scheduled.return_value = {
            2024: pd.DataFrame({"종목명": ["주식A"]})
        }
        mock_enrichment.enrich_data.return_value = set()

        orchestrator.run_daily(target_date=date(2024, 6, 1), today=date(2024, 6, 15))

        mock_repository.load.assert_called_once_with(2024)
        enrich_call_arg = mock_enrichment.enrich_data.call_args[0][0]
        assert set(enrich_call_arg.keys()) == {2024}

    def test_backfills_previous_year_too_in_january(
        self, orchestrator, mock_crawler, mock_enrichment, mock_repository
    ):
        """1월 경계 케이스: 지난해 12월 상장 종목이 아직 미백필일 수 있어 전년도도 같이 훑는다"""
        mock_crawler.run_scheduled.return_value = {}
        mock_enrichment.enrich_data.return_value = set()

        orchestrator.run_daily(target_date=date(2025, 1, 5), today=date(2025, 1, 5))

        assert mock_repository.load.call_count == 2
        called_years = {c.args[0] for c in mock_repository.load.call_args_list}
        assert called_years == {2025, 2024}

    def test_merges_crawl_and_enrich_changed_years(
        self, orchestrator, mock_crawler, mock_enrichment, mock_repository
    ):
        mock_crawler.run_scheduled.return_value = {
            2024: pd.DataFrame({"종목명": ["주식A", "주식B", "주식C"]})
        }
        mock_enrichment.enrich_data.return_value = {2023}

        result = orchestrator.run_daily(
            target_date=date(2024, 6, 1), today=date(2024, 6, 15)
        )

        assert result.collected_count == 3
        assert result.changed_years == {2023, 2024}
