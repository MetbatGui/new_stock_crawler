"""
sync_changed_years_to_drive 단위 테스트

GoogleDriveAdapter/ExcelRenderer를 mock으로 격리해 오케스트레이션 로직만 검증.
"""

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from interface.cli.drive_sync import sync_changed_years_to_drive


@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.load.return_value = pd.DataFrame(
        {"종목명": ["주식A"], "상장일": ["2024-01-15"]}
    )
    return repo


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def drive_env(tmp_path, monkeypatch):
    """config.OUTPUT_DIR/DB_DIR를 임시 디렉토리로 바꾸고 db 파일을 미리 만들어둔다"""
    output_dir = tmp_path / "output"
    db_dir = tmp_path / "db"
    output_dir.mkdir()
    db_dir.mkdir()
    (db_dir / "2024.db").write_bytes(b"dummy")

    monkeypatch.setattr("interface.cli.drive_sync.config.OUTPUT_DIR", output_dir)
    monkeypatch.setattr("interface.cli.drive_sync.config.DB_DIR", db_dir)
    return {"output_dir": output_dir, "db_dir": db_dir}


class TestSyncChangedYearsToDrive:
    def test_empty_years_does_nothing(self, mock_repository, mock_logger):
        with patch("interface.cli.drive_sync.GoogleDriveAdapter") as mock_adapter_cls:
            result = sync_changed_years_to_drive(mock_repository, [], mock_logger)
            mock_adapter_cls.assert_not_called()
            assert result is True

    def test_uploads_excel_before_db(self, mock_repository, mock_logger, drive_env):
        """Excel을 먼저 올리고, 그 다음 db 파일을 db 서브폴더에 올려야 한다"""
        with (
            patch("interface.cli.drive_sync.GoogleDriveAdapter") as mock_adapter_cls,
            patch("interface.cli.drive_sync.ExcelRenderer") as mock_renderer_cls,
        ):
            mock_storage = mock_adapter_cls.return_value
            mock_storage.get_or_create_subfolder.return_value = "db_folder_id"
            mock_storage.upload_file.side_effect = ["excel_id", "db_id"]

            result = sync_changed_years_to_drive(mock_repository, {2024}, mock_logger)

            mock_renderer_cls.return_value.render.assert_called_once()
            assert mock_storage.upload_file.call_count == 2
            assert result is True

            # 1번째 호출: Excel (parent_folder_id 없음)
            first_call = mock_storage.upload_file.call_args_list[0]
            assert first_call.kwargs.get("parent_folder_id") is None

            # 2번째 호출: DB (db 서브폴더로)
            second_call = mock_storage.upload_file.call_args_list[1]
            assert second_call.kwargs.get("parent_folder_id") == "db_folder_id"

    def test_subfolder_failure_is_caught_and_does_not_raise(
        self, mock_repository, mock_logger, drive_env
    ):
        """db 서브폴더 조회/생성이 실패(None 반환)해도 예외 없이 반환되어야 한다
        (Excel 업로드는 이미 끝난 뒤). GoogleDriveAdapter는 인증/API 실패를
        내부에서 삼키고 None을 반환하는 계약이라 여기서는 실제로 예외가 나지 않음."""
        with (
            patch("interface.cli.drive_sync.GoogleDriveAdapter") as mock_adapter_cls,
            patch("interface.cli.drive_sync.ExcelRenderer"),
        ):
            mock_storage = mock_adapter_cls.return_value
            mock_storage.upload_file.return_value = "excel_id"
            mock_storage.get_or_create_subfolder.return_value = None

            result = sync_changed_years_to_drive(mock_repository, {2024}, mock_logger)

            mock_logger.error.assert_called()
            assert result is False

    def test_individual_upload_failure_does_not_stop_other_years(
        self, mock_repository, mock_logger, drive_env
    ):
        """한 연도의 업로드가 실패(None 반환)해도 나머지 연도는 계속 처리되어야 한다"""
        (drive_env["db_dir"] / "2025.db").write_bytes(b"dummy")

        with (
            patch("interface.cli.drive_sync.GoogleDriveAdapter") as mock_adapter_cls,
            patch("interface.cli.drive_sync.ExcelRenderer"),
        ):
            mock_storage = mock_adapter_cls.return_value
            mock_storage.get_or_create_subfolder.return_value = "db_folder_id"
            mock_storage.upload_file.side_effect = [
                None,
                "excel_id_2025",
                "db_id_2024",
                "db_id_2025",
            ]

            result = sync_changed_years_to_drive(mock_repository, {2024, 2025}, mock_logger)

            # 4번 모두 시도되어야 함 (2024 Excel 실패해도 2025 Excel, 두 연도 DB는 계속 진행)
            assert mock_storage.upload_file.call_count == 4
            mock_logger.error.assert_called()
            # 하나라도 실패했으면 전체 결과는 False여야 한다 - 호출부가 exit code를
            # 이걸로 결정한다(db_ssot_guide.md §6.2, docker_guide.md §10).
            assert result is False
