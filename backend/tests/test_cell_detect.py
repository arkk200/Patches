from pathlib import Path

import cv2
import json
import numpy as np
import pytest

from app.services.cell_detect import (
    CellSegment,
    CellShape,
    classify_cell_shapes,
    segment_cells,
)
from app.services.cell_ocr import extract_cell_sizes
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


# ── shape classification unit tests (synthetic) ────────────────────────────

class TestClassifyCellShapeSynthetic:
    """Unit tests for classify_cell_shapes with synthetic (non-fixture) images."""

    @staticmethod
    def _make_cell(h: int, w: int) -> np.ndarray:
        return np.full((h, w, 3), (220, 220, 220), dtype=np.uint8)

    @staticmethod
    def _place_patch(cell: np.ndarray, y1: int, y2: int, x1: int, x2: int,
                     bgr: tuple[int, int, int]) -> np.ndarray:
        result = cell.copy()
        result[y1:y2, x1:x2] = bgr
        return result

    @staticmethod
    def _classify_via_api(cell: np.ndarray) -> CellShape:
        return classify_cell_shapes([CellSegment(row=0, col=0, cell_image=cell)])[0].shape

    def test_wide_shape(self) -> None:
        cell = self._make_cell(100, 100)
        cell = self._place_patch(cell, 30, 70, 10, 90, (80, 160, 240))
        assert self._classify_via_api(cell) == CellShape.WIDE, "wide patch should be WIDE"

    def test_tall_shape(self) -> None:
        cell = self._make_cell(100, 100)
        cell = self._place_patch(cell, 10, 90, 30, 70, (80, 160, 240))
        assert self._classify_via_api(cell) == CellShape.TALL, "tall patch should be TALL"

    def test_square_shape(self) -> None:
        cell = self._make_cell(100, 100)
        cell = self._place_patch(cell, 25, 75, 25, 75, (80, 160, 240))
        assert self._classify_via_api(cell) == CellShape.SQUARE, "square patch should be SQUARE"

    def test_no_color_returns_none(self) -> None:
        cell = np.full((50, 50, 3), (255, 255, 255), dtype=np.uint8)
        assert self._classify_via_api(cell) == CellShape.NONE, "white cell should be NONE"

    def test_tiny_noise_returns_none(self) -> None:
        cell = np.full((50, 50, 3), (220, 220, 220), dtype=np.uint8)
        cell[24:26, 24:26] = (80, 160, 240)  # 2×2 — too small
        assert self._classify_via_api(cell) == CellShape.NONE, "tiny noise should be NONE"


# ── OCR unit tests (synthetic) ─────────────────────────────────────────────

class TestExtractCellSizeSynthetic:
    """Unit tests for OCR with synthetic cell images."""

    @staticmethod
    def _make_cell_with_number(
        h: int, w: int,
        piece_bgr: tuple[int, int, int],
        number: str,
    ) -> np.ndarray:
        """Create cell filled with piece color, white number on top."""
        cell = np.full((h, w, 3), piece_bgr, dtype=np.uint8)
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = min(h, w) / 70.0
        thickness = max(1, int(min(h, w) / 40))
        text_size = cv2.getTextSize(number, font, font_scale, thickness)[0]
        x = (w - text_size[0]) // 2
        y = (h + text_size[1]) // 2
        cv2.putText(cell, number, (x, y), font, font_scale, (255, 255, 255), thickness)
        return cell

    @staticmethod
    def _size_via_api(cell: np.ndarray) -> int | None:
        return extract_cell_sizes([CellSegment(row=0, col=0, cell_image=cell)])[0].size

    def test_single_digit_on_green_piece(self) -> None:
        """Green piece (high sat) — PSM 10 reads reliably."""
        cell = self._make_cell_with_number(60, 60, (50, 200, 100), "3")
        assert self._size_via_api(cell) == 3, f"expected 3, got {self._size_via_api(cell)}"

    def test_double_digit_on_red_piece(self) -> None:
        """Red piece (high sat) — PSM 10 reads 2-digit numbers."""
        cell = self._make_cell_with_number(80, 80, (100, 100, 200), "10")
        assert self._size_via_api(cell) == 10, f"expected 10, got {self._size_via_api(cell)}"

    def test_empty_cell_returns_none(self) -> None:
        cell = np.full((60, 60, 3), (180, 180, 180), dtype=np.uint8)
        assert self._size_via_api(cell) is None, "empty cell should return None"


class TestExtractCellSizesPipeline:
    """Integration of extract_cell_sizes with real CellSegment list."""

    def test_preserves_existing_shape_after_size_extraction(self) -> None:
        cells = [
            CellSegment(row=0, col=0, shape=CellShape.WIDE,
                        cell_image=np.full((60, 60, 3), (200, 100, 50), dtype=np.uint8)),
            CellSegment(row=0, col=1, shape=CellShape.TALL,
                        cell_image=np.full((60, 60, 3), (50, 200, 100), dtype=np.uint8)),
        ]
        result = extract_cell_sizes(cells)
        assert len(result) == 2, f"expected 2, got {len(result)}"
        assert result[0].shape == CellShape.WIDE, f"expected WIDE, got {result[0].shape!r}"
        assert result[1].shape == CellShape.TALL, f"expected TALL, got {result[1].shape!r}"
        for c in result:
            assert c.cell_image.shape == (60, 60, 3), (
                f"expected (60,60,3), got {c.cell_image.shape}"
            )


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
    def test_non_none_shapes_match_expected(
        self, screenshots_dir: Path, puzzles_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        patches_path = self._patches_path(puzzles_dir, screenshot_name)
        expected = self._expected_shapes(patches_path)

        cells = _load_cells(screenshots_dir, tmp_path, screenshot_name)
        cells = classify_cell_shapes(cells)

        for cell in cells:
            exp_shape = expected[(cell.row, cell.col)]
            if exp_shape == CellShape.NONE:
                continue
            assert cell.shape == exp_shape, (
                f"{screenshot_name} ({cell.row},{cell.col}): "
                f"expected {exp_shape!r}, got {cell.shape!r}"
            )


class TestExtractCellSizesWithFixtures:
    """OCR on real screenshots. 3-way voting achieves ~100% on test set."""
    FIXTURE_NAMES = ["a.jpeg", "b.png", "c.png"]
    MIN_ACCURACY = 0.70

    @staticmethod
    def _patches_path(puzzles_dir: Path, screenshot_name: str) -> Path:
        stem = Path(screenshot_name).stem
        return puzzles_dir / f"{stem}.patches"

    @staticmethod
    def _expected_sizes(patches_path: Path) -> dict[tuple[int, int], int]:
        draft = parse_patches(patches_path.read_text())
        return {(p.row, p.col): p.size for p in draft.patches if p.size is not None}

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_each_cell_size_not_none(
        self, screenshots_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        cells = _load_cells(screenshots_dir, tmp_path, screenshot_name)
        cells = extract_cell_sizes(cells)
        nones = [(c.row, c.col) for c in cells if c.size is None]
        ok = len(cells) - len(nones)
        assert ok >= len(cells) * self.MIN_ACCURACY, (
            f"{screenshot_name}: {len(nones)}/{len(cells)} cells have None size: {nones}"
        )

    @pytest.mark.parametrize("screenshot_name", [
        "a.jpeg",
        "b.png",
        "c.png",
    ])
    def test_sizes_match_expected(
        self, screenshots_dir: Path, puzzles_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        patches_path = self._patches_path(puzzles_dir, screenshot_name)
        expected = self._expected_sizes(patches_path)

        cells = _load_cells(screenshots_dir, tmp_path, screenshot_name)
        cells = extract_cell_sizes(cells)

        mismatches = []
        for cell in cells:
            pos = (cell.row, cell.col)
            exp_size = expected[pos]
            if cell.size != exp_size:
                mismatches.append(f"  ({cell.row},{cell.col}): expected {exp_size}, got {cell.size}")

        ok = len(cells) - len(mismatches)
        assert ok >= len(cells) * self.MIN_ACCURACY, (
            f"{screenshot_name}: {len(mismatches)}/{len(cells)} mismatches:\n"
            + "\n".join(mismatches)
        )
