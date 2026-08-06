"""
GoogleDriveAdapter 단위 테스트

어댑터는 OAuth2 사용자 인증(token.json) 방식을 사용합니다.
인증 흐름과 API 호출을 mock으로 격리하여 테스트합니다.
"""

import pytest
from unittest.mock import MagicMock, patch

from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    """
    인증을 건너뛰고 mock service를 직접 주입한 어댑터
    """
    monkeypatch.setattr(
        "infra.adapters.storage.google_drive_adapter.config.GOOGLE_DRIVE_FOLDER_ID",
        "test_folder_id",
    )
    monkeypatch.setattr(
        "infra.adapters.storage.google_drive_adapter.config.GOOGLE_CLIENT_SECRET_FILE",
        str(tmp_path / "creds.json"),
    )
    monkeypatch.setattr(
        "infra.adapters.storage.google_drive_adapter.config.GOOGLE_TOKEN_FILE",
        str(tmp_path / "token.json"),
    )
    a = GoogleDriveAdapter()
    # _service를 mock으로 직접 주입하여 _authenticate 우회
    a._service = MagicMock()
    return a


class TestGoogleDriveAdapterEnsureAuthenticated:
    def test_ensure_authenticated_raises_on_failure(self, tmp_path, monkeypatch):
        """인증 실패 시 예외를 그대로 전파해야 한다 (list_files 등 다른 메서드와 달리
        삼키지 않음 — auth/health 커맨드의 연결 테스트가 이 시그널에 의존함)"""
        monkeypatch.setattr(
            "infra.adapters.storage.google_drive_adapter.config.GOOGLE_TOKEN_FILE",
            str(tmp_path / "missing_token.json"),
        )
        monkeypatch.setattr(
            "infra.adapters.storage.google_drive_adapter.config.GOOGLE_CLIENT_SECRET_FILE",
            str(tmp_path / "missing_creds.json"),
        )
        adapter = GoogleDriveAdapter()  # _service를 주입하지 않은 실제 인스턴스

        with pytest.raises(FileNotFoundError):
            adapter.ensure_authenticated()


class TestGoogleDriveAdapterUpload:
    def test_upload_file_success(self, adapter, tmp_path):
        """로컬 파일이 존재할 때 업로드가 성공해야 한다"""
        # Given: 실제 파일 생성
        local_file = tmp_path / "신규상장종목.xlsx"
        local_file.write_bytes(b"dummy content")

        # Given: 중복 검색 결과 없음, create 성공
        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.return_value = {"files": []}
        mock_files.create.return_value.execute.return_value = {"id": "new_file_id"}

        # When
        with patch("infra.adapters.storage.google_drive_adapter.MediaFileUpload"):
            file_id = adapter.upload_file(local_file)

        # Then
        assert file_id == "new_file_id"
        mock_files.create.assert_called_once()

        call_kwargs = mock_files.create.call_args.kwargs
        assert call_kwargs["body"]["name"] == "신규상장종목.xlsx"
        assert call_kwargs["body"]["parents"] == ["test_folder_id"]

    def test_upload_file_not_found(self, adapter, tmp_path):
        """로컬 파일이 없을 때 FileNotFoundError가 발생해야 한다"""
        missing = tmp_path / "missing.xlsx"

        with pytest.raises(FileNotFoundError):
            adapter.upload_file(missing)

    def test_upload_updates_existing_file(self, adapter, tmp_path):
        """같은 이름의 파일이 이미 있으면 update(덮어쓰기)를 호출해야 한다"""
        local_file = tmp_path / "신규상장종목.xlsx"
        local_file.write_bytes(b"updated content")

        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.return_value = {
            "files": [{"id": "existing_id", "name": "신규상장종목.xlsx"}]
        }
        mock_files.update.return_value.execute.return_value = {"id": "existing_id"}

        with patch("infra.adapters.storage.google_drive_adapter.MediaFileUpload"):
            file_id = adapter.upload_file(local_file)

        assert file_id == "existing_id"
        mock_files.update.assert_called_once()
        mock_files.create.assert_not_called()

    def test_upload_file_returns_none_on_api_failure(self, adapter, tmp_path):
        """Drive API 호출이 예외를 던져도 그대로 raise하지 않고 None을 반환해야 한다"""
        local_file = tmp_path / "신규상장종목.xlsx"
        local_file.write_bytes(b"dummy content")

        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.return_value = {"files": []}
        mock_files.create.return_value.execute.side_effect = Exception("API 오류")

        with patch("infra.adapters.storage.google_drive_adapter.MediaFileUpload"):
            file_id = adapter.upload_file(local_file)

        assert file_id is None


class TestGoogleDriveAdapterSubfolder:
    def test_upload_file_with_parent_folder_id_uses_that_folder(
        self, adapter, tmp_path
    ):
        """parent_folder_id를 지정하면 self.folder_id 대신 그 폴더로 업로드해야 한다"""
        local_file = tmp_path / "2025.db"
        local_file.write_bytes(b"dummy")

        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.return_value = {"files": []}
        mock_files.create.return_value.execute.return_value = {"id": "db_file_id"}

        with patch("infra.adapters.storage.google_drive_adapter.MediaFileUpload"):
            file_id = adapter.upload_file(local_file, parent_folder_id="db_folder_id")

        assert file_id == "db_file_id"
        call_kwargs = mock_files.create.call_args.kwargs
        assert call_kwargs["body"]["parents"] == ["db_folder_id"]

    def test_get_or_create_subfolder_returns_existing(self, adapter):
        """같은 이름의 폴더가 이미 있으면 새로 만들지 않고 그 ID를 반환해야 한다"""
        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.return_value = {
            "files": [{"id": "existing_folder_id", "name": "db"}]
        }

        folder_id = adapter.get_or_create_subfolder("db")

        assert folder_id == "existing_folder_id"
        mock_files.create.assert_not_called()

    def test_get_or_create_subfolder_creates_when_missing(self, adapter):
        """같은 이름의 폴더가 없으면 새로 생성해야 한다"""
        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.return_value = {"files": []}
        mock_files.create.return_value.execute.return_value = {"id": "new_folder_id"}

        folder_id = adapter.get_or_create_subfolder("db")

        assert folder_id == "new_folder_id"
        call_kwargs = mock_files.create.call_args.kwargs
        assert call_kwargs["body"]["mimeType"] == "application/vnd.google-apps.folder"
        assert call_kwargs["body"]["name"] == "db"

    def test_get_or_create_subfolder_returns_none_on_api_failure(self, adapter):
        """Drive API 호출이 예외를 던져도 None을 반환해야 한다"""
        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.side_effect = Exception("API 오류")

        folder_id = adapter.get_or_create_subfolder("db")

        assert folder_id is None


class TestGoogleDriveAdapterListFiles:
    def test_list_files_returns_all_pages(self, adapter):
        """페이지네이션 처리로 전체 파일 목록을 반환해야 한다"""
        page1 = {"files": [{"id": "1", "name": "a.xlsx"}], "nextPageToken": "tok"}
        page2 = {"files": [{"id": "2", "name": "b.xlsx"}]}

        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.side_effect = [page1, page2]

        result = adapter.list_files()

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    def test_list_files_empty(self, adapter):
        """파일이 없을 때 빈 리스트를 반환해야 한다"""
        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.return_value = {"files": []}

        result = adapter.list_files()
        assert result == []

    def test_list_files_returns_empty_on_api_failure(self, adapter):
        """Drive API 호출이 예외를 던져도 빈 리스트를 반환해야 한다"""
        mock_files = adapter._service.files.return_value
        mock_files.list.return_value.execute.side_effect = Exception("API 오류")

        result = adapter.list_files()
        assert result == []


class TestGoogleDriveAdapterDownload:
    def test_download_file_returns_false_on_api_failure(self, adapter, tmp_path):
        """Drive API 호출이 예외를 던져도 False를 반환해야 한다"""
        mock_files = adapter._service.files.return_value
        mock_files.get_media.side_effect = Exception("API 오류")

        result = adapter.download_file("some_id", tmp_path / "out.xlsx")
        assert result is False
