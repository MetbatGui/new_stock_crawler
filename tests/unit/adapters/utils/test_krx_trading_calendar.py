"""
KrxTradingCalendar 단위 테스트 (KRX 네트워크 호출은 모킹)
"""

from datetime import date
from unittest.mock import patch

from infra.adapters.utils.krx_trading_calendar import KrxTradingCalendar


class TestKrxTradingCalendar:
    def test_weekend_is_not_trading_day_without_network_call(self):
        calendar = KrxTradingCalendar()
        with patch.object(calendar, "_fetch_holidays") as mock_fetch:
            assert calendar.is_trading_day(date(2024, 3, 9)) is False  # 토요일
        mock_fetch.assert_not_called()

    def test_labor_day_is_not_trading_day_even_if_api_misses_it(self):
        calendar = KrxTradingCalendar()
        with patch.object(calendar, "_fetch_holidays", return_value=set()) as mock_fetch:
            assert calendar.is_trading_day(date(2024, 5, 1)) is False
        mock_fetch.assert_not_called()

    def test_holiday_from_api_is_not_trading_day(self):
        calendar = KrxTradingCalendar()
        with patch.object(
            calendar, "_fetch_holidays", return_value={date(2024, 1, 1)}
        ):
            assert calendar.is_trading_day(date(2024, 1, 1)) is False

    def test_weekday_not_in_holiday_set_is_trading_day(self):
        calendar = KrxTradingCalendar()
        with patch.object(calendar, "_fetch_holidays", return_value=set()):
            assert calendar.is_trading_day(date(2024, 3, 11)) is True  # 월요일

    def test_fetch_holidays_caches_per_year(self):
        calendar = KrxTradingCalendar()
        with patch.object(
            calendar, "_request_otp", return_value="otp"
        ) as mock_otp, patch.object(
            calendar, "_request_holiday_rows", return_value=[{"calnd_dd": "2024-01-01"}]
        ) as mock_rows:
            first = calendar._fetch_holidays("2024")
            second = calendar._fetch_holidays("2024")

        assert first == {date(2024, 1, 1)}
        assert second == {date(2024, 1, 1)}
        mock_otp.assert_called_once()
        mock_rows.assert_called_once()

    def test_fetch_holidays_returns_empty_set_on_failure(self):
        calendar = KrxTradingCalendar()
        with patch.object(calendar, "_request_otp", side_effect=Exception("network error")):
            result = calendar._fetch_holidays("2024")
        assert result == set()

    def test_fetch_holidays_caches_failure_to_avoid_repeated_retries(self):
        """조회 실패도 캐싱되어야 같은 실행 안의 나머지 날짜들이 매번 재시도로
        시간을 낭비하지 않는다 (예: KRX 장애 중 11일치 백필)"""
        calendar = KrxTradingCalendar()
        with patch.object(
            calendar, "_request_otp", side_effect=Exception("network error")
        ) as mock_otp:
            first = calendar._fetch_holidays("2024")
            second = calendar._fetch_holidays("2024")

        assert first == set()
        assert second == set()
        mock_otp.assert_called_once()

    def test_malformed_holiday_date_falls_back_to_empty_set(self):
        """calnd_dd 포맷이 예상과 다르면(API 변경 등) 예외 없이 빈 집합으로 대체되어야 한다"""
        calendar = KrxTradingCalendar()
        with patch.object(calendar, "_request_otp", return_value="otp"), patch.object(
            calendar, "_request_holiday_rows", return_value=[{"calnd_dd": "20240101"}]
        ):
            result = calendar._fetch_holidays("2024")
        assert result == set()
