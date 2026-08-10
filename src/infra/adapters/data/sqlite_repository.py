"""
SQLite 기반 저장소 어댑터 구현
"""

import os
import sqlite3
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from config import config
from core.ports.repository_ports import RepositoryPort


class SqliteRepository(RepositoryPort):
    """
    SQLite 파일 기반 IPO 데이터 저장소 (연도별 DB 파일 분리)

    레이아웃:
        {DB_DIR}/{year}.db, 테이블명 "stocks"

    upsert 전략:
        종목명 단일키 기준 중복 제거 (상장일은 정정될 수 있어 PK에서 제외).
        신규 데이터가 기존 데이터보다 우선(keep='last').
    """

    TABLE = "stocks"
    _PK_COLS = ["종목명"]

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir: Path = base_dir or config.DB_DIR
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, year: int) -> Path:
        return self._base_dir / f"{year}.db"

    def _meta_path(self) -> Path:
        return self._base_dir / "meta.db"

    # ------------------------------------------------------------------ #
    #  Write                                                               #
    # ------------------------------------------------------------------ #

    def save(self, year: int, df: pd.DataFrame) -> None:
        """
        연도별 데이터를 SQLite로 upsert 저장

        Args:
            year: 저장 대상 연도
            df: 신규 또는 갱신된 DataFrame
        """
        if df.empty:
            return

        path = self._path(year)

        # 기존 파일이 있으면 로드 후 병합
        existing = self.load(year)
        combined = (
            pd.concat([existing, df], ignore_index=True)
            if not existing.empty
            else df.copy()
        )

        # 종목명 단일 PK 기준 중복 제거 — 신규 우선
        pk_cols = [c for c in self._PK_COLS if c in combined.columns]
        if pk_cols:
            combined = combined.drop_duplicates(subset=pk_cols, keep="last")

        # 상장일 기준 오름차순 정렬
        if "상장일" in combined.columns:
            combined = combined.sort_values("상장일", ascending=True)

        tmp_path = path.with_suffix(".db.tmp")
        try:
            conn = sqlite3.connect(tmp_path)
            try:
                combined.to_sql(self.TABLE, conn, if_exists="replace", index=False)
                conn.execute(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{self.TABLE}_name "
                    f'ON {self.TABLE}("종목명")'
                )
                conn.commit()
            finally:
                conn.close()
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
        conn = sqlite3.connect(path)
        try:
            return pd.read_sql(f'SELECT * FROM {self.TABLE} ORDER BY "상장일"', conn)
        finally:
            conn.close()

    def load_all(self) -> Dict[int, pd.DataFrame]:
        """전체 연도 데이터 로드"""
        result: Dict[int, pd.DataFrame] = {}
        for year in self.get_available_years():
            result[year] = self.load(year)
        return result

    def get_available_years(self) -> List[int]:
        """저장된 연도 목록 반환 (오름차순)"""
        years = []
        for p in self._base_dir.glob("*.db"):
            try:
                years.append(int(p.stem))
            except ValueError:
                continue
        return sorted(years)

    # ------------------------------------------------------------------ #
    #  마지막 크롤링 기준일 (연도별 파일과 별개로 meta.db에 단일 값 기록)      #
    # ------------------------------------------------------------------ #

    def get_last_crawl_date(self) -> Optional[date]:
        path = self._meta_path()
        if not path.exists():
            return None
        conn = sqlite3.connect(path)
        try:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'last_crawl_date'"
            ).fetchone()
            return date.fromisoformat(row[0]) if row else None
        finally:
            conn.close()

    def set_last_crawl_date(self, value: date) -> None:
        conn = sqlite3.connect(self._meta_path())
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
            )
            conn.execute(
                "INSERT INTO meta (key, value) VALUES ('last_crawl_date', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (value.isoformat(),),
            )
            conn.commit()
        finally:
            conn.close()
