"""
파일 저장소 관련 포트 인터페이스
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List


class StoragePort(ABC):
    """
    파일 저장소 포트

    책임: 로컬 파일을 원격 저장소로 업로드/다운로드
    """

    @abstractmethod
    def upload_file(self, local_path: Path, remote_filename: str = None) -> str:
        """
        파일 업로드

        Args:
            local_path: 로컬 파일 경로
            remote_filename: 원격 저장소에 저장할 파일명 (None이면 로컬 파일명 사용)

        Returns:
            str: 업로드된 파일의 ID 또는 URL
        """
        pass

    @abstractmethod
    def list_files(self, query: str = None) -> List[dict]:
        """
        파일 목록 조회

        Args:
            query: 저장소별 검색 쿼리 문자열

        Returns:
            List[dict]: 파일 메타데이터 리스트 [{'id': ..., 'name': ...}, ...]
        """
        pass

    @abstractmethod
    def download_file(self, file_id: str, local_path: Path) -> None:
        """
        파일 다운로드

        Args:
            file_id: 다운로드할 파일 ID
            local_path: 저장할 로컬 경로
        """
        pass
