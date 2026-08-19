"""DetailScraperAdapter.scrape_details 유닛 테스트"""
from unittest.mock import MagicMock, patch

from infra.adapters.web.detail_scraper_adapter import DetailScraperAdapter


def test_scrape_details_returns_failed_names_separately():
    """일부 종목 스크래핑이 실패하면, 성공한 종목과 실패한 종목명을 분리해서 반환해야 합니다.

    (회귀 테스트: 예전엔 실패한 종목이 로그만 남기고 반환값에서 조용히
    사라져서, 호출부(run_scheduled)가 부분 실패를 전혀 알 수 없었음.)
    """
    adapter = DetailScraperAdapter(logger=MagicMock())
    mock_stock = MagicMock(confirmed_price=10000, competition_rate="100:1")

    def fake_scrape_single(page, name, href):
        if name == "실패종목":
            return None
        return mock_stock

    with patch.object(adapter, "_scrape_single", side_effect=fake_scrape_single):
        stocks, failed = adapter.scrape_details(
            page=MagicMock(),
            stocks=[("성공종목", "http://a"), ("실패종목", "http://b")],
        )

    assert stocks == [mock_stock]
    assert failed == ["실패종목"]


def test_scrape_details_returns_empty_failed_list_when_all_succeed():
    adapter = DetailScraperAdapter(logger=MagicMock())
    mock_stock = MagicMock(confirmed_price=10000, competition_rate="100:1")

    with patch.object(adapter, "_scrape_single", return_value=mock_stock):
        stocks, failed = adapter.scrape_details(
            page=MagicMock(), stocks=[("성공종목", "http://a")]
        )

    assert stocks == [mock_stock]
    assert failed == []
