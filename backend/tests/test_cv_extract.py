from pathlib import Path

import cv2

from app.services.cv_extract import extract_board
from tests.fixture_helpers import get_screenshot_entry, get_screenshot_path


def assert_a_jpeg_board_selection(board_bbox: tuple[int, int, int, int], selected_quad: list[list[int]] | None = None):
    x, y, w, h = board_bbox
    center_x = x + (w / 2)
    assert 0 <= x < 120
    assert 350 <= y <= 500
    assert w > 900
    assert h > 900
    assert abs(w - h) < 120
    assert abs(center_x - 540) < 40

    if selected_quad is not None:
        xs = [point[0] for point in selected_quad]
        ys = [point[1] for point in selected_quad]
        assert min(xs) < 120
        assert 350 <= min(ys) <= 500
        assert max(xs) - min(xs) > 900
        assert max(ys) - min(ys) > 900
        assert abs(((min(xs) + max(xs)) / 2) - 540) < 40


def test_extract_board_without_debug(tmp_path):
    entry = get_screenshot_entry("a.jpeg")
    image_path = get_screenshot_path("a.jpeg")

    result = extract_board(
        str(image_path),
        str(tmp_path / "job"),
        board_width=entry["board_width"],
        board_height=entry["board_height"],
        debug=False,
    )

    assert result.debug_enabled is False
    assert result.debug_artifacts is None
    assert result.warped_board_path is not None
    assert Path(result.warped_board_path).exists()
    assert result.board_bbox is not None
    assert_a_jpeg_board_selection(result.board_bbox)

    crop = cv2.imread(result.warped_board_path)
    assert crop is not None
    height, width = crop.shape[:2]
    assert abs((width / height) - (entry["board_width"] / entry["board_height"])) < 0.05


def test_extract_board_with_debug(tmp_path):
    entry = get_screenshot_entry("a.jpeg")
    image_path = get_screenshot_path("a.jpeg")

    result = extract_board(
        str(image_path),
        str(tmp_path / "job"),
        board_width=entry["board_width"],
        board_height=entry["board_height"],
        debug=True,
    )

    assert result.debug_enabled is True
    assert result.debug_artifacts is not None

    preprocess = result.debug_artifacts["preprocess"]
    layout = result.debug_artifacts["layout"]

    assert Path(preprocess["grayscale_path"]).exists()
    assert Path(preprocess["blurred_path"]).exists()
    assert Path(preprocess["enhanced_path"]).exists()
    assert Path(preprocess["sharpened_path"]).exists()
    assert Path(preprocess["edges_path"]).exists()
    assert Path(preprocess["board_mask_path"]).exists()
    assert Path(layout["contour_overlay_path"]).exists()
    assert Path(layout["selected_bbox_overlay_path"]).exists()
    assert Path(layout["board_crop_path"]).exists()
    assert layout["selected_bbox"] is not None
    assert layout["selected_quad"] is not None
    assert len(layout["selected_quad"]) == 4
    assert_a_jpeg_board_selection(tuple(layout["selected_bbox"]), layout["selected_quad"])

    crop = cv2.imread(layout["board_crop_path"])
    assert crop is not None
    height, width = crop.shape[:2]
    assert abs((width / height) - (entry["board_width"] / entry["board_height"])) < 0.05


extract_board_size = extract_board

def test_extract_board_size_alias_without_debug(tmp_path):
    entry = get_screenshot_entry("a.jpeg")
    image_path = get_screenshot_path("a.jpeg")

    result = extract_board_size(
        str(image_path),
        str(tmp_path / "job_alias"),
        board_width=entry["board_width"],
        board_height=entry["board_height"],
        debug=False,
    )

    assert result.warped_board_path is not None
    assert Path(result.warped_board_path).exists()
