import json
from pathlib import Path


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SCREENSHOTS_DIR = FIXTURES_DIR / "screenshots"
SCREENSHOT_METADATA_PATH = SCREENSHOTS_DIR / "metadata.json"


def load_screenshot_metadata() -> list[dict]:
    payload = json.loads(SCREENSHOT_METADATA_PATH.read_text())
    return payload["screenshots"]


def get_screenshot_entry(file_name: str) -> dict:
    for entry in load_screenshot_metadata():
        if entry["file_name"] == file_name:
            return entry
    raise KeyError(file_name)


def get_screenshot_path(file_name: str) -> Path:
    return SCREENSHOTS_DIR / file_name
