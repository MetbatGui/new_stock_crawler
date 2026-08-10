"""
KRX 거래일 판별 어댑터

KRX 공식 휴장일 API(open.krx.co.kr OPN99000001)로 연도별 휴장일 목록을 조회한다.
임시공휴일 등으로 목록이 도중에 갱신될 수 있으므로, 이 인스턴스는 "영구 캐시"가
아니라 "같은 프로세스 실행 안에서의 중복 조회 방지"용이다 - `crawler daily`는
매 실행마다 새 프로세스이자 새 인스턴스라(dependencies.py) 다음 실행부터는 항상
최신 목록을 다시 받아온다.
(weekly_gainers 프로젝트의 CalendarService 구현을 참고)
"""

import logging
import time
from datetime import date
from typing import Dict, Set

import requests

from core.ports.utility_ports import TradingCalendarPort
from infra.adapters.utils.network_retry import network_retry

logger = logging.getLogger("crawler")

_OTP_URL = "https://open.krx.co.kr/contents/COM/GenerateOTP.jspx"
_DATA_URL = "https://open.krx.co.kr/contents/OPN/99/OPN99000001.jspx"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://open.krx.co.kr/contents/MKD/01/0110/01100305/MKD01100305.jsp",
}


class KrxTradingCalendar(TradingCalendarPort):
    """
    KRX 공식 휴장일 목록으로 거래일 여부를 판별한다. 같은 인스턴스(= 같은 실행)
    안에서는 연도별로 1회만 조회해 재사용하지만, 인스턴스 자체는 실행마다 새로
    만들어지므로 다음 실행에는 항상 최신 목록을 다시 받는다.
    """

    def __init__(self) -> None:
        self._holidays_cache: Dict[str, Set[date]] = {}

    @network_retry
    def _request_otp(self) -> str:
        resp = requests.get(
            _OTP_URL,
            params={
                "bld": "MKD/01/0110/01100305/mkd01100305_01",
                "name": "form",
                "_": int(time.time() * 1000),
            },
            headers=_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.text.strip()

    @network_retry
    def _request_holiday_rows(self, year: str, otp: str) -> list:
        resp = requests.post(
            _DATA_URL,
            data={
                "search_bas_yy": year,
                "gridTp": "KRX",
                "pagePath": "/contents/MKD/01/0110/01100305/MKD01100305.jsp",
                "code": otp,
            },
            headers=_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("block1", [])

    def _fetch_holidays(self, year: str) -> Set[date]:
        if year in self._holidays_cache:
            return self._holidays_cache[year]

        try:
            otp = self._request_otp()
            rows = self._request_holiday_rows(year, otp)
            holidays = set()
            for row in rows:
                date_str = row.get("calnd_dd")
                if date_str:
                    y, m, d = map(int, date_str.split("-"))
                    holidays.add(date(y, m, d))
        except Exception as e:
            # 조회/파싱 실패 시 빈 집합으로 대체 - is_trading_day가 주말 외엔
            # 모두 거래일로 간주하게 되어(보수적 기본값) 크롤링을 건너뛰지 않는다.
            # 이 결과도 캐싱해서, 같은 실행 안의 나머지 날짜들이 매번 재시도로
            # 시간을 낭비하지 않게 한다(다음 실행 때는 새 인스턴스라 다시 시도됨).
            logger.warning(f"[KRX] {year}년 휴장일 조회 실패, 빈 목록으로 대체: {e}")
            holidays = set()

        self._holidays_cache[year] = holidays
        return holidays

    def is_trading_day(self, target_date: date) -> bool:
        if target_date.weekday() >= 5:
            return False
        # 근로자의 날(5월 1일)은 항상 주식 시장 휴장이므로 명시적 안전망으로 보정
        # (weekly_gainers CalendarService와 동일 - API가 이미 포함해 줘도 무해한 중복 체크)
        if target_date.month == 5 and target_date.day == 1:
            return False
        holidays = self._fetch_holidays(str(target_date.year))
        return target_date not in holidays
