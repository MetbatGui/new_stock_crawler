"""
크롤링 비즈니스 로직 서비스
"""

from datetime import date, timedelta
from typing import Dict
import pandas as pd

from core.ports.web_scraping_ports import (
    PageProvider,
    CalendarScraperPort,
    DetailScraperPort,
)
from core.ports.data_ports import DataMapperPort
from core.ports.repository_ports import RepositoryPort
from core.ports.utility_ports import (
    DateRangeCalculatorPort,
    LoggerPort,
    TradingCalendarPort,
)


class CrawlerService:
    """
    크롤링 워크플로우 오케스트레이션

    원칙 준수:
    - 포트만 의존 (어댑터 직접 참조 X)
    - 비즈니스 로직만 포함
    - 모든 의존성을 명시적으로 주입받음
    """

    def __init__(
        self,
        page_provider: PageProvider,
        calendar_scraper: CalendarScraperPort,
        detail_scraper: DetailScraperPort,
        data_mapper: DataMapperPort,
        repository: RepositoryPort,
        date_calculator: DateRangeCalculatorPort,
        logger: LoggerPort,
        trading_calendar: TradingCalendarPort,
    ):
        # 모든 의존성을 생성자에서 받음 (명시적)
        self.page_provider = page_provider
        self.calendar_scraper = calendar_scraper
        self.detail_scraper = detail_scraper
        self.data_mapper = data_mapper
        self.repository = repository
        self.date_calculator = date_calculator
        self.logger = logger
        self.trading_calendar = trading_calendar

    def run(self, start_year: int) -> Dict[int, pd.DataFrame]:
        """
        크롤링 실행

        흐름:
        1. 날짜 범위 계산
        2. 연도별 크롤링
        3. 데이터 저장
        """
        self.logger.info("크롤링 시작")

        # 1. 날짜 범위 계산 (비즈니스 로직)
        date_ranges = self.date_calculator.calculate(start_year, date.today())

        # 2. Page 객체 준비
        page = self.page_provider.get_page()

        # 3. 연도별 크롤링
        yearly_data: Dict[int, pd.DataFrame] = {}

        for year, date_range in date_ranges.items():
            self.logger.info(f"[{year}년] 크롤링 시작")

            # 3-1. 캘린더에서 IPO 목록 수집
            report = self.calendar_scraper.scrape_calendar(
                page=page,
                year=year,
                start_month=date_range.start_month,
                end_month=date_range.end_month,
                today_day=date_range.day_limit,
            )

            self.logger.info(
                f"[{year}년] {report.final_stock_count}개 종목 발견 "
                f"(스팩 {report.spack_filtered_count}개 제외)"
            )

            if not report.results:
                continue

            # 3-2. 상세 정보 수집
            stock_details = self.detail_scraper.scrape_details(
                page=page, stocks=report.results
            )

            # 3-3. DataFrame 변환 (OHLC 보강은 EnrichmentService가 별도 백필 단계에서 수행)
            df = self.data_mapper.to_dataframe(stock_details)

            if not df.empty:
                yearly_data[year] = df
                self.logger.info(f"[{year}년] {len(df)}건 수집 완료")

        # 4. 데이터 저장 (SQLite upsert)
        if yearly_data:
            for year, df in yearly_data.items():
                self.repository.save(year, df)
            self.logger.info("저장 완료")
        else:
            self.logger.warning("저장할 데이터 없음")

        return yearly_data

    def run_scheduled(
        self, start_date: date, days_ahead: int = 3, days_back: int = 0
    ) -> Dict[int, pd.DataFrame]:
        """
        일일 스케줄 크롤링 (과거 N일 + 당일 + 향후 N일)

        Args:
            start_date: 기준 날짜 (보통 오늘)
            days_ahead: 향후 며칠까지 수집할지 (기본 3일)
            days_back: 과거 며칠까지 재수집할지 (기본 0일 - 크론이 며칠 못 돈 경우
                대비한 백필. upsert가 종목명 기준 dedup이라 중복 수집해도 안전함)

        Returns:
            연도별 DataFrame 딕셔너리
        """

        self.logger.info(
            f"[스케줄 크롤링] {start_date} 기준 -{days_back}일 ~ +{days_ahead}일 수집 시작"
        )

        # Page 객체 준비
        page = self.page_provider.get_page()

        # 수집할 날짜 리스트 생성 (주말/공휴일 등 비거래일은 IPO 상장이 있을 수
        # 없으므로 제외 - 캘린더 페이지 조회 자체를 건너뛰어 낭비 방지)
        all_dates = [
            start_date + timedelta(days=i)
            for i in range(-days_back, days_ahead + 1)
        ]
        target_dates = [d for d in all_dates if self.trading_calendar.is_trading_day(d)]
        skipped = len(all_dates) - len(target_dates)
        if skipped:
            self.logger.info(f"[스케줄 크롤링] 비거래일 {skipped}일 제외")

        from collections import defaultdict

        year_frames: Dict[int, list] = defaultdict(list)
        total_collected = 0

        for target_date in target_dates:
            year = target_date.year
            month = target_date.month
            day = target_date.day

            # 해당 월의 캘린더 조회
            report = self.calendar_scraper.scrape_calendar(
                page=page,
                year=year,
                start_month=month,
                end_month=month,
                today_day=day,
                start_day=day,
            )

            if not report.results:
                continue

            self.logger.info(
                f"[{target_date}] {report.final_stock_count}개 종목 발견 "
                f"(스팩 {report.spack_filtered_count}개 제외)"
            )

            # 상세 정보 수집
            stock_details = self.detail_scraper.scrape_details(
                page=page, stocks=report.results
            )

            # DataFrame 변환 (OHLC 보강은 EnrichmentService가 별도 백필 단계에서 수행)
            df = self.data_mapper.to_dataframe(stock_details)

            if not df.empty:
                year_frames[year].append(df)

                total_collected += len(df)
                self.logger.info(f"[{target_date}] {len(df)}건 처리 완료")

        # 데이터 병합 및 저장 (SQLite upsert)
        yearly_data: Dict[int, pd.DataFrame] = {}
        if year_frames:
            for year, dfs in year_frames.items():
                yearly_data[year] = pd.concat(dfs, ignore_index=True)
                self.repository.save(year, yearly_data[year])
            self.logger.info(f"총 {total_collected}건 저장 완료")
        else:
            self.logger.info("수집된 데이터 없음")

        return yearly_data
