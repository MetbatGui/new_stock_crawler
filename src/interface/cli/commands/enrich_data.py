import typer
import os
import pandas as pd
from pathlib import Path
from typing import Optional
from config import config
from interface.cli.dependencies import build_dependencies
from core.services.enrichment_service import EnrichmentService
from infra.adapters.data.pykrx_adapter import PyKrxAdapter
from infra.adapters.data.excel_exporter import ExcelExporter
from infra.adapters.utils.console_logger import ConsoleLogger
from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter
from core.services.stock_price_enricher import StockPriceEnricher

def enrich_data(
    filepath: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="대상 엑셀 파일 경로 (미지정 시 최신 파일 자동 검색)"
    ),
    drive: bool = typer.Option(False, "--drive", help="구글 드라이브 모드 (다운로드 -> 보강 -> 업로드 -> 삭제)"),
):
    """
    기존 데이터에 OHLC 보강
    
    이미 수집된 엑셀 파일을 읽어서 OHLC 데이터와 수익률을 추가합니다.
    """
    logger = ConsoleLogger()
    storage_adapter = GoogleDriveAdapter()
    
    logger.info("=" * 60)
    logger.info("📈 시세 보강 작업 스크립트 시작")
    logger.info(f"💾 모드: {'Google Drive' if drive else 'Local'}")
    logger.info("=" * 60)
    
    target_path = None
    
    # 1. 대상 파일 결정 (Drive vs Local)
    if drive:
        # Drive 모드: 최신 파일 검색 및 다운로드
        try:
            target_filename = config.get_default_filename()
            logger.info(f"🔍 Google Drive에서 파일 검색 중: {target_filename}")
            
            files = storage_adapter.list_files(f"name = '{target_filename}'")
            if not files:
                logger.error(f"❌ Google Drive에 대상 파일이 없습니다: {target_filename}")
                raise typer.Exit(code=1)
                
            latest_file = files[0] # createdTime desc 정렬됨
            logger.info(f"    - 발견: {latest_file['name']} (ID: {latest_file['id']})")
            
            # 다운로드 (파일명 유지)
            target_path = config.get_output_path(latest_file['name'])
            logger.info(f"⬇️  다운로드 중: {target_path}")
            storage_adapter.download_file(latest_file['id'], target_path)
            
        except Exception as e:
            logger.error(f"❌ Google Drive 작업 실패: {e}")
            raise typer.Exit(code=1)
    else:
        # Local 모드
        if filepath:
            target_path = Path(filepath)
        else:
            target_path = config.get_latest_output_file()
            
        if not target_path or not target_path.exists():
            logger.error(f"❌ 파일을 찾을 수 없습니다: {target_path}")
            logger.info("💡 팁: 먼저 크롤러를 실행하여 데이터를 수집해주세요 (uv run crawler full)")
            raise typer.Exit(code=1)

    logger.info(f"대상 파일: {target_path}")
    
    # 2. 데이터 로드 및 보강
    try:
        excel_file = pd.ExcelFile(target_path)
        yearly_data = {}
        
        for sheet_name in excel_file.sheet_names:
            try:
                year = int(sheet_name)
                df = pd.read_excel(target_path, sheet_name=sheet_name)
                yearly_data[year] = df
                logger.info(f"    - [{year}년] {len(df)}건 로드 완료")
            except ValueError:
                continue
        
        if not yearly_data:
            logger.warning("❌ 처리할 데이터가 없습니다.")
            raise typer.Exit(code=1)
        
        # 서비스 초기화
        pykrx_adapter = PyKrxAdapter()
        data_exporter = ExcelExporter()
        
        stock_enricher = StockPriceEnricher(
            ticker_mapper=pykrx_adapter,
            market_data_provider=pykrx_adapter,
            logger=logger
        )
        
        enrichment_service = EnrichmentService(
            stock_enricher=stock_enricher,
            data_exporter=data_exporter,
            logger=logger
        )
        
        # 보강 실행 (저장까지 수행됨)
        enrichment_service.enrich_data(yearly_data)
        
        logger.info("=" * 60)
        logger.info("🏁 보강 작업 완료")
        
        # 3. Drive 모드 후처리 (업로드 및 삭제)
        if drive:
            output_path = config.get_output_path(config.get_default_filename())
            try:
                if output_path.exists():
                    logger.info("☁️  Google Drive 업로드 시작...")
                    file_id = storage_adapter.upload_file(output_path)
                    logger.info(f"✅ 업로드 성공 (ID: {file_id})")
            except Exception as e:
                logger.warning(f"⚠️  Google Drive 업로드 실패: {e}")
            finally:
                # 로컬 파일 삭제 (Cleanup)
                # 다운로드 받은 원본 파일 삭제
                if target_path and target_path.exists() and target_path != output_path:
                        os.remove(target_path)
                        
                # 새로 생성된 파일 삭제
                if output_path.exists():
                    os.remove(output_path)
                    logger.info(f"🗑️  임시 파일 삭제 완료")
            
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 작업 중 오류 발생: {e}")
        raise
