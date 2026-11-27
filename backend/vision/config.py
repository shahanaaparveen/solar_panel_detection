"""Environment-backed defaults for independent model roles."""
from dataclasses import dataclass
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = Path(os.getenv("MODEL_DIR", BACKEND_DIR / "models"))


@dataclass(frozen=True)
class ModelConfig:
    role: str
    path: Path
    task: str
    modality: str
    image_size: int = 1024
    confidence: float = 0.25
    iou: float = 0.5
    version: str = "unversioned"
    device: str = "auto"


def _config(role, env_prefix, filename, modality):
    return ModelConfig(role,
        Path(os.getenv(f"{env_prefix}_MODEL_PATH", MODELS_DIR / filename)), "detect", modality,
        int(os.getenv(f"{env_prefix}_IMAGE_SIZE", "1024")),
        float(os.getenv(f"{env_prefix}_CONFIDENCE", "0.25")),
        float(os.getenv(f"{env_prefix}_IOU", "0.5")),
        os.getenv(f"{env_prefix}_MODEL_VERSION", "unversioned"),
        os.getenv(f"{env_prefix}_MODEL_DEVICE", os.getenv("MODEL_DEVICE", "auto")))


MODEL_CONFIGS = {
    "panel_detection": _config("panel_detection", "PANEL", "panel_detection.pt", "rgb"),
    "thermal_defect_detection": _config("thermal_defect_detection", "THERMAL", "thermal_defects.pt", "thermal"),
    "rgb_defect_detection": _config("rgb_defect_detection", "RGB", "rgb_defects.pt", "rgb"),
}
