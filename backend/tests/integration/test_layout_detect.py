from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.layout_detect import (
    BoardCandidate,
    _candidate_is_plausible,
    _score_candidate,
    crop_board_region,
    detect_board_candidate,
)


class TestScoreCandidate:
    def test_full_frame_max_score(self) -> None:
        score = _score_candidate((0, 0, 100, 100), (100, 100), expected_ratio=1.0)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_off_center_reduces_score(self) -> None:
        score = _score_candidate((0, 0, 50, 50), (100, 100), expected_ratio=1.0)
        assert 0 < score < 0.95

    def test_none_expected_ratio_no_aspect_penalty(self) -> None:
        score = _score_candidate((25, 25, 50, 50), (100, 100), expected_ratio=None)
        assert 0 < score <= 1.0

    def test_ratio_mismatch_penalizes(self) -> None:
        ok = _score_candidate((25, 25, 50, 50), (100, 100), expected_ratio=1.0)
        bad = _score_candidate((25, 25, 50, 50), (100, 100), expected_ratio=2.0)
        assert ok > bad


class TestCandidateIsPlausible:
    def test_large_centered_is_plausible(self) -> None:
        c = BoardCandidate(bbox=(20, 20, 60, 60), score=0.9)
        assert _candidate_is_plausible(c, (100, 100), expected_ratio=1.0)

    def test_tiny_bbox_not_plausible(self) -> None:
        c = BoardCandidate(bbox=(45, 45, 1, 1), score=0.1)
        assert not _candidate_is_plausible(c, (100, 100), expected_ratio=1.0)

    def test_extreme_aspect_ratio_not_plausible(self) -> None:
        c = BoardCandidate(bbox=(10, 10, 80, 5), score=0.3)
        assert not _candidate_is_plausible(c, (100, 100), expected_ratio=1.0)

    def test_touching_left_edge_not_plausible(self) -> None:
        c = BoardCandidate(bbox=(0, 0, 10, 20), score=0.5)
        assert not _candidate_is_plausible(c, (100, 100), expected_ratio=1.0)

    def test_touching_right_edge_not_plausible(self) -> None:
        c = BoardCandidate(bbox=(90, 0, 10, 20), score=0.5)
        assert not _candidate_is_plausible(c, (100, 100), expected_ratio=1.0)

    def test_ratio_mismatch_with_small_area_not_plausible(self) -> None:
        c = BoardCandidate(bbox=(40, 40, 20, 50), score=0.5)
        assert not _candidate_is_plausible(c, (100, 100), expected_ratio=1.0)


class TestDetectBoardCandidate:
    def test_detects_board_in_fixture(self, screenshots_dir: Path) -> None:
        image = cv2.imread(str(screenshots_dir / "a.jpeg"))
        assert image is not None, "Fixture image failed to load"

        candidate = detect_board_candidate(image, expected_width=5, expected_height=5)
        assert candidate is not None
        assert candidate.score > 0
        x, y, w, h = candidate.bbox
        assert w > 0 and h > 0

    def test_blank_image_returns_none(self) -> None:
        blank = np.full((100, 100, 3), 255, dtype=np.uint8)
        candidate = detect_board_candidate(blank, expected_width=5, expected_height=5)
        assert candidate is None


class TestCropBoardRegion:
    def test_crops_from_detected_candidate(self, screenshots_dir: Path) -> None:
        image = cv2.imread(str(screenshots_dir / "a.jpeg"))
        assert image is not None

        candidate = detect_board_candidate(image, expected_width=5, expected_height=5)
        assert candidate is not None

        cropped = crop_board_region(image, candidate, expected_width=5, expected_height=5)
        assert cropped.ndim == 3
        assert cropped.shape[2] == 3
        assert cropped.shape[0] > 0
        assert cropped.shape[1] > 0
