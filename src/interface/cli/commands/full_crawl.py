"""
전체 기간 크롤링 커맨드
"""

import typer
from datetime import date
from config import config
from interface.cli.dependencies import build_dependencies
from interface.cli.drive_sync import sync_changed_years_to_drive


def full_crawl(
    start_year: int = typer.Option(2020, "--start-year", "-s", help="크롤링 시작 연도"),
    headless: bool = typer.Option(
        config.HEADLESS, "--headless/--no-headless", help="헤드리스 모드"
    ),
    drive: bool = typer.Option(
        False, "--drive", help="변경된 연도의 Excel/DB를 Google Drive로 업로드"
    ),
):
    """
    전체 기간 크롤링 (초기 수집용)

    지정한 연도부터 현재까지의 모든 IPO 데이터를 수집하여
    SQLite 저장소(db/)에 저장한 뒤, 저장된 전체 연도를 대상으로 OHLC 가격 백필을 수행합니다.

    Excel 내보내기: uv run crawler export-excel
    """
    deps = build_dependencies(headless=headless)
    drive_sync_ok = True

    try:
        deps["logger"].info("=" * 60)
        deps["logger"].info("🚀 Stock Crawler - 전체 크롤링")
        deps["logger"].info(f"📅 기준 날짜: {date.today()}")
        deps["logger"].info(f"📆 크롤링 시작 연도: {start_year}년")
        deps["logger"].info("=" * 60)

        deps["page_provider"].setup()
        result = deps["orchestrator"].run_full(start_year=start_year)

        if drive and result.changed_years:
            deps["logger"].info(
                f"☁️  Drive 동기화 대상 연도: {sorted(result.changed_years)}"
            )
            drive_sync_ok = sync_changed_years_to_drive(
                deps["repository"], result.changed_years, deps["logger"]
            )

        deps["logger"].info("=" * 60)
        deps["logger"].info(
            f"🏁 크롤링 완료 → SQLite 저장됨 ({result.collected_count}건 신규 수집)"
        )
        deps["logger"].info("💡 Excel 내보내기: uv run crawler export-excel")
        deps["logger"].info("=" * 60)

    except KeyboardInterrupt:
        deps["logger"].warning("\n⚠️  사용자에 의해 중단되었습니다")
    except Exception as e:
        deps["logger"].error(f"❌ 크롤링 중 오류 발생: {e}")
        raise
    finally:
        deps["page_provider"].cleanup()
        deps["logger"].info("\n✅ 리소스 정리 완료")

    if not drive_sync_ok:
        # 로컬은 항상 불신의 대상이라(db_ssot_guide.md §6.2) 다음 실행이 Drive를 무조건
        # 다시 받아 로컬을 덮어쓴다 - 지금 업로드 안 된 로컬 변경분은 그때 사라진다.
        deps["logger"].error("❌ Drive 업로드 실패 - 다음 실행 전에 재시도 필요")
        raise typer.Exit(code=1)
