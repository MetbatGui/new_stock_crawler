"""
Parquet 기반 저장소 어댑터 구현
"""
from pathlib import Path
from typing import Dict, List
import pandas as pd
import os
import logging

from core.ports.repository_ports import RepositoryPort
from config import config

logger = logging.getLogger("crawler")


class ParquetRepository(RepositoryPort):
    """
    Parquet 파일 기반 IPO 데이터 저장소

    레이아웃:
        {OUTPUT_DIR}/parquet/{year}.parquet

    upsert 전략:
        (종목명, 상장일) 복합키 기준 중복 제거.
        신규 데이터가 기존 데이터보다 우선(keep='last').
    """

    SUBDIR = "parquet"
    # 중복 제거에 사용할 복합 PK
    _PK_COLS = ["종목명", "상장일"]

    def __init__(self, base_dir: Path = None) -> None:
        self._base_dir: Path = (base_dir or config.OUTPUT_DIR) / self.SUBDIR
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, year: int) -> Path:
        return self._base_dir / f"{year}.parquet"

    # ------------------------------------------------------------------ #
    #  Write                                                               #
    # ------------------------------------------------------------------ #

    def save(self, year: int, df: pd.DataFrame) -> None:
        """
        연도별 데이터를 Parquet으로 upsert 저장

        Args:
            year: 저장 대상 연도
            df: 신규 또는 갱신된 DataFrame
        """
        if df.empty:
            return

        path = self._path(year)

        # 기존 파일이 있으면 로드 후 병합
        if path.exists():
            existing = pd.read_parquet(path)
            combined = pd.concat([existing, df], ignore_index=True)
        else:
            combined = df.copy()

        # (종목명, 상장일) 복합키 기준 중복 제거 — 신규 우선
        pk_cols = [c for c in self._PK_COLS if c in combined.columns]
        if pk_cols:
            combined = combined.drop_duplicates(subset=pk_cols, keep="last")
        else:
            logger.warning("PK 컬럼이 없어 중복 제거를 건너뜁니다. (데이터 중복 우려)")

        # 상장일 기준 오름차순 정렬
        if "상장일" in combined.columns:
            combined = combined.sort_values("상장일", ascending=True)

        tmp_path = path.with_suffix(".parquet.tmp")
        try:
            combined.to_parquet(tmp_path, index=False, engine="pyarrow")
            os.replace(tmp_path, path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    # ------------------------------------------------------------------ #
    #  Read                                                                #
    # ------------------------------------------------------------------ #

    def load(self, year: int) -> pd.DataFrame:
        """
        연도별 데이터 로드

        Returns:
            DataFrame. 파일 없으면 빈 DataFrame.
        """
        path = self._path(year)
        if not path.exists():
            return pd.DataFrame()
        return pd.read_parquet(path, engine="pyarrow")

    def load_all(self) -> Dict[int, pd.DataFrame]:
        """전체 연도 데이터 로드"""
        result: Dict[int, pd.DataFrame] = {}
        for year in self.get_available_years():
            result[year] = self.load(year)
        return result

    def get_available_years(self) -> List[int]:
        """저장된 연도 목록 반환 (오름차순)"""
        years = []
        for p in self._base_dir.glob("*.parquet"):
            try:
                years.append(int(p.stem))
            except ValueError:
                continue
        return sorted(years)
