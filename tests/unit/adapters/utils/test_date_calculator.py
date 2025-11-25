"""
DateRangeCalculator 단위 테스트
날짜 범위 계산 로직 검증
"""
import pytest
from datetime import date

from infra.adapters.utils.date_calculator import DateCalculator
from core.ports.utility_ports import DateRange


class TestDateCalculator:
    """DateCalculator 단위 테스트"""
    
    @pytest.fixture
    def calculator(self):
        """DateCalculator 인스턴스"""
        return DateCalculator()
    
    def test_single_past_year(self, calculator):
        """과거 단일 연도 계산"""
        # Given
        start_year = 2023
        reference_date = date(2025, 11, 26)
        
        # When
        result = calculator.calculate(start_year, reference_date)
        
        # Then
        assert len(result) == 3  # 2023, 2024, 2025
        
        # 2023년 (과거)
        assert result[2023].year == 2023
        assert result[2023].start_month == 1
        assert result[2023].end_month == 12
        assert result[2023].day_limit == 32
        
        # 2024년 (과거)
        assert result[2024].year == 2024
        assert result[2024].start_month == 1
        assert result[2024].end_month == 12
        assert result[2024].day_limit == 32
        
        # 2025년 (현재)
        assert result[2025].year == 2025
        assert result[2025].start_month == 1
        assert result[2025].end_month == 11
        assert result[2025].day_limit == 26
    
    def test_current_year_only(self, calculator):
        """현재 연도만 계산"""
        # Given
        start_year = 2025
        reference_date = date(2025, 11, 26)
        
        # When
        result = calculator.calculate(start_year, reference_date)
        
        # Then
        assert len(result) == 1
        assert result[2025].year == 2025
        assert result[2025].start_month == 1
        assert result[2025].end_month == 11
        assert result[2025].day_limit == 26
    
    def test_current_year_january(self, calculator):
        """1월의 현재 연도"""
        # Given
        start_year = 2025
        reference_date = date(2025, 1, 15)
        
        # When
        result = calculator.calculate(start_year, reference_date)
        
        # Then
        assert len(result) == 1
        assert result[2025].year == 2025
        assert result[2025].start_month == 1
        assert result[2025].end_month == 1
        assert result[2025].day_limit == 15
    
    def test_current_year_december(self, calculator):
        """12월의 현재 연도"""
        # Given
        start_year = 2025
        reference_date = date(2025, 12, 31)
        
        # When
        result = calculator.calculate(start_year, reference_date)
        
        # Then
        assert len(result) == 1
        assert result[2025].year == 2025
        assert result[2025].start_month == 1
        assert result[2025].end_month == 12
        assert result[2025].day_limit == 31
    
    def test_multiple_past_years(self, calculator):
        """여러 과거 연도 계산"""
        # Given
        start_year = 2020
        reference_date = date(2025, 6, 15)
        
        # When
        result = calculator.calculate(start_year, reference_date)
        
        # Then
        assert len(result) == 6  # 2020 ~ 2025
        
        # 모든 과거 연도는 전체 연도
        for year in range(2020, 2025):
            assert result[year].year == year
            assert result[year].start_month == 1
            assert result[year].end_month == 12
            assert result[year].day_limit == 32
        
        # 현재 연도만 제한됨
        assert result[2025].year == 2025
        assert result[2025].start_month == 1
        assert result[2025].end_month == 6
        assert result[2025].day_limit == 15
    
    def test_daterange_dataclass(self):
        """DateRange 데이터클래스 테스트"""
        # Given
        date_range = DateRange(
            year=2024,
            start_month=1,
            end_month=12,
            day_limit=32
        )
        
        # Then
        assert date_range.year == 2024
        assert date_range.start_month == 1
        assert date_range.end_month == 12
        assert date_range.day_limit == 32
    
    def test_year_boundary(self, calculator):
        """연도 경계 케이스"""
        # Given: 연초
        start_year = 2024
        reference_date = date(2025, 1, 1)
        
        # When
        result = calculator.calculate(start_year, reference_date)
        
        # Then
        assert len(result) == 2
        assert result[2024].end_month == 12
        assert result[2025].end_month == 1
        assert result[2025].day_limit == 1
    
    def test_result_keys_order(self, calculator):
        """결과 딕셔너리 키 순서 확인"""
        # Given
        start_year = 2022
        reference_date = date(2024, 5, 10)
        
        # When
        result = calculator.calculate(start_year, reference_date)
        
        # Then
        keys = list(result.keys())
        assert keys == [2022, 2023, 2024]
