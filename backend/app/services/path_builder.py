from pathlib import Path

from app.config import settings


def build_upload_image_path(upload_id: str, extension: str = ".png") -> str:
    return str(Path(settings.uploads_dir) / f"{upload_id}{extension}")


def build_candidate_patches_path(puzzle_number: int, sequence: int) -> str:
    return str(Path(settings.generated_patches_dir) / f"{puzzle_number}-{sequence}.patches")


def build_final_patches_path(puzzle_number: int) -> str:
    return str(Path(settings.generated_patches_dir) / f"{puzzle_number}.patches")
