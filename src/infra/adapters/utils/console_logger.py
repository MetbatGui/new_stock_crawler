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

    def __init__(self, name: str = "crawler") -> None:
        self._logger = logging.getLogger(name)

        # 핸들러 중복 추가 방지
        if not self._logger.handlers:
            self._configure_logger()

    def _configure_logger(self) -> None:
        """인스턴스별 로거 핸들러 설정"""

        level = _get_log_level()

        # Windows CP949 환경 이모지 출력 대비 UTF-8 설정
        # pytest 캡처 환경에서는 reconfigure가 없거나 실패할 수 있으므로 안전하게 처리
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)

        self._logger.setLevel(level)
        self._logger.addHandler(handler)
        self._logger.propagate = False

    def info(self, message: str) -> None:
        """정보 로그"""
        self._logger.info(message)

    def warning(self, message: str) -> None:
        """경고 로그"""
        self._logger.warning(message)

    def error(self, message: str) -> None:
        """에러 로그"""
        self._logger.error(message)
