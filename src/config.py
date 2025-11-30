from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    OUTPUT_DIR: Path = BASE_DIR / "output"

    # Web Scraping
    BASE_URL: str = "http://www.38.co.kr"
    HEADLESS: bool = True
    DEFAULT_TIMEOUT: int = 30000  # ms

    # Data Export
    EXCEL_FILENAME: str = "stock_data.xlsx"
    
    # Google Drive Integration
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "secrets/client_secret.json"
    GOOGLE_DRIVE_FOLDER_ID: str = ""  # .env에서 설정 필요
    
    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_output_path(self, filename: str = None) -> Path:
        """출력 파일의 전체 경로를 반환합니다."""
        if not self.OUTPUT_DIR.exists():
            self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        target_filename = filename or self.EXCEL_FILENAME
        return self.OUTPUT_DIR / target_filename

    def get_default_filename(self) -> str:
        """기본 파일명을 반환합니다 (고정값)."""
        return "신규상장종목.xlsx"

    def get_latest_output_file(self) -> Path:
        """output 디렉토리에서 대상 엑셀 파일을 반환합니다."""
        if not self.OUTPUT_DIR.exists():
            return None
        
        # 1. 고정 파일명 검색
        target_file = self.OUTPUT_DIR / self.get_default_filename()
        if target_file.exists():
            return target_file
            
        # 2. 구 포맷 검색 (하위 호환성 - 마이그레이션용)
        files = list(self.OUTPUT_DIR.glob("신규상장종목(*).xlsx"))
        if not files:
            files = list(self.OUTPUT_DIR.glob("stock_data*.xlsx"))
            
        if not files:
            return None
            
        # 수정 시간 기준 정렬
        return max(files, key=lambda p: p.stat().st_mtime)

# 전역 설정 객체
config = Settings()
