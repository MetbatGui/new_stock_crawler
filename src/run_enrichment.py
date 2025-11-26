"""
시세 보강 작업 실행 스크립트
기존에 수집된 엑셀 파일(reports/ipo_data_all_years.xlsx)을 읽어와서
시세 정보(OHLC)와 수익률을 보강하여 다시 저장합니다.
"""
import os
import sys
import pandas as pd
from typing import Dict

# 프로젝트 루트 경로를 sys.path에 추가하여 모듈 import 가능하게 함
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# Adapters & Services
from src.core.services.enrichment_service import EnrichmentService
from src.infra.adapters.data.fdr_adapter import FDRAdapter
from src.infra.adapters.excel_persistence_adapter import LocalExcelPersistenceAdapter
from src.infra.adapters.utils.console_logger import ConsoleLogger

def load_existing_data(filepath: str) -> Dict[int, pd.DataFrame]:
    """
    기존 엑셀 파일을 읽어서 {연도: DataFrame} 딕셔너리로 반환합니다.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")
    
    print(f"[정보] 기존 데이터 로딩 중: {filepath}")
    
    excel_file = pd.ExcelFile(filepath)
    data = {}
    
    for sheet_name in excel_file.sheet_names:
        try:
            year = int(sheet_name)
            df = pd.read_excel(filepath, sheet_name=sheet_name)
            data[year] = df
            print(f"    - [{year}년] {len(df)}건 로드 완료")
        except ValueError:
            print(f"    - [경고] 시트 이름 '{sheet_name}'은(는) 연도가 아니므로 건너뜁니다.")
            continue
            
    return data

def main():
    # 설정
    EXCEL_FILE_PATH = os.path.join("reports", "ipo_data_all_years.xlsx")
    
    # 로거 초기화
    logger = ConsoleLogger()
    
    try:
        logger.info("=" * 60)
        logger.info("📈 시세 보강 작업 스크립트 시작")
        logger.info("=" * 60)
        
        # 1. 기존 데이터 로드
        yearly_data = load_existing_data(EXCEL_FILE_PATH)
        
        if not yearly_data:
            logger.warning("❌ 처리할 데이터가 없습니다.")
            return

        # 2. 서비스 초기화
        # FDRAdapter는 TickerMapperPort와 MarketDataProviderPort를 모두 구현함
        fdr_adapter = FDRAdapter()
        data_exporter = LocalExcelPersistenceAdapter()
        
        enrichment_service = EnrichmentService(
            ticker_mapper=fdr_adapter,
            market_data_provider=fdr_adapter,
            data_exporter=data_exporter,
            logger=logger
        )
        
        # 3. 보강 작업 실행
        enrichment_service.enrich_data(yearly_data)
        
        logger.info("=" * 60)
        logger.info("🏁 보강 작업 스크립트 완료")
        logger.info("=" * 60)
        
    except FileNotFoundError as e:
        logger.error(f"❌ 파일 오류: {e}")
        logger.info("💡 팁: 먼저 크롤러를 실행하여 데이터를 수집해주세요 (uv run src/main.py)")
    except Exception as e:
        logger.error(f"❌ 작업 중 오류 발생: {e}")
        raise

if __name__ == "__main__":
    main()
