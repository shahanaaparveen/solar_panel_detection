"""Evidence-based pairing between RGB and thermal drone captures."""
from pathlib import Path
import re
from .metadata import extract_image_metadata, haversine_meters, parse_timestamp

_MODALITY_SUFFIX_RE = re.compile(
    r"(?:^|[_\-\s])(rgb|visible|vis|wide|w|zoom|z|thermal|thm|ir|t)(?=$|[_\-\s])",
    re.IGNORECASE,
)


def normalize_pair_stem(filename):
    """Strip extension and common drone modality suffixes for filename pairing."""
    stem = Path(str(filename or "")).stem
    cleaned = _MODALITY_SUFFIX_RE.sub("", stem)
    cleaned = re.sub(r"[_\-\s]+", "_", cleaned).strip("_").lower()
    return cleaned or stem.lower()


def _resolve_meta(record, upload_dir=None):
    meta = dict(record.get("metadata") or {})
    if upload_dir and record.get("path") and ("gps" not in meta or "capturedAt" not in meta):
        disk_path = Path(upload_dir) / record["path"]
        if disk_path.is_file():
            extracted = extract_image_metadata(disk_path)
            for k, v in extracted.items():
                meta.setdefault(k, v)
    return meta


def pair_rgb_thermal_images(
    rgb_images,
    thermal_images,
    *,
    upload_dir=None,
    max_time_diff_seconds=10.0,
    max_gps_meters=15.0,
):
    """Pair RGB and thermal images using filename stems, capture timestamps, or GPS proximity.

    Never pairs images arbitrarily when no corroborating evidence exists.
    """
    if not rgb_images or not thermal_images:
        return []

    rgb_metas = {r["imageId"]: _resolve_meta(r, upload_dir) for r in rgb_images}
    thm_metas = {t["imageId"]: _resolve_meta(t, upload_dir) for t in thermal_images}

    candidates = []
    for rgb in rgb_images:
        r_id = rgb["imageId"]
        r_stem = normalize_pair_stem(rgb.get("imageName") or rgb.get("path"))
        r_meta = rgb_metas[r_id]
        r_dt = parse_timestamp(r_meta.get("capturedAt"))
        r_gps = r_meta.get("gps")

        for thm in thermal_images:
            t_id = thm["imageId"]
            t_stem = normalize_pair_stem(thm.get("imageName") or thm.get("path"))
            t_meta = thm_metas[t_id]
            t_dt = parse_timestamp(t_meta.get("capturedAt"))
            t_gps = t_meta.get("gps")

            reasons = []
            score = 0.0
            if r_stem and t_stem and r_stem == t_stem:
                score = max(score, 0.95)
                reasons.append("filename_stem")
            if r_dt and t_dt:
                dt = abs((r_dt - t_dt).total_seconds())
                if dt <= max_time_diff_seconds:
                    ts_score = 0.85 * (1.0 - dt / max(max_time_diff_seconds, 1.0)) + 0.05
                    score = max(score, ts_score)
                    reasons.append(f"timestamp_delta_{dt:.1f}s")
            if r_gps and t_gps:
                dist = haversine_meters(
                    r_gps["latitude"], r_gps["longitude"], t_gps["latitude"], t_gps["longitude"]
                )
                if dist <= max_gps_meters:
                    gps_score = 0.75 * (1.0 - dist / max(max_gps_meters, 1.0)) + 0.05
                    score = max(score, gps_score)
                    reasons.append(f"gps_{dist:.2f}m")
            if reasons:
                candidates.append({
                    "rgb_image_id": r_id,
                    "thermal_image_id": t_id,
                    "rgb_name": rgb.get("imageName"),
                    "thermal_name": thm.get("imageName"),
                    "confidence": round(min(1.0, score), 4),
                    "signals": reasons,
                })

    candidates.sort(key=lambda c: (-c["confidence"], c["rgb_image_id"], c["thermal_image_id"]))
    used_rgb = set()
    used_thm = set()
    paired = []
    for cand in candidates:
        if cand["rgb_image_id"] in used_rgb or cand["thermal_image_id"] in used_thm:
            continue
        used_rgb.add(cand["rgb_image_id"])
        used_thm.add(cand["thermal_image_id"])
        paired.append(cand)
    return paired
