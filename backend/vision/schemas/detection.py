"""Shared detection response builders."""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: dict
    modality: str
    model_id: str
    image_size: dict
    mask: Optional[list] = None
    normalized_bbox: Optional[dict] = None
    coordinate_convention: str = "xyxy_pixels_exif_oriented"
    image_id: Optional[str] = None
    model_run_id: Optional[str] = None
    inference_ms: Optional[float] = None
    model_version: Optional[str] = None
    model_sha256: Optional[str] = None

    def to_dict(self):
        return asdict(self)
