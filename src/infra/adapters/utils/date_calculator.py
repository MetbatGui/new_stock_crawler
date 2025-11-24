"""
날짜 범위 계산 어댑터
"""
from datetime import date
from typing import Dict

from core.ports.utility_ports import DateRangeCalculatorPort, DateRange


class DateCalculator(DateRangeCalculatorPort):
    """
    크롤링 날짜 범위 계산 구현
    
    비즈니스 룰:
    - 현재 연도는 오늘까지만
    - 과거 연도는 전체 연도
    """
    
    def calculate(self, start_year: int, reference_date: date) -> Dict[int, DateRange]:
        """연도별 크롤링 범위 계산"""
        ranges = {}
        current_year = reference_date.year
        
        for year in range(start_year, current_year + 1):
            if year == current_year:
                # 현재 연도: 1월 ~ 현재 월, 현재 일까지
                ranges[year] = DateRange(
                    year=year,
                    start_month=1,
                    end_month=reference_date.month,
                    day_limit=reference_date.day
                )
            else:
                # 과거 연도: 전체
                ranges[year] = DateRange(
                    year=year,
                    start_month=1,
                    end_month=12,
                    day_limit=32
                )
        
        return ranges
