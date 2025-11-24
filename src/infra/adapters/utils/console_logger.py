"""
콘솔 로거 어댑터
"""
from core.ports.utility_ports import LoggerPort


class ConsoleLogger(LoggerPort):
    """
    콘솔 출력 로거 구현
    
    단순히 print로 출력하는 구현
    향후 logging 모듈이나 다른 로거로 교체 가능
    """
    
    def info(self, message: str) -> None:
        """정보 로그"""
        print(f"[INFO] {message}")
    
    def warning(self, message: str) -> None:
        """경고 로그"""
        print(f"[WARNING] {message}")
    
    def error(self, message: str) -> None:
        """에러 로그"""
        print(f"[ERROR] {message}")
