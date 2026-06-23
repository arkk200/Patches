from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.config import settings
from app.schemas.puzzle import PuzzleExtractionResponse
from app.services.cv_extract import extract_board
from app.services.path_builder import build_upload_image_path


router = APIRouter(prefix="/puzzles", tags=["puzzles"])

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.post("", response_model=PuzzleExtractionResponse, status_code=status.HTTP_201_CREATED)
def create_puzzle_extraction(
    puzzle_number: int = Form(..., ge=1),
    board_width: int = Form(..., ge=1),
    board_height: int = Form(..., ge=1),
    image: UploadFile = File(...),
) -> PuzzleExtractionResponse:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type.",
        )

    extract_id = f"puz_{uuid4().hex[:12]}"
    suffix = Path(image.filename or "upload.png").suffix.lower() or ".png"
    image_path = build_upload_image_path(extract_id, extension=suffix)
    output_path = Path(image_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image.file.read())

    artifacts_dir = str(Path(settings.artifacts_dir) / extract_id)
    result = extract_board(
        image_path,
        artifacts_dir,
        board_width=board_width,
        board_height=board_height,
    )

    if not result.board_path:
        output_path.unlink(missing_ok=True)

    return PuzzleExtractionResponse(
        puzzle_number=puzzle_number,
        board_width=board_width,
        board_height=board_height,
        status="completed" if result.board_path else "failed",
        confidence=result.confidence if result.board_path else None,
        board_bbox=result.board_bbox,
        board_path=result.board_path,
    )
