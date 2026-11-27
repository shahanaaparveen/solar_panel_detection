"""Bounding box area, intersection area, and intersection-over-union helpers."""


def coords(box):
    """Extract (x1, y1, x2, y2) float tuple from list, tuple, or dict."""
    if isinstance(box, dict) and "bbox" in box:
        box = box["bbox"]
    if isinstance(box, (list, tuple)):
        return tuple(map(float, box))
    if {"x1", "y1", "x2", "y2"}.issubset(box):
        return tuple(float(box[k]) for k in ("x1", "y1", "x2", "y2"))
    return (
        float(box["x"]),
        float(box["y"]),
        float(box["x"]) + float(box["w"]),
        float(box["y"]) + float(box["h"]),
    )


def box_area(box):
    """Compute non-negative area of a bounding box."""
    x1, y1, x2, y2 = coords(box)
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def intersection_area(a, b):
    """Compute intersection area between two bounding boxes."""
    ax1, ay1, ax2, ay2 = coords(a)
    bx1, by1, bx2, by2 = coords(b)
    iw = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0.0, min(ay2, by2) - max(ay1, by1))
    return iw * ih


def box_iou(a, b):
    """Compute intersection-over-union between two bounding boxes."""
    inter = intersection_area(a, b)
    if inter <= 0.0:
        return 0.0
    union = box_area(a) + box_area(b) - inter
    return inter / union if union > 0.0 else 0.0
