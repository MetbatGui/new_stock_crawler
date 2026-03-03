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
