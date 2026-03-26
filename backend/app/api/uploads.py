from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models.upload import Upload
from app.schemas.upload import UploadResponse
from app.services.path_builder import build_upload_image_path


router = APIRouter(prefix="/uploads", tags=["uploads"])

Base.metadata.create_all(bind=engine)

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def create_upload(
    puzzle_number: int = Form(..., ge=1),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type.",
        )

    upload_id = f"upl_{uuid4().hex[:12]}"
    suffix = Path(image.filename or "upload.png").suffix.lower() or ".png"
    file_path = build_upload_image_path(upload_id, extension=suffix)
    content = image.file.read()
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)

    created_at = datetime.now(timezone.utc)
    upload = Upload(
        id=upload_id,
        puzzle_number=puzzle_number,
        original_filename=image.filename or f"{upload_id}{suffix}",
        content_type=image.content_type,
        file_path=file_path,
        file_size=len(content),
        created_at=created_at,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    return UploadResponse(
        id=upload.id,
        puzzle_number=upload.puzzle_number,
        original_filename=upload.original_filename,
        content_type=upload.content_type,
        file_path=upload.file_path,
        file_size=upload.file_size,
        created_at=upload.created_at,
        status="uploaded",
    )
