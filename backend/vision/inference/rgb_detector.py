"""RGB defect model service."""
from .base_detector import infer


def detect_rgb(image_path, **kwargs):
    return infer("rgb_defect_detection", image_path, "rgb", **kwargs)
