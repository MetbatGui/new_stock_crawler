"""
Google Drive 저장소 어댑터 구현
"""
import os
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from core.ports.storage_ports import StoragePort
from config import config


class GoogleDriveAdapter(StoragePort):
    """
    Google Drive API를 사용한 파일 업로드 어댑터
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, service_account_file: str = None, folder_id: str = None):
        self.service_account_file = service_account_file or config.GOOGLE_SERVICE_ACCOUNT_FILE
        self.folder_id = folder_id or config.GOOGLE_DRIVE_FOLDER_ID
        self._service = None
        
    def _authenticate(self):
        """Google Drive API 인증 및 서비스 생성 (Lazy Loading)"""
        if self._service:
            return

        if not os.path.exists(self.service_account_file):
            raise FileNotFoundError(f"인증 파일을 찾을 수 없습니다: {self.service_account_file}")

        # 1. 서비스 계정 시도
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.service_account_file, scopes=self.SCOPES
            )
        except ValueError:
            # 2. OAuth 2.0 클라이언트 시크릿 시도 (fallback)
            # 주의: 이 경우 사용자 인터랙션이 필요할 수 있음.
            # 여기서는 일단 서비스 계정으로 가정하고 실패 시 에러 메시지 개선
            raise ValueError(f"잘못된 인증 파일 형식입니다. 서비스 계정 키 파일(JSON)이어야 합니다: {self.service_account_file}")
            
        self._service = build('drive', 'v3', credentials=creds)

    def upload_file(self, local_path: Path, remote_filename: str = None) -> str:
        """
        파일을 Google Drive 폴더로 업로드 (이미 존재하면 덮어쓰기)
        
        Args:
            local_path: 로컬 파일 경로
            remote_filename: 저장할 파일명 (기본값: 로컬 파일명)
            
        Returns:
            str: 업로드된 파일 ID
        """
        self._authenticate()
        
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"업로드할 파일을 찾을 수 없습니다: {local_path}")
            
        file_name = remote_filename or local_path.name
        
        # 1. 기존 파일 검색
        existing_files = self.list_files(f"name = '{file_name}'")
        
        media = MediaFileUpload(
            str(local_path),
            resumable=True
        )
        
        if existing_files:
            # 2. 덮어쓰기 (Update)
            file_id = existing_files[0]['id']
            print(f"      [Google Drive] 기존 파일 업데이트 중... (ID: {file_id})")
            
            file = self._service.files().update(
                fileId=file_id,
                media_body=media,
                fields='id'
            ).execute()
            
            print(f"      [Google Drive] 업데이트 완료: {file_name} (ID: {file.get('id')})")
            return file.get('id')
            
        else:
            # 3. 새로 만들기 (Create)
            print(f"      [Google Drive] 새 파일 업로드 중...: {file_name}")
            
            file_metadata = {
                'name': file_name,
                'parents': [self.folder_id] if self.folder_id else []
            }
            
            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            print(f"      [Google Drive] 업로드 완료: {file_name} (ID: {file.get('id')})")
            return file.get('id')

    def list_files(self, query: str = None) -> list:
        """
        파일 목록 조회
        
        Args:
            query: 검색 쿼리 (예: "name contains '신규상장종목'")
            
        Returns:
            list: 파일 메타데이터 리스트 [{'id': ..., 'name': ..., 'createdTime': ...}]
        """
        self._authenticate()
        
        q = "trashed = false"
        if self.folder_id:
            q += f" and '{self.folder_id}' in parents"
        if query:
            q += f" and ({query})"
            
        results = self._service.files().list(
            q=q,
            pageSize=10,
            fields="nextPageToken, files(id, name, createdTime)",
            orderBy="createdTime desc"
        ).execute()
        
        return results.get('files', [])

    def download_file(self, file_id: str, local_path: Path) -> None:
        """
        파일 다운로드
        
        Args:
            file_id: 다운로드할 파일 ID
            local_path: 저장할 로컬 경로
        """
        self._authenticate()
        
        request = self._service.files().get_media(fileId=file_id)
        
        with open(local_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
        print(f"      [Google Drive] 다운로드 완료: {local_path}")
