from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient


class TestCreatePuzzleExtraction:
    def test_happy_path_with_fixture(self, client: TestClient, screenshots_dir: Path) -> None:
        fixture_path = screenshots_dir / "a.jpeg"
        with open(fixture_path, "rb") as f:
            response = client.post(
                "/puzzles",
                data={"puzzle_number": 1, "board_width": 5, "board_height": 5},
                files={"image": ("a.jpeg", f, "image/jpeg")},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["puzzle_number"] == 1
        assert data["board_width"] == 5
        assert data["board_height"] == 5
        assert data["status"] == "completed"
        assert "patches" in data
        assert isinstance(data["patches"], list)
        assert len(data["patches"]) > 0
        for patch in data["patches"]:
            assert "id" in patch
            assert "row" in patch
            assert "col" in patch
            assert "shape" in patch
            assert patch["shape"] in ("wide", "tall", "square", "cross")

    def test_rejects_unsupported_content_type(self, client: TestClient) -> None:
        response = client.post(
            "/puzzles",
            data={"puzzle_number": 1, "board_width": 5, "board_height": 5},
            files={"image": ("test.txt", b"not an image", "text/plain")},
        )

        assert response.status_code == 400
        assert "Unsupported image type" in response.text

    def test_blank_image_returns_failed_status(self, client: TestClient, tmp_path: pytest.TempPathFactory) -> None:
        blank_path = str(tmp_path / "blank.png")
        cv2.imwrite(blank_path, np.full((100, 100, 3), 255, dtype=np.uint8))

        with open(blank_path, "rb") as f:
            response = client.post(
                "/puzzles",
                data={"puzzle_number": 1, "board_width": 5, "board_height": 5},
                files={"image": ("blank.png", f, "image/png")},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "failed"
        assert data["patches"] == []

    def test_missing_required_fields_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/puzzles",
            files={"image": ("test.png", b"fake", "image/png")},
        )

        assert response.status_code == 422

    def test_invalid_puzzle_number_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/puzzles",
            data={"puzzle_number": 0, "board_width": 5, "board_height": 5},
            files={"image": ("test.png", b"fake", "image/png")},
        )

        assert response.status_code == 422

    def test_invalid_board_dimensions_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/puzzles",
            data={"puzzle_number": 1, "board_width": 0, "board_height": 0},
            files={"image": ("test.png", b"fake", "image/png")},
        )

        assert response.status_code == 422
