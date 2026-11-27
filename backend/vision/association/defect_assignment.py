"""Multi-factor defect-to-panel spatial assignment preserving traceability."""
from .association_validation import compute_association_score, is_ambiguous_match, validate_defect_geometry
from .centroid_matching import centroid_inside, defect_centroid, normalized_centroid_distance
from .polygon_matching import defect_panel_polygon_metrics


def associate_defect(
    defect,
    panels,
    min_overlap=0.2,
    registration_quality=None,
    registration_status=None,
):
    """Associate one defect with a solar panel using polygon/box coverage, centroid, and IoU.

    Never selects the nearest panel when spatial overlap criteria are not satisfied.
    """
    source_ref = {
        k: defect.get(k)
        for k in ("image_id", "model_run_id", "model_id", "class_name", "label", "confidence", "bbox")
        if defect.get(k) is not None
    }

    if registration_status is not None and registration_status != "REGISTERED":
        return {
            "panel_id": None,
            "match_status": "UNREGISTERED",
            "association_status": "unregistered",
            "spatial_match_confidence": 0.0,
            "overlap_iou": 0.0,
            "defect_overlap_ratio": 0.0,
            "centroid_contained": False,
            "candidate_panel_ids": [],
            "review_required": True,
            "source_detection_ref": source_ref,
        }

    try:
        dbox = validate_defect_geometry(defect)
    except ValueError:
        return {
            "panel_id": None,
            "match_status": "UNASSIGNED",
            "association_status": "unassigned",
            "spatial_match_confidence": 0.0,
            "overlap_iou": 0.0,
            "defect_overlap_ratio": 0.0,
            "centroid_contained": False,
            "candidate_panel_ids": [],
            "review_required": True,
            "source_detection_ref": source_ref,
        }

    defect_geom = defect.get("mask") or defect.get("polygon") or dbox
    cx, cy = defect_centroid(dbox)

    candidates = []
    for panel in panels or []:
        panel_geom = panel.get("geometry") or panel["bbox"]
        inside = centroid_inside((cx, cy), panel_geom)
        iou, coverage, _inter, _da, _pa = defect_panel_polygon_metrics(defect_geom, panel_geom)
        norm_dist = normalized_centroid_distance((cx, cy), panel)
        score = compute_association_score(
            iou,
            coverage,
            inside,
            norm_centroid_dist=norm_dist,
            registration_quality=registration_quality,
        )
        if score >= min_overlap:
            candidates.append({
                "panel": panel,
                "panel_id": panel.get("panel_id"),
                "site_panel_id": panel.get("site_panel_id"),
                "score": score,
                "overlap_iou": iou,
                "defect_overlap_ratio": coverage,
                "centroid_contained": inside,
                "normalized_centroid_distance": round(norm_dist, 4),
            })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    if not candidates:
        return {
            "panel_id": None,
            "match_status": "UNASSIGNED",
            "association_status": "unassigned",
            "spatial_match_confidence": 0.0,
            "overlap_iou": 0.0,
            "defect_overlap_ratio": 0.0,
            "centroid_contained": False,
            "candidate_panel_ids": [],
            "review_required": True,
            "source_detection_ref": source_ref,
        }

    best = candidates[0]
    ambiguous = is_ambiguous_match(candidates)
    return {
        "panel_id": None if ambiguous else best["panel_id"],
        "site_panel_id": None if ambiguous else best["site_panel_id"],
        "match_status": "REVIEW_REQUIRED" if ambiguous else "MATCHED",
        "association_status": "ambiguous" if ambiguous else "matched",
        "spatial_match_confidence": round(best["score"], 4),
        "overlap_iou": round(best["overlap_iou"], 4),
        "defect_overlap_ratio": round(best["defect_overlap_ratio"], 4),
        "centroid_contained": best["centroid_contained"],
        "normalized_centroid_distance": best["normalized_centroid_distance"],
        "candidate_panel_ids": [item["panel_id"] for item in candidates],
        "candidate_scores": [
            {"panel_id": item["panel_id"], "score": round(item["score"], 4), "coverage": round(item["defect_overlap_ratio"], 4)}
            for item in candidates
        ],
        "review_required": ambiguous,
        "source_detection_ref": source_ref,
    }
