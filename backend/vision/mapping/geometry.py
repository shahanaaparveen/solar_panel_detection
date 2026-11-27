"""Geometric primitives, validation, clipping, and orientation helpers for solar panels."""
from math import atan2, degrees, hypot, isfinite, sqrt


def extract_bbox_tuple(box):
    """Extract (x1, y1, x2, y2) float coordinates from dict or sequence representations."""
    if isinstance(box, dict) and "bbox" in box:
        box = box["bbox"]
    if isinstance(box, (list, tuple)):
        if len(box) != 4:
            raise ValueError("Bounding box sequence must have exactly 4 coordinates")
        vals = tuple(float(v) for v in box)
    elif isinstance(box, dict):
        if {"x1", "y1", "x2", "y2"}.issubset(box):
            vals = tuple(float(box[k]) for k in ("x1", "y1", "x2", "y2"))
        elif {"x", "y", "w", "h"}.issubset(box):
            x, y, w, h = float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"])
            vals = (x, y, x + w, y + h)
        else:
            raise ValueError("Bounding box dict must contain x1/y1/x2/y2 or x/y/w/h")
    else:
        raise ValueError("Unsupported bounding box format")
    if not all(isfinite(v) for v in vals):
        raise ValueError("Bounding box coordinates must be finite numbers")
    return vals


def clip_bbox(box, image_width=None, image_height=None):
    """Validate and clip bounding box to image bounds, returning an xyxy dict."""
    x1, y1, x2, y2 = extract_bbox_tuple(box)
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    was_clipped = False
    if image_width is not None:
        w_bound = float(image_width)
        if w_bound <= 0:
            raise ValueError("image_width must be positive")
        nx1 = max(0.0, min(w_bound, x1))
        nx2 = max(0.0, min(w_bound, x2))
        was_clipped = was_clipped or nx1 != x1 or nx2 != x2
        x1, x2 = nx1, nx2
    if image_height is not None:
        h_bound = float(image_height)
        if h_bound <= 0:
            raise ValueError("image_height must be positive")
        ny1 = max(0.0, min(h_bound, y1))
        ny2 = max(0.0, min(h_bound, y2))
        was_clipped = was_clipped or ny1 != y1 or ny2 != y2
        y1, y2 = ny1, ny2
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Panel bounding box must have positive area")
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}, was_clipped


def normalize_polygon(polygon, image_width=None, image_height=None):
    """Validate and clip a polygon of [x, y] points; returns None if absent or invalid."""
    if polygon is None:
        return None
    if not isinstance(polygon, (list, tuple)) or len(polygon) < 3:
        return None
    cleaned = []
    for pt in polygon:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            return None
        x, y = float(pt[0]), float(pt[1])
        if not (isfinite(x) and isfinite(y)):
            return None
        if image_width is not None:
            x = max(0.0, min(float(image_width), x))
        if image_height is not None:
            y = max(0.0, min(float(image_height), y))
        if not cleaned or hypot(x - cleaned[-1][0], y - cleaned[-1][1]) > 1e-6:
            cleaned.append([x, y])
    if len(cleaned) >= 2 and hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) <= 1e-6:
        cleaned.pop()
    if len(cleaned) < 3 or polygon_area(cleaned) <= 1e-6:
        return None
    return cleaned


def polygon_area(polygon):
    """Compute unsigned area of a 2D polygon via the Shoelace formula."""
    if not polygon or len(polygon) < 3:
        return 0.0
    total = 0.0
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return abs(total) * 0.5


def polygon_centroid(polygon):
    """Compute geometric centroid of a polygon, falling back to vertex mean if degenerate."""
    if not polygon or len(polygon) < 3:
        raise ValueError("Polygon must have at least 3 vertices")
    signed_area = 0.0
    cx_acc = 0.0
    cy_acc = 0.0
    n = len(polygon)
    for i in range(n):
        x0, y0 = polygon[i]
        x1, y1 = polygon[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        signed_area += cross
        cx_acc += (x0 + x1) * cross
        cy_acc += (y0 + y1) * cross
    signed_area *= 0.5
    if abs(signed_area) < 1e-9:
        return {
            "x": sum(p[0] for p in polygon) / n,
            "y": sum(p[1] for p in polygon) / n,
        }
    factor = 1.0 / (6.0 * signed_area)
    return {"x": cx_acc * factor, "y": cy_acc * factor}


def polygon_bbox(polygon):
    """Return axis-aligned bounding box dict enclosing a polygon."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return {"x1": min(xs), "y1": min(ys), "x2": max(xs), "y2": max(ys)}


def estimate_polygon_orientation(polygon):
    """Estimate long-axis angle in [-90, 90) degrees and side lengths from a polygon."""
    try:
        import cv2
        import numpy as np

        pts = np.asarray(polygon, dtype=np.float32)
        (_cx, _cy), (rw, rh), angle = cv2.minAreaRect(pts)
        if rw < rh:
            angle += 90.0
            long_side, short_side = float(rh), float(rw)
        else:
            long_side, short_side = float(rw), float(rh)
        while angle >= 90.0:
            angle -= 180.0
        while angle < -90.0:
            angle += 180.0
        return float(angle), long_side, short_side
    except Exception:
        n = len(polygon)
        mx = sum(p[0] for p in polygon) / n
        my = sum(p[1] for p in polygon) / n
        xx = sum((p[0] - mx) ** 2 for p in polygon)
        yy = sum((p[1] - my) ** 2 for p in polygon)
        xy = sum((p[0] - mx) * (p[1] - my) for p in polygon)
        theta = 0.5 * atan2(2.0 * xy, xx - yy)
        bbox = polygon_bbox(polygon)
        w = bbox["x2"] - bbox["x1"]
        h = bbox["y2"] - bbox["y1"]
        return degrees(theta), max(w, h), min(w, h)


def panel_dimensions(bbox, polygon=None):
    """Compute dimensions, area, aspect ratio, and orientation for a panel."""
    width = max(0.0, bbox["x2"] - bbox["x1"])
    height = max(0.0, bbox["y2"] - bbox["y1"])
    bbox_area = width * height
    if polygon:
        area = polygon_area(polygon)
        angle_deg, long_side, short_side = estimate_polygon_orientation(polygon)
        if short_side <= 1e-6:
            long_side, short_side = max(width, height), min(width, height)
    else:
        area = bbox_area
        long_side, short_side = max(width, height), min(width, height)
        angle_deg = degrees(atan2(height, width))
    aspect_ratio = (long_side / short_side) if short_side > 1e-6 else 0.0
    return {
        "width": width,
        "height": height,
        "area": area,
        "bbox_area": bbox_area,
        "long_side": long_side,
        "short_side": short_side,
        "aspect_ratio": aspect_ratio,
        "orientation_degrees": angle_deg,
    }


def panel_record(
    box,
    confidence,
    panel_id=None,
    geometry=None,
    image_width=None,
    image_height=None,
    image_id=None,
):
    """Construct a validated, normalized panel record from detection coordinates."""
    bbox, was_clipped = clip_bbox(box, image_width=image_width, image_height=image_height)
    polygon = normalize_polygon(geometry, image_width=image_width, image_height=image_height)
    conf = float(confidence)
    if not isfinite(conf) or not 0.0 <= conf <= 1.0:
        raise ValueError("Panel confidence must be within [0, 1]")
    dims = panel_dimensions(bbox, polygon)
    centroid = (
        polygon_centroid(polygon)
        if polygon
        else {"x": (bbox["x1"] + bbox["x2"]) / 2.0, "y": (bbox["y1"] + bbox["y2"]) / 2.0}
    )
    record = {
        "panel_id": panel_id,
        "class": "solar_panel",
        "confidence": conf,
        "bbox": bbox,
        "centroid": centroid,
        "dimensions": {
            "width": round(dims["width"], 3),
            "height": round(dims["height"], 3),
            "area": round(dims["area"], 3),
            "long_side": round(dims["long_side"], 3),
            "short_side": round(dims["short_side"], 3),
        },
        "aspect_ratio": round(dims["aspect_ratio"], 4),
        "row_id": None,
        "column_id": None,
        "geometry": polygon,
        "orientation_degrees": round(dims["orientation_degrees"], 4),
        "clipped_to_image": was_clipped,
    }
    if image_id is not None:
        record["image_id"] = image_id
    return record
