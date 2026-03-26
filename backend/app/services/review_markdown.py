from datetime import datetime

from app.schemas.puzzle import PuzzleDraft, ValidationIssue


def render_review_markdown(
    *,
    review_id: str,
    upload_id: str,
    puzzle_number: int,
    status: str,
    created_at: datetime,
    image_path: str,
    candidate_patches_path: str | None,
    overall_confidence: float | None,
    requires_review: bool,
    draft: PuzzleDraft,
    issues: list[ValidationIssue],
    patch_confidences: dict[str, float] | None = None,
    reviewer_notes: list[str] | None = None,
) -> str:
    confidence_text = "-" if overall_confidence is None else f"{overall_confidence:.2f}"
    issue_codes = ", ".join(issue.code for issue in issues) if issues else "없음"
    issue_lines = "\n".join(
        f"- {issue.code}: {issue.message}" for issue in issues
    ) or "- 없음"
    board_text = "\n".join(draft.board_rows)
    candidate_line = (
        f"candidate_patches_path: {candidate_patches_path}\n" if candidate_patches_path else ""
    )
    patch_confidences = patch_confidences or {}
    reviewer_notes = reviewer_notes or ["- 없음"]
    notes_text = "\n".join(reviewer_notes)

    patch_rows = []
    for patch in draft.patches:
        size_text = "?" if patch.size is None else str(patch.size)
        confidence = patch_confidences.get(patch.id)
        confidence_text_for_patch = "-" if confidence is None else f"{confidence:.2f}"
        patch_rows.append(
            f"| {patch.id} | {patch.row} | {patch.col} | {size_text} | {patch.shape} | {confidence_text_for_patch} |"
        )
    patch_table = "\n".join(patch_rows) if patch_rows else "| - | - | - | - | - | - |"

    return (
        "---\n"
        f"review_id: {review_id}\n"
        f"upload_id: {upload_id}\n"
        f"puzzle_number: \"{puzzle_number}\"\n"
        f"status: {status}\n"
        f"created_at: {created_at.isoformat()}\n"
        f"image_path: {image_path}\n"
        f"{candidate_line}"
        f"overall_confidence: {confidence_text}\n"
        f"requires_review: {str(requires_review).lower()}\n"
        "---\n\n"
        "# Review Summary\n\n"
        "- OCR 결과에 불확실성이 있어 수동 검토가 필요합니다.\n"
        f"- 주요 이슈: {issue_codes}\n\n"
        "## Extraction Issues\n\n"
        f"{issue_lines}\n\n"
        "## Draft Puzzle\n\n"
        "### Grid Size\n\n"
        f"`{draft.width}x{draft.height}`\n\n"
        "### Board Layout\n\n"
        "```text\n"
        f"{board_text}\n"
        "```\n\n"
        "### Patch Definitions\n\n"
        "| ID | Row | Col | Size | Shape | Confidence |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"{patch_table}\n\n"
        "## Reviewer Decision\n\n"
        "- [ ] Approve as-is\n"
        "- [ ] Edit and approve\n"
        "- [ ] Reject\n\n"
        "## Reviewer Notes\n\n"
        f"{notes_text}\n"
    )
