"""
크롤링/백필 이후 변경된 연도의 Excel과 DB 파일을 Google Drive에 동기화.

순서 고정: Excel을 먼저 올리고(사람이 바로 확인 가능한 산출물), 그 다음
db/{year}.db를 "db" 서브폴더에 올린다.

sync_db_years_from_drive()는 그 반대 방향 - 처리를 시작하기 전에 Drive의 DB 파일을
로컬로 받아온다. 이게 없으면 로컬 db/가 디스크 장애나 재배포로 유실됐을 때 자동
복구 경로가 없다(db_ssot_guide.md §6) - Drive엔 데이터가 있어도 아무 코드도 그걸
다시 받아오지 않기 때문(실제로 이 프로젝트가 그 상태였다 - download_file()이 정의만
되어 있고 호출하는 곳이 하나도 없었음).

**로컬은 항상 불신의 대상이다**(db_ssot_guide.md §6.2) - 로컬에 파일이 있어도 원격에
있으면 항상 다시 받아서 덮어쓴다. "로컬에 있으니 건너뛴다"는 하지 않는다 - 그러면
다운로드 자체가 무의미해진다(로컬이 한 번 채워지면 다시는 Drive를 확인 안 하게 됨).
직전 실행이 로컬 저장은 성공하고 업로드만 실패했을 경우 이번 다운로드가 그 변경분을
지울 수 있지만, 그 대가는 업로드 실패를 exit code로 절대 조용히 넘기지 않는 것으로
상쇄한다(daily_update.py/full_crawl.py 참고).
"""

from pathlib import Path
from typing import Iterable, Set

from config import config
from core.ports.repository_ports import RepositoryPort
from core.ports.storage_ports import StoragePort
from core.ports.utility_ports import LoggerPort
from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter
from interface.cli.rendering.excel_renderer import ExcelRenderer


def sync_db_years_from_drive(years: Iterable[int], logger: LoggerPort) -> None:
    """Drive의 db/{year}.db 파일들을 로컬로 미리 받아온다 (처리 시작 전 호출).

    원격에 파일이 없으면(최초 백필 전이거나 조회 실패) 건너뛴다 - list_files()의
    계약상 "없음"과 "조회 실패"를 구분하지 못하지만(storage_ports.py의 기존 계약),
    로컬은 여전히 이번 실행의 유일한 작업 사본이므로 다운로드를 못 하는 것은 치명적이지
    않다. download_file() 자체의 실패는 명확히 False로 구분되며 경고만 남기고 계속한다.
    """
    storage: StoragePort = GoogleDriveAdapter()
    db_folder_id = storage.get_or_create_subfolder("db")
    if db_folder_id is None:
        logger.error(
            "   ⚠️  Google Drive db 서브폴더 조회 실패 — DB 다운로드 건너뜀 (로컬 사본으로 계속 진행)"
        )
        return

    for year in sorted(set(years)):
        filename = f"{year}.db"
        matches = storage.list_files(f"name = '{filename}'", folder_id=db_folder_id)
        if not matches:
            continue  # 원격에 아직 없음 - 정상(최초 백필 전)

        file_id = matches[0]["id"]
        local_path: Path = config.DB_DIR / filename
        config.DB_DIR.mkdir(parents=True, exist_ok=True)
        if storage.download_file(file_id, local_path):
            logger.info(f"   ☁️  [{year}년] DB Drive 다운로드 완료")
        else:
            logger.warning(
                f"   ⚠️  [{year}년] DB Drive 다운로드 실패 - 로컬 사본으로 계속 진행합니다"
            )


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
        file_id = storage.upload_file(excel_path)
        if file_id:
            logger.info(f"   ☁️  [{year}년] Excel Drive 업로드 완료 (ID: {file_id})")
        else:
            logger.error(f"   ⚠️  [{year}년] Excel Drive 업로드 실패")

    # 2. db/{year}.db 나중 (db 서브폴더로)
    db_folder_id = storage.get_or_create_subfolder("db")
    if db_folder_id is None:
        logger.error("   ⚠️  Google Drive db 서브폴더 조회/생성 실패 — DB 업로드 건너뜀")
        return

    for year in sorted(years):
        db_path = config.DB_DIR / f"{year}.db"
        if not db_path.exists():
            continue
        file_id = storage.upload_file(db_path, parent_folder_id=db_folder_id)
        if file_id:
            logger.info(f"   ☁️  [{year}년] DB Drive 업로드 완료 (ID: {file_id})")
        else:
            logger.error(f"   ⚠️  [{year}년] DB Drive 업로드 실패")
