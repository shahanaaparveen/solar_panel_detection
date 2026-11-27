"""Cross-image duplicate finding detection with strict spatial and temporal evidence gates."""
from math import hypot
from uuid import uuid4
from ..mapping.coordinate_transform import transform_bbox
from ..registration.metadata import parse_timestamp
from .iou import box_iou, coords


def _within_panel_box(defect_bbox, panel_bbox):
    px1, py1, px2, py2 = coords(panel_bbox)
    dx1, dy1, dx2, dy2 = coords(defect_bbox)
    pw = max(1e-6, px2 - px1)
    ph = max(1e-6, py2 - py1)
    return {
        "x1": (dx1 - px1) / pw,
        "y1": (dy1 - py1) / ph,
        "x2": (dx2 - px1) / pw,
        "y2": (dy2 - py1) / ph,
    }


def _box_center_and_diag(bbox):
    x1, y1, x2, y2 = coords(bbox)
    return ((x1 + x2) * 0.5, (y1 + y2) * 0.5), hypot(x2 - x1, y2 - y1)


def _same_inspection_window(obs_a, obs_b, images_by_id, max_hours):
    img_a = (images_by_id or {}).get(obs_a.get("imageId"), {})
    img_b = (images_by_id or {}).get(obs_b.get("imageId"), {})
    ts_a = parse_timestamp(obs_a.get("capturedAt") or (img_a.get("metadata") or {}).get("capturedAt"))
    ts_b = parse_timestamp(obs_b.get("capturedAt") or (img_b.get("metadata") or {}).get("capturedAt"))
    if ts_a is not None and ts_b is not None:
        return abs((ts_a - ts_b).total_seconds()) <= max_hours * 3600.0
    # If timestamps are unavailable, do not merge across explicitly different inspectionDate values.
    date_a = obs_a.get("inspectionDate") or img_a.get("inspectionDate")
    date_b = obs_b.get("inspectionDate") or img_b.get("inspectionDate")
    if date_a and date_b and date_a != date_b:
        return False
    return True


def _build_reg_lookup(pairwise_registrations):
    lookup = {}
    for reg in pairwise_registrations or []:
        if reg.get("status") != "REGISTERED" or not reg.get("transform"):
            continue
        src = reg.get("source_image_id") or reg.get("movingImageId")
        dst = reg.get("target_image_id") or reg.get("referenceImageId")
        if src and dst:
            lookup[(src, dst)] = reg["transform"]
    return lookup


def _extract_bbox(finding):
    ev = (finding.get("evidence") or [{}])[0]
    return finding.get("bbox") or ev.get("bbox")


def _panel_lookup(panels_by_image):
    lookup = {}
    for img_id, panels in (panels_by_image or {}).items():
        for panel in panels:
            pid = panel.get("panel_id")
            if pid:
                lookup[(img_id, pid)] = panel
    return lookup


def _spatial_correspondence(
    fa,
    fb,
    reg_lookup,
    panel_by_key,
    iou_threshold,
    max_center_dist_ratio,
):
    """Return (matched_bool, evidence_method) only when verified cross-image geometry matches."""
    img_a = fa.get("imageId")
    img_b = fb.get("imageId")
    if not img_a or not img_b or img_a == img_b:
        return False, None

    box_a = _extract_bbox(fa)
    box_b = _extract_bbox(fb)
    if box_a and box_b:
        for src_id, src_box, dst_id, dst_box in (
            (img_a, box_a, img_b, box_b),
            (img_b, box_b, img_a, box_a),
        ):
            matrix = reg_lookup.get((src_id, dst_id))
            if matrix:
                projected = transform_bbox(src_box, matrix)
                if projected:
                    if box_iou(projected, dst_box) >= iou_threshold:
                        return True, "registered_homography_iou"
                    ca, da = _box_center_and_diag(projected)
                    cb, db = _box_center_and_diag(dst_box)
                    if max(da, db) > 0 and hypot(ca[0] - cb[0], ca[1] - cb[1]) <= max_center_dist_ratio * max(da, db):
                        return True, "registered_homography_centroid"

    site_a = fa.get("sitePanelId")
    site_b = fb.get("sitePanelId")
    if site_a and site_b and site_a == site_b and box_a and box_b:
        pa = panel_by_key.get((img_a, fa.get("panelId")))
        pb = panel_by_key.get((img_b, fb.get("panelId")))
        if pa and pb:
            na = _within_panel_box(box_a, pa["bbox"])
            nb = _within_panel_box(box_b, pb["bbox"])
            if box_iou(na, nb) >= 0.2:
                return True, "site_panel_normalized_iou"
            ca, _ = _box_center_and_diag(na)
            cb, _ = _box_center_and_diag(nb)
            if hypot(ca[0] - cb[0], ca[1] - cb[1]) <= max_center_dist_ratio:
                return True, "site_panel_normalized_centroid"

    return False, None


def deduplicate_findings_across_images(
    findings,
    *,
    images_by_id=None,
    panels_by_image=None,
    pairwise_registrations=None,
    max_time_window_hours=24.0,
    iou_threshold=0.25,
    max_center_dist_ratio=0.35,
):
    """Consolidate repeated observations of the same physical defect across overlapping images.

    Never merges across different defect classes, different inspection windows, or unaligned images.
    Preserves all original image-level finding and evidence records.
    """
    raw = list(findings or [])
    if not raw:
        return {
            "status": "NO_FINDINGS",
            "cross_image_verified": False,
            "raw_observation_count": 0,
            "consolidated_count": 0,
            "duplicates_merged": 0,
            "consolidated_findings": [],
        }

    reg_lookup = _build_reg_lookup(pairwise_registrations)
    panel_by_key = _panel_lookup(panels_by_image)
    has_cross_image_evidence = bool(reg_lookup) or any(
        p.get("site_panel_id") for panels in (panels_by_image or {}).values() for p in panels
    )

    n = len(raw)
    parent = list(range(n))
    merge_methods = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b, method):
        ra, rb = find(a), find(b)
        if ra != rb:
            lo, hi = (ra, rb) if ra < rb else (rb, ra)
            parent[hi] = lo
            merge_methods.setdefault(lo, set()).add(method)

    if has_cross_image_evidence:
        for i in range(n):
            fi = raw[i]
            label_i = str(fi.get("defectType") or fi.get("label") or "").strip().lower()
            for j in range(i + 1, n):
                fj = raw[j]
                label_j = str(fj.get("defectType") or fj.get("label") or "").strip().lower()
                if not label_i or label_i != label_j:
                    continue
                if not _same_inspection_window(fi, fj, images_by_id, max_time_window_hours):
                    continue
                matched, method = _spatial_correspondence(
                    fi, fj, reg_lookup, panel_by_key, iou_threshold, max_center_dist_ratio
                )
                if matched:
                    union(i, j, method)

    groups = {}
    for idx in range(n):
        groups.setdefault(find(idx), []).append(raw[idx])

    consolidated = []
    for root_idx in sorted(groups):
        obs = groups[root_idx]
        primary = max(obs, key=lambda o: (o.get("modelConfidence") or 0.0, o.get("spatialMatchConfidence") or 0.0))
        timestamps = []
        evidence_all = []
        source_ids = []
        image_ids = []
        modalities = []
        for item in obs:
            if item.get("findingId"):
                source_ids.append(item["findingId"])
            if item.get("imageId") and item["imageId"] not in image_ids:
                image_ids.append(item["imageId"])
            if item.get("modality") and item["modality"] not in modalities:
                modalities.append(item["modality"])
            img_meta = ((images_by_id or {}).get(item.get("imageId"), {}) or {}).get("metadata") or {}
            ts = item.get("capturedAt") or img_meta.get("capturedAt") or item.get("createdAt")
            if ts:
                timestamps.append(ts)
            evidence_all.extend(item.get("evidence") or [])

        methods = sorted(merge_methods.get(root_idx, set()))
        dedup_status = (
            "DEDUPLICATED"
            if len(obs) > 1
            else ("VERIFIED_UNIQUE" if has_cross_image_evidence else "UNVERIFIED_CROSS_IMAGE")
        )
        consolidated.append({
            "consolidatedFindingId": primary.get("findingId") or uuid4().hex,
            "panelId": primary.get("sitePanelId") or primary.get("panelId"),
            "localPanelIds": sorted({o.get("panelId") for o in obs if o.get("panelId")}),
            "sitePanelId": primary.get("sitePanelId"),
            "defectType": primary.get("defectType") or primary.get("label"),
            "modality": primary.get("modality"),
            "modalitiesObserved": modalities,
            "modelConfidence": max(float(o.get("modelConfidence") or 0.0) for o in obs),
            "spatialMatchConfidence": max(float(o.get("spatialMatchConfidence") or 0.0) for o in obs),
            "matchStatus": primary.get("matchStatus"),
            "inspectionPriority": primary.get("inspectionPriority"),
            "severity": primary.get("severity"),
            "severityStatus": primary.get("severityStatus"),
            "reviewRequired": any(bool(o.get("reviewRequired")) for o in obs),
            "recommendation": primary.get("recommendation"),
            "observationCount": len(obs),
            "sourceFindingIds": source_ids,
            "imageIds": image_ids,
            "observationTimestamps": timestamps,
            "deduplicationStatus": dedup_status,
            "deduplicationMethods": methods,
            "evidence": evidence_all,
        })

    return {
        "status": "COMPLETED" if has_cross_image_evidence else "UNVERIFIED_CROSS_IMAGE",
        "cross_image_verified": has_cross_image_evidence,
        "raw_observation_count": n,
        "consolidated_count": len(consolidated),
        "duplicates_merged": n - len(consolidated),
        "consolidated_findings": consolidated,
    }
