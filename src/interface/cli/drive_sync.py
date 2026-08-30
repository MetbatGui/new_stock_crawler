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
) -> bool:
    """변경된 연도의 Excel/DB를 Drive로 업로드한다.

    Returns:
        bool: 모든 업로드가 성공했으면 True. 하나라도 실패하면 False - 호출부는 이 값이
            False면 exit code를 0이 아닌 값으로 끝내야 한다(db_ssot_guide.md §6.2).
            sync_db_years_from_drive()가 로컬을 항상 불신하고 매번 Drive로 덮어쓰므로,
            업로드 실패를 조용히 넘기면 이번에 계산한 최신 데이터가 다음 실행에서
            낡은 원격 사본에 덮어써져 사라질 수 있다.
    """
    years: Set[int] = set(changed_years)
    if not years:
        return True

    renderer = ExcelRenderer()
    storage = GoogleDriveAdapter()
    all_succeeded = True

    # 1. Excel 먼저
    for year in sorted(years):
        df = repository.load(year)
        if df.empty:
            continue

        excel_path = config.OUTPUT_DIR / f"신규상장종목({year}년).xlsx"
        renderer.render({year: df}, excel_path)
        file_id = storage.upload_file(excel_path)
        if file_id:
            logger.info(f"   ☁️  [{year}년] Excel Drive 업로드 완료 (ID: {file_id})")
        else:
            logger.error(f"   ⚠️  [{year}년] Excel Drive 업로드 실패")
            all_succeeded = False

    # 2. db/{year}.db 나중 (db 서브폴더로)
    db_folder_id = storage.get_or_create_subfolder("db")
    if db_folder_id is None:
        logger.error("   ⚠️  Google Drive db 서브폴더 조회/생성 실패 — DB 업로드 건너뜀")
        return False

    for year in sorted(years):
        db_path = config.DB_DIR / f"{year}.db"
        if not db_path.exists():
            continue
        file_id = storage.upload_file(db_path, parent_folder_id=db_folder_id)
        if file_id:
            logger.info(f"   ☁️  [{year}년] DB Drive 업로드 완료 (ID: {file_id})")
        else:
            logger.error(f"   ⚠️  [{year}년] DB Drive 업로드 실패")
            all_succeeded = False

    return all_succeeded
