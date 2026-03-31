from pathlib import Path

import cv2
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import create_app
from tests.fixture_helpers import get_screenshot_entry, get_screenshot_path


def assert_a_jpeg_board_selection(board_bbox: list[int], selected_quad: list[list[int]] | None = None):
    x, y, w, h = board_bbox
    center_x = x + (w / 2)
    assert 0 <= x < 120
    assert 350 <= y <= 500
    assert w > 900
    assert h > 900
    assert abs(w - h) < 120
    assert abs(center_x - 540) < 40

    if selected_quad is not None:
        xs = [point[0] for point in selected_quad]
        ys = [point[1] for point in selected_quad]
        assert min(xs) < 120
        assert 350 <= min(ys) <= 500
        assert max(xs) - min(xs) > 900
        assert max(ys) - min(ys) > 900
        assert abs(((min(xs) + max(xs)) / 2) - 540) < 40


def make_client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    app = create_app()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def upload_fixture(client: TestClient, file_name: str):
    entry = get_screenshot_entry(file_name)
    image_path = get_screenshot_path(file_name)
    content_type = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"

    with image_path.open("rb") as image_file:
        response = client.post(
            "/uploads",
            data={
                "puzzle_number": str(entry["puzzle_number"]),
                "board_width": str(entry["board_width"]),
                "board_height": str(entry["board_height"]),
            },
            files={"image": (image_path.name, image_file, content_type)},
        )

    assert response.status_code == 201
    return response.json(), entry


def test_create_extraction_job_after_fixture_upload(tmp_path):
    client = make_client(tmp_path)
    upload_payload, entry = upload_fixture(client, "a.jpeg")

    response = client.post(f"/extractions/{upload_payload['id']}")
    assert response.status_code == 201
    payload = response.json()

    assert payload["upload_id"] == upload_payload["id"]
    assert payload["status"] == "completed"
    assert payload["board_width"] == entry["board_width"]
    assert payload["board_height"] == entry["board_height"]
    assert payload["debug_enabled"] is False
    assert payload["debug_artifacts"] is None
    assert "detected_width" not in payload
    assert "detected_height" not in payload
    assert Path(payload["artifacts"]["warped_board_path"]).exists()
    assert payload["artifacts"]["board_bbox"] is not None
    assert_a_jpeg_board_selection(payload["artifacts"]["board_bbox"])
    assert "job_id" in payload

    crop = cv2.imread(payload["artifacts"]["warped_board_path"])
    assert crop is not None
    height, width = crop.shape[:2]
    assert abs((width / height) - (entry["board_width"] / entry["board_height"])) < 0.05


def test_create_extraction_job_with_debug_artifacts(tmp_path):
    client = make_client(tmp_path)
    upload_payload, entry = upload_fixture(client, "a.jpeg")

    response = client.post(f"/extractions/{upload_payload['id']}?debug=true")
    assert response.status_code == 201
    payload = response.json()

    assert payload["debug_enabled"] is True
    debug_artifacts = payload["debug_artifacts"]
    assert debug_artifacts is not None
    assert Path(debug_artifacts["preprocess"]["grayscale_path"]).exists()
    assert Path(debug_artifacts["preprocess"]["blurred_path"]).exists()
    assert Path(debug_artifacts["preprocess"]["enhanced_path"]).exists()
    assert Path(debug_artifacts["preprocess"]["sharpened_path"]).exists()
    assert Path(debug_artifacts["preprocess"]["edges_path"]).exists()
    assert Path(debug_artifacts["preprocess"]["board_mask_path"]).exists()
    assert Path(debug_artifacts["layout"]["contour_overlay_path"]).exists()
    assert Path(debug_artifacts["layout"]["selected_bbox_overlay_path"]).exists()
    assert Path(debug_artifacts["layout"]["board_crop_path"]).exists()
    assert debug_artifacts["layout"]["selected_bbox"] is not None
    assert debug_artifacts["layout"]["selected_quad"] is not None
    assert len(debug_artifacts["layout"]["selected_quad"]) == 4
    assert_a_jpeg_board_selection(debug_artifacts["layout"]["selected_bbox"], debug_artifacts["layout"]["selected_quad"])
    assert "grid" not in debug_artifacts

    crop = cv2.imread(debug_artifacts["layout"]["board_crop_path"])
    assert crop is not None
    height, width = crop.shape[:2]
    assert abs((width / height) - (entry["board_width"] / entry["board_height"])) < 0.05

    get_response = client.get(f"/extractions/{payload['job_id']}")
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["debug_enabled"] is True
    assert get_payload["debug_artifacts"] == debug_artifacts


def test_create_extraction_jobs_for_all_fixture_inputs(tmp_path):
    client = make_client(tmp_path)

    for file_name, expected in (("a.jpeg", (5, 5)), ("b.png", (6, 6)), ("c.png", (6, 6))):
        upload_payload, entry = upload_fixture(client, file_name)
        response = client.post(f"/extractions/{upload_payload['id']}")
        assert response.status_code == 201
        payload = response.json()
        assert payload["board_width"] == expected[0] == entry["board_width"]
        assert payload["board_height"] == expected[1] == entry["board_height"]
        assert "detected_width" not in payload
        assert "detected_height" not in payload


def test_get_extraction_job_not_found(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/extractions/job_missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Extraction job not found."


def test_create_extraction_job_returns_failed_when_crop_not_found(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    upload_payload, entry = upload_fixture(client, "a.jpeg")

    from app.api import extractions as extraction_api
    from app.services.cv_extract import BoardExtractionResult

    def fake_extract_board(*args, **kwargs):
        return BoardExtractionResult(
            confidence=0.0,
            board_bbox=None,
            warped_board_path=None,
            debug_enabled=kwargs.get("debug", False),
            debug_artifacts=None,
        )

    monkeypatch.setattr(extraction_api, "extract_board", fake_extract_board)

    response = client.post(f"/extractions/{upload_payload['id']}")
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["board_width"] == entry["board_width"]
    assert payload["board_height"] == entry["board_height"]
    assert payload["artifacts"]["warped_board_path"] is None
    assert payload["artifacts"]["board_bbox"] is None
    assert payload["debug_artifacts"] is None

    get_response = client.get(f"/extractions/{payload['job_id']}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "failed"
    assert get_response.json()["artifacts"]["warped_board_path"] is None
    assert get_response.json()["artifacts"]["board_bbox"] is None

    crop_ratio = entry["board_width"] / entry["board_height"]
    assert crop_ratio == 1.0
