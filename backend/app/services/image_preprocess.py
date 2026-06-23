from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# ── Preprocessing constants ─────────────────────────────────────────────────
GAUSSIAN_KERNEL = (5, 5)
GAUSSIAN_SIGMA = 0
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)
SHARPEN_SIGMA = 1.2
SHARPEN_WEIGHT_ORIG = 1.35
SHARPEN_WEIGHT_BLUR = -0.35
CANNY_THRESHOLD_LOW = 35
CANNY_THRESHOLD_HIGH = 110
MORPH_CLOSE_KERNEL = (5, 5)
MORPH_DILATE_KERNEL = (3, 3)
MORPH_DILATE_ITERATIONS = 1
CONNECTIVITY = 8
MIN_COMPONENT_AREA = 24


@dataclass
class PreprocessStages:
    edges: np.ndarray


def load_image(image_path: str) -> np.ndarray:
    image = cv2.imread(str(Path(image_path)))
    if image is None:
        raise ValueError(f"Failed to load image: {image_path}")
    return image


def to_grayscale(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise_image(image: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(image, GAUSSIAN_KERNEL, GAUSSIAN_SIGMA)


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID)
    return clahe.apply(image)


def sharpen_image(image: np.ndarray) -> np.ndarray:
    softened = cv2.GaussianBlur(image, (0, 0), SHARPEN_SIGMA)
    return cv2.addWeighted(image, SHARPEN_WEIGHT_ORIG, softened, SHARPEN_WEIGHT_BLUR, 0)


def build_edge_map(image: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(image, CANNY_THRESHOLD_LOW, CANNY_THRESHOLD_HIGH)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_CLOSE_KERNEL)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, close_kernel)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_DILATE_KERNEL), iterations=MORPH_DILATE_ITERATIONS)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=CONNECTIVITY)
    cleaned = np.zeros_like(edges)
    for index in range(1, num_labels):
        if stats[index, cv2.CC_STAT_AREA] >= MIN_COMPONENT_AREA:
            cleaned[labels == index] = 255
    return cleaned


def build_preprocess_stages(image: np.ndarray) -> PreprocessStages:
    gray = to_grayscale(image)
    blurred = denoise_image(gray)
    enhanced = enhance_contrast(blurred)
    sharpened = sharpen_image(enhanced)
    edges = build_edge_map(sharpened)
    return PreprocessStages(
        edges=edges,
    )
