"""
enrich-data 커맨드 — Parquet 저장소 기반 OHLC 보강
"""
import typer
from infra.adapters.data.parquet_repository import ParquetRepository
from infra.adapters.data.pykrx_adapter import PyKrxAdapter
from infra.adapters.utils.console_logger import ConsoleLogger
from core.services.stock_price_enricher import StockPriceEnricher
from core.services.enrichment_service import EnrichmentService


def enrich_data():
    """
    Parquet 저장소에서 데이터를 읽어 OHLC 및 수익률을 보강 후 다시 저장

    Excel 파일이 아닌 Parquet 저장소를 진실의 공급원으로 사용합니다.
    보강 결과를 확인하려면 `export-excel` 커맨드를 실행하세요.
    """
    logger = ConsoleLogger()
    repository = ParquetRepository()

    logger.info("=" * 60)
    logger.info("📈 시세 보강 작업 시작")

    # 1. 전체 데이터 로드
    yearly_data = repository.load_all()
    if not yearly_data:
        logger.warning("저장된 데이터가 없습니다. 먼저 크롤링을 실행해 주세요.")
        raise typer.Exit(code=1)

    total = sum(len(df) for df in yearly_data.values())
    logger.info(f"전체 {len(yearly_data)}개 연도, {total}건 로드 완료")

    # 2. 보강 서비스 초기화
    pykrx_adapter = PyKrxAdapter()
    stock_enricher = StockPriceEnricher(
        ticker_mapper=pykrx_adapter,
        market_data_provider=pykrx_adapter,
        logger=logger,
    )

    enrichment_service = EnrichmentService(
        stock_enricher=stock_enricher,
        repository=repository,
        logger=logger,
    )

    # 3. 보강 실행 (Parquet upsert)
    enrichment_service.enrich_data(yearly_data)

    logger.info("🏁 보강 작업 완료")
    logger.info("💡 Excel 내보내기: uv run crawler export-excel")
    logger.info("=" * 60)
