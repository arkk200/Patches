from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.cell_detect import CellSegment, segment_cells


def _make_colored_square(h: int, w: int, bgr: tuple[int, int, int]) -> np.ndarray:
    """Create a solid color square image."""
    return np.full((h, w, 3), list(bgr), dtype=np.uint8)


def _make_board(
    board_h: int, board_w: int,
    cell_h: int, cell_w: int,
    colored: set[tuple[int, int]],
) -> np.ndarray:
    """Create a synthetic board image with colored cells and white empty cells."""
    total_h = board_h * cell_h
    total_w = board_w * cell_w
    board = np.full((total_h, total_w, 3), 255, dtype=np.uint8)

    for row in range(board_h):
        for col in range(board_w):
            if (row, col) in colored:
                color = (100 + row * 30, 150 + col * 20, 200)
                y1, y2 = row * cell_h, (row + 1) * cell_h
                x1, x2 = col * cell_w, (col + 1) * cell_w
                board[y1:y2, x1:x2] = _make_colored_square(cell_h, cell_w, color)

    return board


class TestCellHasColor:
    def test_colored_cell_returns_true(self) -> None:
        cell = _make_colored_square(20, 20, (80, 160, 240))
        from app.services.cell_detect import _cell_has_color
        assert _cell_has_color(cell)

    def test_white_cell_returns_false(self) -> None:
        cell = np.full((20, 20, 3), 255, dtype=np.uint8)
        from app.services.cell_detect import _cell_has_color
        assert not _cell_has_color(cell)

    def test_gray_cell_returns_false(self) -> None:
        cell = np.full((20, 20, 3), 128, dtype=np.uint8)
        from app.services.cell_detect import _cell_has_color
        assert not _cell_has_color(cell)


class TestSegmentCells:
    def test_returns_only_colored_cells(self) -> None:
        board = _make_board(2, 2, 20, 20, {(0, 1), (1, 0)})

        result = segment_cells(board, board_width=2, board_height=2)

        assert len(result) == 2
        positions = {(c.row, c.col) for c in result}
        assert positions == {(0, 1), (1, 0)}

    def test_all_colored_returns_all(self) -> None:
        board = _make_board(3, 3, 10, 10, {(r, c) for r in range(3) for c in range(3)})

        result = segment_cells(board, board_width=3, board_height=3)

        assert len(result) == 9

    def test_no_colored_returns_empty(self) -> None:
        board = np.full((30, 30, 3), 255, dtype=np.uint8)

        result = segment_cells(board, board_width=3, board_height=3)

        assert result == []

    def test_each_cell_has_correct_row_col(self) -> None:
        board = _make_board(2, 3, 10, 10, {(0, 0), (0, 2), (1, 1)})

        result = segment_cells(board, board_width=3, board_height=2)

        assert len(result) == 3
        result.sort(key=lambda c: (c.row, c.col))
        assert result[0].row == 0 and result[0].col == 0
        assert result[1].row == 0 and result[1].col == 2
        assert result[2].row == 1 and result[2].col == 1

    def test_cell_image_not_empty(self) -> None:
        board = _make_board(2, 2, 15, 15, {(0, 0), (1, 1)})

        result = segment_cells(board, board_width=2, board_height=2)

        for cell in result:
            assert cell.cell_image.shape[0] > 0
            assert cell.cell_image.shape[1] > 0
            assert cell.cell_image.shape[2] == 3

    def test_with_extracted_board(self, screenshots_dir: Path, tmp_path: pytest.TempPathFactory) -> None:
        from app.services.cv_extract import extract_board

        result = extract_board(
            str(screenshots_dir / "a.jpeg"),
            str(tmp_path / "board"),
            board_width=5,
            board_height=5,
        )
        assert result.board_path is not None

        board = cv2.imread(result.board_path)
        assert board is not None

        cells = segment_cells(board, board_width=5, board_height=5)

        # Fixture "a.jpeg" → 5 colored cells at corner + center positions
        assert len(cells) == 5
        positions = {(c.row, c.col) for c in cells}
        assert positions == {(0, 0), (0, 4), (2, 2), (4, 0), (4, 4)}
