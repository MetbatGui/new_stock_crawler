"""
콘솔 로거 어댑터
"""
import logging
import sys

from core.ports.utility_ports import LoggerPort


def _get_log_level() -> int:
    """config 순환 임포트 방지를 위해 지연 로드로 LOG_LEVEL 반환"""
    try:
        from config import config  # noqa: PLC0415
        return getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    except Exception:
        return logging.INFO


class ConsoleLogger(LoggerPort):
    """
    Python 표준 logging 기반 콘솔 로거

    - 타임스탬프, 레벨, 메시지 포맷 출력
    - LOG_LEVEL 환경변수로 레벨 제어 가능
    - 향후 파일 핸들러/구조화 로거로 교체 가능
    """

    _root_logger_configured: bool = False

    def __init__(self, name: str = "crawler") -> None:
        self._logger = logging.getLogger(name)

        if not ConsoleLogger._root_logger_configured:
            self._configure_root()
            ConsoleLogger._root_logger_configured = True

    @staticmethod
    def _configure_root() -> None:
        """루트 로거 핸들러 설정 (1회만 실행)"""
        level = _get_log_level()

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)

        root = logging.getLogger()
        root.setLevel(level)
        # 핸들러 중복 추가 방지
        if not root.handlers:
            root.addHandler(handler)

    def info(self, message: str) -> None:
        """정보 로그"""
        self._logger.info(message)

    def warning(self, message: str) -> None:
        """경고 로그"""
        self._logger.warning(message)

    def error(self, message: str) -> None:
        """에러 로그"""
        self._logger.error(message)
