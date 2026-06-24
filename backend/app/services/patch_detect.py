from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np


class PatchShape(StrEnum):
    WIDE = "wide"
    TALL = "tall"
    SQUARE = "square"
    CROSS = "cross"


SATURATION_THRESHOLD = 10   # Lower captures gray/desaturated pieces; max bg sat across fixtures ≈ 2.5
SHAPE_RATIO_WIDE = 1.15   # w/h > 1.15 → WIDE
SHAPE_RATIO_TALL = 0.85   # w/h < 0.85 → TALL (long/short ≈ 1.18)
TALL_REF_RATIO = 0.66     # actual TALL piece short/long (e.g. e(2,2)=62/94)
CLOSE_KERNEL_SIZE = 3
MIN_SHAPE_DIMENSION = 2


@dataclass
class PatchSegment:
    row: int
    col: int
    cell_image: np.ndarray
    shape: PatchShape | None = None
    size: int | None = None


def _patch_has_color(cell_image: np.ndarray) -> bool:
    hsv = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)
    mean_saturation = hsv[:, :, 1].mean()
    return mean_saturation > SATURATION_THRESHOLD


def segment_patches(
    board_image: np.ndarray,
    board_width: int,
    board_height: int,
) -> list[PatchSegment]:
    img_h, img_w = board_image.shape[:2]
    cell_h = img_h // board_height
    cell_w = img_w // board_width

    cells: list[PatchSegment] = []

    for row in range(board_height):
        for col in range(board_width):
            y1 = row * cell_h
            y2 = (row + 1) * cell_h if row < board_height - 1 else img_h
            x1 = col * cell_w
            x2 = (col + 1) * cell_w if col < board_width - 1 else img_w

            cell = board_image[y1:y2, x1:x2].copy()

            if _patch_has_color(cell):
                cells.append(PatchSegment(row=row, col=col, cell_image=cell))

    return cells


def _extract_patch_ratio(cell_image: np.ndarray) -> float | None:
    hsv = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    _, mask = cv2.threshold(sat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_KERNEL_SIZE, CLOSE_KERNEL_SIZE))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    all_pts = np.vstack(contours)
    _, _, w, h = cv2.boundingRect(all_pts)

    if w <= MIN_SHAPE_DIMENSION or h <= MIN_SHAPE_DIMENSION:
        return None

    return w / h


def _classify_patch_shape(cell_image: np.ndarray) -> PatchShape:
    ratio = _extract_patch_ratio(cell_image)
    if ratio is None:
        return PatchShape.CROSS

    # Build Otsu mask (shared with _extract_patch_ratio but cheap so dup OK)
    cell_h, cell_w = cell_image.shape[:2]
    cell_area = cell_h * cell_w
    hsv = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    _, mask = cv2.threshold(sat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_KERNEL_SIZE, CLOSE_KERNEL_SIZE))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest = max(contours, key=cv2.contourArea)
        lx, ly, lw, lh = cv2.boundingRect(largest)
        bbox_fill_frac = (lw * lh) / cell_area if cell_area > 0 else 0

        # Greek cross detection: bbox corners are empty because cross arms
        # leave the 4 quadrants unfilled. Corner size derived from TALL piece
        # ratio: corner = (dim - dim * TALL_REF_RATIO) / 2  → arm protrusion.
        # Real pieces fill bbox corners.
        if SHAPE_RATIO_TALL <= ratio <= SHAPE_RATIO_WIDE and bbox_fill_frac > 0.4:
            csize = int(min(lw, lh) * (1.0 - TALL_REF_RATIO) / 2.0)
            if csize > 2:
                corners = [
                    mask[ly:ly + csize, lx:lx + csize],                          # TL
                    mask[ly:ly + csize, lx + lw - csize:lx + lw],                # TR
                    mask[ly + lh - csize:ly + lh, lx:lx + csize],                # BL
                    mask[ly + lh - csize:ly + lh, lx + lw - csize:lx + lw],      # BR
                ]
                empty_corners = sum(
                    1 for c in corners if np.sum(c > 0) / c.size < 0.3
                )
                if empty_corners >= 3:  # 항상 4일테지만, 혹시 모를 노이즈 티오 1개 허용
                    return PatchShape.CROSS

    if ratio >= SHAPE_RATIO_WIDE:
        return PatchShape.WIDE
    if ratio <= SHAPE_RATIO_TALL:
        return PatchShape.TALL
    return PatchShape.SQUARE


def classify_patch_shapes(cells: list[PatchSegment]) -> list[PatchSegment]:
    return [
        PatchSegment(
            row=c.row,
            col=c.col,
            cell_image=c.cell_image,
            shape=_classify_patch_shape(c.cell_image),
        )
        for c in cells
    ]
