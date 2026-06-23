from dataclasses import dataclass
from enum import StrEnum

import cv2
import numpy as np


class CellShape(StrEnum):
    WIDE = "wide"
    TALL = "tall"
    SQUARE = "square"
    ANY = "any"


SATURATION_THRESHOLD = 25
SHAPE_RATIO_WIDE = 1.15
SHAPE_RATIO_TALL = 0.85
CLOSE_KERNEL_SIZE = 3
MIN_SHAPE_DIMENSION = 2


@dataclass
class CellSegment:
    row: int
    col: int
    cell_image: np.ndarray
    shape: CellShape | None = None


def _cell_has_color(cell_image: np.ndarray) -> bool:
    hsv = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)
    mean_saturation = hsv[:, :, 1].mean()
    return mean_saturation > SATURATION_THRESHOLD


def segment_cells(
    board_image: np.ndarray,
    board_width: int,
    board_height: int,
) -> list[CellSegment]:
    img_h, img_w = board_image.shape[:2]
    cell_h = img_h // board_height
    cell_w = img_w // board_width

    cells: list[CellSegment] = []

    for row in range(board_height):
        for col in range(board_width):
            y1 = row * cell_h
            y2 = (row + 1) * cell_h if row < board_height - 1 else img_h
            x1 = col * cell_w
            x2 = (col + 1) * cell_w if col < board_width - 1 else img_w

            cell = board_image[y1:y2, x1:x2].copy()

            if _cell_has_color(cell):
                cells.append(CellSegment(row=row, col=col, cell_image=cell))

    return cells


def _classify_cell_shape(cell_image: np.ndarray) -> CellShape:
    hsv = cv2.cvtColor(cell_image, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    _, mask = cv2.threshold(sat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_KERNEL_SIZE, CLOSE_KERNEL_SIZE))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return CellShape.ANY

    all_pts = np.vstack(contours)
    _, _, w, h = cv2.boundingRect(all_pts)

    if w <= MIN_SHAPE_DIMENSION or h <= MIN_SHAPE_DIMENSION:
        return CellShape.ANY

    ratio = w / h
    if ratio >= SHAPE_RATIO_WIDE:
        return CellShape.WIDE
    if ratio <= SHAPE_RATIO_TALL:
        return CellShape.TALL
    return CellShape.SQUARE


def classify_cell_shapes(cells: list[CellSegment]) -> list[CellSegment]:
    return [
        CellSegment(
            row=c.row,
            col=c.col,
            cell_image=c.cell_image,
            shape=_classify_cell_shape(c.cell_image),
        )
        for c in cells
    ]
