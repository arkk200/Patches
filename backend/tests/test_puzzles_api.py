from pathlib import Path

import cv2
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fixture_helpers import get_screenshot_entry, get_screenshot_path, load_screenshot_metadata


def make_client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_create_puzzle_extraction_happy_path():
    client = make_client()
    entry = get_screenshot_entry("a.jpeg")
    image_path = get_screenshot_path(entry["file_name"])
    content_type = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"

    with image_path.open("rb") as image_file:
        response = client.post(
            "/puzzles",
            data={
                "puzzle_number": str(entry["puzzle_number"]),
                "board_width": str(entry["board_width"]),
                "board_height": str(entry["board_height"]),
            },
            files={"image": (image_path.name, image_file, content_type)},
        )

    assert response.status_code == 201
    payload = response.json()

    assert payload["puzzle_number"] == entry["puzzle_number"]
    assert payload["board_width"] == entry["board_width"]
    assert payload["board_height"] == entry["board_height"]
    assert payload["status"] == "completed"
    assert payload["confidence"] is not None
    assert payload["board_bbox"] is not None
    assert payload["board_path"] is not None
    assert Path(payload["board_path"]).exists()

    x, y, w, h = payload["board_bbox"]
    center_x = x + (w / 2)
    assert 0 <= x < 120
    assert 350 <= y <= 500
    assert w > 900
    assert h > 900
    assert abs(w - h) < 120
    assert abs(center_x - 540) < 40

    crop = cv2.imread(payload["board_path"])
    assert crop is not None
    height, width = crop.shape[:2]
    assert abs((width / height) - (entry["board_width"] / entry["board_height"])) < 0.05


def test_create_puzzle_extraction_all_fixtures():
    client = make_client()

    for file_name in ("a.jpeg", "b.png", "c.png"):
        entry = get_screenshot_entry(file_name)
        image_path = get_screenshot_path(entry["file_name"])
        content_type = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"

        with image_path.open("rb") as image_file:
            response = client.post(
                "/puzzles",
                data={
                    "puzzle_number": str(entry["puzzle_number"]),
                    "board_width": str(entry["board_width"]),
                    "board_height": str(entry["board_height"]),
                },
                files={"image": (image_path.name, image_file, content_type)},
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "completed"
        assert payload["board_bbox"] is not None
        assert payload["board_path"] is not None
        assert Path(payload["board_path"]).exists()


def test_create_puzzle_extraction_rejects_unsupported_type():
    client = make_client()
    from io import BytesIO

    response = client.post(
        "/puzzles",
        data={"puzzle_number": "1", "board_width": "5", "board_height": "5"},
        files={"image": ("sample.txt", BytesIO(b"not-an-image"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported image type."


def test_create_puzzle_extraction_returns_failed_when_no_board_found(monkeypatch):
    client = make_client()

    from app.api import puzzles as puzzles_api
    from app.services.cv_extract import BoardExtractionResult

    def fake_extract_board(*args, **kwargs):
        return BoardExtractionResult(
            confidence=0.0,
            board_bbox=None,
            board_path=None,
        )

    monkeypatch.setattr(puzzles_api, "extract_board", fake_extract_board)

    entry = get_screenshot_entry("a.jpeg")
    image_path = get_screenshot_path(entry["file_name"])

    with image_path.open("rb") as image_file:
        response = client.post(
            "/puzzles",
            data={
                "puzzle_number": str(entry["puzzle_number"]),
                "board_width": str(entry["board_width"]),
                "board_height": str(entry["board_height"]),
            },
            files={"image": (image_path.name, image_file, "image/jpeg")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["board_path"] is None
    assert payload["board_bbox"] is None
    assert payload["confidence"] is None


def test_fixture_metadata_covers_expected_screenshots():
    metadata = load_screenshot_metadata()

    assert [entry["puzzle_number"] for entry in metadata] == [1, 2, 3]
    assert [(entry["board_width"], entry["board_height"]) for entry in metadata] == [
        (5, 5),
        (6, 6),
        (6, 6),
    ]

    for file_name in ("a.jpeg", "b.png", "c.png"):
        assert get_screenshot_path(file_name).exists()
