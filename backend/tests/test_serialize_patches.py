from pathlib import Path

from app.services.parse_patches import parse_patches
from app.services.serialize_patches import serialize_patches


ROOT = Path(__file__).resolve().parents[2]
PUZZLES_DIR = ROOT / "puzzles"


def test_serialize_round_trip_sample_1():
    original = (PUZZLES_DIR / "1.patches").read_text().strip()
    draft = parse_patches(original)

    assert serialize_patches(draft) == original


def test_serialize_round_trip_sample_2():
    original = (PUZZLES_DIR / "2.patches").read_text().strip()
    draft = parse_patches(original)

    assert serialize_patches(draft) == original


def test_serialize_round_trip_sample_3():
    original = (PUZZLES_DIR / "3.patches").read_text().strip()
    draft = parse_patches(original)

    assert serialize_patches(draft) == original
