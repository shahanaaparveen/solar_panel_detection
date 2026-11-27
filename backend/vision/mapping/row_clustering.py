"""PCA-oriented row clustering that adapts its tolerance to panel scale."""
from math import atan2, cos, sin
from statistics import median


def map_panel_rows(panels):
    if not panels:
        return panels
    centers = [(p["centroid"]["x"], p["centroid"]["y"]) for p in panels]
    mx = sum(x for x, _ in centers) / len(centers)
    my = sum(y for _, y in centers) / len(centers)
    xx = sum((x-mx)**2 for x, _ in centers)
    yy = sum((y-my)**2 for _, y in centers)
    xy = sum((x-mx)*(y-my) for x, y in centers)
    theta = 0.5 * atan2(2*xy, xx-yy) if len(panels) > 1 else 0.0
    ux, uy = cos(theta), sin(theta)
    vx, vy = -uy, ux
    for p, (x, y) in zip(panels, centers):
        p["map_coordinates"] = {"along": x*ux+y*uy, "across": x*vx+y*vy}
    sizes = [max(1.0, min(p["bbox"]["x2"]-p["bbox"]["x1"], p["bbox"]["y2"]-p["bbox"]["y1"])) for p in panels]
    tolerance = max(2.0, median(sizes) * 0.65)
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
    panels_sorted = []
    for row_idx, row in enumerate(rows, start=1):
        line = sorted(row["items"], key=lambda p: p["map_coordinates"]["along"])
        for col_idx, p in enumerate(line, start=1):
            p["row_id"] = row_idx
            p["column_id"] = col_idx
            p["panel_id"] = f"R{row_idx:02d}C{col_idx:02d}"
            panels_sorted.append(p)
    return panels_sorted
