"""
Excel 내보내기 어댑터 구현
"""
from pathlib import Path
import os
from typing import Dict, Union
import pandas as pd

from core.ports.data_ports import DataExporterPort
from config import config


class ExcelExporter(DataExporterPort):
    """
    DataFrame을 Excel 파일로 저장하는 어댑터
    """
    
    def __init__(self, output_dir: Union[str, Path] = None):
        # config.OUTPUT_DIR을 기본값으로 사용
        self.output_dir = Path(output_dir) if output_dir else config.OUTPUT_DIR
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        """출력 디렉토리 생성"""
        os.makedirs(self.output_dir, exist_ok=True)
    
    def export(self, data: Dict[int, pd.DataFrame]) -> None:
        """
        연도별 데이터를 엑셀 파일로 저장
        
        Args:
            data: {연도: DataFrame} 형태의 딕셔너리
        """
        if not data:
            return
            
        # 파일명 생성
        filename = config.get_default_filename()
            
        filepath = os.path.join(self.output_dir, filename)
        
        # 엑셀 저장
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            for year, df in data.items():
                sheet_name = f"{year}년"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 컬럼 너비 자동 조정 (선택 사항, openpyxl 필요)
                self._adjust_column_width(writer, sheet_name, df)
                
        print(f"      [저장 완료] {filepath}")

    def _adjust_column_width(self, writer, sheet_name: str, df: pd.DataFrame) -> None:
        """컬럼 너비 자동 조정"""
        worksheet = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns):
            # 헤더 길이와 데이터 길이 중 최대값 계산
            max_len = len(str(col))
            
            # 데이터 샘플링 (최대 50개 행만 검사하여 속도 향상)
            sample_values = df[col].astype(str).head(50)
            if not sample_values.empty:
                max_data_len = sample_values.map(lambda x: len(str(x).encode('utf-8'))).max()
                # 한글 고려하여 적절히 조정 (단순 길이 * 1.2 정도)
                max_len = max(max_len, int(max_data_len * 0.8))
            
            # 너비 설정 (최소 10, 최대 50)
            width = min(max(max_len + 2, 10), 50)
            worksheet.column_dimensions[chr(65 + idx)].width = width
