"""
KrxTradingCalendar 단위 테스트 (pykrx 네트워크 호출은 모킹)
"""

from datetime import date
from unittest.mock import patch

from infra.adapters.utils.krx_trading_calendar import KrxTradingCalendar


class TestKrxTradingCalendar:
    def test_returns_true_when_nearest_business_day_matches_target(self):
        calendar = KrxTradingCalendar()
        with patch(
            "infra.adapters.utils.krx_trading_calendar.stock.get_nearest_business_day_in_a_week",
            return_value="20240311",
        ):
            assert calendar.is_trading_day(date(2024, 3, 11)) is True

    def test_returns_false_when_nearest_business_day_differs(self):
        """토요일(2024-03-09) -> 직전 영업일(2024-03-08)과 날짜가 다르므로 휴장일 판정"""
        calendar = KrxTradingCalendar()
        with patch(
            "infra.adapters.utils.krx_trading_calendar.stock.get_nearest_business_day_in_a_week",
            return_value="20240308",
        ):
            assert calendar.is_trading_day(date(2024, 3, 9)) is False

    def test_returns_true_on_lookup_failure(self):
        """조회 실패 시 보수적으로 거래일로 간주해 크롤링을 건너뛰지 않는다"""
        calendar = KrxTradingCalendar()
        with patch(
            "infra.adapters.utils.krx_trading_calendar.stock.get_nearest_business_day_in_a_week",
            side_effect=Exception("network error"),
        ):
            assert calendar.is_trading_day(date(2024, 3, 9)) is True
