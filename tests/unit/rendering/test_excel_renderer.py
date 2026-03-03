"""
ExcelRenderer 단위 테스트
"""
import pytest
import pandas as pd
from pathlib import Path

from interface.cli.rendering.excel_renderer import ExcelRenderer


@pytest.fixture
def renderer() -> ExcelRenderer:
    return ExcelRenderer()


@pytest.fixture
def sample_data() -> dict:
    return {
        2024: pd.DataFrame({
            "종목명": ["주식A", "주식B"],
            "상장일": ["2024-01-15", "2024-02-20"],
        }),
        2025: pd.DataFrame({
            "종목명": ["주식C"],
            "상장일": ["2025-03-10"],
        }),
    }


class TestExcelRenderer:

    def test_render_creates_excel_file(
        self, renderer: ExcelRenderer, sample_data: dict, tmp_path: Path
    ):
        """render() 후 Excel 파일이 생성되어야 한다"""
        output = tmp_path / "test.xlsx"
        renderer.render(sample_data, output)
        assert output.exists()

    def test_render_creates_correct_sheets(
        self, renderer: ExcelRenderer, sample_data: dict, tmp_path: Path
    ):
        """각 연도에 대한 시트가 생성되어야 한다"""
        output = tmp_path / "test.xlsx"
        renderer.render(sample_data, output)

        excel = pd.ExcelFile(output)
        assert "2024년" in excel.sheet_names
        assert "2025년" in excel.sheet_names

    def test_render_skips_empty_dataframes(
        self, renderer: ExcelRenderer, tmp_path: Path
    ):
        """빈 DataFrame이 있는 연도는 시트를 생성하지 않는다"""
        data = {
            2024: pd.DataFrame({"종목명": ["주식A"], "상장일": ["2024-01-15"]}),
            2025: pd.DataFrame(),  # 빈 DataFrame
        }
        output = tmp_path / "test.xlsx"
        renderer.render(data, output)

        excel = pd.ExcelFile(output)
        assert "2024년" in excel.sheet_names
        assert "2025년" not in excel.sheet_names

    def test_render_does_nothing_on_empty_data(
        self, renderer: ExcelRenderer, tmp_path: Path
    ):
        """데이터가 없으면 파일을 생성하지 않는다"""
        output = tmp_path / "test.xlsx"
        renderer.render({}, output)
        assert not output.exists()

    def test_render_data_integrity(
        self, renderer: ExcelRenderer, sample_data: dict, tmp_path: Path
    ):
        """렌더링된 Excel의 데이터가 원본과 일치해야 한다"""
        output = tmp_path / "test.xlsx"
        renderer.render(sample_data, output)

        loaded = pd.read_excel(output, sheet_name="2024년")
        assert list(loaded["종목명"]) == ["주식A", "주식B"]
