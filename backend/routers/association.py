"""FastAPI router for defect-to-panel association, deduplication, and panel-level findings."""
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from auth import require_project_access
from database import findings_col, panels_col, projects_col, registrations_col
from vision.association.spatial_matching import associate_defect
from vision.mapping.coordinate_transform import transform_bbox
from vision.risk.severity_engine import assess_finding
from .mapping import compute_project_mapping_snapshot
from .schemas import AssociationAnalyzeRequest, parse_project_oid

router = APIRouter(tags=["association"])


def refresh_project_associations(project_id: str, *, job_id: str | None = None, min_overlap: float = 0.2, max_time_window_hours: float = 24.0):
    """Re-run geometric defect-to-panel association using current panels & verified registrations."""
    if not projects_col.find_one({"_id": parse_project_oid(project_id)}):
        raise HTTPException(404, "Project not found")

    panels_by_image = {
        row["imageId"]: row.get("panels", [])
        for row in panels_col.find({"projectId": project_id, "status": "COMPLETED"})
    }
    regs = {
        row["movingImageId"]: row
        for row in registrations_col.find({"projectId": project_id, "status": "REGISTERED"})
    }
    query = {"projectId": project_id}
    if job_id:
        query["jobId"] = job_id

    updated_count = 0
    for finding in findings_col.find(query):
        modality = finding.get("modality")
        img_id = finding.get("imageId")
        ev = (finding.get("evidence") or [{}])[0]
        bbox = ev.get("bbox")
        if not bbox:
            continue

        if modality == "rgb":
            panels = panels_by_image.get(img_id, [])
            if not panels:
                continue
            match = associate_defect({"bbox": bbox}, panels, min_overlap=min_overlap)
        elif modality == "thermal":
            reg = regs.get(img_id)
            if not reg or not reg.get("transform"):
                continue
            ref_panels = panels_by_image.get(reg.get("referenceImageId"), [])
            transformed = transform_bbox(bbox, reg["transform"])
            if not transformed or not ref_panels:
                continue
            match = associate_defect(
                {"bbox": transformed},
                ref_panels,
                min_overlap=min_overlap,
                registration_quality=reg.get("quality"),
                registration_status="REGISTERED",
            )
        else:
            continue

        risk = assess_finding(
            finding.get("defectType", "unknown"),
            float(finding.get("modelConfidence") or 0.0),
            match.get("spatial_match_confidence"),
        )
        res = findings_col.update_one(
            {"_id": finding["_id"]},
            {
                "$set": {
                    "panelId": match.get("panel_id"),
                    "sitePanelId": match.get("site_panel_id"),
                    "matchStatus": match["match_status"],
                    "spatialMatchConfidence": match.get("spatial_match_confidence"),
                    "candidatePanelIds": match.get("candidate_panel_ids", []),
                    "inspectionPriority": risk["inspection_priority"],
                    "reviewRequired": risk["review_required"] or match["match_status"] != "MATCHED",
                }
            },
        )
        updated_count += res.modified_count

    snapshot = compute_project_mapping_snapshot(
        project_id,
        job_id=job_id,
        min_overlap=min_overlap,
        max_time_window_hours=max_time_window_hours,
        persist=True,
    )
    snapshot["reassociatedFindings"] = updated_count
    return snapshot


@router.post("/api/projects/{project_id}/association/analyze", dependencies=[Depends(require_project_access)])
async def analyze_project_association(project_id: str, payload: AssociationAnalyzeRequest | None = None):
    cfg = payload or AssociationAnalyzeRequest()
    return await run_in_threadpool(
        refresh_project_associations,
        project_id,
        job_id=cfg.job_id,
        min_overlap=cfg.min_overlap,
        max_time_window_hours=cfg.max_time_window_hours,
    )


@router.get("/api/projects/{project_id}/association/summary", dependencies=[Depends(require_project_access)])
def get_association_summary(project_id: str, job_id: str | None = None):
    snapshot = compute_project_mapping_snapshot(project_id, job_id=job_id, persist=False)
    return {
        "projectId": project_id,
        "jobId": job_id,
        "panelAggregation": snapshot["panelAggregation"],
        "deduplication": snapshot["deduplication"],
        "quality": snapshot["quality"],
    }
