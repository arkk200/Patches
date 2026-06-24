import json
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import create_app
from app.models import PuzzleResult  # noqa: F401 — register model metadata on Base


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCREENSHOTS_DIR = FIXTURES_DIR / "screenshots"
PUZZLES_DIR = FIXTURES_DIR / "puzzles"


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Use temp dirs so tests never write to real storage."""
    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "artifacts_dir", str(tmp_path / "artifacts"))


@pytest.fixture
def db_engine(tmp_path: Path):
    """File-based temp SQLite so threads don't collide."""
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def client(db_engine) -> Generator[TestClient, None, None]:
    TestSessionLocal = sessionmaker(bind=db_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def fixtures_metadata() -> list[dict]:
    with open(SCREENSHOTS_DIR / "metadata.json") as f:
        data = json.load(f)
    return data["screenshots"]


@pytest.fixture(scope="session")
def screenshots_dir() -> Path:
    return SCREENSHOTS_DIR


@pytest.fixture(scope="session")
def puzzles_dir() -> Path:
    return PUZZLES_DIR
