"""
일일 업데이트 커맨드
"""

import typer
from datetime import date, datetime
from typing import Optional
from config import config
from interface.cli.dependencies import build_dependencies
from interface.cli.drive_sync import sync_changed_years_to_drive


def daily_update(
    target_date: Optional[str] = typer.Option(
        None,
        "--date",
        "-d",
        help="대상 날짜 (YYYY-MM-DD 형식), 기본값: 오늘",
    ),
    headless: bool = typer.Option(
        config.HEADLESS, "--headless/--no-headless", help="헤드리스 모드"
    ),
    drive: bool = typer.Option(
        False, "--drive", help="변경된 연도의 Excel/DB를 Google Drive로 업로드"
    ),
):
    """
    일일 업데이트 (스케줄 실행용 - docker-compose의 crawler-cron 서비스가 매일 호출)

    과거 7일 + 당일 + 향후 3일의 IPO 데이터를 크롤링하여 SQLite 저장소(db/)에 upsert한 뒤,
    당해연도(1월이면 전년도까지) 데이터를 대상으로 OHLC 가격 백필을 수행합니다.

    Excel 내보내기: uv run crawler export-excel
    """
    # 날짜 파싱
    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            typer.echo(
                "❌ 날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 입력해주세요."
            )
            raise typer.Exit(code=1)
    else:
        parsed_date = date.today()

    deps = build_dependencies(headless=headless)

    try:
        deps["logger"].info("=" * 60)
        deps["logger"].info("📅 Stock Crawler - 일일 스케줄 업데이트")
        deps["logger"].info(f"기준 날짜: {parsed_date}")
        deps["logger"].info("수집 범위: 과거 7일 + 당일 + 향후 3일 (총 11일)")
        deps["logger"].info("=" * 60)

        deps["page_provider"].setup()
        result = deps["orchestrator"].run_daily(
            target_date=parsed_date, days_ahead=3, days_back=7
        )

        if result.collected_count:
            deps["logger"].info(f"✅ 총 {result.collected_count}건 SQLite 저장 완료")
        else:
            deps["logger"].info("ℹ️  수집된 상장 정보 없음")

        if drive and result.changed_years:
            deps["logger"].info(
                f"☁️  Drive 동기화 대상 연도: {sorted(result.changed_years)}"
            )
            sync_changed_years_to_drive(
                deps["repository"], result.changed_years, deps["logger"]
            )

        deps["logger"].info("🏁 일일 업데이트 완료")
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
