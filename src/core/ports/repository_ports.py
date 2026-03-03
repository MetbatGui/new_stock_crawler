"""
저장소 포트 인터페이스
"""
from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd


class RepositoryPort(ABC):
    """
    IPO 데이터 저장소 포트 (진실의 공급원)

    책임:
        - 연도별 IPO 데이터의 영구 저장 및 조회
        - upsert 시 (종목명, 상장일) 복합키 기준 중복 제거

    구현체 예: ParquetRepository
    """

    @abstractmethod
    def save(self, year: int, df: pd.DataFrame) -> None:
        """
        연도별 데이터를 저장소에 upsert

        Args:
            year: 저장 대상 연도
            df: 저장할 DataFrame (기존 데이터와 병합 후 중복 제거)
        """
        pass

    @abstractmethod
    def load(self, year: int) -> pd.DataFrame:
        """
        연도별 데이터 로드

        Args:
            year: 조회 대상 연도

        Returns:
            해당 연도 DataFrame. 데이터 없으면 빈 DataFrame.
        """
        pass

    @abstractmethod
    def load_all(self) -> Dict[int, pd.DataFrame]:
        """
        전체 연도 데이터 로드

        Returns:
            {연도: DataFrame} 딕셔너리
        """
        pass

    @abstractmethod
    def get_available_years(self) -> List[int]:
        """
        저장된 데이터가 있는 연도 목록 반환 (오름차순)
        """
        pass
