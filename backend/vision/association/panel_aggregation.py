"""Panel-level inspection aggregation derived strictly from real panel and finding records."""


def aggregate_panel_findings(
    panels_by_image,
    findings,
    *,
    consolidated_findings=None,
    image_analysis_statuses=None,
):
    """Aggregate findings by panel identity without double-counting or fabricating healthy counts.

    Healthy panel counts are computed ONLY over detected panels whose corresponding images
    completed defect inference cleanly (status == 'COMPLETED').
    """
    active_findings = list(consolidated_findings if consolidated_findings is not None else (findings or []))
    analysis_status_map = dict(image_analysis_statuses or {})

    panel_buckets = {}
    for img_id, panels in (panels_by_image or {}).items():
        for panel in panels:
            site_id = panel.get("site_panel_id")
            local_id = panel.get("panel_id")
            key = site_id or local_id
            if not key:
                continue
            bucket = panel_buckets.get(key)
            if bucket is None:
                bucket = {
                    "panel_id": key,
                    "local_panel_ids": [],
                    "site_panel_id": site_id,
                    "identity_scope": "site_registered" if site_id else "image_local",
                    "row_id": panel.get("row_id"),
                    "column_id": panel.get("column_id"),
                    "row_label": panel.get("row_label"),
                    "column_label": panel.get("column_label"),
                    "confidence": panel.get("confidence"),
                    "image_ids": [],
                    "findings": [],
                    "thermal_finding_count": 0,
                    "rgb_finding_count": 0,
                    "priority_distribution": {"High": 0, "Medium": 0, "Low": 0},
                    "severity_distribution": {},
                    "evidence_refs": [],
                    "last_observation_date": None,
                }
                panel_buckets[key] = bucket
            if local_id and local_id not in bucket["local_panel_ids"]:
                bucket["local_panel_ids"].append(local_id)
            if img_id and img_id not in bucket["image_ids"]:
                bucket["image_ids"].append(img_id)

    unassigned = []
    uncertain = []

    for finding in active_findings:
        status = finding.get("matchStatus")
        pid = finding.get("sitePanelId") or finding.get("panelId")
        if status in {"UNASSIGNED", "UNREGISTERED"} or not pid:
            unassigned.append(finding)
            continue
        if status == "REVIEW_REQUIRED":
            uncertain.append(finding)
            continue
        bucket = panel_buckets.get(pid)
        if bucket is None:
            unassigned.append(finding)
            continue

        bucket["findings"].append({
            "finding_id": finding.get("consolidatedFindingId") or finding.get("findingId"),
            "defect_type": finding.get("defectType") or finding.get("label"),
            "modality": finding.get("modality"),
            "modalities_observed": finding.get("modalitiesObserved") or ([finding.get("modality")] if finding.get("modality") else []),
            "model_confidence": finding.get("modelConfidence"),
            "spatial_match_confidence": finding.get("spatialMatchConfidence"),
            "inspection_priority": finding.get("inspectionPriority"),
            "severity": finding.get("severity"),
            "severity_status": finding.get("severityStatus"),
            "observation_count": finding.get("observationCount", 1),
            "review_required": bool(finding.get("reviewRequired")),
            "evidence": finding.get("evidence") or [],
        })
        mods = set(finding.get("modalitiesObserved") or ([finding.get("modality")] if finding.get("modality") else []))
        if "thermal" in mods:
            bucket["thermal_finding_count"] += 1
        if "rgb" in mods:
            bucket["rgb_finding_count"] += 1
        prio = finding.get("inspectionPriority")
        if prio in bucket["priority_distribution"]:
            bucket["priority_distribution"][prio] += 1
        sev_key = finding.get("severity") or finding.get("severityStatus") or "UNVALIDATED"
        bucket["severity_distribution"][sev_key] = bucket["severity_distribution"].get(sev_key, 0) + 1
        bucket["evidence_refs"].extend(finding.get("evidence") or [])
        timestamps = finding.get("observationTimestamps") or ([finding.get("createdAt")] if finding.get("createdAt") else [])
        for ts in timestamps:
            if ts and (bucket["last_observation_date"] is None or str(ts) > str(bucket["last_observation_date"])):
                bucket["last_observation_date"] = ts

    healthy_count = 0
    affected_count = 0
    review_count = 0
    incomplete_count = 0
    evaluated_count = 0

    records = []
    for key in sorted(panel_buckets):
        bucket = panel_buckets[key]
        img_statuses = [analysis_status_map.get(img_id) for img_id in bucket["image_ids"] if img_id in analysis_status_map]
        analysis_complete = bool(img_statuses) and all(st == "COMPLETED" for st in img_statuses)
        if not analysis_status_map and bucket["findings"]:
            analysis_complete = True

        f_count = len(bucket["findings"])
        needs_review = any(f.get("review_required") for f in bucket["findings"])

        if img_statuses and not analysis_complete and f_count == 0:
            insp_status = "Incomplete"
            manual_status = "analysis_incomplete"
            incomplete_count += 1
        elif needs_review:
            insp_status = "Requires Review"
            manual_status = "pending_review"
            review_count += 1
            affected_count += 1
            evaluated_count += 1
        elif f_count > 0:
            insp_status = "Defect Detected"
            manual_status = "pending_review"
            affected_count += 1
            evaluated_count += 1
        elif analysis_complete:
            insp_status = "Healthy"
            manual_status = "not_required"
            healthy_count += 1
            evaluated_count += 1
        else:
            insp_status = "Not Evaluated"
            manual_status = "not_evaluated"
            incomplete_count += 1

        bucket["finding_count"] = f_count
        bucket["inspection_status"] = insp_status
        bucket["manual_verification_status"] = manual_status
        records.append(bucket)

    total_panels = len(records)
    health_rate = round((healthy_count / evaluated_count) * 100.0, 2) if evaluated_count > 0 else None

    return {
        "panels": records,
        "unassigned_findings": unassigned,
        "uncertain_findings": uncertain,
        "summary": {
            "total_panels": total_panels,
            "evaluated_panels": evaluated_count,
            "healthy_panels": healthy_count if evaluated_count > 0 else None,
            "affected_panels": affected_count,
            "review_required_panels": review_count,
            "incomplete_panels": incomplete_count,
            "health_rate": health_rate,
            "unassigned_finding_count": len(unassigned),
            "uncertain_finding_count": len(uncertain),
            "consolidated_finding_count": len(active_findings),
            "raw_finding_count": len(findings or []),
        },
    }
