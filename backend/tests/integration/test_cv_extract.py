from pathlib import Path

import cv2
import numpy as np
import pytest

from app.config import settings
from app.services.cv_extract import BoardExtractionResult, extract_board


class TestExtractBoard:
    def test_with_fixture_screenshot(self, screenshots_dir: Path) -> None:
        image_path = str(screenshots_dir / "a.jpeg")
        artifacts_dir = str(Path(settings.artifacts_dir) / "test_extract")

        result = extract_board(image_path, artifacts_dir, board_width=5, board_height=5)

        assert isinstance(result, BoardExtractionResult)
        assert result.confidence > 0
        assert result.board_bbox is not None
        assert len(result.board_bbox) == 4
        assert result.board_path is not None
        assert Path(result.board_path).exists()

    def test_blank_image_returns_failed(self, tmp_path: pytest.TempPathFactory) -> None:
        blank_path = str(tmp_path / "blank.png")
        blank = np.full((100, 100, 3), 255, dtype=np.uint8)
        cv2.imwrite(blank_path, blank)

        artifacts_dir = str(tmp_path / "blank_artifact")
        result = extract_board(blank_path, artifacts_dir, board_width=5, board_height=5)

        assert result.confidence == 0.0
        assert result.board_bbox is None
        assert result.board_path is None
