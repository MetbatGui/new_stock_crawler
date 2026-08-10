import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from infra.adapters.data.krx_native_adapter import KrxNativeAdapter, _resolve_name


@pytest.mark.live
class TestKrxNativeAdapter(unittest.TestCase):
    """실제 KRX 서버에 접속하는 라이브 테스트 — 기본 pytest 실행에서 제외됨.
    `uv run pytest -m live`로만 별도 실행 (KRX_USERNAME/PASSWORD .env 설정 필요)."""

    def setUp(self):
        self.adapter = KrxNativeAdapter()

    def test_get_ticker(self):
        # 삼성전자 티커 확인
        ticker = self.adapter.get_ticker("삼성전자")
        print(f"\n삼성전자 티커: {ticker}")
        self.assertEqual(ticker, "005930")

    def test_get_ohlc(self):
        # 2024년 3월 11일 (평일) 삼성전자 시세 확인
        target_date = date(2024, 3, 11)
        ohlc = self.adapter.get_ohlc(ticker="005930", target_date=target_date)
        print(f"\n삼성전자 OHLC (2024-03-11): {ohlc}")
        self.assertIsNotNone(ohlc)
        self.assertIn("Close", ohlc)
        self.assertGreater(ohlc["Close"], 0)


class TestResolveName(unittest.TestCase):
    """이름 매칭 로직(_resolve_name) 순수 유닛테스트 — 네트워크 의존 없음"""

    def test_exact_match(self):
        table = {"삼성전자": "005930"}
        self.assertEqual(_resolve_name(table, "삼성전자"), "005930")

    def test_matches_after_stripping_juju_suffix(self):
        table = {"스트라드비젼": "475040"}
        self.assertEqual(_resolve_name(table, "스트라드비젼(주)"), "475040")

    def test_exact_match_takes_priority_over_stripped(self):
        # "삼성전자(주)"라는 이름이 테이블에 그대로 존재하면 그걸 우선 반환
        table = {"삼성전자(주)": "AAA", "삼성전자": "BBB"}
        self.assertEqual(_resolve_name(table, "삼성전자(주)"), "AAA")

    def test_not_found_returns_none(self):
        table = {"삼성전자": "005930"}
        self.assertIsNone(_resolve_name(table, "존재하지않는종목"))

    def test_empty_table_returns_none(self):
        self.assertIsNone(_resolve_name({}, "삼성전자"))

    def test_whitespace_only_difference_still_matches(self):
        table = {"삼성전자": "005930"}
        self.assertEqual(_resolve_name(table, "삼성전자 "), "005930")


class TestFetchAllMarketsRetry(unittest.TestCase):
    """네트워크 계층 일시 오류에 대한 tenacity 재시도 동작 검증 (네트워크 의존 없음)"""

    def setUp(self):
        sleep_patcher = patch("tenacity.nap.time.sleep", lambda _: None)
        sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)
        self.adapter = KrxNativeAdapter(mbr_id="u", pw="p")
        self.adapter.is_logged_in = True

    def test_retries_then_succeeds_on_transient_connection_error(self):
        call_count = {"n": 0}

        def flaky_post(url, data=None, timeout=None):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise requests.exceptions.ConnectionError("boom")
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"OutBlock_1": []}
            return resp

        with patch.object(self.adapter.session, "post", side_effect=flaky_post):
            result = self.adapter._fetch_all_markets("20240311")

        self.assertEqual(call_count["n"], 3)
        self.assertEqual(result, [])

    def test_gives_up_after_max_attempts(self):
        with patch.object(
            self.adapter.session,
            "post",
            side_effect=requests.exceptions.ConnectionError("boom"),
        ) as mock_post:
            # _fetch_all_markets가 예외를 삼켜 [] 반환하므로 시도 횟수로 검증
            result = self.adapter._fetch_all_markets("20240311")

        self.assertEqual(mock_post.call_count, 3)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
