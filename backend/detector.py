"""Compatibility imports for the modular vision services."""

from vision.inference.inference_pipeline import analyze_image
from vision.inference.panel_detector import detect_panels


def detect_defects(image_path: str, image_type: str = "unknown", **kwargs):
    """Return real detections only; unavailable models produce an explicit status."""
    return analyze_image(image_path, image_type, **kwargs)


def detect_and_number_panels_yolo(image_path: str, **kwargs):
    """Compatibility wrapper; returns an empty list when panel weights are absent."""
    result = detect_panels(image_path, **kwargs)
    return result.get("panels", [])
