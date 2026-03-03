"""
ConsoleLogger 단위 테스트
logging 모듈 기반 출력 검증
"""
import logging
import pytest
from unittest.mock import patch

from infra.adapters.utils.console_logger import ConsoleLogger


class TestConsoleLogger:
    """ConsoleLogger 단위 테스트"""

    @pytest.fixture
    def logger(self):
        """ConsoleLogger 인스턴스 (고유 이름으로 핸들러 격리)"""
        # 각 테스트마다 격리된 logger 이름 사용
        import uuid
        return ConsoleLogger(name=f"test_{uuid.uuid4().hex[:8]}")

    def test_info_message(self, logger, caplog):
        """info 메서드 테스트"""
        with caplog.at_level(logging.INFO):
            logger.info("테스트 정보 메시지")
        assert "테스트 정보 메시지" in caplog.text

    def test_warning_message(self, logger, caplog):
        """warning 메서드 테스트"""
        with caplog.at_level(logging.WARNING):
            logger.warning("테스트 경고 메시지")
        assert "테스트 경고 메시지" in caplog.text

    def test_error_message(self, logger, caplog):
        """error 메서드 테스트"""
        with caplog.at_level(logging.ERROR):
            logger.error("테스트 에러 메시지")
        assert "테스트 에러 메시지" in caplog.text

    def test_multiple_messages(self, logger, caplog):
        """여러 메시지 연속 출력 테스트"""
        with caplog.at_level(logging.DEBUG):
            logger.info("첫 번째")
            logger.warning("두 번째")
            logger.error("세 번째")
        assert "첫 번째" in caplog.text
        assert "두 번째" in caplog.text
        assert "세 번째" in caplog.text

    def test_empty_message(self, logger, caplog):
        """빈 메시지 테스트"""
        with caplog.at_level(logging.INFO):
            logger.info("")
        # 빈 메시지도 로그 레코드 생성
        assert any(r.levelno == logging.INFO for r in caplog.records)

    def test_special_characters(self, logger, caplog):
        """특수 문자 포함 메시지 테스트"""
        message = "테스트 🚀 메시지 with special chars: @#$%"
        with caplog.at_level(logging.INFO):
            logger.info(message)
        assert message in caplog.text

    def test_multiline_message(self, logger, caplog):
        """여러 줄 메시지 테스트"""
        message = "첫 줄\n두 번째 줄\n세 번째 줄"
        with caplog.at_level(logging.INFO):
            logger.info(message)
        assert "첫 줄" in caplog.text
