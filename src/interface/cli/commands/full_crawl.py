"""
전체 기간 크롤링 커맨드
"""

import typer
from datetime import date
from config import config
from interface.cli.dependencies import build_dependencies


def full_crawl(
    start_year: int = typer.Option(2020, "--start-year", "-s", help="크롤링 시작 연도"),
    headless: bool = typer.Option(
        config.HEADLESS, "--headless/--no-headless", help="헤드리스 모드"
    ),
):
    """
    전체 기간 크롤링 (초기 수집용)

    지정한 연도부터 현재까지의 모든 IPO 데이터를 수집하여
    SQLite 저장소(db/)에 저장한 뒤, 저장된 전체 연도를 대상으로 OHLC 가격 백필을 수행합니다.

    Excel 내보내기: uv run crawler export-excel
    """
    deps = build_dependencies(headless=headless)

    try:
        deps["logger"].info("=" * 60)
        deps["logger"].info("🚀 Stock Crawler - 전체 크롤링")
        deps["logger"].info(f"📅 기준 날짜: {date.today()}")
        deps["logger"].info(f"📆 크롤링 시작 연도: {start_year}년")
        deps["logger"].info("=" * 60)

        deps["page_provider"].setup()
        deps["crawler"].run(start_year=start_year)

        # 저장된 전체 연도를 대상으로 OHLC 가격 백필 (DB 상태 기준으로 누락분만 채움)
        deps["enrichment"].enrich_data(deps["repository"].load_all())

        deps["logger"].info("=" * 60)
        deps["logger"].info("🏁 크롤링 완료 → SQLite 저장됨")
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
