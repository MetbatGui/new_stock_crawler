import unittest
from datetime import date
import pytest
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


if __name__ == "__main__":
    unittest.main()
