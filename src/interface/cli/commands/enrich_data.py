"""
enrich-data 커맨드 — SQLite 저장소 기반 OHLC 보강
"""

import typer
from interface.cli.dependencies import build_dependencies


def enrich_data():
    """
    SQLite 저장소에서 데이터를 읽어 OHLC 및 수익률을 보강 후 다시 저장

    Excel 파일이 아닌 SQLite 저장소를 진실의 공급원으로 사용합니다. 이미 채워진 행과
    상장일 컷오프 전인 행은 건너뛰므로 재실행해도 안전합니다.
    보강 결과를 확인하려면 `export-excel` 커맨드를 실행하세요.
    """
    deps = build_dependencies()
    logger = deps["logger"]
    repository = deps["repository"]

    logger.info("=" * 60)
    logger.info("📈 시세 보강 작업 시작")

    yearly_data = repository.load_all()
    if not yearly_data:
        logger.warning("저장된 데이터가 없습니다. 먼저 크롤링을 실행해 주세요.")
        raise typer.Exit(code=1)

    total = sum(len(df) for df in yearly_data.values())
    logger.info(f"전체 {len(yearly_data)}개 연도, {total}건 로드 완료")

    deps["enrichment"].enrich_data(yearly_data)

    logger.info("🏁 보강 작업 완료")
    logger.info("💡 Excel 내보내기: uv run crawler export-excel")
    logger.info("=" * 60)
