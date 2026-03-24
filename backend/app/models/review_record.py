from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    extraction_job_id: Mapped[str] = mapped_column(ForeignKey("extraction_jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    markdown_path: Mapped[str] = mapped_column(String)
    candidate_file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    issues_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
