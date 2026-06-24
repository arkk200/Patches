from pathlib import Path

import cv2
import json
import numpy as np
import pytest

from app.services.patch_detect import (
    PatchSegment,
    PatchShape,
    classify_patch_shapes,
    segment_patches,
)
from app.services.patch_ocr import extract_patch_sizes
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


def _load_patches(screenshots_dir: Path, tmp_path: Path, screenshot_name: str) -> list:
    bw, bh = _board_dimensions(screenshots_dir, screenshot_name)
    result = extract_board(
        str(screenshots_dir / screenshot_name),
        str(tmp_path / screenshot_name),
        bw, bh,
    )
    assert result.board_path is not None, f"Board extraction failed for {screenshot_name}"
    board = cv2.imread(result.board_path)
    assert board is not None, f"Could not read extracted board for {screenshot_name}"
    return segment_patches(board, bw, bh)


# ── shape classification unit tests (synthetic) ────────────────────────────

class TestClassifyPatchShapeSynthetic:
    """Unit tests for classify_patch_shapes with synthetic (non-fixture) images."""

    @staticmethod
    def _make_patch(h: int, w: int) -> np.ndarray:
        return np.full((h, w, 3), (220, 220, 220), dtype=np.uint8)

    @staticmethod
    def _place_patch(patch: np.ndarray, y1: int, y2: int, x1: int, x2: int,
                     bgr: tuple[int, int, int]) -> np.ndarray:
        result = patch.copy()
        result[y1:y2, x1:x2] = bgr
        return result

    @staticmethod
    def _classify_via_api(patch: np.ndarray) -> PatchShape:
        return classify_patch_shapes([PatchSegment(row=0, col=0, cell_image=patch)])[0].shape

    def test_wide_shape(self) -> None:
        patch = self._make_patch(100, 100)
        patch = self._place_patch(patch, 30, 70, 10, 90, (80, 160, 240))
        assert self._classify_via_api(patch) == PatchShape.WIDE, "wide patch should be WIDE"

    def test_tall_shape(self) -> None:
        patch = self._make_patch(100, 100)
        patch = self._place_patch(patch, 10, 90, 30, 70, (80, 160, 240))
        assert self._classify_via_api(patch) == PatchShape.TALL, "tall patch should be TALL"

    def test_square_shape(self) -> None:
        patch = self._make_patch(100, 100)
        patch = self._place_patch(patch, 25, 75, 25, 75, (80, 160, 240))
        assert self._classify_via_api(patch) == PatchShape.SQUARE, "square patch should be SQUARE"

    def test_no_color_returns_cross(self) -> None:
        patch = np.full((50, 50, 3), (255, 255, 255), dtype=np.uint8)
        assert self._classify_via_api(patch) == PatchShape.CROSS, "white patch should be CROSS"

    def test_tiny_noise_returns_cross(self) -> None:
        patch = np.full((50, 50, 3), (220, 220, 220), dtype=np.uint8)
        patch[24:26, 24:26] = (80, 160, 240)  # 2×2 — too small
        assert self._classify_via_api(patch) == PatchShape.CROSS, "tiny noise should be CROSS"


# ── OCR unit tests (synthetic) ─────────────────────────────────────────────

class TestExtractPatchSizeSynthetic:
    """Unit tests for OCR with synthetic patch images."""

    @staticmethod
    def _make_patch_with_number(
        h: int, w: int,
        piece_bgr: tuple[int, int, int],
        number: str,
    ) -> np.ndarray:
        """Create patch filled with piece color, white number on top."""
        patch = np.full((h, w, 3), piece_bgr, dtype=np.uint8)
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = min(h, w) / 70.0
        thickness = max(1, int(min(h, w) / 40))
        text_size = cv2.getTextSize(number, font, font_scale, thickness)[0]
        x = (w - text_size[0]) // 2
        y = (h + text_size[1]) // 2
        cv2.putText(patch, number, (x, y), font, font_scale, (255, 255, 255), thickness)
        return patch

    @staticmethod
    def _size_via_api(patch: np.ndarray) -> int | None:
        return extract_patch_sizes([PatchSegment(row=0, col=0, cell_image=patch)])[0].size

    def test_single_digit_on_green_piece(self) -> None:
        """Green piece (high sat) — PSM 8 reads reliably."""
        patch = self._make_patch_with_number(60, 60, (50, 200, 100), "3")
        assert self._size_via_api(patch) == 3, f"expected 3, got {self._size_via_api(patch)}"

    def test_double_digit_on_red_piece(self) -> None:
        """Red piece (high sat) — PSM 7+8 reads 2-digit numbers."""
        patch = self._make_patch_with_number(80, 80, (100, 100, 200), "10")
        assert self._size_via_api(patch) == 10, f"expected 10, got {self._size_via_api(patch)}"

    def test_empty_patch_returns_none(self) -> None:
        patch = np.full((60, 60, 3), (180, 180, 180), dtype=np.uint8)
        assert self._size_via_api(patch) is None, "empty patch should return None"


class TestExtractPatchSizesPipeline:
    """Integration of extract_patch_sizes with real PatchSegment list."""

    def test_preserves_existing_shape_after_size_extraction(self) -> None:
        patches = [
            PatchSegment(row=0, col=0, shape=PatchShape.WIDE,
                         cell_image=np.full((60, 60, 3), (200, 100, 50), dtype=np.uint8)),
            PatchSegment(row=0, col=1, shape=PatchShape.TALL,
                         cell_image=np.full((60, 60, 3), (50, 200, 100), dtype=np.uint8)),
        ]
        result = extract_patch_sizes(patches)
        assert len(result) == 2, f"expected 2, got {len(result)}"
        assert result[0].shape == PatchShape.WIDE, f"expected WIDE, got {result[0].shape!r}"
        assert result[1].shape == PatchShape.TALL, f"expected TALL, got {result[1].shape!r}"
        for p in result:
            assert p.cell_image.shape == (60, 60, 3), (
                f"expected (60,60,3), got {p.cell_image.shape}"
            )


# ── integration tests (fixture-based) ──────────────────────────────────────

class TestSegmentPatchesWithFixtures:
    FIXTURE_NAMES = ["a.jpeg", "b.png", "c.png"]

    @staticmethod
    def _patches_path(puzzles_dir: Path, screenshot_name: str) -> Path:
        stem = Path(screenshot_name).stem
        return puzzles_dir / f"{stem}.patches"

    @staticmethod
    def _expected_patch_positions(patches_path: Path) -> set[tuple[int, int]]:
        draft = parse_patches(patches_path.read_text())
        return {(p.row, p.col) for p in draft.patches}

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_patch_positions_match_patches(
        self, screenshots_dir: Path, puzzles_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        patches = self._patches_path(puzzles_dir, screenshot_name)
        expected = self._expected_patch_positions(patches)

        cells = _load_patches(screenshots_dir, tmp_path, screenshot_name)
        actual = {(c.row, c.col) for c in cells}

        assert actual == expected, (
            f"{screenshot_name}: expected {sorted(expected)}, got {sorted(actual)}"
        )

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_each_patch_has_valid_image(
        self, screenshots_dir: Path, puzzles_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        patches_path = self._patches_path(puzzles_dir, screenshot_name)
        expected_count = len(self._expected_patch_positions(patches_path))

        cells = _load_patches(screenshots_dir, tmp_path, screenshot_name)

        assert len(cells) == expected_count, (
            f"{screenshot_name}: expected {expected_count} patches, got {len(cells)}"
        )
        for i, cell in enumerate(cells):
            assert cell.cell_image.ndim == 3, f"{screenshot_name} patch[{i}] not color"
            assert cell.cell_image.shape[2] == 3, f"{screenshot_name} patch[{i}] missing channels"


class TestClassifyPatchShapesWithFixtures:
    FIXTURE_NAMES = ["a.jpeg", "b.png", "c.png"]

    @staticmethod
    def _patches_path(puzzles_dir: Path, screenshot_name: str) -> Path:
        stem = Path(screenshot_name).stem
        return puzzles_dir / f"{stem}.patches"

    @staticmethod
    def _expected_shapes(patches_path: Path) -> dict[tuple[int, int], PatchShape]:
        draft = parse_patches(patches_path.read_text())
        return {(p.row, p.col): PatchShape(p.shape) for p in draft.patches}

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_each_patch_gets_valid_shape(
        self, screenshots_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        cells = _load_patches(screenshots_dir, tmp_path, screenshot_name)
        cells = classify_patch_shapes(cells)
        for cell in cells:
            assert cell.shape in set(PatchShape), (
                f"{screenshot_name} ({cell.row},{cell.col}): unexpected shape {cell.shape!r}"
            )

    @pytest.mark.parametrize("screenshot_name", FIXTURE_NAMES)
    def test_non_cross_shapes_match_expected(
        self, screenshots_dir: Path, puzzles_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        patches_path = self._patches_path(puzzles_dir, screenshot_name)
        expected = self._expected_shapes(patches_path)

        cells = _load_patches(screenshots_dir, tmp_path, screenshot_name)
        cells = classify_patch_shapes(cells)

        for cell in cells:
            exp_shape = expected[(cell.row, cell.col)]
            if exp_shape == PatchShape.CROSS:
                continue
            assert cell.shape == exp_shape, (
                f"{screenshot_name} ({cell.row},{cell.col}): "
                f"expected {exp_shape!r}, got {cell.shape!r}"
            )


class TestExtractPatchSizesWithFixtures:
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
    def test_each_patch_size_not_none(
        self, screenshots_dir: Path, tmp_path: Path,
        screenshot_name: str,
    ) -> None:
        cells = _load_patches(screenshots_dir, tmp_path, screenshot_name)
        cells = extract_patch_sizes(cells)
        nones = [(c.row, c.col) for c in cells if c.size is None]
        ok = len(cells) - len(nones)
        assert ok >= len(cells) * self.MIN_ACCURACY, (
            f"{screenshot_name}: {len(nones)}/{len(cells)} patches have None size: {nones}"
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

        cells = _load_patches(screenshots_dir, tmp_path, screenshot_name)
        cells = extract_patch_sizes(cells)

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
