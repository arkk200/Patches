import json

from sqlalchemy.orm import Session

from app.models.puzzle import PuzzleResult


def upsert_extraction(
    db: Session,
    puzzle_number: int,
    extract_id: str,
    board_width: int,
    board_height: int,
    status: str,
    patches_json: list[dict],
    upload_filename: str,
) -> PuzzleResult:
    patches_text = json.dumps(patches_json)
    record = PuzzleResult(
        puzzle_number=puzzle_number,
        extract_id=extract_id,
        board_width=board_width,
        board_height=board_height,
        status=status,
        patches_json=patches_text,
        upload_filename=upload_filename,
    )
    record = db.merge(record)
    db.commit()
    db.refresh(record)
    return record


def find_by_puzzle_number(db: Session, puzzle_number: int) -> PuzzleResult | None:
    return db.get(PuzzleResult, puzzle_number)


def list_all(db: Session) -> list[PuzzleResult]:
    return db.query(PuzzleResult).order_by(PuzzleResult.puzzle_number).all()
