from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


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
    return cv2.GaussianBlur(image, (5, 5), 0)


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(image)


def sharpen_image(image: np.ndarray) -> np.ndarray:
    softened = cv2.GaussianBlur(image, (0, 0), 1.2)
    return cv2.addWeighted(image, 1.35, softened, -0.35, 0)


def build_edge_map(image: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(image, 35, 110)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, close_kernel)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    cleaned = np.zeros_like(edges)
    for index in range(1, num_labels):
        if stats[index, cv2.CC_STAT_AREA] >= 24:
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
