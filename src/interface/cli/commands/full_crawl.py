import typer
import os
from datetime import date
from config import config
from interface.cli.dependencies import build_dependencies

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
    deps = build_dependencies(headless=headless)
    
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
