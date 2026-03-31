from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import create_app
from tests.fixture_helpers import get_screenshot_entry, get_screenshot_path, load_screenshot_metadata


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


def test_create_upload_from_fixture_metadata(tmp_path):
    client = make_client(tmp_path)
    entry = get_screenshot_entry("a.jpeg")
    image_path = get_screenshot_path(entry["file_name"])

    with image_path.open("rb") as image_file:
        response = client.post(
            "/uploads",
            data={
                "puzzle_number": str(entry["puzzle_number"]),
                "board_width": str(entry["board_width"]),
                "board_height": str(entry["board_height"]),
            },
            files={"image": (image_path.name, image_file, "image/jpeg")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "uploaded"
    assert payload["puzzle_number"] == entry["puzzle_number"]
    assert payload["board_width"] == entry["board_width"]
    assert payload["board_height"] == entry["board_height"]
    assert payload["content_type"] == "image/jpeg"
    assert payload["file_size"] == image_path.stat().st_size
    assert Path(payload["file_path"]).exists()


def test_create_upload_rejects_unsupported_type(tmp_path: str):
    client = make_client(tmp_path)

    response = client.post(
        "/uploads",
        data={"puzzle_number": "22", "board_width": "5", "board_height": "5"},
        files={"image": ("sample.txt", BytesIO(b"not-an-image"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported image type."


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
