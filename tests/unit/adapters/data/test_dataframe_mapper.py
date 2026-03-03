"""
DataFrameMapper 단위 테스트
"""
import pytest
import pandas as pd
from core.domain.models import StockInfo
from infra.adapters.data.dataframe_mapper import DataFrameMapper


# 실제 DataFrameMapper.COLUMN_MAPPING 값에서 파생된 기대 컬럼 목록
EXPECTED_COLUMNS = [
    "종목명",
    "시장구분",
    "업종",
    "매출액(백만원)",
    "법인세비용차감전(백만원)",
    "순이익(백만원)",
    "자본금(백만원)",
    "총공모주식수",
    "액면가",
    "희망공모가액",
    "확정공모가",
    "공모금액(백만원)",
    "주간사",
    "상장일",
    "기관경쟁률",
    "우리사주조합",
    "기관투자자",
    "일반청약자",
    "유통가능물량(주)",
    "유통가능물량(%)",
    # OHLC 시세 정보
    "시가",
    "고가",
    "저가",
    "종가",
    "수익률(%)",
]


def _make_stock(name: str, listing_date: str) -> StockInfo:
    return StockInfo(
        name=name,
        url=f"http://{name}.com",
        market_segment="코스닥",
        sector="IT",
        revenue=1000,
        profit_pre_tax=100,
        net_profit=80,
        capital=500,
        total_shares=10000,
        par_value=500,
        desired_price_range="10000~12000",
        confirmed_price=11000,
        offering_amount=110000,
        underwriter="테스트증권",
        listing_date=listing_date,
        competition_rate="1000:1",
        emp_shares=100,
        inst_shares=5000,
        retail_shares=2000,
        tradable_shares_count="3000",
        tradable_shares_percent="30%",
    )


class TestDataFrameMapper:
    """DataFrameMapper 클래스 테스트"""

    @pytest.fixture
    def mapper(self):
        return DataFrameMapper()

    def test_to_dataframe_with_data(self, mapper):
        """
        데이터가 있는 경우 DataFrame으로 올바르게 변환되는지 테스트
        """
        stocks = [_make_stock("테스트기업", "2024-01-01"), _make_stock("샘플기업", "2024-02-01")]
        df = mapper.to_dataframe(stocks)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == EXPECTED_COLUMNS

        # 실제 값 검증
        assert df.iloc[0]["종목명"] == "테스트기업"
        assert df.iloc[0]["매출액(백만원)"] == 1000
        assert df.iloc[1]["종목명"] == "샘플기업"
        assert df.iloc[1]["확정공모가"] == 11000

    def test_to_dataframe_empty_list(self, mapper):
        """
        빈 리스트 입력 시 빈 DataFrame을 반환하되 컬럼은 존재해야 함
        """
        df = mapper.to_dataframe([])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_to_dataframe_numeric_columns_are_int(self, mapper):
        """
        숫자형 컬럼이 Int64로 변환되는지 확인
        """
        stocks = [_make_stock("정수테스트", "2024-03-01")]
        df = mapper.to_dataframe(stocks)

        assert df.iloc[0]["매출액(백만원)"] == 1000
        # Int64 (Nullable Integer) 타입이어야 함
        assert str(df["매출액(백만원)"].dtype) == "Int64"

    def test_column_mapping_matches_schema(self, mapper):
        """
        COLUMN_MAPPING이 실제로 정의된 컬럼 목록과 일치하는지 검증
        """
        actual_cols = list(mapper.COLUMN_MAPPING.values())
        assert len(actual_cols) == len(EXPECTED_COLUMNS), (
            f"COLUMN_MAPPING 컬럼 수 불일치: "
            f"실제={len(actual_cols)}, 기대={len(EXPECTED_COLUMNS)}"
        )
        assert actual_cols == EXPECTED_COLUMNS
