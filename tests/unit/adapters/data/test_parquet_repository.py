"""
ParquetRepository 단위 테스트
"""
import pytest
import pandas as pd
from pathlib import Path

from infra.adapters.data.parquet_repository import ParquetRepository


@pytest.fixture
def repo(tmp_path: Path) -> ParquetRepository:
    """임시 디렉터리를 base_dir로 사용하는 저장소"""
    return ParquetRepository(base_dir=tmp_path)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "종목명": ["주식A", "주식B"],
        "상장일": ["2024-01-15", "2024-02-20"],
        "확정공모가": [10000, 20000],
    })


class TestParquetRepository:

    def test_save_creates_parquet_file(self, repo: ParquetRepository, sample_df: pd.DataFrame):
        """save() 후 Parquet 파일이 생성되어야 한다"""
        repo.save(2024, sample_df)
        assert (repo._base_dir / "2024.parquet").exists()

    def test_load_returns_saved_data(self, repo: ParquetRepository, sample_df: pd.DataFrame):
        """load()는 save()한 데이터를 반환해야 한다"""
        repo.save(2024, sample_df)
        loaded = repo.load(2024)
        assert len(loaded) == len(sample_df)
        assert list(loaded["종목명"]) == list(sample_df["종목명"])

    def test_load_returns_empty_df_when_no_data(self, repo: ParquetRepository):
        """데이터 없는 연도 로드 시 빈 DataFrame 반환"""
        result = repo.load(9999)
        assert result.empty

    def test_save_upsert_deduplicates_by_pk(self, repo: ParquetRepository):
        """같은 (종목명, 상장일)이 있으면 마지막(신규) 데이터가 우선"""
        df1 = pd.DataFrame({
            "종목명": ["주식A"],
            "상장일": ["2024-01-15"],
            "확정공모가": [10000],
        })
        repo.save(2024, df1)

        df2 = pd.DataFrame({
            "종목명": ["주식A"],
            "상장일": ["2024-01-15"],
            "확정공모가": [12000],  # 갱신
        })
        repo.save(2024, df2)

        loaded = repo.load(2024)
        assert len(loaded) == 1
        assert loaded.iloc[0]["확정공모가"] == 12000

    def test_save_skips_empty_dataframe(self, repo: ParquetRepository):
        """빈 DataFrame은 저장하지 않는다"""
        repo.save(2024, pd.DataFrame())
        assert not (repo._base_dir / "2024.parquet").exists()

    def test_load_all_returns_all_years(self, repo: ParquetRepository, sample_df: pd.DataFrame):
        """load_all()은 저장된 모든 연도 데이터를 반환한다"""
        repo.save(2024, sample_df)
        repo.save(2025, sample_df)

        result = repo.load_all()
        assert 2024 in result
        assert 2025 in result

    def test_get_available_years_returns_sorted_years(
        self, repo: ParquetRepository, sample_df: pd.DataFrame
    ):
        """get_available_years()는 오름차순 연도 목록을 반환한다"""
        repo.save(2025, sample_df)
        repo.save(2023, sample_df)
        repo.save(2024, sample_df)

        years = repo.get_available_years()
        assert years == [2023, 2024, 2025]
