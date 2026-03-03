from pathlib import Path
from typing import Optional
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
    GOOGLE_CLIENT_SECRET_FILE: str = "secrets/client_secret.json"
    GOOGLE_TOKEN_FILE: str = "secrets/token.json"
    GOOGLE_DRIVE_FOLDER_ID: str = ""  # .env에서 설정 필요
    
    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# 전역 설정 객체
config = Settings()
