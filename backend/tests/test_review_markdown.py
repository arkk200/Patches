from datetime import datetime

from app.schemas.puzzle import PatchDefinition, PuzzleDraft, ValidationIssue
from app.services.review_markdown import render_review_markdown


def test_render_review_markdown_contains_review_sections():
    draft = PuzzleDraft(
        width=5,
        height=5,
        board_rows=["..a..", ".....", "b.c.d", ".....", "..e.."],
        patches=[
            PatchDefinition(id="a", row=0, col=2, size=5, shape="wide"),
            PatchDefinition(id="c", row=2, col=2, size=None, shape="tall"),
        ],
    )
    issues = [
        ValidationIssue(code="LOW_CONFIDENCE_SIZE", message="patch c size is uncertain."),
    ]

    markdown = render_review_markdown(
        review_id="rev_1",
        upload_id="upl_1",
        puzzle_number=22,
        status="pending",
        created_at=datetime(2026, 4, 9, 9, 0, 0),
        image_path="backend/storage/uploads/upl_1.png",
        candidate_patches_path="backend/storage/generated-patches/22-1.patches",
        overall_confidence=0.82,
        requires_review=True,
        draft=draft,
        issues=issues,
        patch_confidences={"a": 0.97, "c": 0.61},
        reviewer_notes=["- c의 size를 재확인 필요"],
    )

    assert "review_id: rev_1" in markdown
    assert 'puzzle_number: "22"' in markdown
    assert "candidate_patches_path: backend/storage/generated-patches/22-1.patches" in markdown
    assert "LOW_CONFIDENCE_SIZE" in markdown
    assert "| a | 0 | 2 | 5 | wide | 0.97 |" in markdown
    assert "| c | 2 | 2 | ? | tall | 0.61 |" in markdown
    assert "## Reviewer Decision" in markdown
