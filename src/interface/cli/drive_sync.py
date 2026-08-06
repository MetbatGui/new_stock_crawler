"""
크롤링/백필 이후 변경된 연도의 Excel과 DB 파일을 Google Drive에 동기화.

순서 고정: Excel을 먼저 올리고(사람이 바로 확인 가능한 산출물), 그 다음
db/{year}.db를 "db" 서브폴더에 올린다.
"""

from typing import Iterable, Set

from config import config
from core.ports.repository_ports import RepositoryPort
from core.ports.utility_ports import LoggerPort
from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter
from interface.cli.rendering.excel_renderer import ExcelRenderer


def sync_changed_years_to_drive(
    repository: RepositoryPort, changed_years: Iterable[int], logger: LoggerPort
) -> None:
    years: Set[int] = set(changed_years)
    if not years:
        return

    renderer = ExcelRenderer()
    storage = GoogleDriveAdapter()

    # 1. Excel 먼저
    for year in sorted(years):
        df = repository.load(year)
        if df.empty:
            continue

        excel_path = config.OUTPUT_DIR / f"신규상장종목({year}년).xlsx"
        renderer.render({year: df}, excel_path)
        try:
            file_id = storage.upload_file(excel_path)
            logger.info(f"   ☁️  [{year}년] Excel Drive 업로드 완료 (ID: {file_id})")
        except Exception as e:
            logger.error(f"   ⚠️  [{year}년] Excel Drive 업로드 실패: {e}")

    # 2. db/{year}.db 나중 (db 서브폴더로)
    try:
        db_folder_id = storage.get_or_create_subfolder("db")
    except Exception as e:
        logger.error(f"   ⚠️  Google Drive db 서브폴더 조회/생성 실패: {e}")
        return

    for year in sorted(years):
        db_path = config.DB_DIR / f"{year}.db"
        if not db_path.exists():
            continue
        try:
            file_id = storage.upload_file(db_path, parent_folder_id=db_folder_id)
            logger.info(f"   ☁️  [{year}년] DB Drive 업로드 완료 (ID: {file_id})")
        except Exception as e:
            logger.error(f"   ⚠️  [{year}년] DB Drive 업로드 실패: {e}")
