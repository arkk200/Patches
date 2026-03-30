from dataclasses import dataclass, field

import cv2
import numpy as np

from app.services.image_preprocess import to_grayscale


@dataclass
class GridCandidate:
    width: int
    height: int
    confidence: float


@dataclass
class GridDetectionResult:
    width: int | None
    height: int | None
    confidence: float
    row_peak_count: int
    col_peak_count: int
    candidate_sizes: list[GridCandidate] = field(default_factory=list)
    binary: np.ndarray | None = None
    horizontal_lines: np.ndarray | None = None
    vertical_lines: np.ndarray | None = None
    overlay: np.ndarray | None = None


def detect_grid_size(
    board_image: np.ndarray,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> tuple[int | None, int | None, float]:
    result = _detect_grid_size_impl(
        board_image,
        expected_width=expected_width,
        expected_height=expected_height,
        include_debug=False,
    )
    return result.width, result.height, result.confidence


def detect_grid_size_with_debug(
    board_image: np.ndarray,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> GridDetectionResult:
    return _detect_grid_size_impl(
        board_image,
        expected_width=expected_width,
        expected_height=expected_height,
        include_debug=True,
    )


def _detect_grid_size_impl(
    board_image: np.ndarray,
    *,
    expected_width: int | None,
    expected_height: int | None,
    include_debug: bool,
) -> GridDetectionResult:
    binary = _build_binary(board_image)
    horizontal_lines, vertical_lines = _extract_line_images(binary, board_image)
    horizontal_profile = horizontal_lines.sum(axis=1)
    vertical_profile = vertical_lines.sum(axis=0)

    candidates: list[GridCandidate] = []

    row_peaks = _count_peaks(horizontal_profile)
    col_peaks = _count_peaks(vertical_profile)
    if row_peaks >= 2 and col_peaks >= 2:
        detected_height = row_peaks - 1
        detected_width = col_peaks - 1
        confidence = min(0.99, 0.5 + (0.05 * (row_peaks + col_peaks)))
        candidates.append(GridCandidate(width=detected_width, height=detected_height, confidence=confidence))

    periodic_width = _estimate_periodic_count(vertical_profile)
    periodic_height = _estimate_periodic_count(horizontal_profile)
    if periodic_width and periodic_height:
        candidates.append(GridCandidate(width=periodic_width, height=periodic_height, confidence=0.45))

    if expected_width is not None and expected_height is not None:
        guided_confidence = _score_expected_grid_fit(binary, expected_width, expected_height)
        candidates.append(GridCandidate(width=expected_width, height=expected_height, confidence=guided_confidence))

    best_width: int | None = None
    best_height: int | None = None
    best_confidence = 0.0
    if candidates:
        best = max(candidates, key=lambda item: item.confidence)
        if expected_width is not None and expected_height is not None:
            best = max(
                candidates,
                key=lambda item: item.confidence + (0.35 if (item.width, item.height) == (expected_width, expected_height) else 0.0),
            )
            if (best.width, best.height) == (expected_width, expected_height):
                best_width = expected_width
                best_height = expected_height
                best_confidence = min(0.99, best.confidence + 0.1)
            else:
                best_width = best.width
                best_height = best.height
                best_confidence = best.confidence
        else:
            best_width = best.width
            best_height = best.height
            best_confidence = best.confidence

    overlay = _render_grid_overlay(board_image, best_width, best_height) if include_debug else None
    return GridDetectionResult(
        width=best_width,
        height=best_height,
        confidence=best_confidence,
        row_peak_count=row_peaks,
        col_peak_count=col_peaks,
        candidate_sizes=candidates,
        binary=binary if include_debug else None,
        horizontal_lines=horizontal_lines if include_debug else None,
        vertical_lines=vertical_lines if include_debug else None,
        overlay=overlay,
    )


def score_expected_grid(board_image: np.ndarray, expected_width: int, expected_height: int) -> float:
    binary = _build_binary(board_image)
    return _score_expected_grid_fit(binary, expected_width, expected_height)


def _build_binary(board_image: np.ndarray) -> np.ndarray:
    gray = to_grayscale(board_image)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21,
        5,
    )


def _extract_line_images(binary: np.ndarray, board_image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, board_image.shape[1] // 8), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, board_image.shape[0] // 8)))

    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    return horizontal, vertical


def _build_profiles(binary: np.ndarray, board_image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    horizontal, vertical = _extract_line_images(binary, board_image)
    return horizontal.sum(axis=1), vertical.sum(axis=0)


def _count_peaks(profile: np.ndarray) -> int:
    if profile.size == 0 or profile.max() <= 0:
        return 0
    threshold = profile.max() * 0.35
    active = profile > threshold
    count = 0
    in_peak = False
    for value in active:
        if value and not in_peak:
            count += 1
            in_peak = True
        elif not value:
            in_peak = False
    return count


def _estimate_periodic_count(profile: np.ndarray) -> int | None:
    if profile.size == 0 or profile.max() <= 0:
        return None
    active = np.where(profile > profile.max() * 0.2)[0]
    if active.size < 2:
        return None
    span = int(active[-1] - active[0])
    if span <= 0:
        return None

    best_count = None
    best_error = None
    for candidate in range(3, 11):
        cell_size = span / candidate
        error = abs((cell_size * candidate) - span)
        if best_error is None or error < best_error:
            best_error = error
            best_count = candidate
    return best_count


def _score_expected_grid_fit(binary: np.ndarray, expected_width: int, expected_height: int) -> float:
    if expected_width <= 0 or expected_height <= 0:
        return 0.0

    height, width = binary.shape
    cell_width = width / expected_width
    cell_height = height / expected_height
    if cell_width < 5 or cell_height < 5:
        return 0.0

    vertical_scores = []
    for index in range(1, expected_width):
        x = int(round(index * cell_width))
        stripe = binary[:, max(0, x - 1) : min(width, x + 2)]
        vertical_scores.append(float(stripe.mean() / 255.0))

    horizontal_scores = []
    for index in range(1, expected_height):
        y = int(round(index * cell_height))
        stripe = binary[max(0, y - 1) : min(height, y + 2), :]
        horizontal_scores.append(float(stripe.mean() / 255.0))

    combined = vertical_scores + horizontal_scores
    if not combined:
        return 0.0
    return min(0.95, sum(combined) / len(combined))


def _render_grid_overlay(board_image: np.ndarray, width: int | None, height: int | None) -> np.ndarray:
    overlay = board_image.copy()
    if width is None or height is None or width <= 0 or height <= 0:
        return overlay

    image_height, image_width = board_image.shape[:2]
    cell_width = image_width / width
    cell_height = image_height / height

    for index in range(1, width):
        x = int(round(index * cell_width))
        cv2.line(overlay, (x, 0), (x, image_height), (0, 255, 0), 2)
    for index in range(1, height):
        y = int(round(index * cell_height))
        cv2.line(overlay, (0, y), (image_width, y), (0, 255, 0), 2)

    return overlay
