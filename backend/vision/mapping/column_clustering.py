"""Adaptive column clustering and missing-slot estimation within array regions."""
from math import cos, sin
from statistics import median


def _projected_along_span(panel, theta):
    ux, uy = cos(theta), sin(theta)
    if panel.get("geometry"):
        vals = [pt[0] * ux + pt[1] * uy for pt in panel["geometry"]]
        return max(1.0, max(vals) - min(vals))
    w = panel["bbox"]["x2"] - panel["bbox"]["x1"]
    h = panel["bbox"]["y2"] - panel["bbox"]["y1"]
    return max(1.0, abs(w * ux) + abs(h * uy))


def cluster_columns_in_region(rows, theta=0.0):
    """Align panel columns across rows, tolerating missing panels and irregular rows."""
    all_panels = [p for row in rows for p in row["items"]]
    if not all_panels:
        return {"column_pitch": 0.0, "column_count": 0, "estimated_missing_slots": 0, "column_spacing_cv": 0.0}

    along_spans = [_projected_along_span(p, theta) for p in all_panels]
    med_span = median(along_spans)

    within_row_diffs = []
    for row in rows:
        items = row["items"]
        for i in range(len(items) - 1):
            diff = items[i + 1]["map_coordinates"]["along"] - items[i]["map_coordinates"]["along"]
            if 0.6 * med_span <= diff <= 2.1 * med_span:
                within_row_diffs.append(diff)

    col_pitch = median(within_row_diffs) if within_row_diffs else med_span * 1.08
    tol = max(2.0, col_pitch * 0.45)

    ordered = sorted(all_panels, key=lambda p: p["map_coordinates"]["along"])
    col_clusters = []
    for p in ordered:
        val = p["map_coordinates"]["along"]
        if not col_clusters or val - col_clusters[-1]["center"] > tol:
            col_clusters.append({"center": val, "items": [p]})
        else:
            cl = col_clusters[-1]
            cl["items"].append(p)
            cl["center"] = sum(item["map_coordinates"]["along"] for item in cl["items"]) / len(cl["items"])

    # Assign gap-aware grid_column_id across column clusters using estimated pitch.
    grid_col = 1
    col_centers = [cl["center"] for cl in col_clusters]
    col_gaps = [col_centers[i + 1] - col_centers[i] for i in range(len(col_centers) - 1)]
    for idx, cl in enumerate(col_clusters):
        if idx > 0 and col_pitch > 0:
            step = max(1, round((cl["center"] - col_clusters[idx - 1]["center"]) / col_pitch))
            grid_col += step
        for item in cl["items"]:
            item["grid_column_id"] = grid_col

    if len(col_gaps) >= 2:
        unit_gaps = [g for g in col_gaps if g <= 1.5 * col_pitch]
        if len(unit_gaps) >= 2:
            mean_g = sum(unit_gaps) / len(unit_gaps)
            var_g = sum((g - mean_g) ** 2 for g in unit_gaps) / len(unit_gaps)
            col_cv = (var_g ** 0.5) / mean_g if mean_g > 0 else 0.0
        else:
            col_cv = 0.0
    else:
        col_cv = 0.0

    # Estimate missing slots inside the observed grid bounding rectangle.
    total_grid_cols = grid_col
    total_grid_rows = rows[-1]["grid_row_index"] if rows else 0
    expected_full = total_grid_rows * total_grid_cols
    missing_est = max(0, expected_full - len(all_panels))

    return {
        "column_pitch": round(col_pitch, 3),
        "column_count": len(col_clusters),
        "grid_column_count": total_grid_cols,
        "estimated_missing_slots": missing_est,
        "column_spacing_cv": round(col_cv, 4),
    }
