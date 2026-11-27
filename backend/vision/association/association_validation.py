"""Validation, confidence calculation, and ambiguity detection for defect-to-panel association."""
from .iou import box_area, coords


def validate_defect_geometry(defect):
    """Validate defect coordinates and return (x1, y1, x2, y2) with positive area."""
    x1, y1, x2, y2 = coords(defect)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Defect bounding box must have positive area")
    return (x1, y1, x2, y2)


def compute_association_score(
    overlap_iou,
    coverage_ratio,
    centroid_contained,
    norm_centroid_dist=None,
    registration_quality=None,
):
    """Compute documented spatial-match confidence combining coverage, containment, and IoU.

    Score combines:
      - Defect area coverage ratio (primary when defects are small relative to panels)
      - Centroid containment bonus (0.75 floor when defect center lies inside panel boundary)
      - IoU overlap
      - Optional cross-modal registration quality attenuation factor
    """
    base = max(float(overlap_iou), float(coverage_ratio), 0.75 if centroid_contained else 0.0)
    if norm_centroid_dist is not None and centroid_contained and coverage_ratio >= 0.5:
        consistency_bonus = max(0.0, (0.5 - min(0.5, norm_centroid_dist)) * 0.1)
        base = min(1.0, base + consistency_bonus)
    if registration_quality is not None:
        reg_q = max(0.0, min(1.0, float(registration_quality)))
        base = base * (0.5 + 0.5 * reg_q)
    return max(0.0, min(1.0, base))


def is_ambiguous_match(candidates, margin_threshold=0.1, secondary_coverage_threshold=0.25):
    """Return True if top candidates are too close or defect meaningfully spans multiple panels."""
    if len(candidates) <= 1:
        return False
    best = candidates[0]
    second = candidates[1]
    if best["score"] - second["score"] < margin_threshold:
        return True
    if second["defect_overlap_ratio"] >= secondary_coverage_threshold and best["defect_overlap_ratio"] < 0.75:
        return True
    return False
