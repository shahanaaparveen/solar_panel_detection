"""Adaptive PCA- and density-based solar panel row clustering."""
from math import cos, sin
from statistics import median
from .coordinate_transform import assign_local_coordinates, estimate_array_frame
from .orientation import estimate_region_orientation, segment_array_regions


def _projected_across_span(panel, theta):
    """Project panel extent perpendicular to the row axis theta."""
    vx, vy = -sin(theta), cos(theta)
    if panel.get("geometry"):
        vals = [pt[0] * vx + pt[1] * vy for pt in panel["geometry"]]
        return max(1.0, max(vals) - min(vals))
    w = panel["bbox"]["x2"] - panel["bbox"]["x1"]
    h = panel["bbox"]["y2"] - panel["bbox"]["y1"]
    return max(1.0, min(w, h) if abs(sin(theta)) < 1e-6 else (abs(w * vx) + abs(h * vy)))


def _cluster_1d_across(panels, tolerance):
    """Cluster panels into ordered rows using adaptive perpendicular distance tolerance."""
    ordered = sorted(panels, key=lambda p: p["map_coordinates"]["across"])
    rows = []
    for panel in ordered:
        across = panel["map_coordinates"]["across"]
        if not rows or across - rows[-1]["center"] > tolerance:
            rows.append({"center": across, "items": [panel]})
        else:
            row = rows[-1]
            row["items"].append(panel)
            row["center"] = sum(p["map_coordinates"]["across"] for p in row["items"]) / len(row["items"])
    return rows


def cluster_rows_in_region(region_panels, theta=None):
    """Cluster panels in a single region into ordered rows, returning rows and metrics."""
    if not region_panels:
        return [], {"theta": 0.0, "tolerance": 0.0, "row_pitch": 0.0, "row_spacing_cv": 0.0}
    if theta is None:
        theta = estimate_region_orientation(region_panels)

    centers = [(p["centroid"]["x"], p["centroid"]["y"]) for p in region_panels]
    frame = estimate_array_frame(centers, theta)
    assign_local_coordinates(region_panels, frame)

    spans = [_projected_across_span(p, theta) for p in region_panels]
    tolerance = max(2.0, median(spans) * 0.65)
    rows = _cluster_1d_across(region_panels, tolerance)

    row_centers = [row["center"] for row in rows]
    inter_gaps = [row_centers[i + 1] - row_centers[i] for i in range(len(row_centers) - 1)]
    row_pitch = median(inter_gaps) if inter_gaps else median(spans) * 1.1
    if len(inter_gaps) >= 2 and row_pitch > 0:
        mean_gap = sum(inter_gaps) / len(inter_gaps)
        variance = sum((g - mean_gap) ** 2 for g in inter_gaps) / len(inter_gaps)
        row_cv = (variance ** 0.5) / mean_gap if mean_gap > 0 else 0.0
    else:
        row_cv = 0.0

    # Assign gap-aware grid_row_id so a fully missing intermediate row preserves row spacing index.
    grid_row = 1
    for idx, row in enumerate(rows):
        if idx > 0 and row_pitch > 0:
            step = max(1, round((row["center"] - rows[idx - 1]["center"]) / row_pitch))
            grid_row += step
        row["row_index"] = idx + 1
        row["grid_row_index"] = grid_row
        row["items"].sort(key=lambda p: p["map_coordinates"]["along"])

    return rows, {
        "theta": theta,
        "tolerance": round(tolerance, 3),
        "row_pitch": round(row_pitch, 3),
        "row_spacing_cv": round(row_cv, 4),
    }


def map_panel_rows(panels):
    """Segment array regions, estimate orientations, cluster rows, and assign row/column IDs."""
    if not panels:
        return panels
    # Ensure lightweight panel dicts without precomputed dimensions still work.
    for p in panels:
        if "dimensions" not in p:
            w = max(0.0, p["bbox"]["x2"] - p["bbox"]["x1"])
            h = max(0.0, p["bbox"]["y2"] - p["bbox"]["y1"])
            p["dimensions"] = {
                "width": w,
                "height": h,
                "area": w * h,
                "long_side": max(w, h),
                "short_side": min(w, h),
            }

    regions = segment_array_regions(panels)
    panels_sorted = []
    global_row_offset = 0
    for region_idx, region_panels in enumerate(regions, start=1):
        rows, info = cluster_rows_in_region(region_panels)
        for local_row_idx, row in enumerate(rows, start=1):
            row_id = global_row_offset + local_row_idx
            for col_idx, p in enumerate(row["items"], start=1):
                p["region_id"] = region_idx
                p["row_id"] = row_id
                p["grid_row_id"] = global_row_offset + row["grid_row_index"]
                p["column_id"] = col_idx
                p["panel_id"] = f"R{row_id:02d}C{col_idx:02d}"
                p["region_orientation_radians"] = round(info["theta"], 6)
                panels_sorted.append(p)
        global_row_offset += len(rows)
    return panels_sorted
