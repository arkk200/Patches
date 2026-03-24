from pathlib import Path

from app.config import settings


def build_upload_image_path(upload_id: str, extension: str = ".png") -> str:
    return str(Path(settings.uploads_dir) / f"{upload_id}{extension}")


def build_review_markdown_path(review_id: str, status: str = "pending") -> str:
    if status == "approved":
        base_dir = settings.reviews_approved_dir
    elif status == "rejected":
        base_dir = settings.reviews_rejected_dir
    else:
        base_dir = settings.reviews_pending_dir
    return str(Path(base_dir) / f"{review_id}.md")


def build_candidate_patches_path(puzzle_number: int, sequence: int) -> str:
    return str(Path(settings.generated_patches_dir) / f"{puzzle_number}-{sequence}.patches")


def build_final_patches_path(puzzle_number: int) -> str:
    return str(Path(settings.generated_patches_dir) / f"{puzzle_number}.patches")
