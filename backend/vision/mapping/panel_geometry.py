"""Geometry normalization helpers."""
from math import atan2, degrees


def panel_record(box, confidence, panel_id=None, geometry=None):
    x1, y1, x2, y2 = map(float, box)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Panel bounding box must have positive area")
    return {"panel_id": panel_id, "class": "solar_panel", "confidence": float(confidence),
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "centroid": {"x": (x1+x2)/2, "y": (y1+y2)/2},
            "row_id": None, "column_id": None, "geometry": geometry,
            "orientation_degrees": degrees(atan2(y2-y1, x2-x1))}
