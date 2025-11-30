import typer
import os
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
