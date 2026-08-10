"""
KRX 거래일 판별 어댑터 (pykrx 기반)
"""

import logging
from datetime import date

from pykrx import stock

from core.ports.utility_ports import TradingCalendarPort

logger = logging.getLogger("crawler")


class KrxTradingCalendar(TradingCalendarPort):
    """
    pykrx로 KRX 실제 개장일을 조회한다 (주말/공휴일/임시휴장 전부 반영,
    별도 공휴일 목록을 직접 유지할 필요 없음).
    """

    def is_trading_day(self, target_date: date) -> bool:
        d_str = target_date.strftime("%Y%m%d")
        try:
            nearest = stock.get_nearest_business_day_in_a_week(date=d_str, prev=True)
        except Exception as e:
            # 조회 실패 시 휴장일 여부를 알 수 없으므로 보수적으로 거래일로 간주
            # (기존 동작 유지 - 크롤링을 건너뛰지 않음)
            logger.warning(f"[KRX] 거래일 조회 실패({target_date}), 거래일로 간주: {e}")
            return True
        return nearest == d_str
