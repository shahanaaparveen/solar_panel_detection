"""Thermal defect model service."""
from .base_detector import infer


def detect_thermal(image_path, **kwargs):
    return infer("thermal_defect_detection", image_path, "thermal", **kwargs)
