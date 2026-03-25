from app.schemas.puzzle import PatchDefinition, PuzzleDraft
from app.services.validate_patches import validate_puzzle_draft


def test_validate_accepts_valid_draft():
    draft = PuzzleDraft(
        width=2,
        height=2,
        board_rows=["a.", ".b"],
        patches=[
            PatchDefinition(id="a", row=0, col=0, size=3, shape="wide"),
            PatchDefinition(id="b", row=1, col=1, size=None, shape="any"),
        ],
    )

    assert validate_puzzle_draft(draft) == []


def test_validate_rejects_invalid_shape_and_missing_patch():
    draft = PuzzleDraft(
        width=2,
        height=2,
        board_rows=["a.", ".."],
        patches=[
            PatchDefinition(id="a", row=0, col=0, size=3, shape="diagonal"),
        ],
    )

    issues = validate_puzzle_draft(draft)
    codes = {issue.code for issue in issues}

    assert "INVALID_SHAPE" in codes


def test_validate_rejects_extra_patch_definition():
    draft = PuzzleDraft(
        width=2,
        height=1,
        board_rows=["a."],
        patches=[
            PatchDefinition(id="a", row=0, col=0, size=3, shape="wide"),
            PatchDefinition(id="b", row=0, col=1, size=4, shape="tall"),
        ],
    )

    issues = validate_puzzle_draft(draft)
    codes = {issue.code for issue in issues}

    assert "EXTRA_PATCH_DEFINITION" in codes
