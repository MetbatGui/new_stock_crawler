"""
export-excel 커맨드 — SQLite → Excel 렌더링
"""

import typer
from pathlib import Path
from typing import Optional

from config import config
from infra.adapters.data.sqlite_repository import SqliteRepository
from interface.cli.rendering.excel_renderer import ExcelRenderer
from infra.adapters.utils.console_logger import ConsoleLogger


def export_excel(
    year: Optional[int] = typer.Option(
        None,
        "--year",
        "-y",
        help="렌더링할 연도 (지정 안 하면 전체 연도)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="저장할 디렉토리 또는 특정 파일 경로 (기본: output/)",
    ),
    drive: bool = typer.Option(False, "--drive", help="Google Drive로 업로드"),
):
    """
    SQLite 저장소에서 데이터를 읽어 연도별로 개별 Excel 파일로 렌더링
    """
    logger = ConsoleLogger()
    repository = SqliteRepository()
    renderer = ExcelRenderer()

    logger.info("=" * 60)
    logger.info("📊 연도별 Excel 분할 렌더링 시작")

    # 데이터 로드
    if year is not None:
        raw_data = {year: repository.load(year)}
        if raw_data[year].empty:
            logger.warning(f"[{year}년] 저장된 데이터가 없습니다.")
            raise typer.Exit(code=1)
    else:
        raw_data = repository.load_all()
        if not raw_data:
            logger.warning("저장된 데이터가 없습니다. 먼저 크롤링을 실행해 주세요.")
            raise typer.Exit(code=1)

    # output이 파일 경로(확장자 있음)인지 디렉토리인지 판단.
    # 아직 생성되지 않은 디렉토리도 디렉토리로 취급해야 하므로 is_dir() 대신 확장자로 판단.
    output_is_file_path = output is not None and output.suffix != ""
    base_output_dir = (
        output.parent if output_is_file_path else (output or config.OUTPUT_DIR)
    )
    base_output_dir.mkdir(parents=True, exist_ok=True)

    # 연도별로 루프를 돌며 개별 파일만 생성 (Drive 업로드는 루프 밖에서 일괄 처리)
    generated_paths: list[Path] = []
    for y, df in sorted(raw_data.items()):
        if df.empty:
            continue

        # 단일 연도 조회 + output이 파일 경로로 들어온 경우 그 경로를 존중
        if output_is_file_path and year is not None:
            output_path = output
        else:
            output_path = base_output_dir / f"신규상장종목({y}년).xlsx"

        # 렌더링 (단일 연도 데이터를 딕셔너리로 감싸서 전달)
        renderer.render({y: df}, output_path)
        logger.info(f"✅ [{y}년] Excel 저장 완료: {output_path.name}")
        generated_paths.append(output_path)

    # Google Drive 업로드 — 로컬에 전부 쓴 뒤 실행 끝에 한 번만 동기화
    if drive and generated_paths:
        from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter

        storage = GoogleDriveAdapter()
        for path in generated_paths:
            try:
                file_id = storage.upload_file(path)
                logger.info(
                    f"   ☁️  Google Drive 업로드 완료: {path.name} (ID: {file_id})"
                )
            except Exception as e:
                logger.error(f"   ⚠️  Google Drive 업로드 실패: {path.name} - {e}")

    logger.info("=" * 60)
