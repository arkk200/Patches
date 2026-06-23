from pydantic import BaseModel, Field

from app.services.cell_detect import CellShape


class PatchDefinition(BaseModel):
    id: str = Field(min_length=1, max_length=1)
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    size: int | None = Field(default=None, ge=1)
    shape: CellShape


class PuzzleDraft(BaseModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    board_rows: list[str]
    patches: list[PatchDefinition]


class PuzzleExtractionResponse(BaseModel):
    puzzle_number: int
    board_width: int
    board_height: int
    status: str
    confidence: float | None = None
    board_bbox: tuple[int, int, int, int] | None = None
    board_path: str | None = None

