"""
유틸리티 관련 포트 인터페이스
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Dict


@dataclass(frozen=True)
class DateRange:
    """날짜 범위 값 객체"""
    year: int
    start_month: int
    end_month: int
    day_limit: int


class DateRangeCalculatorPort(ABC):
    """
    날짜 범위 계산 포트
    
    책임: 크롤링 날짜 범위 계산
    """
    
    @abstractmethod
    def calculate(self, start_year: int, reference_date: date) -> Dict[int, DateRange]:
        """
        연도별 크롤링 범위 계산
        
        Contract:
            반환되는 Dict의 키(연도) 순서는 반드시 오름차순이어야 합니다.
            호출자(CrawlerService 등)는 이 순서를 데이터 병합 순서로 신뢰합니다.
        """
        pass


class LoggerPort(ABC):
    """
    로깅 포트
    
    책임: 로그 출력
    """
    
    @abstractmethod
    def info(self, message: str) -> None:
        """정보 로그"""
        pass
    
    @abstractmethod
    def warning(self, message: str) -> None:
        """경고 로그"""
        pass
    
    @abstractmethod
    def error(self, message: str) -> None:
        """에러 로그"""
        pass
