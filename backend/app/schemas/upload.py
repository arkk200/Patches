from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    id: str
    puzzle_number: int = Field(ge=1)
    original_filename: str
    content_type: str
    file_path: str
    file_size: int
    created_at: datetime
    status: str
