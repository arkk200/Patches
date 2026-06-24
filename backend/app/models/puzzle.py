from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


class PuzzleResult(Base):
    __tablename__ = "puzzle_results"

    puzzle_number = Column(Integer, primary_key=True)
    extract_id = Column(String, unique=True, nullable=False)
    board_width = Column(Integer, nullable=False)
    board_height = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # "completed" | "failed"
    patches_json = Column(Text, nullable=False, default="[]")
    upload_filename = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
