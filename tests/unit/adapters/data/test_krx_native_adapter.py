import unittest
from datetime import date
from infra.adapters.data.krx_native_adapter import KrxNativeAdapter

class TestKrxNativeAdapter(unittest.TestCase):
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
        ohlc = self.adapter.get_ohlc("005930", target_date)
        print(f"\n삼성전자 OHLC (2024-03-11): {ohlc}")
        self.assertIsNotNone(ohlc)
        self.assertIn("Close", ohlc)
        self.assertGreater(ohlc["Close"], 0)

if __name__ == "__main__":
    unittest.main()
