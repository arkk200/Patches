from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np

from app.services.image_preprocess import build_preprocess_stages, load_image
from app.services.layout_detect import crop_board_region, detect_board_candidate, detect_board_candidate_with_debug


@dataclass
class BoardExtractionResult:
    confidence: float
    board_bbox: tuple[int, int, int, int] | None
    warped_board_path: str | None
    debug_enabled: bool
    debug_artifacts: dict[str, Any] | None


def _write_image(path: Path, image: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)
    return str(path)


def extract_board(
    image_path: str,
    artifacts_dir: str,
    board_width: int,
    board_height: int,
    debug: bool = False,
) -> BoardExtractionResult:
    image = load_image(image_path)
    artifacts_path = Path(artifacts_dir)

    preprocess = build_preprocess_stages(image) if debug else None
    if debug:
        candidate, board_debug = detect_board_candidate_with_debug(
            image,
            expected_width=board_width,
            expected_height=board_height,
        )
    else:
        candidate = detect_board_candidate(
            image,
            expected_width=board_width,
            expected_height=board_height,
        )
        board_debug = None

    debug_preprocess = cast(Any, preprocess)
    debug_board = cast(Any, board_debug)

    if candidate is None:
        debug_artifacts = None
        if debug:
            debug_dir = artifacts_path / "debug"
            debug_artifacts = {
                "artifact_dir": str(debug_dir),
                "preprocess": {
                    "original_path": image_path,
                    "grayscale_path": _write_image(debug_dir / "preprocess" / "grayscale.png", debug_preprocess.grayscale),
                    "blurred_path": _write_image(debug_dir / "preprocess" / "blurred.png", debug_preprocess.blurred),
                    "enhanced_path": _write_image(debug_dir / "preprocess" / "enhanced.png", debug_preprocess.enhanced),
                    "sharpened_path": _write_image(debug_dir / "preprocess" / "sharpened.png", debug_preprocess.sharpened),
                    "edges_path": _write_image(debug_dir / "preprocess" / "edges.png", debug_preprocess.edges),
                    "board_mask_path": _write_image(debug_dir / "preprocess" / "board_mask.png", debug_preprocess.board_mask),
                },
                "layout": {
                    "contour_overlay_path": _write_image(debug_dir / "layout" / "contours.png", debug_board.contour_overlay),
                    "selected_bbox_overlay_path": _write_image(debug_dir / "layout" / "selected_bbox.png", debug_board.selected_bbox_overlay),
                    "selected_bbox": None,
                    "selected_quad": None,
                    "selected_score": None,
                    "board_crop_path": None,
                },
            }

        return BoardExtractionResult(
            confidence=0.0,
            board_bbox=None,
            warped_board_path=None,
            debug_enabled=debug,
            debug_artifacts=debug_artifacts,
        )

    board = crop_board_region(
        image,
        candidate,
        expected_width=board_width,
        expected_height=board_height,
    )
    artifacts_path.mkdir(parents=True, exist_ok=True)
    warped_board_path = str(artifacts_path / "board.png")
    cv2.imwrite(warped_board_path, board)

    debug_artifacts = None
    if debug:
        debug_dir = artifacts_path / "debug"
        debug_artifacts = {
            "artifact_dir": str(debug_dir),
            "preprocess": {
                "original_path": image_path,
                "grayscale_path": _write_image(debug_dir / "preprocess" / "grayscale.png", preprocess.grayscale),
                "blurred_path": _write_image(debug_dir / "preprocess" / "blurred.png", preprocess.blurred),
                "enhanced_path": _write_image(debug_dir / "preprocess" / "enhanced.png", preprocess.enhanced),
                "sharpened_path": _write_image(debug_dir / "preprocess" / "sharpened.png", preprocess.sharpened),
                "edges_path": _write_image(debug_dir / "preprocess" / "edges.png", preprocess.edges),
                "board_mask_path": _write_image(debug_dir / "preprocess" / "board_mask.png", preprocess.board_mask),
            },
            "layout": {
                "contour_overlay_path": _write_image(debug_dir / "layout" / "contours.png", board_debug.contour_overlay),
                "selected_bbox_overlay_path": _write_image(debug_dir / "layout" / "selected_bbox.png", board_debug.selected_bbox_overlay),
                "selected_bbox": list(candidate.bbox),
                "selected_quad": [[int(round(x)), int(round(y))] for x, y in candidate.quad.tolist()],
                "selected_score": candidate.score,
                "board_crop_path": warped_board_path,
            },
        }

    return BoardExtractionResult(
        confidence=candidate.score,
        board_bbox=candidate.bbox,
        warped_board_path=warped_board_path,
        debug_enabled=debug,
        debug_artifacts=debug_artifacts,
    )


extract_board_size = extract_board
