from typing import List, Tuple
from playwright.sync_api import Locator


class TableGridBuilder:
    """
    Converts complex HTML tables (with rowspan/colspan) into a 2D list (grid).
    """

    def build_grid(self, table: Locator) -> List[List[str]]:
        """Convert HTML table to 2D grid handling rowspan/colspan."""
        try:
            rows = table.locator("tr").all()
            if not rows:
                return []

            max_cols = self._calculate_max_columns(rows)
            grid, occupied = self._initialize_grid(len(rows), max_cols)

            for row_idx, row in enumerate(rows):
                self._process_table_row(row, row_idx, grid, occupied, max_cols)

            return grid
        except Exception as e:
            print(f"      [오류] 테이블 그리드 변환 중 예외: {e}")
            return []

    def _calculate_max_columns(self, rows: List[Locator]) -> int:
        """Calculate maximum number of columns in table."""
        max_cols = 0
        for row in rows:
            cells = row.locator("td, th").all()
            col_count = sum(int(cell.get_attribute("colspan") or "1") for cell in cells)
            max_cols = max(max_cols, col_count)
        return max_cols

    def _initialize_grid(
        self, num_rows: int, num_cols: int
    ) -> Tuple[List[List[str]], List[List[bool]]]:
        """Initialize grid and occupied tracking matrix."""
        grid = [["" for _ in range(num_cols)] for _ in range(num_rows)]
        occupied = [[False for _ in range(num_cols)] for _ in range(num_rows)]
        return grid, occupied

    def _fill_cell_in_grid(
        self,
        grid: List[List[str]],
        occupied: List[List[bool]],
        row_idx: int,
        col_idx: int,
        cell_text: str,
        rowspan: int,
        colspan: int,
    ) -> None:
        """Fill cell text in grid considering rowspan and colspan."""
        for r in range(rowspan):
            if row_idx + r >= len(grid):
                break
            for c in range(colspan):
                if col_idx + c >= len(grid[0]):
                    break
                grid[row_idx + r][col_idx + c] = cell_text
                occupied[row_idx + r][col_idx + c] = True

    def _process_table_row(
        self,
        row: Locator,
        row_idx: int,
        grid: List[List[str]],
        occupied: List[List[bool]],
        max_cols: int,
    ) -> None:
        """Process single table row and fill grid."""
        cells = row.locator("td, th").all()
        col_idx = 0

        for cell in cells:
            while col_idx < max_cols and occupied[row_idx][col_idx]:
                col_idx += 1

            if col_idx >= max_cols:
                break

            cell_text = cell.inner_text().replace("\u00a0", " ").strip()
            rowspan = int(cell.get_attribute("rowspan") or "1")
            colspan = int(cell.get_attribute("colspan") or "1")

            self._fill_cell_in_grid(
                grid, occupied, row_idx, col_idx, cell_text, rowspan, colspan
            )
            col_idx += colspan
