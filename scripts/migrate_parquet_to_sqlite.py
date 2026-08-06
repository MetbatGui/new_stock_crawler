"""
1회성 마이그레이션 스크립트: output/parquet/*.parquet -> db/{year}.db

기존 Parquet 저장소(종목명+상장일 복합키)를 SqliteRepository(종목명 단일키)로 옮긴다.
SqliteRepository.save()가 종목명 기준 dedup을 자동 적용하므로(상장일 오름차순 정렬 후
keep="last") 별도 dedup 로직 없이 그대로 저장하면 된다.

실행: uv run python scripts/migrate_parquet_to_sqlite.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402

from config import config  # noqa: E402
from infra.adapters.data.sqlite_repository import SqliteRepository  # noqa: E402

PARQUET_DIR = config.OUTPUT_DIR / "parquet"


def main() -> None:
    if not PARQUET_DIR.exists():
        print(f"Parquet 디렉토리가 없습니다: {PARQUET_DIR}")
        return

    repository = SqliteRepository()

    for path in sorted(PARQUET_DIR.glob("*.parquet")):
        try:
            year = int(path.stem)
        except ValueError:
            continue

        df = pd.read_parquet(path, engine="pyarrow")
        if df.empty:
            print(f"[{year}] 빈 데이터, 건너뜀")
            continue

        before = len(df)
        repository.save(year, df)
        after = len(repository.load(year))
        print(
            f"[{year}] {before}건 -> {after}건 (종목명 dedup 후) db/{year}.db 저장 완료"
        )


if __name__ == "__main__":
    main()
