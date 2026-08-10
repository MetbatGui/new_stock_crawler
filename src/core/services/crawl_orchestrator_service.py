"""
크롤링 + 가격 백필 오케스트레이션 서비스
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Set

from core.services.crawler_service import CrawlerService
from core.services.enrichment_service import EnrichmentService
from core.ports.repository_ports import RepositoryPort
from core.ports.utility_ports import LoggerPort


@dataclass
class CrawlRunResult:
    """오케스트레이터 실행 결과"""

    collected_count: int
    changed_years: Set[int] = field(default_factory=set)


class CrawlOrchestratorService:
    """
    크롤링(CrawlerService)과 가격 백필(EnrichmentService)을 조합해 실행하는
    오케스트레이션 서비스.

    Drive 동기화 등 인프라 관심사는 포함하지 않는다 - 반환된 CrawlRunResult를
    보고 필요하면 인터페이스 계층(CLI)이 별도로 처리한다.
    """

    def __init__(
        self,
        crawler: CrawlerService,
        enrichment: EnrichmentService,
        repository: RepositoryPort,
        logger: LoggerPort,
    ):
        self.crawler = crawler
        self.enrichment = enrichment
        self.repository = repository
        self.logger = logger

    def run_full(self, start_year: int) -> CrawlRunResult:
        """전체 기간 크롤링 + 저장된 전체 연도 대상 가격 백필"""
        crawl_result = self.crawler.run(start_year=start_year)
        collected_count = sum(len(df) for df in crawl_result.values())

        # 저장된 전체 연도를 대상으로 OHLC 가격 백필 (DB 상태 기준으로 누락분만 채움)
        enriched_years = self.enrichment.enrich_data(self.repository.load_all())

        changed_years = set(crawl_result.keys()) | enriched_years
        return CrawlRunResult(
            collected_count=collected_count, changed_years=changed_years
        )

    def run_daily(
        self,
        target_date: date,
        days_ahead: int = 3,
        days_back: int = 7,
        today: Optional[date] = None,
    ) -> CrawlRunResult:
        """과거 N일+당일+N일 크롤링 + 당해연도(1월이면 전년도 포함) 가격 백필

        Args:
            target_date: 크롤링 기준 날짜
            days_ahead: 향후 며칠까지 수집할지
            days_back: 과거 며칠까지 재수집할지 (크론이 며칠 못 돈 경우 대비)
            today: 백필 대상 연도 판단 기준 (기본값 date.today(), 테스트용 주입 지점)
        """
        crawl_result = self.crawler.run_scheduled(
            start_date=target_date, days_ahead=days_ahead, days_back=days_back
        )
        collected_count = sum(len(df) for df in crawl_result.values())

        # 당해연도(1월이면 전년도 포함) OHLC 가격 백필 — DB 상태 기준으로 누락분만 채움
        anchor = today or date.today()
        backfill_years = [anchor.year]
        if anchor.month == 1:
            backfill_years.append(anchor.year - 1)
        backfill_data = {y: self.repository.load(y) for y in backfill_years}
        enriched_years = self.enrichment.enrich_data(backfill_data)

        changed_years = set(crawl_result.keys()) | enriched_years
        return CrawlRunResult(
            collected_count=collected_count, changed_years=changed_years
        )
