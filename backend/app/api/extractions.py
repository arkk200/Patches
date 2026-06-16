import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.extraction_job import ExtractionJob
from app.models.upload import Upload
from app.schemas.extraction import ExtractionArtifacts, ExtractionJobResponse
from app.schemas.puzzle import PuzzleDraft
from app.services.cv_extract import extract_board


router = APIRouter(prefix="/extractions", tags=["extractions"])


@router.post("/{upload_id}", response_model=ExtractionJobResponse, status_code=status.HTTP_201_CREATED)
def create_extraction_job(upload_id: str, db: Session = Depends(get_db)) -> ExtractionJobResponse:
    upload = db.get(Upload, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found.")

    job_id = f"job_{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)
    artifacts_dir = Path(settings.artifacts_dir) / job_id
    extraction = extract_board(
        upload.file_path,
        str(artifacts_dir),
        board_width=upload.board_width,
        board_height=upload.board_height,
    )

    draft = PuzzleDraft(
        width=upload.board_width,
        height=upload.board_height,
        board_rows=["." * upload.board_width for _ in range(upload.board_height)],
        patches=[],
    )

    status_value = "completed" if extraction.warped_board_path else "failed"
    raw_result = {
        "board_bbox": list(extraction.board_bbox) if extraction.board_bbox else None,
        "warped_board_path": extraction.warped_board_path,
    }

    job = ExtractionJob(
        id=job_id,
        upload_id=upload.id,

        status=status_value,
        overall_confidence=extraction.confidence,
        raw_result_json=json.dumps(raw_result),
        normalized_draft_json=draft.model_dump_json(),
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return ExtractionJobResponse(
        job_id=job.id,
        upload_id=job.upload_id,
        status=job.status,
        board_width=upload.board_width,
        board_height=upload.board_height,
        overall_confidence=job.overall_confidence,
        created_at=job.created_at,
        updated_at=job.updated_at,
        artifacts=ExtractionArtifacts(
            board_bbox=list(extraction.board_bbox) if extraction.board_bbox else None,
            warped_board_path=extraction.warped_board_path,
        ),
    )


@router.get("/{job_id}", response_model=ExtractionJobResponse)
def get_extraction_job(job_id: str, db: Session = Depends(get_db)) -> ExtractionJobResponse:
    job = db.get(ExtractionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Extraction job not found.")

    raw_result = json.loads(job.raw_result_json) if job.raw_result_json else {}

    upload = db.get(Upload, job.upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found.")

    return ExtractionJobResponse(
        job_id=job.id,
        upload_id=job.upload_id,
        status=job.status,
        board_width=upload.board_width,
        board_height=upload.board_height,
        overall_confidence=job.overall_confidence,
        created_at=job.created_at,
        updated_at=job.updated_at,
        artifacts=ExtractionArtifacts(
            board_bbox=raw_result.get("board_bbox"),
            warped_board_path=raw_result.get("warped_board_path"),
        ),
    )
