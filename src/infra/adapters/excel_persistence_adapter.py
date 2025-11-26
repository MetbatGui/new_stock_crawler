# infra/adapters/excel_persistence_adapter.py
import os
import pandas as pd
from typing import Dict
from openpyxl.utils import get_column_letter
from core.ports.data_ports import DataExporterPort

class LocalExcelPersistenceAdapter(DataExporterPort):
    
    # ▼▼▼ [수정] 단일 파일 이름으로 변경 ▼▼▼
    OUTPUT_DIR: str = "reports"
    FILENAME: str = "ipo_data_all_years.xlsx"


    def __init__(self):
        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR)
            print(f"'{self.OUTPUT_DIR}' 디렉터리를 생성했습니다.")
        
    def save_report(self, data: Dict[int, pd.DataFrame]) -> None:
        """
        {연도: DataFrame} 딕셔너리를 받아
        단일 엑셀 파일에 연도별 시트로 저장합니다.
        이 메서드는 내부 export 메서드를 호출합니다.
        
        Args:
            data (Dict[int, pd.DataFrame]): 저장할 데이터 딕셔너리.
        """
        self.export(data)

    def export(self, data: Dict[int, pd.DataFrame]) -> None:
        """
        {연도: DataFrame} 딕셔너리를 받아
        단일 엑셀 파일에 연도별 시트로 저장합니다.
        
        Args:
            data (Dict[int, pd.DataFrame]): 저장할 데이터 딕셔너리.
        """
        
        filepath = os.path.join(self.OUTPUT_DIR, self.FILENAME)
        
        try:
            print(f"   [정보] 엑셀 파일 쓰기 시작: '{filepath}'")
            
            # ExcelWriter를 사용하여 파일을 엽니다.
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                
                # 딕셔너리를 순회하며 각 연도(key)와 DataFrame(value)을 가져옵니다.
                for year, df in data.items():
                    if df.empty:
                        print(f"    - [{year}년] 데이터가 비어있어 시트 생성을 건너뜁니다.")
                        continue
                        
                    # 연도(e.g., 2023)를 시트 이름으로 사용합니다.
                    sheet_name = str(year)
                    
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # 컬럼 너비 자동 조정
                    self._adjust_column_width(writer.sheets[sheet_name], df)
                    
                    print(f"    - [{sheet_name}] 시트 저장 완료 (총 {len(df)}개 항목)")

            print(f"\n   [성공] 모든 연도 데이터가 '{filepath}'에 통합 저장되었습니다. ✅")
            
        except Exception as e:
            print(f"   [실패] 엑셀 파일 저장 중 오류 발생: {e} ❌")

    def _adjust_column_width(self, worksheet, df: pd.DataFrame):
        """워크시트의 컬럼 너비를 데이터 길이에 맞춰 조정"""
        for idx, col in enumerate(df.columns):
            # 헤더 길이
            header_len = len(str(col))
            
            # 데이터 최대 길이 (한글 고려하여 1.5배 가중치 줄 수도 있으나 일단 단순 길이)
            # 데이터가 비어있으면 0
            if not df[col].empty:
                # 각 셀의 문자열 길이 계산 (None/NaN 처리 포함)
                max_data_len = df[col].astype(str).map(lambda x: len(x) if x != 'nan' else 0).max()
            else:
                max_data_len = 0
            
            # 최종 너비: (최대 길이 + 여유) * 계수
            # 한글이 포함될 수 있으므로 약간 넉넉하게 잡음
            final_width = max(header_len, max_data_len) + 2
            
            # 너무 넓어지지 않게 제한 (선택사항)
            final_width = min(final_width, 50)
            
            col_letter = get_column_letter(idx + 1)
            worksheet.column_dimensions[col_letter].width = final_width