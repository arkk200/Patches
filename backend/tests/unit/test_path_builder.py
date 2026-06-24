from pathlib import Path

from app.config import settings
from app.services.path_builder import build_upload_image_path


class TestBuildUploadImagePath:
    def test_default_extension(self) -> None:
        upload_id = "puz_abc123"
        result = build_upload_image_path(upload_id)
        expected = str(Path(settings.uploads_dir) / f"{upload_id}.png")
        assert result == expected

    def test_custom_extension(self) -> None:
        upload_id = "puz_def456"
        result = build_upload_image_path(upload_id, extension=".jpeg")
        expected = str(Path(settings.uploads_dir) / f"{upload_id}.jpeg")
        assert result == expected
