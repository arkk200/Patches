from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import create_app


def test_create_upload(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
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
    client = TestClient(app)

    response = client.post(
        "/uploads",
        data={"puzzle_number": "22"},
        files={"image": ("sample.png", BytesIO(b"fake-image-content"), "image/png")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "uploaded"
    assert payload["puzzle_number"] == 22
    assert payload["content_type"] == "image/png"
    assert payload["file_size"] == len(b"fake-image-content")
    assert Path(payload["file_path"]).exists()


def test_create_upload_rejects_unsupported_type():
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/uploads",
        data={"puzzle_number": "22"},
        files={"image": ("sample.txt", BytesIO(b"not-an-image"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported image type."
