from datetime import datetime

from pydantic import BaseModel


class ExtractionArtifacts(BaseModel):
    board_bbox: list[int] | None = None
    warped_board_path: str | None = None


class ExtractionJobResponse(BaseModel):
    job_id: str
    upload_id: str
    status: str
    board_width: int
    board_height: int
    overall_confidence: float | None
    created_at: datetime
    updated_at: datetime
    artifacts: ExtractionArtifacts
