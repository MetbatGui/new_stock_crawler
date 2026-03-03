"""
export-excel 커맨드 — Parquet → Excel 렌더링
"""
import typer
from pathlib import Path
from typing import Optional

from config import config
from infra.adapters.data.parquet_repository import ParquetRepository
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
        help="저장할 Excel 경로 (기본: output/신규상장종목.xlsx)",
    ),
    drive: bool = typer.Option(
        False, "--drive", help="Google Drive로 업로드"
    ),
):
    """
    Parquet 저장소에서 데이터를 읽어 Excel 파일로 렌더링

    저장소(Parquet)와 표현(Excel)을 분리한 구조에서
    이 커맨드가 유일하게 Excel 파일을 생성합니다.
    """
    logger = ConsoleLogger()
    repository = ParquetRepository()
    renderer = ExcelRenderer()

    logger.info("=" * 60)
    logger.info("📊 Excel 렌더링 시작")

    # 데이터 로드
    if year is not None:
        data = {year: repository.load(year)}
        if data[year].empty:
            logger.warning(f"[{year}년] 저장된 데이터가 없습니다.")
            raise typer.Exit(code=1)
        logger.info(f"[{year}년] {len(data[year])}건 로드")
    else:
        data = repository.load_all()
        if not data:
            logger.warning("저장된 데이터가 없습니다. 먼저 크롤링을 실행해 주세요.")
            raise typer.Exit(code=1)
        total = sum(len(df) for df in data.values())
        logger.info(f"전체 {len(data)}개 연도, {total}건 로드")

    # 출력 경로 결정
    if output:
        output_path = Path(output)
    else:
        output_path = config.OUTPUT_DIR / "신규상장종목.xlsx"
    
    # 출력 디렉토리 생성 보장
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 렌더링
    renderer.render(data, output_path)
    logger.info(f"✅ Excel 저장 완료: {output_path}")

    # Google Drive 업로드
    if drive:
        try:
            from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter
            storage = GoogleDriveAdapter()
            file_id = storage.upload_file(output_path)
            logger.info(f"☁️  Google Drive 업로드 완료 (ID: {file_id})")
        except Exception as e:
            logger.error(f"⚠️  Google Drive 업로드 실패: {e}")
            logger.info("=" * 60)
            raise typer.Exit(code=1)

    logger.info("=" * 60)
