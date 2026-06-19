from dataclasses import dataclass

import cv2
import numpy as np


SATURATION_THRESHOLD = 25


@dataclass
class CellSegment:
    row: int
    col: int
    cell_image: np.ndarray


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
