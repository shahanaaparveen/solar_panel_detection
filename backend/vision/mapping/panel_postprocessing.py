"""Panel localization postprocessing: validation, clipping, suppression, and quality assessment."""
from statistics import median
from ..association.iou import box_iou, intersection_area
from .geometry import clip_bbox, normalize_polygon, panel_record


def _parse_input(payload_or_detections, image_width=None, image_height=None, image_id=None):
    if isinstance(payload_or_detections, dict):
        detections = payload_or_detections.get("detections", [])
        image_id = image_id or payload_or_detections.get("image_id")
        image_width = image_width or payload_or_detections.get("image_width")
        image_height = image_height or payload_or_detections.get("image_height")
    elif isinstance(payload_or_detections, list):
        detections = payload_or_detections
    else:
        raise ValueError("Expected detection payload dict or list of detections")
    return image_id, image_width, image_height, detections


def _matches_target(det, target_class_ids, target_classes):
    if target_class_ids is None and target_classes is None:
        return True
    cid = det.get("class_id")
    cname = det.get("class_name") or det.get("class") or det.get("label")
    if target_class_ids is not None and cid is not None and int(cid) in target_class_ids:
        return True
    if target_classes is not None and cname is not None and str(cname) in target_classes:
        return True
    return False


def suppress_duplicate_panels(panels, iou_threshold=0.55, containment_threshold=0.85):
    """Suppress duplicate or nested detections via IoU and containment NMS."""
    ordered = sorted(
        panels,
        key=lambda p: (p["confidence"], p["dimensions"]["area"]),
        reverse=True,
    )
    kept = []
    suppressed = 0
    for candidate in ordered:
        cbox = candidate["bbox"]
        carea = max(1e-9, (cbox["x2"] - cbox["x1"]) * (cbox["y2"] - cbox["y1"]))
        is_dup = False
        for existing in kept:
            ebox = existing["bbox"]
            if box_iou(cbox, ebox) >= iou_threshold:
                is_dup = True
                break
            earea = max(1e-9, (ebox["x2"] - ebox["x1"]) * (ebox["y2"] - ebox["y1"]))
            inter = intersection_area(cbox, ebox)
            if inter / min(carea, earea) >= containment_threshold:
                is_dup = True
                break
        if is_dup:
            suppressed += 1
        else:
            kept.append(candidate)
    return kept, suppressed


def assess_panel_quality(panels, image_width=None, image_height=None):
    """Flag partial/truncated or geometrically anomalous panel detections using scale statistics."""
    if not panels:
        return {"partial_count": 0, "mean_confidence": 0.0, "median_area": 0.0, "median_aspect_ratio": 0.0}
    areas = [p["dimensions"]["area"] for p in panels if p["dimensions"]["area"] > 0]
    aspects = [p["aspect_ratio"] for p in panels if p["aspect_ratio"] > 0]
    med_area = median(areas) if areas else 0.0
    med_aspect = median(aspects) if aspects else 1.0
    partial_count = 0
    for p in panels:
        flags = []
        area = p["dimensions"]["area"]
        aspect = p["aspect_ratio"]
        if med_area > 0 and area < 0.30 * med_area:
            flags.append("small_area_outlier")
        if med_aspect > 0 and (aspect > 2.2 * med_aspect or aspect < 0.45 * med_aspect):
            flags.append("aspect_ratio_outlier")
        if p.get("clipped_to_image"):
            flags.append("image_boundary_clipped")
        elif image_width is not None and image_height is not None:
            b = p["bbox"]
            if b["x1"] <= 1.0 or b["y1"] <= 1.0 or b["x2"] >= image_width - 1.0 or b["y2"] >= image_height - 1.0:
                flags.append("touches_image_boundary")
        is_partial = bool(
            "small_area_outlier" in flags
            or ("image_boundary_clipped" in flags and "aspect_ratio_outlier" in flags)
        )
        if is_partial:
            partial_count += 1
        p["is_partial"] = is_partial
        p["quality_flags"] = flags
        p["quality_score"] = round(
            max(0.0, p["confidence"] * (0.7 if is_partial else 1.0)),
            4,
        )
    return {
        "partial_count": partial_count,
        "mean_confidence": round(sum(p["confidence"] for p in panels) / len(panels), 4),
        "median_area": round(med_area, 3),
        "median_aspect_ratio": round(med_aspect, 4),
    }


def postprocess_panel_detections(
    payload_or_detections,
    *,
    image_width=None,
    image_height=None,
    image_id=None,
    target_classes=None,
    target_class_ids=None,
    min_confidence=0.25,
    iou_threshold=0.55,
    containment_threshold=0.85,
):
    """Validate, clip, suppress duplicates, and assess quality for raw panel detections."""
    img_id, width, height, raw_detections = _parse_input(
        payload_or_detections, image_width=image_width, image_height=image_height, image_id=image_id
    )
    target_classes_set = set(map(str, target_classes)) if target_classes is not None else None
    target_ids_set = set(map(int, target_class_ids)) if target_class_ids is not None else None

    valid_panels = []
    rejected = []
    filtered_low_conf = 0
    filtered_non_target = 0

    for idx, det in enumerate(raw_detections):
        if not isinstance(det, dict):
            rejected.append({"index": idx, "reason": "Detection must be a dict"})
            continue
        if not _matches_target(det, target_ids_set, target_classes_set):
            filtered_non_target += 1
            continue
        try:
            conf = float(det.get("confidence", 0.0))
        except (TypeError, ValueError):
            rejected.append({"index": idx, "reason": "Invalid confidence"})
            continue
        if not 0.0 <= conf <= 1.0:
            rejected.append({"index": idx, "reason": "Confidence outside [0, 1]"})
            continue
        if conf < min_confidence:
            filtered_low_conf += 1
            continue

        det_img_size = det.get("image_size") or {}
        w = width or det_img_size.get("width")
        h = height or det_img_size.get("height")
        raw_box = det.get("bbox") or det
        raw_poly = det.get("mask") or det.get("polygon") or det.get("geometry")
        try:
            record = panel_record(
                raw_box,
                conf,
                panel_id=det.get("panel_id"),
                geometry=raw_poly,
                image_width=w,
                image_height=h,
                image_id=det.get("image_id") or img_id,
            )
            if det.get("class_id") is not None:
                record["source_class_id"] = int(det["class_id"])
            if det.get("class_name"):
                record["source_class_name"] = str(det["class_name"])
            valid_panels.append(record)
        except ValueError as exc:
            rejected.append({"index": idx, "reason": str(exc)})

    deduped, suppressed_count = suppress_duplicate_panels(
        valid_panels, iou_threshold=iou_threshold, containment_threshold=containment_threshold
    )
    quality = assess_panel_quality(deduped, image_width=width, image_height=height)

    diagnostics = {
        "raw_count": len(raw_detections),
        "valid_count": len(valid_panels),
        "kept_count": len(deduped),
        "rejected_count": len(rejected),
        "filtered_low_confidence": filtered_low_conf,
        "filtered_non_target": filtered_non_target,
        "suppressed_duplicates": suppressed_count,
        "rejected_details": rejected[:20],
        **quality,
    }
    return {
        "status": "COMPLETED" if deduped else "NO_PANELS_DETECTED",
        "image_id": img_id,
        "image_size": {"width": width, "height": height} if width and height else None,
        "panels": deduped,
        "diagnostics": diagnostics,
    }
