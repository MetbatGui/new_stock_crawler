"""
파일 저장소 관련 포트 인터페이스
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class StoragePort(ABC):
    """
    파일 저장소 포트

    책임: 로컬 파일을 원격 저장소로 업로드/다운로드

    계약: 구현체는 인증/네트워크/API 실패를 내부에서 처리하고 실패를 나타내는
    값(None/False/빈 리스트)을 반환해야 한다 (예외를 그대로 raise하지 않음).
    호출자 실수(예: 존재하지 않는 로컬 파일 경로)는 예외로 raise해도 된다.
    """

    @abstractmethod
    def upload_file(
        self,
        local_path: Path,
        remote_filename: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        파일 업로드

        Args:
            local_path: 로컬 파일 경로
            remote_filename: 원격 저장소에 저장할 파일명 (None이면 로컬 파일명 사용)
            parent_folder_id: 업로드할 상위 폴더 ID (None이면 기본 루트 폴더)

        Returns:
            Optional[str]: 업로드된 파일의 ID 또는 URL. 실패 시 None.
        """
        pass

    @abstractmethod
    def list_files(self, query: Optional[str] = None) -> List[dict]:
        """
        파일 목록 조회

        Args:
            query: 저장소별 검색 쿼리 문자열

        Returns:
            List[dict]: 파일 메타데이터 리스트 [{'id': ..., 'name': ...}, ...].
            실패 시 빈 리스트.
        """
        pass

    @abstractmethod
    def download_file(self, file_id: str, local_path: Path) -> bool:
        """
        파일 다운로드

        Args:
            file_id: 다운로드할 파일 ID
            local_path: 저장할 로컬 경로

        Returns:
            bool: 다운로드 성공 여부
        """
        pass
