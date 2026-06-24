import cv2
import numpy as np
import pytest

from app.services.image_preprocess import (
    build_edge_map,
    build_preprocess_stages,
    denoise_image,
    enhance_contrast,
    load_image,
    sharpen_image,
    to_grayscale,
)


class TestLoadImage:
    def test_loads_valid_image(self, tmp_path: pytest.TempPathFactory) -> None:
        img_path = str(tmp_path / "test.png")
        test_img = np.full((10, 10, 3), 128, dtype=np.uint8)
        cv2.imwrite(img_path, test_img)

        loaded = load_image(img_path)
        assert loaded.shape == (10, 10, 3)
        assert loaded.dtype == np.uint8

    def test_raises_on_missing_path(self) -> None:
        with pytest.raises(ValueError, match="Failed to load image"):
            load_image("/nonexistent/path.png")


class TestToGrayscale:
    def test_converts_bgr_to_gray(self) -> None:
        bgr = np.full((20, 20, 3), 128, dtype=np.uint8)
        gray = to_grayscale(bgr)
        assert gray.shape == (20, 20)
        assert gray.dtype == np.uint8

    def test_preserves_content(self) -> None:
        bgr = np.full((10, 10, 3), [100, 150, 200], dtype=np.uint8)
        gray = to_grayscale(bgr)
        expected = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        assert np.array_equal(gray, expected)


class TestDenoiseImage:
    def test_preserves_shape_and_type(self) -> None:
        gray = np.random.randint(0, 256, (30, 30), dtype=np.uint8)
        result = denoise_image(gray)
        assert result.shape == (30, 30)
        assert result.dtype == np.uint8


class TestEnhanceContrast:
    def test_preserves_shape_and_type(self) -> None:
        gray = np.random.randint(0, 256, (30, 30), dtype=np.uint8)
        result = enhance_contrast(gray)
        assert result.shape == (30, 30)
        assert result.dtype == np.uint8


class TestSharpenImage:
    def test_preserves_shape_and_type(self) -> None:
        gray = np.random.randint(0, 256, (30, 30), dtype=np.uint8)
        result = sharpen_image(gray)
        assert result.shape == (30, 30)
        assert result.dtype == np.uint8


class TestBuildEdgeMap:
    def test_returns_binary_image(self) -> None:
        gray = np.random.randint(0, 256, (30, 30), dtype=np.uint8)
        edges = build_edge_map(gray)
        assert edges.shape == (30, 30)
        assert edges.dtype == np.uint8
        assert set(np.unique(edges)).issubset({0, 255})

    def test_solid_image_produces_few_edges(self) -> None:
        gray = np.full((30, 30), 128, dtype=np.uint8)
        edges = build_edge_map(gray)
        edge_ratio = np.count_nonzero(edges) / edges.size
        assert edge_ratio < 0.05


class TestBuildPreprocessStages:
    def test_pipeline_returns_edges(self) -> None:
        color = np.random.randint(0, 256, (20, 20, 3), dtype=np.uint8)
        result = build_preprocess_stages(color)
        assert result.edges.shape == (20, 20)
        assert result.edges.dtype == np.uint8
