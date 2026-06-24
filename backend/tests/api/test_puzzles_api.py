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


class TestGetPuzzleExtraction:
    def test_get_after_create_returns_same_data(
        self, client: TestClient, screenshots_dir: Path
    ) -> None:
        fixture_path = screenshots_dir / "a.jpeg"
        with open(fixture_path, "rb") as f:
            post_resp = client.post(
                "/puzzles",
                data={"puzzle_number": 99, "board_width": 5, "board_height": 5},
                files={"image": ("a.jpeg", f, "image/jpeg")},
            )
        assert post_resp.status_code == 201
        post_data = post_resp.json()

        get_resp = client.get("/puzzles/99")
        assert get_resp.status_code == 200
        get_data = get_resp.json()

        assert get_data["puzzle_number"] == post_data["puzzle_number"]
        assert get_data["board_width"] == post_data["board_width"]
        assert get_data["board_height"] == post_data["board_height"]
        assert get_data["status"] == post_data["status"]
        assert get_data["patches"] == post_data["patches"]

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        response = client.get("/puzzles/9999")
        assert response.status_code == 404
        assert "Puzzle not found" in response.text


class TestGetPuzzlePatches:
    def test_patches_after_create(
        self, client: TestClient, screenshots_dir: Path
    ) -> None:
        fixture_path = screenshots_dir / "a.jpeg"
        with open(fixture_path, "rb") as f:
            post_resp = client.post(
                "/puzzles",
                data={"puzzle_number": 50, "board_width": 5, "board_height": 5},
                files={"image": ("a.jpeg", f, "image/jpeg")},
            )
        assert post_resp.status_code == 201

        resp = client.get("/puzzles/50/patches")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"
        text = resp.text
        assert text.startswith("5x5")
        assert ":" in text

    def test_patches_nonexistent_returns_404(self, client: TestClient) -> None:
        response = client.get("/puzzles/9999/patches")
        assert response.status_code == 404


class TestGetPuzzleImages:
    def test_image_after_create(self, client: TestClient, screenshots_dir: Path) -> None:
        fixture_path = screenshots_dir / "a.jpeg"
        with open(fixture_path, "rb") as f:
            post_resp = client.post(
                "/puzzles",
                data={"puzzle_number": 60, "board_width": 5, "board_height": 5},
                files={"image": ("a.jpeg", f, "image/jpeg")},
            )
        assert post_resp.status_code == 201

        resp = client.get("/puzzles/60/image")
        assert resp.status_code == 200
        assert resp.headers["content-type"] in ("image/jpeg", "image/png")

    def test_board_image_after_create(self, client: TestClient, screenshots_dir: Path) -> None:
        fixture_path = screenshots_dir / "a.jpeg"
        with open(fixture_path, "rb") as f:
            post_resp = client.post(
                "/puzzles",
                data={"puzzle_number": 61, "board_width": 5, "board_height": 5},
                files={"image": ("a.jpeg", f, "image/jpeg")},
            )
        assert post_resp.status_code == 201

        resp = client.get("/puzzles/61/board_image")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_image_nonexistent_returns_404(self, client: TestClient) -> None:
        assert client.get("/puzzles/9999/image").status_code == 404

    def test_board_image_nonexistent_returns_404(self, client: TestClient) -> None:
        assert client.get("/puzzles/9999/board_image").status_code == 404
