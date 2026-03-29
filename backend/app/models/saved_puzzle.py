from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SavedPuzzle(Base):
    __tablename__ = "saved_puzzles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    puzzle_number: Mapped[int] = mapped_column(Integer, index=True)
    extraction_job_id: Mapped[str] = mapped_column(ForeignKey("extraction_jobs.id"), index=True)
    patches_file_path: Mapped[str] = mapped_column(String)
    patches_content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
