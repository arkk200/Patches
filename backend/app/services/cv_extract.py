from dataclasses import dataclass
from pathlib import Path

import cv2

from app.services.image_preprocess import load_image
from app.services.layout_detect import crop_board_region, detect_board_candidate


@dataclass
class BoardExtractionResult:
    confidence: float
    board_bbox: tuple[int, int, int, int] | None
    board_path: str | None


def extract_board(
    image_path: str,
    artifacts_dir: str,
    board_width: int,
    board_height: int,
) -> BoardExtractionResult:
    image = load_image(image_path)
    artifacts_path = Path(artifacts_dir)

    candidate = detect_board_candidate(
        image,
        expected_width=board_width,
        expected_height=board_height,
    )

    if candidate is None:
        return BoardExtractionResult(
            confidence=0.0,
            board_bbox=None,
            board_path=None,
        )

    board = crop_board_region(
        image,
        candidate,
        expected_width=board_width,
        expected_height=board_height,
    )
    artifacts_path.mkdir(parents=True, exist_ok=True)
    board_path = str(artifacts_path / "board.png")
    cv2.imwrite(board_path, board)

    return BoardExtractionResult(
        confidence=candidate.score,
        board_bbox=candidate.bbox,
        board_path=board_path,
    )
