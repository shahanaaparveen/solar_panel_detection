"""Evidence-based defect-to-panel spatial matching."""
from .iou import box_iou, coords


def _intersection_area(a, b):
    ax1, ay1, ax2, ay2 = coords(a)
    bx1, by1, bx2, by2 = coords(b)
    return max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))


def centroid_inside(point, polygon):
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and x < (xj-xi)*(y-yi)/(yj-yi or 1e-12)+xi:
            inside = not inside
        j = i
    return inside


def associate_defect(defect, panels, min_overlap=0.2):
    dx1,dy1,dx2,dy2 = coords(defect)
    da = max(0,dx2-dx1)*max(0,dy2-dy1)
    cx,cy = (dx1+dx2)/2,(dy1+dy2)/2
    candidates=[]
    for panel in panels:
        pb = panel.get("geometry") or panel["bbox"]
        if isinstance(pb, list):
            inside = centroid_inside((cx,cy), pb)
            pbox = [min(x for x,y in pb),min(y for x,y in pb),max(x for x,y in pb),max(y for x,y in pb)]
        else:
            inside = pb.get("x1",0) <= cx <= pb.get("x2",0) and pb.get("y1",0) <= cy <= pb.get("y2",0)
            pbox = pb
        overlap = box_iou((dx1,dy1,dx2,dy2), pbox)
        overlap_ratio = _intersection_area((dx1,dy1,dx2,dy2), pbox) / da if da else 0.0
        score = max(overlap, overlap_ratio, 0.75 if inside else 0.0)
        if score >= min_overlap:
            candidates.append((score, panel, overlap, inside, overlap_ratio))
    candidates.sort(key=lambda x:x[0], reverse=True)
    if not candidates:
        return {"panel_id": None, "match_status": "UNASSIGNED", "spatial_match_confidence": 0.0, "candidate_panel_ids": []}
    best=candidates[0]
    ambiguous=len(candidates)>1 and best[0]-candidates[1][0] < 0.1
    return {"panel_id": None if ambiguous else best[1].get("panel_id"),
            "match_status": "REVIEW_REQUIRED" if ambiguous else "MATCHED",
            "spatial_match_confidence": round(best[0],4), "overlap_iou": round(best[2],4),
            "defect_overlap_ratio": round(best[4],4), "centroid_contained": best[3],
            "candidate_panel_ids": [x[1].get("panel_id") for x in candidates]}
