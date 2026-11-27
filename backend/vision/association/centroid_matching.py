"""Centroid containment and normalized distance metrics for defect-to-panel matching."""
from math import hypot
from .iou import coords


def centroid_inside(point, region):
    """Return True if point (x, y) falls inside polygon vertices or bounding box."""
    x, y = float(point[0]), float(point[1])
    if isinstance(region, list) and len(region) >= 3 and isinstance(region[0], (list, tuple)):
        inside = False
        j = len(region) - 1
        for i, (xi, yi) in enumerate(region):
            xj, yj = region[j]
            if ((yi > y) != (yj > y)) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
                inside = not inside
            j = i
        return inside
    x1, y1, x2, y2 = coords(region)
    return x1 <= x <= x2 and y1 <= y <= y2


def defect_centroid(defect):
    """Return (cx, cy) centroid of a defect box or polygon."""
    x1, y1, x2, y2 = coords(defect)
    return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)


def normalized_centroid_distance(point, panel):
    """Distance from point to panel centroid normalized by panel bounding-box diagonal."""
    x1, y1, x2, y2 = coords(panel["bbox"])
    px = panel.get("centroid", {}).get("x", (x1 + x2) * 0.5)
    py = panel.get("centroid", {}).get("y", (y1 + y2) * 0.5)
    diag = hypot(x2 - x1, y2 - y1)
    if diag <= 1e-9:
        return float("inf")
    return hypot(float(point[0]) - px, float(point[1]) - py) / diag
