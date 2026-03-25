from app.schemas.puzzle import PuzzleDraft


def serialize_patches(draft: PuzzleDraft) -> str:
    lines = [f"{draft.width}x{draft.height}"]
    lines.extend(draft.board_rows)

    for patch in sorted(draft.patches, key=lambda item: item.id):
        size_text = "-" if patch.size is None else str(patch.size)
        lines.append(f"{patch.id}:{size_text}:{patch.shape}")

    return "\n".join(lines)
