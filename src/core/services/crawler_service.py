"""
크롤링 비즈니스 로직 서비스
"""
from datetime import date
from typing import Dict, List
import pandas as pd

from core.ports.web_scraping_ports import PageProvider, CalendarScraperPort, DetailScraperPort
from core.ports.data_ports import DataMapperPort, DataExporterPort
from core.ports.utility_ports import DateRangeCalculatorPort, LoggerPort
from core.domain.models import StockInfo
from core.services.stock_price_enricher import StockPriceEnricher


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
        data_exporter: DataExporterPort,
        date_calculator: DateRangeCalculatorPort,
        stock_enricher: StockPriceEnricher,
        logger: LoggerPort
    ):
        # 모든 의존성을 생성자에서 받음 (명시적)
        self.page_provider = page_provider
        self.calendar_scraper = calendar_scraper
        self.detail_scraper = detail_scraper
        self.data_mapper = data_mapper
        self.data_exporter = data_exporter
        self.date_calculator = date_calculator
        self.stock_enricher = stock_enricher
        self.logger = logger
    
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
                today_day=date_range.day_limit
            )
            
            self.logger.info(
                f"[{year}년] {report.final_stock_count}개 종목 발견 "
                f"(스팩 {report.spack_filtered_count}개 제외)"
            )
            
            if not report.results:
                continue
            
            # 3-2. 상세 정보 수집
            stock_details = self.detail_scraper.scrape_details(
                page=page,
                stocks=report.results
            )
            
            # 3-2-1. 데이터 보강 (OHLC)
            enriched_details = [
                self.stock_enricher.enrich_stock_info(stock) 
                for stock in stock_details
            ]
            
            # 3-3. DataFrame 변환
            df = self.data_mapper.to_dataframe(enriched_details)
            
            if not df.empty:
                yearly_data[year] = df
                self.logger.info(f"[{year}년] {len(df)}건 수집 완료")
        
        # 4. 데이터 저장
        if yearly_data:
            self.data_exporter.export(yearly_data)
            self.logger.info("저장 완료")
        else:
            self.logger.warning("저장할 데이터 없음")
            
        return yearly_data
    
    def run_daily(self, target_date: date) -> Dict[int, pd.DataFrame]:
        """
        특정 날짜만 크롤링 (일일 업데이트용)
        
        Args:
            target_date: 크롤링할 날짜
            
        Returns:
            연도별 DataFrame 딕셔너리 (해당 날짜 데이터만)
        """
        year = target_date.year
        month = target_date.month
        day = target_date.day
        
        self.logger.info(f"[일일 업데이트] {target_date} 크롤링 시작")
        
        # Page 객체 준비
        page = self.page_provider.get_page()
        
        # 해당 월의 캘린더 조회 (day_limit로 해당 날짜까지만)
        report = self.calendar_scraper.scrape_calendar(
            page=page,
            year=year,
            start_month=month,
            end_month=month,
            today_day=day
        )
        
        if not report.results:
            self.logger.info(f"[{target_date}] 상장 예정 항목 없음")
            return {}
        
        self.logger.info(
            f"[{target_date}] {report.final_stock_count}개 종목 발견 "
            f"(스팩 {report.spack_filtered_count}개 제외)"
        )
        
        # 상세 정보 수집
        stock_details = self.detail_scraper.scrape_details(
            page=page,
            stocks=report.results
        )
        
        # 데이터 보강 (OHLC)
        enriched_details = [
            self.stock_enricher.enrich_stock_info(stock) 
            for stock in stock_details
        ]
        
        # DataFrame 변환
        df = self.data_mapper.to_dataframe(enriched_details)
        
        if not df.empty:
            yearly_data = {year: df}
            self.logger.info(f"[{target_date}] {len(df)}건 수집 완료")
            
            # 데이터 저장
            self.data_exporter.export(yearly_data)
            self.logger.info("저장 완료")
            
            return yearly_data
        else:
            self.logger.info(f"[{target_date}] 수집된 데이터 없음")
            return {}
