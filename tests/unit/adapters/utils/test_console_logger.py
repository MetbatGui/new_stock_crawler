"""
ConsoleLogger 단위 테스트
콘솔 로거 출력 검증
"""
import pytest
from unittest.mock import patch
from io import StringIO

from infra.adapters.utils.console_logger import ConsoleLogger


class TestConsoleLogger:
    """ConsoleLogger 단위 테스트"""
    
    @pytest.fixture
    def logger(self):
        """ConsoleLogger 인스턴스"""
        return ConsoleLogger()
    
    def test_info_message(self, logger):
        """info 메서드 테스트"""
        # Given
        message = "테스트 정보 메시지"
        
        # When/Then
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            logger.info(message)
            output = mock_stdout.getvalue()
            
            assert "[INFO]" in output
            assert message in output
    
    def test_warning_message(self, logger):
        """warning 메서드 테스트"""
        # Given
        message = "테스트 경고 메시지"
        
        # When/Then
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            logger.warning(message)
            output = mock_stdout.getvalue()
            
            assert "[WARNING]" in output
            assert message in output
    
    def test_error_message(self, logger):
        """error 메서드 테스트"""
        # Given
        message = "테스트 에러 메시지"
        
        # When/Then
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            logger.error(message)
            output = mock_stdout.getvalue()
            
            assert "[ERROR]" in output
            assert message in output
    
    def test_multiple_messages(self, logger):
        """여러 메시지 연속 출력 테스트"""
        # When/Then
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            logger.info("첫 번째")
            logger.warning("두 번째")
            logger.error("세 번째")
            
            output = mock_stdout.getvalue()
            
            assert "[INFO] 첫 번째" in output
            assert "[WARNING] 두 번째" in output
            assert "[ERROR] 세 번째" in output
    
    def test_empty_message(self, logger):
        """빈 메시지 테스트"""
        # When/Then
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            logger.info("")
            output = mock_stdout.getvalue()
            
            assert "[INFO]" in output
    
    def test_special_characters(self, logger):
        """특수 문자 포함 메시지 테스트"""
        # Given
        message = "테스트 🚀 메시지 with special chars: @#$%"
        
        # When/Then
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            logger.info(message)
            output = mock_stdout.getvalue()
            
            assert message in output
    
    def test_multiline_message(self, logger):
        """여러 줄 메시지 테스트"""
        # Given
        message = "첫 줄\n두 번째 줄\n세 번째 줄"
        
        # When/Then
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            logger.info(message)
            output = mock_stdout.getvalue()
            
            assert message in output
            assert "[INFO]" in output
