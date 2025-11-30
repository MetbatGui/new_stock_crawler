"""
Stock Crawler CLI - 단일 진입점
"""
import typer
from datetime import date, datetime
from typing import Optional
import pandas as pd
import os
from pathlib import Path
from config import config

app = typer.Typer(help="IPO 데이터 크롤러 CLI")


def _build_dependencies(headless: bool = config.HEADLESS):
    """
    의존성 조립 (DI Container 역할)
    
    Args:
        headless: Playwright 헤드리스 모드
        
    Returns:
        dict: 조립된 의존성 객체들
    """
    from infra.adapters.utils.console_logger import ConsoleLogger
    from infra.adapters.utils.date_calculator import DateCalculator
    from infra.adapters.web.playwright_page_provider import PlaywrightPageProvider
    from infra.adapters.web.calendar_scraper_adapter import CalendarScraperAdapter
    from infra.adapters.web.detail_scraper_adapter import DetailScraperAdapter
    from infra.adapters.data.dataframe_mapper import DataFrameMapper
    from infra.adapters.data.excel_exporter import ExcelExporter
    from infra.adapters.data.fdr_adapter import FDRAdapter
    from core.services.crawler_service import CrawlerService
    from core.services.stock_price_enricher import StockPriceEnricher
    
    # 1. 유틸리티
    logger = ConsoleLogger()
    date_calculator = DateCalculator()
    
    # 2. Data
    fdr_adapter = FDRAdapter()
    data_mapper = DataFrameMapper()
    data_exporter = ExcelExporter()  # config 사용
    
    # 3. Storage
    from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter
    storage_adapter = GoogleDriveAdapter()

    # 3.5 Enrichment
    stock_enricher = StockPriceEnricher(
        ticker_mapper=fdr_adapter,
        market_data_provider=fdr_adapter,
        logger=logger
    )
    
    # 4. Web Scraping
    page_provider = PlaywrightPageProvider(headless=headless)
    calendar_scraper = CalendarScraperAdapter()
    detail_scraper = DetailScraperAdapter(
        logger=logger
    )
    
    # 5. Service
    crawler_service = CrawlerService(
        page_provider=page_provider,
        calendar_scraper=calendar_scraper,
        detail_scraper=detail_scraper,
        data_mapper=data_mapper,
        data_exporter=data_exporter,
        date_calculator=date_calculator,
        stock_enricher=stock_enricher,
        logger=logger
    )
    
    return {
        'crawler': crawler_service,
        'page_provider': page_provider,
        'logger': logger,
        'fdr': fdr_adapter,
        'exporter': data_exporter,
        'storage': storage_adapter,
    }


@app.command("full")
def full_crawl(
    start_year: int = typer.Option(2020, "--start-year", "-s", help="크롤링 시작 연도"),
    headless: bool = typer.Option(config.HEADLESS, "--headless/--no-headless", help="헤드리스 모드"),
    drive: bool = typer.Option(False, "--drive", help="구글 드라이브 모드 (업로드 및 로컬 파일 삭제)"),
):
    """
    전체 기간 크롤링 (초기 수집용)
    
    지정한 연도부터 현재까지의 모든 IPO 데이터를 수집합니다.
    각 기업 스크래핑 직후 즉시 OHLC 데이터를 FDR로 조회하여 추가합니다.
    """
    deps = _build_dependencies(headless=headless)
    
    try:
        deps['logger'].info("=" * 60)
        deps['logger'].info("🚀 Stock Crawler - 전체 크롤링")
        deps['logger'].info(f"📅 기준 날짜: {date.today()}")
        deps['logger'].info(f"📆 크롤링 시작 연도: {start_year}년")
        deps['logger'].info(f"💾 모드: {'Google Drive' if drive else 'Local'}")
        deps['logger'].info("=" * 60)
        
        # Playwright 초기화
        deps['page_provider'].setup()
        
        # 크롤링 실행
        yearly_data = deps['crawler'].run(start_year=start_year)
        
        deps['logger'].info("=" * 60)
        deps['logger'].info("🏁 모든 크롤링 및 보강 작업 완료")
        
        # Google Drive 모드 처리
        if drive:
            output_path = config.get_output_path(config.get_default_filename())
            try:
                if output_path.exists():
                    deps['logger'].info("☁️  Google Drive 업로드 시작...")
                    file_id = deps['storage'].upload_file(output_path)
                    deps['logger'].info(f"✅ 업로드 성공 (ID: {file_id})")
            except Exception as e:
                deps['logger'].warning(f"⚠️  Google Drive 처리 실패: {e}")
            finally:
                # 로컬 파일 삭제 (Cleanup) - 성공/실패 여부와 관계없이 삭제
                if output_path.exists():
                    os.remove(output_path)
                    deps['logger'].info(f"🗑️  임시 파일 삭제 완료: {output_path}")
            
        deps['logger'].info("=" * 60)
        
    except KeyboardInterrupt:
        deps['logger'].warning("\n⚠️  사용자에 의해 중단되었습니다")
    except Exception as e:
        deps['logger'].error(f"❌ 크롤링 중 오류 발생: {e}")
        raise
    finally:
        # 리소스 정리
        deps['page_provider'].cleanup()
        deps['logger'].info("\n✅ 리소스 정리 완료")


@app.command("enrich")
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
    from core.services.enrichment_service import EnrichmentService
    from infra.adapters.data.fdr_adapter import FDRAdapter
    from infra.adapters.data.excel_exporter import ExcelExporter
    from infra.adapters.utils.console_logger import ConsoleLogger
    from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter
    from core.services.stock_price_enricher import StockPriceEnricher
    
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
        fdr_adapter = FDRAdapter()
        data_exporter = ExcelExporter()
        
        stock_enricher = StockPriceEnricher(
            ticker_mapper=fdr_adapter,
            market_data_provider=fdr_adapter,
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


@app.command("daily")
def daily_update(
    target_date: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="대상 날짜 (YYYY-MM-DD 형식), 기본값: 오늘"
    ),
    headless: bool = typer.Option(config.HEADLESS, "--headless/--no-headless", help="헤드리스 모드"),
    drive: bool = typer.Option(False, "--drive", help="구글 드라이브 모드 (업로드 및 로컬 파일 삭제)"),
):
    """
    일일 업데이트 (GitHub Actions용)
    
    특정 날짜의 IPO 데이터만 크롤링하여 기존 엑셀에 추가합니다.
    날짜를 지정하지 않으면 오늘 날짜로 실행됩니다.
    """
    # 날짜 파싱
    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            typer.echo("❌ 날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 입력해주세요.")
            raise typer.Exit(code=1)
    else:
        parsed_date = date.today()
    
    deps = _build_dependencies(headless=headless)
    
    try:
        deps['logger'].info("=" * 60)
        deps['logger'].info("📅 Stock Crawler - 일일 업데이트")
        deps['logger'].info(f"대상 날짜: {parsed_date}")
        deps['logger'].info(f"💾 모드: {'Google Drive' if drive else 'Local'}")
        deps['logger'].info("=" * 60)
        
        # Playwright 초기화
        deps['page_provider'].setup()
        
        # 일일 크롤링 실행
        new_data = deps['crawler'].run_daily(target_date=parsed_date)
        
        if new_data:
            total_count = sum(len(df) for df in new_data.values())
            deps['logger'].info(f"✅ {total_count}건 추가됨")
        else:
            deps['logger'].info("ℹ️  오늘은 상장 예정 없음")
        
        deps['logger'].info("=" * 60)
        deps['logger'].info("🏁 일일 업데이트 완료")
        
        # Google Drive 모드 처리
        if drive and new_data:
            output_path = config.get_output_path(config.get_default_filename())
            try:
                if output_path.exists():
                    deps['logger'].info("☁️  Google Drive 업로드 시작...")
                    file_id = deps['storage'].upload_file(output_path)
                    deps['logger'].info(f"✅ 업로드 성공 (ID: {file_id})")
            except Exception as e:
                deps['logger'].warning(f"⚠️  Google Drive 처리 실패: {e}")
            finally:
                # 로컬 파일 삭제 (Cleanup)
                if output_path.exists():
                    os.remove(output_path)
                    deps['logger'].info(f"🗑️  임시 파일 삭제 완료")
                
        deps['logger'].info("=" * 60)
        
    except KeyboardInterrupt:
        deps['logger'].warning("\n⚠️  사용자에 의해 중단되었습니다")
    except Exception as e:
        deps['logger'].error(f"❌ 크롤링 중 오류 발생: {e}")
        raise
    finally:
        # 리소스 정리
        deps['page_provider'].cleanup()
        deps['logger'].info("\n✅ 리소스 정리 완료")


if __name__ == "__main__":
    app()
