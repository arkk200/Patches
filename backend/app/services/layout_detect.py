from dataclasses import dataclass
from itertools import combinations

import cv2
import numpy as np

from app.services.grid_detect import score_expected_grid
from app.services.image_preprocess import build_preprocess_stages


@dataclass
class BoardCandidate:
    bbox: tuple[int, int, int, int]
    contours: list[np.ndarray]
    quad: np.ndarray
    score: float
    source_area: int
    merged: bool = False


@dataclass
class BoardDetectionDebug:
    contour_overlay: np.ndarray
    selected_bbox_overlay: np.ndarray


def _order_quad_points(points: np.ndarray) -> np.ndarray:
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).reshape(-1)
    return np.array(
        [
            points[np.argmin(sums)],
            points[np.argmin(diffs)],
            points[np.argmax(sums)],
            points[np.argmax(diffs)],
        ],
        dtype=np.float32,
    )


def _build_bbox_candidate_quad(x: int, y: int, w: int, h: int) -> np.ndarray:
    return np.array(
        [
            [x, y],
            [x + w - 1, y],
            [x + w - 1, y + h - 1],
            [x, y + h - 1],
        ],
        dtype=np.float32,
    )


def _build_candidate_quad(points: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    if len(points) >= 4:
        rect = cv2.minAreaRect(points.astype(np.float32))
        quad = cv2.boxPoints(rect).astype(np.float32)
        if quad.shape == (4, 2):
            return _order_quad_points(quad)

    x, y, w, h = bbox
    return _build_bbox_candidate_quad(x, y, w, h)


def _quad_dimensions(quad: np.ndarray) -> tuple[float, float]:
    top = float(np.linalg.norm(quad[1] - quad[0]))
    bottom = float(np.linalg.norm(quad[2] - quad[3]))
    left = float(np.linalg.norm(quad[3] - quad[0]))
    right = float(np.linalg.norm(quad[2] - quad[1]))
    width = max(top, bottom)
    height = max(left, right)
    return width, height


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
    contour_area: float,
    image_shape: tuple[int, int],
    expected_ratio: float | None,
    grid_score: float,
) -> float:
    x, y, w, h = bbox
    image_height, image_width = image_shape
    image_area = image_height * image_width

    center_x = x + (w / 2)
    center_y = y + (h / 2)
    x_center_score = max(0.0, 1.0 - (abs(center_x - (image_width / 2)) / max(image_width / 2, 1)))
    y_center_score = max(0.0, 1.0 - (abs(center_y - (image_height / 2)) / max(image_height / 2, 1)))

    area_score = min(1.0, (w * h) / max(image_area * 0.3, 1))
    fill_score = min(1.0, contour_area / max(w * h, 1))
    bbox_ratio = w / max(h, 1)
    aspect_score = 1.0
    if expected_ratio is not None:
        aspect_score = max(0.0, 1.0 - (abs(bbox_ratio - expected_ratio) / max(expected_ratio, 1e-6)))

    return (
        (x_center_score * 0.27)
        + (y_center_score * 0.08)
        + (area_score * 0.2)
        + (fill_score * 0.12)
        + (aspect_score * 0.18)
        + (grid_score * 0.15)
    )


def _build_candidate_from_contours(
    image: np.ndarray,
    contours: list[np.ndarray],
    expected_width: int | None,
    expected_height: int | None,
    *,
    merged: bool = False,
) -> BoardCandidate | None:
    if not contours:
        return None

    points = np.vstack(contours)
    x, y, w, h = cv2.boundingRect(points)
    if w <= 1 or h <= 1:
        return None

    contour_area = float(sum(cv2.contourArea(contour) for contour in contours))
    bbox = (x, y, w, h)
    quad = _build_candidate_quad(points.reshape(-1, 2), bbox)
    expected_ratio = (expected_width / expected_height) if expected_width and expected_height else None

    crop = _crop_from_bbox(image, bbox, expected_width, expected_height)
    grid_score = 0.0
    if expected_width and expected_height and crop.size > 0:
        grid_score = score_expected_grid(crop, expected_width, expected_height)

    score = _score_candidate(
        bbox,
        contour_area,
        image.shape[:2],
        expected_ratio,
        grid_score,
    )
    return BoardCandidate(
        bbox=bbox,
        contours=contours,
        quad=quad,
        score=score,
        source_area=int(contour_area),
        merged=merged,
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
    contour_overlay: np.ndarray,
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
        cv2.polylines(contour_overlay, [candidate.quad.astype(np.int32)], True, (255, 0, 0), 2)

    max_merge_inputs = min(6, len(plausible_contours))
    for size in range(2, max_merge_inputs + 1):
        for grouped_contours in combinations(plausible_contours[:max_merge_inputs], size):
            merged_candidate = _build_candidate_from_contours(
                image,
                list(grouped_contours),
                expected_width,
                expected_height,
                merged=True,
            )
            if merged_candidate is None:
                continue
            if not _candidate_is_plausible(merged_candidate, image.shape[:2], expected_ratio):
                continue
            candidates.append(merged_candidate)
            cv2.polylines(contour_overlay, [merged_candidate.quad.astype(np.int32)], True, (255, 165, 0), 3)

    return candidates


def _detect_board_candidate_impl(
    image: np.ndarray,
    *,
    expected_width: int | None,
    expected_height: int | None,
    include_debug: bool,
) -> tuple[BoardCandidate | None, BoardDetectionDebug | None]:
    preprocess = build_preprocess_stages(image)
    board_mask = preprocess.board_mask
    edges = preprocess.edges

    mask_contours, _ = cv2.findContours(board_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    edge_contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    contour_overlay = image.copy()
    if mask_contours:
        cv2.drawContours(contour_overlay, mask_contours, -1, (0, 255, 0), 2)

    candidates = _collect_candidates(
        image,
        mask_contours,
        expected_width,
        expected_height,
        contour_overlay,
    )
    edge_candidates = _collect_candidates(
        image,
        edge_contours,
        expected_width,
        expected_height,
        contour_overlay,
    )
    candidates.extend(edge_candidates)

    if not candidates:
        debug = None
        if include_debug:
            debug = BoardDetectionDebug(
                contour_overlay=contour_overlay,
                selected_bbox_overlay=contour_overlay.copy(),
            )
        return None, debug

    best_candidate = max(candidates, key=lambda candidate: candidate.score)

    if not include_debug:
        return best_candidate, None

    selected_bbox_overlay = contour_overlay.copy()
    cv2.drawContours(selected_bbox_overlay, best_candidate.contours, -1, (0, 255, 255), 2)
    cv2.polylines(selected_bbox_overlay, [best_candidate.quad.astype(np.int32)], True, (0, 0, 255), 3)
    x, y, w, h = best_candidate.bbox
    cv2.rectangle(selected_bbox_overlay, (x, y), (x + w, y + h), (255, 255, 0), 2)

    return best_candidate, BoardDetectionDebug(
        contour_overlay=contour_overlay,
        selected_bbox_overlay=selected_bbox_overlay,
    )


def detect_board_candidate(
    image: np.ndarray,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> BoardCandidate | None:
    candidate, _ = _detect_board_candidate_impl(
        image,
        expected_width=expected_width,
        expected_height=expected_height,
        include_debug=False,
    )
    return candidate


def detect_board_candidate_with_debug(
    image: np.ndarray,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> tuple[BoardCandidate | None, BoardDetectionDebug]:
    candidate, debug = _detect_board_candidate_impl(
        image,
        expected_width=expected_width,
        expected_height=expected_height,
        include_debug=True,
    )
    return candidate, debug or BoardDetectionDebug(
        contour_overlay=image.copy(),
        selected_bbox_overlay=image.copy(),
    )


def crop_board_region(
    image: np.ndarray,
    candidate: BoardCandidate,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> np.ndarray:
    quad = candidate.quad.astype(np.float32)
    quad_width, quad_height = _quad_dimensions(quad)
    if quad_width <= 1 or quad_height <= 1:
        return _crop_from_bbox(image, candidate.bbox, expected_width, expected_height)

    if expected_width and expected_height:
        ratio = expected_width / expected_height
        output_width = max(int(round(max(quad_width, quad_height * ratio))), expected_width * 40)
        output_height = max(int(round(output_width / ratio)), expected_height * 40)
    else:
        output_width = max(int(round(quad_width)), 1)
        output_height = max(int(round(quad_height)), 1)

    destination = np.array(
        [
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(quad, destination)
    return cv2.warpPerspective(image, matrix, (output_width, output_height))
