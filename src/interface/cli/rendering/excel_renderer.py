"""
Excel 렌더러 — 표현 계층

DataFrame → Excel 파일 생성만 담당. 저장소 역할 없음.
"""
from pathlib import Path
from typing import Dict
import pandas as pd
from openpyxl.utils import get_column_letter


class ExcelRenderer:
    """
    DataFrame을 Excel 파일로 렌더링하는 표현 계층 어댑터

    역할:
        - 연도별 DataFrame → Excel 시트 생성
        - 컬럼 너비 자동 조정
        - 상장일 기준 오름차순 정렬

    역할 아님:
        - 데이터 저장 (RepositoryPort / ParquetRepository 역할)
        - 기존 파일 병합 (호출자가 load_all()로 준비해서 넘김)
    """

    def render(self, data: Dict[int, pd.DataFrame], output_path: Path) -> None:
        """
        연도별 DataFrame을 Excel 파일로 렌더링

        Args:
            data: {연도: DataFrame} 딕셔너리
            output_path: 저장할 Excel 파일 경로
        """
        if not data:
            return

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 연도별 상장일 오름차순 정렬
        sorted_data = {}
        for year, df in sorted(data.items()):
            if df.empty:
                continue
            if "상장일" in df.columns:
                df = df.sort_values("상장일", ascending=True)
            sorted_data[year] = df

        if not sorted_data:
            return

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for year, df in sorted_data.items():
                sheet_name = f"{year}년"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                self._adjust_column_width(writer, sheet_name, df)

    def _adjust_column_width(
        self, writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame
    ) -> None:
        """컬럼 너비 자동 조정 (한글 고려)"""
        worksheet = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns):
            max_len = len(str(col))

            sample_values = df[col].astype(str).head(50)
            if not sample_values.empty:
                max_data_len = sample_values.map(
                    lambda x: len(str(x).encode("utf-8"))
                ).max()
                max_len = max(max_len, int(max_data_len * 0.8))

            width = min(max(max_len + 2, 10), 50)
            worksheet.column_dimensions[get_column_letter(idx + 1)].width = width
