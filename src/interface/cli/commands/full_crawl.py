import typer
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
    각 기업 스크래핑 직후 즉시 OHLC 데이터를 PyKrx로 조회하여 추가합니다.
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
        
        # Google Drive 모드일 경우, 기존 파일 다운로드 (병합을 위해)
        if drive:
            try:
                target_filename = config.get_default_filename()
                deps['logger'].info(f"🔍 Google Drive에서 기존 파일 검색 중: {target_filename}")
                
                files = deps['storage'].list_files(f"name = '{target_filename}'")
                if files:
                    latest_file = files[0]
                    target_path = config.get_output_path(target_filename)
                    deps['logger'].info(f"⬇️  기존 파일 다운로드 중: {target_path}")
                    deps['storage'].download_file(latest_file['id'], target_path)
                    deps['logger'].info("✅ 다운로드 완료 (기존 데이터 병합 준비 완료)")
                else:
                    deps['logger'].info("ℹ️  Google Drive에 기존 파일이 없습니다. (신규 생성 예정)")
            except Exception as e:
                deps['logger'].warning(f"⚠️  Google Drive 파일 다운로드 실패 (신규 생성 진행): {e}")

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
                pass  # 로컈 파일 유지 (당분은 삭제 안 함)
            
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
