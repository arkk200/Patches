from app.schemas.puzzle import PatchDefinition, PuzzleDraft


def parse_patches(content: str) -> PuzzleDraft:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    size_line = lines[0]
    width_text, height_text = size_line.split("x", maxsplit=1)
    width = int(width_text)
    height = int(height_text)

    board_rows = lines[1 : 1 + height]
    patch_lines = lines[1 + height :]

    positions: dict[str, tuple[int, int]] = {}
    for row_index, row in enumerate(board_rows):
        for col_index, char in enumerate(row):
            if char != ".":
                positions[char] = (row_index, col_index)

    patches: list[PatchDefinition] = []
    for patch_line in patch_lines:
        patch_id, size_text, shape = patch_line.split(":", maxsplit=2)
        row, col = positions[patch_id]
        size = None if size_text == "-" else int(size_text)
        patches.append(
            PatchDefinition(
                id=patch_id,
                row=row,
                col=col,
                size=size,
                shape=shape,
            )
        )

    return PuzzleDraft(
        width=width,
        height=height,
        board_rows=board_rows,
        patches=patches,
    )
