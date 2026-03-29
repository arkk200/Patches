from datetime import datetime

from pydantic import BaseModel


class ExtractionArtifacts(BaseModel):
    board_bbox: list[int] | None = None
    warped_board_path: str | None = None


class PreprocessDebugArtifacts(BaseModel):
    original_path: str | None = None
    grayscale_path: str | None = None
    blurred_path: str | None = None
    enhanced_path: str | None = None
    sharpened_path: str | None = None
    edges_path: str | None = None
    board_mask_path: str | None = None


class LayoutDebugArtifacts(BaseModel):
    contour_overlay_path: str | None = None
    selected_bbox_overlay_path: str | None = None
    selected_bbox: list[int] | None = None
    selected_quad: list[list[int]] | None = None
    selected_score: float | None = None
    board_crop_path: str | None = None


class DebugArtifacts(BaseModel):
    artifact_dir: str
    preprocess: PreprocessDebugArtifacts
    layout: LayoutDebugArtifacts


class ExtractionJobResponse(BaseModel):
    job_id: str
    upload_id: str
    status: str
    board_width: int
    board_height: int
    overall_confidence: float | None
    created_at: datetime
    updated_at: datetime
    artifacts: ExtractionArtifacts
    debug_enabled: bool = False
    debug_artifacts: DebugArtifacts | None = None
