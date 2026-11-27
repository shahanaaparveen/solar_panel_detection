"""Multi-region array segmentation and PCA/neighbor-based orientation estimation."""
from math import atan2, cos, degrees, hypot, pi, radians, sin, sqrt
from statistics import median


def _canonical_angle(theta):
    """Normalize an undirected axis angle into (-pi/2, pi/2] so along runs left-to-right."""
    while theta <= -pi / 2:
        theta += pi
    while theta > pi / 2:
        theta -= pi
    return theta


def _angular_diff(a, b):
    """Smallest undirected angular difference in [0, pi/2] between two axis angles."""
    diff = abs(_canonical_angle(a) - _canonical_angle(b))
    if diff > pi / 2:
        diff = pi - diff
    return diff


def _panel_principal_angle(panel):
    """Return panel orientation in radians from polygon minAreaRect if available, else None."""
    if panel.get("geometry"):
        return _canonical_angle(radians(panel.get("orientation_degrees", 0.0)))
    return None


def _connected_components(n, adjacency):
    visited = [False] * n
    components = []
    for start in range(n):
        if visited[start]:
            continue
        stack = [start]
        visited[start] = True
        comp = []
        while stack:
            node = stack.pop()
            comp.append(node)
            for nxt in adjacency[node]:
                if not visited[nxt]:
                    visited[nxt] = True
                    stack.append(nxt)
        components.append(comp)
    return components


def segment_array_regions(panels):
    """Group panels into spatially & orientationally coherent solar-array regions."""
    if not panels:
        return []
    if len(panels) == 1:
        return [list(panels)]

    longs = [max(1.0, p["dimensions"]["long_side"]) if "dimensions" in p else max(1.0, p["bbox"]["x2"] - p["bbox"]["x1"]) for p in panels]
    shorts = [max(1.0, p["dimensions"]["short_side"]) if "dimensions" in p else max(1.0, p["bbox"]["y2"] - p["bbox"]["y1"]) for p in panels]
    med_long = median(longs)
    med_short = median(shorts)
    # Tolerate up to ~3 missing panels along a row before separating into distinct array blocks.
    eps = max(3.6 * med_long, 4.6 * med_short)

    centers = [(p["centroid"]["x"], p["centroid"]["y"]) for p in panels]
    poly_angles = [_panel_principal_angle(p) for p in panels]

    n = len(panels)
    adjacency = [[] for _ in range(n)]
    angle_tol = radians(22.0)

    for i in range(n):
        xi, yi = centers[i]
        for j in range(i + 1, n):
            xj, yj = centers[j]
            dist = hypot(xj - xi, yj - yi)
            if dist <= eps:
                # Split nearby panels only when explicit polygon geometry confirms different array rotations.
                if poly_angles[i] is not None and poly_angles[j] is not None:
                    if _angular_diff(poly_angles[i], poly_angles[j]) > angle_tol:
                        continue
                adjacency[i].append(j)
                adjacency[j].append(i)

    components = _connected_components(n, adjacency)
    regions = [[panels[idx] for idx in comp] for comp in components]
    # Deterministic top-to-bottom, left-to-right ordering of array regions.
    regions.sort(
        key=lambda reg: (
            sum(p["centroid"]["y"] for p in reg) / len(reg),
            sum(p["centroid"]["x"] for p in reg) / len(reg),
        )
    )
    return regions


def _row_compactness_score(panels, theta):
    """Measure how cleanly panels collapse into distinct rows at angle theta."""
    if len(panels) < 2:
        return 0.0
    vx, vy = -sin(theta), cos(theta)
    across = sorted(p["centroid"]["x"] * vx + p["centroid"]["y"] * vy for p in panels)
    gaps = [across[i + 1] - across[i] for i in range(len(across) - 1)]
    spans = []
    for p in panels:
        w = p["bbox"]["x2"] - p["bbox"]["x1"]
        h = p["bbox"]["y2"] - p["bbox"]["y1"]
        spans.append(max(1.0, abs(w * vx) + abs(h * vy)))
    tol = max(2.0, median(spans) * 0.65)
    inter_gaps = [g for g in gaps if g > tol]
    intra_gaps = [g for g in gaps if g <= tol]
    intra_spread = (sum(g * g for g in intra_gaps) / len(intra_gaps)) if intra_gaps else 0.0
    inter_margin = min(inter_gaps) if inter_gaps else 0.0
    return inter_margin - sqrt(intra_spread)


def estimate_region_orientation(region_panels):
    """Estimate dominant row-axis angle (radians) for one array region using PCA + geometry."""
    if not region_panels:
        return 0.0
    if len(region_panels) == 1:
        pa = _panel_principal_angle(region_panels[0])
        return pa if pa is not None else 0.0

    centers = [(p["centroid"]["x"], p["centroid"]["y"]) for p in region_panels]
    n = len(centers)
    mx = sum(x for x, _ in centers) / n
    my = sum(y for _, y in centers) / n
    xx = sum((x - mx) ** 2 for x, _ in centers)
    yy = sum((y - my) ** 2 for _, y in centers)
    xy = sum((x - mx) * (y - my) for x, y in centers)

    trace = xx + yy
    det_term = sqrt(max(0.0, (xx - yy) ** 2 + 4.0 * xy * xy))
    lambda1 = 0.5 * (trace + det_term)
    lambda2 = 0.5 * (trace - det_term)

    theta_pca = _canonical_angle(0.5 * atan2(2.0 * xy, xx - yy))
    # When variance is strongly elongated along one axis, PCA directly identifies row direction;
    # for near-square grids, compare perpendicular candidate axes for tighter row separation.
    if lambda1 >= 1.25 * max(lambda2, 1e-6):
        return theta_pca

    poly_angles = [_panel_principal_angle(p) for p in region_panels if _panel_principal_angle(p) is not None]
    candidates = [theta_pca, _canonical_angle(theta_pca + pi / 2)]
    if poly_angles:
        # Weight candidate closer to median polygon edge axis.
        med_poly = median(poly_angles)
        candidates.sort(key=lambda cand: _angular_diff(cand, med_poly))
        if _angular_diff(candidates[0], med_poly) + radians(10.0) < _angular_diff(candidates[1], med_poly):
            return candidates[0]

    return max(candidates, key=lambda cand: _row_compactness_score(region_panels, cand))
