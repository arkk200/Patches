from pathlib import Path

from app.config import settings


def build_upload_image_path(upload_id: str, extension: str = ".png") -> str:
    return str(Path(settings.uploads_dir) / f"{upload_id}{extension}")

