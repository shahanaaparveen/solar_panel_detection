"""Stage-by-stage mapping quality and uncertainty diagnostics (no arbitrary accuracy scores)."""


def _mean(values):
    return round(sum(values) / len(values), 4) if values else None


def compute_mapping_quality(
    *,
    panel_results=None,
    mapping_diagnostics=None,
    registrations=None,
    findings=None,
    deduplication_report=None,
    validation_dataset_metrics=None,
):
    """Report transparent, separate per-stage quality metrics without blending into a fake score."""
    all_panels = [p for res in (panel_results or []) for p in res.get("panels", [])]
    confs = [float(p["confidence"]) for p in all_panels if p.get("confidence") is not None]
    partial_count = sum(1 for p in all_panels if p.get("is_partial"))

    post_diags = [
        d.get("postprocessing", {}) for d in (mapping_diagnostics or []) if isinstance(d, dict)
    ]
    clust_diags = [
        d.get("clustering", {}) for d in (mapping_diagnostics or []) if isinstance(d, dict)
    ]
    raw_panel_hits = sum(d.get("raw_count", 0) for d in post_diags)
    suppressed_dups = sum(d.get("suppressed_duplicates", 0) for d in post_diags)

    assigned_panels = sum(1 for p in all_panels if p.get("row_id") and p.get("column_id"))
    missing_slots = sum(d.get("estimated_missing_slots", 0) for d in clust_diags)
    total_regions = sum(d.get("region_count", 0) for d in clust_diags) or len(
        {(p.get("image_id"), p.get("region_id")) for p in all_panels if p.get("region_id")}
    )

    regs = list(registrations or [])
    registered = [r for r in regs if r.get("status") == "REGISTERED"]
    inlier_ratios = [float(r["quality"]) for r in registered if r.get("quality") is not None]
    reproj_errors = [
        float(r["mean_reprojection_error_px"])
        for r in registered
        if r.get("mean_reprojection_error_px") is not None
    ]

    all_findings = list(findings or [])
    matched = [f for f in all_findings if f.get("matchStatus") == "MATCHED"]
    ambiguous = [f for f in all_findings if f.get("matchStatus") == "REVIEW_REQUIRED"]
    unassigned = [f for f in all_findings if f.get("matchStatus") == "UNASSIGNED"]
    unregistered = [f for f in all_findings if f.get("matchStatus") == "UNREGISTERED"]
    spatial_confs = [
        float(f["spatialMatchConfidence"])
        for f in matched
        if f.get("spatialMatchConfidence") is not None
    ]

    dedup = deduplication_report or {}
    return {
        "measured_accuracy_status": (
            "EVALUATED" if validation_dataset_metrics else "UNMEASURED_NO_GROUND_TRUTH"
        ),
        "measured_accuracy_note": (
            "Evaluated against labeled validation data."
            if validation_dataset_metrics
            else "Measured mapping accuracy has not been established; no labeled ground-truth dataset was evaluated."
        ),
        "validation_dataset_metrics": validation_dataset_metrics,
        "stages": {
            "panel_detection": {
                "detected_panel_count": len(all_panels),
                "mean_confidence": _mean(confs),
                "min_confidence": round(min(confs), 4) if confs else None,
                "partial_panel_count": partial_count,
                "partial_panel_ratio": round(partial_count / len(all_panels), 4) if all_panels else None,
                "suppressed_duplicate_count": suppressed_dups,
                "duplicate_suppression_rate": (
                    round(suppressed_dups / raw_panel_hits, 4) if raw_panel_hits > 0 else None
                ),
            },
            "clustering": {
                "array_region_count": total_regions,
                "assigned_row_column_ratio": (
                    round(assigned_panels / len(all_panels), 4) if all_panels else None
                ),
                "estimated_missing_slots": missing_slots,
            },
            "registration": {
                "pair_count": len(regs),
                "registered_count": len(registered),
                "unregistered_count": len(regs) - len(registered),
                "mean_inlier_ratio": _mean(inlier_ratios),
                "mean_reprojection_error_px": _mean(reproj_errors),
                "max_reprojection_error_px": round(max(reproj_errors), 4) if reproj_errors else None,
            },
            "association": {
                "total_findings": len(all_findings),
                "matched_count": len(matched),
                "ambiguous_count": len(ambiguous),
                "unassigned_count": len(unassigned),
                "unregistered_count": len(unregistered),
                "unassigned_ratio": (
                    round((len(unassigned) + len(unregistered)) / len(all_findings), 4)
                    if all_findings
                    else None
                ),
                "mean_spatial_match_confidence": _mean(spatial_confs),
            },
            "deduplication": {
                "cross_image_verified": bool(dedup.get("cross_image_verified", False)),
                "status": dedup.get("status", "NOT_RUN"),
                "raw_observations": dedup.get("raw_observation_count", len(all_findings)),
                "consolidated_findings": dedup.get("consolidated_count", len(all_findings)),
                "duplicates_merged": dedup.get("duplicates_merged", 0),
            },
        },
    }
