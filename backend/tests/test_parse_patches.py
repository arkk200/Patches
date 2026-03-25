from pathlib import Path

from app.services.parse_patches import parse_patches


ROOT = Path(__file__).resolve().parents[2]
PUZZLES_DIR = ROOT / "puzzles"


def test_parse_sample_puzzle_1():
    draft = parse_patches((PUZZLES_DIR / "1.patches").read_text())

    assert draft.width == 5
    assert draft.height == 5
    assert draft.board_rows == ["..a..", ".....", "b.c.d", ".....", "..e.."]
    assert [patch.id for patch in draft.patches] == ["a", "b", "c", "d", "e"]
    assert draft.patches[0].row == 0
    assert draft.patches[0].col == 2
    assert draft.patches[0].size == 5
    assert draft.patches[0].shape == "wide"


def test_parse_sample_puzzle_2_positions():
    draft = parse_patches((PUZZLES_DIR / "2.patches").read_text())

    assert draft.width == 5
    assert draft.height == 5
    patch_a = next(patch for patch in draft.patches if patch.id == "a")
    patch_e = next(patch for patch in draft.patches if patch.id == "e")
    assert patch_a.row == 0 and patch_a.col == 0
    assert patch_e.row == 4 and patch_e.col == 4
    assert patch_e.shape == "tall"


def test_parse_sample_puzzle_3_unknown_size():
    draft = parse_patches((PUZZLES_DIR / "3.patches").read_text())

    assert draft.width == 6
    assert draft.height == 6
    patch_d = next(patch for patch in draft.patches if patch.id == "d")
    patch_e = next(patch for patch in draft.patches if patch.id == "e")
    patch_h = next(patch for patch in draft.patches if patch.id == "h")
    assert patch_d.size is None
    assert patch_e.size is None
    assert patch_d.shape == "wide"
    assert patch_e.shape == "tall"
    assert patch_h.row == 5 and patch_h.col == 4
    assert patch_h.shape == "square"
