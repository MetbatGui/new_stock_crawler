import typer
from datetime import date, datetime
from typing import Optional
from config import config
from interface.cli.dependencies import build_dependencies

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
    
    deps = build_dependencies(headless=headless)
    
    try:
        deps['logger'].info("=" * 60)
        deps['logger'].info("📅 Stock Crawler - 일일 스케줄 업데이트")
        deps['logger'].info(f"시작 날짜: {parsed_date}")
        deps['logger'].info(f"수집 범위: 당일 + 3일 (총 4일)")
        deps['logger'].info(f"💾 모드: {'Google Drive' if drive else 'Local'}")
        deps['logger'].info("=" * 60)
        
        # Playwright 초기화
        deps['page_provider'].setup()
        
        # Google Drive 모드일 경우, 기존 파일 다운로드 (Append를 위해)
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
                    deps['logger'].info(f"⚠️  Google Drive에서 파일을 찾을 수 없습니다: {target_filename}")
                    deps['logger'].info("ℹ️  (신규 생성 예정)")
            except Exception as e:
                deps['logger'].warning(f"⚠️  Google Drive 파일 다운로드 실패 (신규 생성 진행): {e}")

        # 일일 스케줄 크롤링 실행 (당일 + 3일)
        new_data = deps['crawler'].run_scheduled(start_date=parsed_date, days_ahead=3)
        
        if new_data:
            total_count = sum(len(df) for df in new_data.values())
            deps['logger'].info(f"✅ 총 {total_count}건 처리됨")
        else:
            deps['logger'].info("ℹ️  수집된 상장 정보 없음")
        
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
                # 로컬 파일 유지 (사용자 요청)
                # if output_path.exists():
                #     os.remove(output_path)
                #     deps['logger'].info(f"🗑️  임시 파일 삭제 완료")
                pass
                
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
