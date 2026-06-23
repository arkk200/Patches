import json
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import settings
from app.main import create_app


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCREENSHOTS_DIR = FIXTURES_DIR / "screenshots"
PUZZLES_DIR = FIXTURES_DIR / "puzzles"


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Use temp dirs so tests never write to real storage."""
    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "artifacts_dir", str(tmp_path / "artifacts"))


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


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app = create_app()
    with TestClient(app) as c:
        yield c
