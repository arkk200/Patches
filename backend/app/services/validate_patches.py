from app.schemas.puzzle import ALLOWED_SHAPES, PuzzleDraft, ValidationIssue


def validate_puzzle_draft(draft: PuzzleDraft) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if len(draft.board_rows) != draft.height:
        issues.append(
            ValidationIssue(
                code="INVALID_BOARD_HEIGHT",
                message="Board row count must match height.",
                field="board_rows",
            )
        )

    board_ids: set[str] = set()
    for row_index, row in enumerate(draft.board_rows):
        if len(row) != draft.width:
            issues.append(
                ValidationIssue(
                    code="INVALID_ROW_LENGTH",
                    message="Board row length must match width.",
                    field=f"board_rows[{row_index}]",
                )
            )
        for col_index, char in enumerate(row):
            if char == ".":
                continue
            if not (char.islower() and len(char) == 1):
                issues.append(
                    ValidationIssue(
                        code="INVALID_BOARD_SYMBOL",
                        message="Board cells must contain '.' or a lowercase id.",
                        field=f"board_rows[{row_index}][{col_index}]",
                    )
                )
            board_ids.add(char)

    patch_ids: list[str] = []
    for patch in draft.patches:
        patch_ids.append(patch.id)
        if patch.shape not in ALLOWED_SHAPES:
            issues.append(
                ValidationIssue(
                    code="INVALID_SHAPE",
                    message="Patch shape must be one of wide, tall, square, any.",
                    field=f"patches.{patch.id}.shape",
                )
            )

    duplicate_patch_ids = {patch_id for patch_id in patch_ids if patch_ids.count(patch_id) > 1}
    for patch_id in sorted(duplicate_patch_ids):
        issues.append(
            ValidationIssue(
                code="DUPLICATE_PATCH_ID",
                message="Patch id must be unique.",
                field=f"patches.{patch_id}",
            )
        )

    missing_definitions = sorted(board_ids - set(patch_ids))
    for patch_id in missing_definitions:
        issues.append(
            ValidationIssue(
                code="MISSING_PATCH_DEFINITION",
                message="Board id is missing a patch definition.",
                field=f"patches.{patch_id}",
            )
        )

    extra_definitions = sorted(set(patch_ids) - board_ids)
    for patch_id in extra_definitions:
        issues.append(
            ValidationIssue(
                code="EXTRA_PATCH_DEFINITION",
                message="Patch definition id does not appear on the board.",
                field=f"patches.{patch_id}",
            )
        )

    return issues
