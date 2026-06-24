import json
from pathlib import Path
from uuid import uuid4

import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.repositories.puzzle import find_by_puzzle_number, upsert_extraction
from app.schemas.puzzle import PatchDefinition, PuzzleDraft, PuzzleExtractionResponse
from app.services.cv_extract import extract_board
from app.services.patch_detect import segment_patches, classify_patch_shapes
from app.services.patch_ocr import extract_patch_sizes
from app.services.path_builder import build_upload_image_path
from app.services.serialize_patches import serialize_patches


router = APIRouter(prefix="/puzzles", tags=["puzzles"])

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}

_READING_ORDER_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _build_board_rows(
    patches: list[PatchDefinition],
    width: int,
    height: int,
) -> list[str]:
    grid = [["." for _ in range(width)] for _ in range(height)]
    for p in patches:
        grid[p.row][p.col] = p.id
    return ["".join(row) for row in grid]


@router.post("", response_model=PuzzleExtractionResponse, status_code=status.HTTP_201_CREATED)
def create_puzzle_extraction(
    puzzle_number: int = Form(..., ge=1),
    board_width: int = Form(..., ge=1),
    board_height: int = Form(..., ge=1),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PuzzleExtractionResponse:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type.",
        )

    extract_id = f"puz_{uuid4().hex[:12]}"
    suffix = Path(image.filename or "upload.png").suffix.lower() or ".png"
    upload_filename = f"{extract_id}{suffix}"
    image_path = build_upload_image_path(extract_id, extension=suffix)
    output_path = Path(image_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image.file.read())

    board_output_path = str(Path(settings.artifacts_dir) / f"{extract_id}.png")
    result = extract_board(
        image_path,
        board_output_path,
        board_width=board_width,
        board_height=board_height,
    )

    patches: list[PatchDefinition] = []
    if result.board_path:
        board = cv2.imread(result.board_path)
        cells = segment_patches(board, board_width, board_height)
        cells = classify_patch_shapes(cells)
        cells = extract_patch_sizes(cells)
        for i, cell in enumerate(cells):
            letter = _READING_ORDER_LETTERS[i] if i < 26 else f"p{i}"
            patches.append(
                PatchDefinition(
                    id=letter,
                    row=cell.row,
                    col=cell.col,
                    size=cell.size,
                    shape=cell.shape,
                )
            )
    else:
        output_path.unlink(missing_ok=True)

    status_text = "completed" if result.board_path else "failed"
    upsert_extraction(
        db=db,
        puzzle_number=puzzle_number,
        extract_id=extract_id,
        board_width=board_width,
        board_height=board_height,
        status=status_text,
        patches_json=[p.model_dump() for p in patches],
        upload_filename=upload_filename,
    )

    return PuzzleExtractionResponse(
        puzzle_number=puzzle_number,
        board_width=board_width,
        board_height=board_height,
        status=status_text,
        patches=patches,
    )


@router.get("/{puzzle_number}", response_model=PuzzleExtractionResponse)
def get_puzzle_extraction(
    puzzle_number: int,
    db: Session = Depends(get_db),
) -> PuzzleExtractionResponse:
    record = find_by_puzzle_number(db, puzzle_number)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puzzle not found.",
        )
    patches = [PatchDefinition(**p) for p in json.loads(record.patches_json)]
    return PuzzleExtractionResponse(
        puzzle_number=record.puzzle_number,
        board_width=record.board_width,
        board_height=record.board_height,
        status=record.status,
        patches=patches,
    )


@router.get("/{puzzle_number}/patches")
def get_puzzle_patches(
    puzzle_number: int,
    db: Session = Depends(get_db),
) -> Response:
    record = find_by_puzzle_number(db, puzzle_number)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puzzle not found.",
        )
    patches = [PatchDefinition(**p) for p in json.loads(record.patches_json)]
    board_rows = _build_board_rows(patches, record.board_width, record.board_height)
    draft = PuzzleDraft(
        width=record.board_width,
        height=record.board_height,
        board_rows=board_rows,
        patches=patches,
    )
    text = serialize_patches(draft)
    return Response(content=text, media_type="text/plain")


@router.get("/{puzzle_number}/image")
def get_puzzle_image(
    puzzle_number: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    record = find_by_puzzle_number(db, puzzle_number)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puzzle not found.",
        )
    image_path = Path(settings.uploads_dir) / record.upload_filename
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image file not found on disk.",
        )
    return FileResponse(str(image_path))


@router.get("/{puzzle_number}/board_image")
def get_puzzle_board_image(
    puzzle_number: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    record = find_by_puzzle_number(db, puzzle_number)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Puzzle not found.",
        )
    board_path = Path(settings.artifacts_dir) / f"{record.extract_id}.png"
    if not board_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Board image not found on disk.",
        )
    return FileResponse(str(board_path))
