"""
Google Drive 저장소 어댑터 구현
"""
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from core.ports.storage_ports import StoragePort
from config import config


class GoogleDriveAdapter(StoragePort):
    """
    Google Drive API를 사용한 파일 업로드 어댑터 (OAuth 2.0)
    """
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, client_secret_file: str = None, token_file: str = None, folder_id: str = None):
        self.client_secret_file = client_secret_file or config.GOOGLE_CLIENT_SECRET_FILE
        self.token_file = token_file or config.GOOGLE_TOKEN_FILE
        self.folder_id = folder_id or config.GOOGLE_DRIVE_FOLDER_ID
        self._service = None
        self._creds = None
        
    def _authenticate(self):
        """Google Drive API 인증 및 서비스 생성 (OAuth 2.0)"""
        if self._service:
            return

        # 1. 토큰 파일 로드
        if os.path.exists(self.token_file):
            self._creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
            
        # 2. 유효성 검사 및 갱신
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                try:
                    self._creds.refresh(Request())
                except Exception as e:
                    print(f"      [Google Drive] 토큰 갱신 실패, 재인증 필요: {e}")
                    self._creds = None
            
            # 토큰이 없거나 갱신 실패 시, 여기서는 자동으로 브라우저를 띄우지 않습니다.
            # (CLI 실행 중 불필요한 브라우저 팝업 방지 및 헤드리스 환경 고려)
            # 사용자가 명시적으로 'auth' 커맨드를 실행해야 합니다.
            
            if not self._creds:
                 raise FileNotFoundError(
                     f"유효한 인증 토큰이 없습니다. 'just auth' 또는 'uv run crawler auth'를 실행하여 인증을 진행해주세요.\n"
                     f"토큰 파일 경로: {self.token_file}"
                 )
            
        self._service = build('drive', 'v3', credentials=self._creds)

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
        파일 목록 조회 (페이지네이션 지원)

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

        all_files = []
        page_token = None

        while True:
            kwargs: dict = {
                "q": q,
                "pageSize": 100,
                "fields": "nextPageToken, files(id, name, createdTime)",
                "orderBy": "createdTime desc",
            }
            if page_token:
                kwargs["pageToken"] = page_token

            results = self._service.files().list(**kwargs).execute()
            all_files.extend(results.get("files", []))

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        print(f"      [Google Drive] 파일 목록 조회 완료 (Query: {query}, Found: {len(all_files)}개)")
        return all_files


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
