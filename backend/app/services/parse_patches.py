from app.schemas.puzzle import PatchDefinition, PuzzleDraft


def parse_patches(content: str) -> PuzzleDraft:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Patches content is empty")

    size_line = lines[0]
    if "x" not in size_line:
        raise ValueError(
            f"First line must be '<width>x<height>', got {size_line!r}"
        )
    width_text, height_text = size_line.split("x", maxsplit=1)
    try:
        width = int(width_text)
        height = int(height_text)
    except ValueError:
        raise ValueError(
            f"Invalid board dimensions: {size_line!r}"
        )
    if width < 1 or height < 1:
        raise ValueError(f"Board dimensions must be positive: {width}x{height}")

    if 1 + height > len(lines):
        raise ValueError(
            f"Board height {height} requires {height} row lines, "
            f"but only {len(lines) - 1} provided"
        )
    board_rows = lines[1 : 1 + height]
    patch_lines = lines[1 + height :]

    positions: dict[str, tuple[int, int]] = {}
    for row_index, row in enumerate(board_rows):
        for col_index, char in enumerate(row):
            if char != ".":
                positions[char] = (row_index, col_index)

    patches: list[PatchDefinition] = []
    for patch_line in patch_lines:
        parts = patch_line.split(":", maxsplit=2)
        if len(parts) < 3:
            raise ValueError(
                f"Invalid patch line (expected 'id:size:shape'): {patch_line!r}"
            )
        patch_id, size_text, shape = parts
        if patch_id not in positions:
            raise ValueError(
                f"Patch id {patch_id!r} found in definitions "
                f"but not on board grid"
            )
        row, col = positions[patch_id]
        try:
            size = None if size_text == "-" else int(size_text)
        except ValueError:
            raise ValueError(
                f"Invalid size value for patch {patch_id!r}: {size_text!r}"
            )
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
