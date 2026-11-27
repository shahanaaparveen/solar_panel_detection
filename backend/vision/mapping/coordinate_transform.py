"""Geometric coordinate transformations for local array frames and projective homographies."""
from math import cos, sin


def estimate_array_frame(centers, theta):
    """Build a canonical 2D local frame aligned along row direction theta (radians)."""
    if not centers:
        return {"origin": {"x": 0.0, "y": 0.0}, "theta": float(theta), "ux": 1.0, "uy": 0.0, "vx": 0.0, "vy": 1.0}
    mx = sum(x for x, _ in centers) / len(centers)
    my = sum(y for _, y in centers) / len(centers)
    ux, uy = cos(theta), sin(theta)
    vx, vy = -uy, ux
    return {
        "origin": {"x": mx, "y": my},
        "theta": float(theta),
        "ux": ux,
        "uy": uy,
        "vx": vx,
        "vy": vy,
    }


def to_local_frame(point, frame):
    """Project an image-space (x, y) point into local (along, across) coordinates."""
    if isinstance(point, dict):
        x, y = float(point["x"]), float(point["y"])
    else:
        x, y = float(point[0]), float(point[1])
    dx = x - frame["origin"]["x"]
    dy = y - frame["origin"]["y"]
    return {
        "along": dx * frame["ux"] + dy * frame["uy"],
        "across": dx * frame["vx"] + dy * frame["vy"],
    }


def from_local_frame(local_point, frame):
    """Invert local (along, across) coordinates back to original image pixels."""
    along = float(local_point["along"])
    across = float(local_point["across"])
    x = frame["origin"]["x"] + along * frame["ux"] + across * frame["vx"]
    y = frame["origin"]["y"] + along * frame["uy"] + across * frame["vy"]
    return {"x": x, "y": y}


def assign_local_coordinates(panels, frame):
    """Attach local array-aligned coordinates to panels without mutating image coordinates."""
    for p in panels:
        c = p["centroid"]
        p["map_coordinates"] = to_local_frame(c, frame)
    return panels


def transform_point(point, matrix):
    """Apply a 3x3 homography matrix to a 2D point, returning None if near singularity."""
    if isinstance(point, dict):
        x, y = float(point["x"]), float(point["y"])
    else:
        x, y = float(point[0]), float(point[1])
    denom = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2]
    if abs(denom) < 1e-9:
        return None
    nx = (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]) / denom
    ny = (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]) / denom
    return [nx, ny]


def transform_polygon(polygon, matrix):
    """Project every vertex of a polygon through a 3x3 homography matrix."""
    if not polygon:
        return None
    projected = []
    for pt in polygon:
        mapped = transform_point(pt, matrix)
        if mapped is None:
            return None
        projected.append(mapped)
    return projected


def transform_bbox(bbox, matrix):
    """Project a bounding box through a 3x3 homography matrix via its 4 corners."""
    x1, y1, x2, y2 = (float(bbox[k]) for k in ("x1", "y1", "x2", "y2"))
    corners = []
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        mapped = transform_point((x, y), matrix)
        if mapped is None:
            return None
        corners.append(mapped)
    return {
        "x1": min(p[0] for p in corners),
        "y1": min(p[1] for p in corners),
        "x2": max(p[0] for p in corners),
        "y2": max(p[1] for p in corners),
    }
