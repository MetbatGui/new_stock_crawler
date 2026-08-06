"""
Google Drive 저장소 어댑터 구현
"""

import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from core.ports.storage_ports import StoragePort
from config import config


class GoogleDriveAdapter(StoragePort):
    """
    Google Drive API를 사용한 파일 업로드 어댑터 (OAuth 2.0)
    """

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(
        self,
        client_secret_file: Optional[str] = None,
        token_file: Optional[str] = None,
        folder_id: Optional[str] = None,
    ):
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
            self._creds = Credentials.from_authorized_user_file(
                self.token_file, self.SCOPES
            )

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

        self._service = build("drive", "v3", credentials=self._creds)

    def ensure_authenticated(self) -> None:
        """인증을 시도하고 실패 시 예외를 그대로 raise한다 (연결 테스트/헬스체크 전용).

        다른 public 메서드(upload_file/list_files/...)는 실패를 삼키고 안전한
        값을 반환하지만, "지금 인증이 되는가"를 직접 확인하려는 호출자(auth/health
        커맨드)는 실패를 명확히 알아야 하므로 별도로 노출한다.
        """
        self._authenticate()

    def upload_file(
        self,
        local_path: Path,
        remote_filename: Optional[str] = None,
        parent_folder_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        파일을 Google Drive 폴더로 업로드 (이미 존재하면 덮어쓰기)

        Args:
            local_path: 로컬 파일 경로
            remote_filename: 저장할 파일명 (기본값: 로컬 파일명)
            parent_folder_id: 업로드할 상위 폴더 ID (기본값: self.folder_id 루트)

        Returns:
            Optional[str]: 업로드된 파일 ID. 인증/API 실패 시 None
            (로컬 파일이 없는 건 호출자 실수이므로 예외로 그대로 raise됨).
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"업로드할 파일을 찾을 수 없습니다: {local_path}")

        try:
            self._authenticate()
            assert self._service is not None

            file_name = remote_filename or local_path.name
            target_folder_id = parent_folder_id or self.folder_id

            # 1. 기존 파일 검색 (같은 폴더 내에서)
            # list_files는 실패 시 예외 대신 빈 리스트를 반환하므로, 중복 검색 자체가
            # 실패해도 업로드를 막지 않고 새 파일 생성으로 진행한다(드물게 중복 생성 가능).
            existing_files = self.list_files(
                f"name = '{file_name}'", folder_id=target_folder_id
            )

            media = MediaFileUpload(str(local_path), resumable=True)

            if existing_files:
                # 2. 덮어쓰기 (Update)
                file_id = existing_files[0]["id"]
                print(f"      [Google Drive] 기존 파일 업데이트 중... (ID: {file_id})")

                file = (
                    self._service.files()
                    .update(fileId=file_id, media_body=media, fields="id")
                    .execute()
                )

                print(
                    f"      [Google Drive] 업데이트 완료: {file_name} (ID: {file.get('id')})"
                )
                return file.get("id")

            else:
                # 3. 새로 만들기 (Create)
                print(f"      [Google Drive] 새 파일 업로드 중...: {file_name}")

                file_metadata = {
                    "name": file_name,
                    "parents": [target_folder_id] if target_folder_id else [],
                }

                file = (
                    self._service.files()
                    .create(body=file_metadata, media_body=media, fields="id")
                    .execute()
                )

                print(
                    f"      [Google Drive] 업로드 완료: {file_name} (ID: {file.get('id')})"
                )
                return file.get("id")
        except Exception as e:
            print(f"      [Google Drive] 업로드 실패: {local_path.name} - {e}")
            return None

    def get_or_create_subfolder(self, name: str) -> Optional[str]:
        """`self.folder_id` 하위에서 이름이 `name`인 폴더를 찾고, 없으면 생성해 ID를 반환.
        인증/API 실패 시 None."""
        try:
            self._authenticate()
            assert self._service is not None

            q = (
                f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder' "
                "and trashed = false"
            )
            if self.folder_id:
                q += f" and '{self.folder_id}' in parents"

            results = (
                self._service.files().list(q=q, fields="files(id, name)").execute()
            )
            found = results.get("files", [])
            if found:
                return found[0]["id"]

            metadata = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [self.folder_id] if self.folder_id else [],
            }
            folder = self._service.files().create(body=metadata, fields="id").execute()
            print(f"      [Google Drive] 서브폴더 생성: {name} (ID: {folder['id']})")
            return folder["id"]
        except Exception as e:
            print(f"      [Google Drive] 서브폴더 조회/생성 실패: {name} - {e}")
            return None

    def list_files(
        self, query: Optional[str] = None, folder_id: Optional[str] = None
    ) -> list:
        """
        파일 목록 조회 (페이지네이션 지원)

        Args:
            query: 검색 쿼리 (예: "name contains '신규상장종목'")
            folder_id: 조회할 상위 폴더 ID (기본값: self.folder_id 루트)

        Returns:
            list: 파일 메타데이터 리스트 [{'id': ..., 'name': ..., 'createdTime': ...}].
            인증/API 실패 시 빈 리스트.
        """
        try:
            self._authenticate()
            assert self._service is not None

            target_folder_id = folder_id or self.folder_id

            q = "trashed = false"
            if target_folder_id:
                q += f" and '{target_folder_id}' in parents"
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

            print(
                f"      [Google Drive] 파일 목록 조회 완료 (Query: {query}, Found: {len(all_files)}개)"
            )
            return all_files
        except Exception as e:
            print(f"      [Google Drive] 파일 목록 조회 실패: {e}")
            return []

    def download_file(self, file_id: str, local_path: Path) -> bool:
        """
        파일 다운로드

        Args:
            file_id: 다운로드할 파일 ID
            local_path: 저장할 로컬 경로

        Returns:
            bool: 다운로드 성공 여부
        """
        try:
            self._authenticate()
            assert self._service is not None

            request = self._service.files().get_media(fileId=file_id)

            with open(local_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

            print(f"      [Google Drive] 다운로드 완료: {local_path}")
            return True
        except Exception as e:
            print(f"      [Google Drive] 다운로드 실패: {file_id} - {e}")
            return False
