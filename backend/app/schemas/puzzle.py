from pydantic import BaseModel, Field


class PatchDefinition(BaseModel):
    id: str = Field(min_length=1, max_length=1)
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    size: int | None = Field(default=None, ge=1)
    shape: str


class PuzzleDraft(BaseModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    board_rows: list[str]
    patches: list[PatchDefinition]


class PuzzleExtractionResponse(BaseModel):
    puzzle_number: int
    board_width: int = Field(ge=1)
    board_height: int = Field(ge=1)
    status: str
    confidence: float | None = None
    board_bbox: list[int] | None = None
    board_path: str | None = None

