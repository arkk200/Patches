from pathlib import Path

import cv2

from app.services.cv_extract import extract_board
from tests.fixture_helpers import get_screenshot_entry, get_screenshot_path


def test_extract_board(tmp_path):
    entry = get_screenshot_entry("a.jpeg")
    image_path = get_screenshot_path("a.jpeg")

    result = extract_board(
        str(image_path),
        str(tmp_path / "job"),
        board_width=entry["board_width"],
        board_height=entry["board_height"],
    )

    assert result.warped_board_path is not None
    assert Path(result.warped_board_path).exists()
    assert result.board_bbox is not None

    x, y, w, h = result.board_bbox
    center_x = x + (w / 2)
    assert 0 <= x < 120
    assert 350 <= y <= 500
    assert w > 900
    assert h > 900
    assert abs(w - h) < 120
    assert abs(center_x - 540) < 40

    crop = cv2.imread(result.warped_board_path)
    assert crop is not None
    height, width = crop.shape[:2]
    assert abs((width / height) - (entry["board_width"] / entry["board_height"])) < 0.05
