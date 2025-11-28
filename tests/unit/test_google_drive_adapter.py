import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from infra.adapters.storage.google_drive_adapter import GoogleDriveAdapter

@pytest.fixture
def mock_config():
    with patch('infra.adapters.storage.google_drive_adapter.config') as mock:
        mock.GOOGLE_SERVICE_ACCOUNT_FILE = "dummy_service_account.json"
        mock.GOOGLE_DRIVE_FOLDER_ID = "dummy_folder_id"
        yield mock

@pytest.fixture
def adapter(mock_config):
    return GoogleDriveAdapter()

@patch('infra.adapters.storage.google_drive_adapter.build')
@patch('infra.adapters.storage.google_drive_adapter.service_account.Credentials')
@patch('os.path.exists')
def test_upload_file_success(mock_exists, mock_creds, mock_build, adapter):
    # Arrange
    mock_exists.return_value = True  # 파일 존재함
    
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    
    mock_files = MagicMock()
    mock_service.files.return_value = mock_files
    
    mock_create = MagicMock()
    mock_files.create.return_value = mock_create
    mock_create.execute.return_value = {'id': 'uploaded_file_id'}
    
    local_path = Path("test_file.xlsx")
    
    # Act
    file_id = adapter.upload_file(local_path)
    
    # Assert
    assert file_id == 'uploaded_file_id'
    mock_files.create.assert_called_once()
    
    # 호출 인자 검증
    call_args = mock_files.create.call_args
    assert call_args.kwargs['body']['name'] == "test_file.xlsx"
    assert call_args.kwargs['body']['parents'] == ["dummy_folder_id"]

@patch('os.path.exists')
def test_upload_file_not_found(mock_exists, adapter):
    # Arrange
    mock_exists.side_effect = lambda p: p != Path("non_existent_file.xlsx") # 서비스 계정 파일은 존재한다고 가정
    
    # Act & Assert
    with pytest.raises(FileNotFoundError):
        adapter.upload_file(Path("non_existent_file.xlsx"))
