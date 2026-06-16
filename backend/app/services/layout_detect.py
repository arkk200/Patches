from dataclasses import dataclass
from itertools import combinations

import cv2
import numpy as np

from app.services.image_preprocess import build_preprocess_stages


@dataclass
class BoardCandidate:
    bbox: tuple[int, int, int, int]
    score: float


def _crop_from_bbox(
    image: np.ndarray,
    bbox: tuple[int, int, int, int],
    expected_width: int | None,
    expected_height: int | None,
) -> np.ndarray:
    x, y, w, h = bbox
    image_height, image_width = image.shape[:2]

    if expected_width and expected_height:
        target_ratio = expected_width / expected_height
        current_ratio = w / max(h, 1)
        if current_ratio < target_ratio:
            target_width = int(round(h * target_ratio))
            delta = max(target_width - w, 0)
            x -= delta // 2
            w += delta
        elif current_ratio > target_ratio:
            target_height = int(round(w / target_ratio))
            delta = max(target_height - h, 0)
            y -= delta // 2
            h += delta

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(image_width, x + w)
    y2 = min(image_height, y + h)
    return image[y1:y2, x1:x2].copy()


def _score_candidate(
    bbox: tuple[int, int, int, int],
    image_shape: tuple[int, int],
    expected_ratio: float | None,
) -> float:
    x, y, w, h = bbox
    image_height, image_width = image_shape
    image_area = image_height * image_width

    center_x = x + (w / 2)
    center_y = y + (h / 2)
    x_center_score = max(0.0, 1.0 - (abs(center_x - (image_width / 2)) / max(image_width / 2, 1)))
    y_center_score = max(0.0, 1.0 - (abs(center_y - (image_height / 2)) / max(image_height / 2, 1)))

    area_score = min(1.0, (w * h) / max(image_area * 0.3, 1))
    bbox_ratio = w / max(h, 1)
    aspect_score = 1.0
    if expected_ratio is not None:
        aspect_score = max(0.0, 1.0 - (abs(bbox_ratio - expected_ratio) / max(expected_ratio, 1e-6)))

    return (
        (x_center_score * 0.27)
        + (y_center_score * 0.08)
        + (area_score * 0.32)
        + (aspect_score * 0.33)
    )


def _build_candidate_from_contours(
    image: np.ndarray,
    contours: list[np.ndarray],
    expected_width: int | None,
    expected_height: int | None,
) -> BoardCandidate | None:
    if not contours:
        return None

    points = np.vstack(contours)
    x, y, w, h = cv2.boundingRect(points)
    if w <= 1 or h <= 1:
        return None

    bbox = (x, y, w, h)
    expected_ratio = (expected_width / expected_height) if expected_width and expected_height else None
    score = _score_candidate(
        bbox,
        image.shape[:2],
        expected_ratio,
    )
    return BoardCandidate(
        bbox=bbox,
        score=score,
    )


def _candidate_is_plausible(
    candidate: BoardCandidate,
    image_shape: tuple[int, int],
    expected_ratio: float | None,
) -> bool:
    image_height, image_width = image_shape
    x, y, w, h = candidate.bbox
    bbox_area = w * h
    image_area = image_height * image_width
    if bbox_area < image_area * 0.015:
        return False

    bbox_ratio = w / max(h, 1)
    if expected_ratio is not None and abs(bbox_ratio - expected_ratio) > 0.45 and bbox_area < image_area * 0.2:
        return False
    if not 0.35 <= bbox_ratio <= 1.8:
        return False
    if x + w <= image_width * 0.1 or x >= image_width * 0.9:
        return False
    return True


def _collect_candidates(
    image: np.ndarray,
    contours: list[np.ndarray],
    expected_width: int | None,
    expected_height: int | None,
) -> list[BoardCandidate]:
    candidates: list[BoardCandidate] = []
    expected_ratio = (expected_width / expected_height) if expected_width and expected_height else None
    plausible_contours: list[np.ndarray] = []

    for contour in contours:
        candidate = _build_candidate_from_contours(
            image,
            [contour],
            expected_width,
            expected_height,
        )
        if candidate is None:
            continue
        if not _candidate_is_plausible(candidate, image.shape[:2], expected_ratio):
            continue
        candidates.append(candidate)
        plausible_contours.append(contour)

    max_merge_inputs = min(6, len(plausible_contours))
    for size in range(2, max_merge_inputs + 1):
        for grouped_contours in combinations(plausible_contours[:max_merge_inputs], size):
            merged_candidate = _build_candidate_from_contours(
                image,
                list(grouped_contours),
                expected_width,
                expected_height,
            )
            if merged_candidate is None:
                continue
            if not _candidate_is_plausible(merged_candidate, image.shape[:2], expected_ratio):
                continue
            candidates.append(merged_candidate)

    return candidates


def _detect_board_candidate_impl(
    image: np.ndarray,
    *,
    expected_width: int | None,
    expected_height: int | None,
) -> BoardCandidate | None:
    preprocess = build_preprocess_stages(image)
    edges = preprocess.edges

    edge_contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    candidates = _collect_candidates(
        image,
        edge_contours,
        expected_width,
        expected_height,
    )

    if not candidates:
        return None

    return max(candidates, key=lambda candidate: candidate.score)


def detect_board_candidate(
    image: np.ndarray,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> BoardCandidate | None:
    return _detect_board_candidate_impl(
        image,
        expected_width=expected_width,
        expected_height=expected_height,
    )


def crop_board_region(
    image: np.ndarray,
    candidate: BoardCandidate,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> np.ndarray:
    return _crop_from_bbox(image, candidate.bbox, expected_width, expected_height)
