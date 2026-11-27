"""Exact analytical and raster-backed polygon intersection and IoU matching."""
from ..mapping.geometry import polygon_area, polygon_bbox
from .iou import coords, intersection_area


def bbox_to_polygon(box):
    """Convert an axis-aligned bounding box to a 4-vertex polygon."""
    x1, y1, x2, y2 = coords(box)
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def _to_polygon(geom):
    if isinstance(geom, list) and len(geom) >= 3 and isinstance(geom[0], (list, tuple)):
        return [[float(p[0]), float(p[1])] for p in geom]
    return bbox_to_polygon(geom)


def _signed_area(poly):
    total = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return 0.5 * total


def _is_convex(poly):
    if len(poly) < 3:
        return False
    sign = 0
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        cx, cy = poly[(i + 2) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) <= 1e-9:
            continue
        cur = 1 if cross > 0 else -1
        if sign == 0:
            sign = cur
        elif sign != cur:
            return False
    return sign != 0


def _sutherland_hodgman_clip(subject_poly, clip_poly):
    """Clip subject_poly against convex clip_poly (CCW oriented)."""
    if _signed_area(clip_poly) < 0:
        clip_poly = list(reversed(clip_poly))
    output = list(subject_poly)
    for i in range(len(clip_poly)):
        if not output:
            return []
        cp1 = clip_poly[i]
        cp2 = clip_poly[(i + 1) % len(clip_poly)]
        edge_x, edge_y = cp2[0] - cp1[0], cp2[1] - cp1[1]

        def inside(p):
            return edge_x * (p[1] - cp1[1]) - edge_y * (p[0] - cp1[0]) >= -1e-9

        def intersect(s, e):
            dcx, dcy = cp1[0] - cp2[0], cp1[1] - cp2[1]
            dpx, dpy = s[0] - e[0], s[1] - e[1]
            n1 = cp1[0] * cp2[1] - cp1[1] * cp2[0]
            n2 = s[0] * e[1] - s[1] * e[0]
            denom = dcx * dpy - dcy * dpx
            if abs(denom) < 1e-12:
                return [(s[0] + e[0]) * 0.5, (s[1] + e[1]) * 0.5]
            return [(n1 * dpx - n2 * dcx) / denom, (n1 * dpy - n2 * dcy) / denom]

        input_list = output
        output = []
        s = input_list[-1]
        for e in input_list:
            if inside(e):
                if not inside(s):
                    output.append(intersect(s, e))
                output.append(e)
            elif inside(s):
                output.append(intersect(s, e))
            s = e
    return output


def _raster_polygon_intersection_area(poly_a, poly_b, grid_size=256):
    import cv2
    import numpy as np

    ba = polygon_bbox(poly_a)
    bb = polygon_bbox(poly_b)
    ox1 = max(ba["x1"], bb["x1"])
    oy1 = max(ba["y1"], bb["y1"])
    ox2 = min(ba["x2"], bb["x2"])
    oy2 = min(ba["y2"], bb["y2"])
    w = ox2 - ox1
    h = oy2 - oy1
    if w <= 0 or h <= 0:
        return 0.0
    scale = grid_size / max(w, h)
    gw = max(2, int(round(w * scale)) + 2)
    gh = max(2, int(round(h * scale)) + 2)
    mask_a = np.zeros((gh, gw), dtype=np.uint8)
    mask_b = np.zeros((gh, gw), dtype=np.uint8)
    pts_a = np.round((np.asarray(poly_a, dtype=np.float64) - [ox1, oy1]) * scale).astype(np.int32)
    pts_b = np.round((np.asarray(poly_b, dtype=np.float64) - [ox1, oy1]) * scale).astype(np.int32)
    cv2.fillPoly(mask_a, [pts_a], 1)
    cv2.fillPoly(mask_b, [pts_b], 1)
    overlap_pixels = int(np.count_nonzero(mask_a & mask_b))
    return overlap_pixels / (scale * scale)


def polygon_intersection_area(geom_a, geom_b):
    """Compute exact intersection area between two polygons or boxes."""
    poly_a = _to_polygon(geom_a)
    poly_b = _to_polygon(geom_b)
    if intersection_area(polygon_bbox(poly_a), polygon_bbox(poly_b)) <= 0.0:
        return 0.0
    if _is_convex(poly_b):
        clipped = _sutherland_hodgman_clip(poly_a, poly_b)
        return polygon_area(clipped)
    if _is_convex(poly_a):
        clipped = _sutherland_hodgman_clip(poly_b, poly_a)
        return polygon_area(clipped)
    return _raster_polygon_intersection_area(poly_a, poly_b)


def polygon_iou(geom_a, geom_b):
    """Compute IoU between two polygons or bounding boxes."""
    poly_a = _to_polygon(geom_a)
    poly_b = _to_polygon(geom_b)
    inter = polygon_intersection_area(poly_a, poly_b)
    if inter <= 0.0:
        return 0.0
    union = polygon_area(poly_a) + polygon_area(poly_b) - inter
    return inter / union if union > 0.0 else 0.0


def defect_panel_polygon_metrics(defect_geom, panel_geom):
    """Return (iou, defect_coverage_ratio, intersection_area, defect_area, panel_area)."""
    poly_d = _to_polygon(defect_geom)
    poly_p = _to_polygon(panel_geom)
    area_d = polygon_area(poly_d)
    area_p = polygon_area(poly_p)
    inter = polygon_intersection_area(poly_d, poly_p)
    coverage = (inter / area_d) if area_d > 0.0 else 0.0
    union = area_d + area_p - inter
    iou = (inter / union) if union > 0.0 else 0.0
    return iou, coverage, inter, area_d, area_p
