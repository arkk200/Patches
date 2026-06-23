from pathlib import Path

import cv2
import json
import numpy as np
import pytest

from app.services.cell_detect import (
    CellShape,
    _cell_has_color,
    _classify_cell_shape,
    classify_cell_shapes,
    segment_cells,
)
from app.services.cv_extract import extract_board
from app.services.parse_patches import parse_patches


# ── module-level helpers (shared across test classes) ──────────────────────

def _board_dimensions(screenshots_dir: Path, screenshot_name: str) -> tuple[int, int]:
    meta_path = screenshots_dir / "metadata.json"
    screenshots = json.loads(meta_path.read_text())["screenshots"]
    for s in screenshots:
        if s["file_name"] == screenshot_name:
            return s["board_width"], s["board_height"]
    raise ValueError(f"{screenshot_name} not in metadata.json")


def _load_cells(screenshots_dir: Path, tmp_path: Path, screenshot_name: str) -> list:
    bw, bh = _board_dimensions(screenshots_dir, screenshot_name)
    result = extract_board(
        str(screenshots_dir / screenshot_name),
        str(tmp_path / screenshot_name),
        bw, bh,
    )
    assert result.board_path is not None, f"Board extraction failed for {screenshot_name}"
    board = cv2.imread(result.board_path)
    assert board is not None, f"Could not read extracted board for {screenshot_name}"
    return segment_cells(board, bw, bh)


# ── unit tests ─────────────────────────────────────────────────────────────

class TestCellHasColor:
    @staticmethod
    def _make_colored_square(h: int, w: int, bgr: tuple[int, int, int]) -> np.ndarray:
        return np.full((h, w, 3), bgr, dtype=np.uint8)

    def test_colored_cell_returns_true(self) -> None:
        cell = self._make_colored_square(20, 20, (80, 160, 240))
        assert _cell_has_color(cell)

    def test_white_cell_returns_false(self) -> None:
        cell = self._make_colored_square(20, 20, (255, 255, 255))
        assert not _cell_has_color(cell)

    def test_gray_cell_returns_false(self) -> None:
        cell = self._make_colored_square(20, 20, (128, 128, 128))
        assert not _cell_has_color(cell)


class TestClassifyCellShapeSynthetic:
    """Unit tests for _classify_cell_shape with synthetic (non-fixture) images."""

    @staticmethod
    def _make_cell(h: int, w: int, patch_bgr: tuple[int, int, int]) -> np.ndarray:
        cell = np.full((h, w, 3), (220, 220, 220), dtype=np.uint8)
        return cell

    @staticmethod
    def _place_patch(cell: np.ndarray, y1: int, y2: int, x1: int, x2: int,
                     bgr: tuple[int, int, int]) -> np.ndarray:
        result = cell.copy()
        result[y1:y2, x1:x2] = bgr
        # add subtle saturation gradient around edges to mimic real rendering
        return result

    def test_wide_shape(self) -> None:
        cell = self._make_cell(100, 100, (80, 160, 240))
        cell = self._place_patch(cell, 30, 70, 10, 90, (80, 160, 240))
        assert _classify_cell_shape(cell) == CellShape.WIDE

    def test_tall_shape(self) -> None:
        cell = self._make_cell(100, 100, (80, 160, 240))
        cell = self._place_patch(cell, 10, 90, 30, 70, (80, 160, 240))
        assert _classify_cell_shape(cell) == CellShape.TALL

    def test_square_shape(self) -> None:
        cell = self._make_cell(100, 100, (80, 160, 240))
        cell = self._place_patch(cell, 25, 75, 25, 75, (80, 160, 240))
        assert _classify_cell_shape(cell) == CellShape.SQUARE

    def test_no_color_returns_any(self) -> None:
        cell = np.full((50, 50, 3), (255, 255, 255), dtype=np.uint8)
        assert _classify_cell_shape(cell) == CellShape.ANY

    def test_tiny_noise_returns_any(self) -> None:
        cell = np.full((50, 50, 3), (220, 220, 220), dtype=np.uint8)
        cell[24:26, 24:26] = (80, 160, 240)  # 2×2 — too small
        assert _classify_cell_shape(cell) == CellShape.ANY


# ── integration tests (fixture-based) ──────────────────────────────────────

class TestSegmentCellsWithFixtures:
    FIXTURE_NAMES = ["a.jpeg", "b.png", "c.png"]

    @staticmethod
    def _patches_path(puzzles_dir: Path, screenshot_name: str) -> Path:
        stem = Path(screenshot_name).stem
        return puzzles_dir / f"{stem}.patches"

    @staticmethod
    def _expected_cell_positions(patches_path: Path) -> set[tuple[int, int]]:
        draft = parse_patches(patches_path.read_text())
        return {(p.row, p.col) for p in draft.patches}

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_cell_positions_match_patches(
        self, screenshots_dir: Path, puzzles_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        patches = self._patches_path(puzzles_dir, screenshot_name)
        expected = self._expected_cell_positions(patches)

        cells = _load_cells(screenshots_dir, tmp_path, screenshot_name)
        actual = {(c.row, c.col) for c in cells}

        assert actual == expected, (
            f"{screenshot_name}: expected {sorted(expected)}, got {sorted(actual)}"
        )

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_each_cell_has_valid_image(
        self, screenshots_dir: Path, puzzles_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        patches_path = self._patches_path(puzzles_dir, screenshot_name)
        expected_count = len(self._expected_cell_positions(patches_path))

        cells = _load_cells(screenshots_dir, tmp_path, screenshot_name)

        assert len(cells) == expected_count, (
            f"{screenshot_name}: expected {expected_count} cells, got {len(cells)}"
        )
        for i, cell in enumerate(cells):
            assert cell.cell_image.ndim == 3, f"{screenshot_name} cell[{i}] not color"
            assert cell.cell_image.shape[2] == 3, f"{screenshot_name} cell[{i}] missing channels"


class TestClassifyCellShapesWithFixtures:
    FIXTURE_NAMES = ["a.jpeg", "b.png", "c.png"]

    @staticmethod
    def _patches_path(puzzles_dir: Path, screenshot_name: str) -> Path:
        stem = Path(screenshot_name).stem
        return puzzles_dir / f"{stem}.patches"

    @staticmethod
    def _expected_shapes(patches_path: Path) -> dict[tuple[int, int], CellShape]:
        draft = parse_patches(patches_path.read_text())
        return {(p.row, p.col): CellShape(p.shape) for p in draft.patches}

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_each_cell_gets_valid_shape(
        self, screenshots_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        cells = _load_cells(screenshots_dir, tmp_path, screenshot_name)
        cells = classify_cell_shapes(cells)
        for cell in cells:
            assert cell.shape in set(CellShape), (
                f"{screenshot_name} ({cell.row},{cell.col}): unexpected shape {cell.shape!r}"
            )

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_non_any_shapes_match_expected(
        self, screenshots_dir: Path, puzzles_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        patches_path = self._patches_path(puzzles_dir, screenshot_name)
        expected = self._expected_shapes(patches_path)

        cells = _load_cells(screenshots_dir, tmp_path, screenshot_name)
        cells = classify_cell_shapes(cells)

        for cell in cells:
            exp_shape = expected[(cell.row, cell.col)]
            if exp_shape == CellShape.ANY:
                continue
            assert cell.shape == exp_shape, (
                f"{screenshot_name} ({cell.row},{cell.col}): "
                f"expected {exp_shape!r}, got {cell.shape!r}"
            )
