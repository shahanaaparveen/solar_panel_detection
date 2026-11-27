"""FastAPI router for evidence-gated RGB-thermal pairing and registration."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from auth import require_project_access
from database import detections_col, findings_col, images_col, panels_col, projects_col, registrations_col
from vision.association.spatial_matching import associate_defect
from vision.mapping.coordinate_transform import transform_bbox
from vision.registration.image_alignment import align_images
from vision.registration.image_pairing import pair_rgb_thermal_images
from vision.risk.severity_engine import assess_finding
from .schemas import AutoRegistrationRequest, get_upload_dir, parse_project_oid, serialize_docs, utc_now

logger = logging.getLogger("solar_inspect.registration")
router = APIRouter(tags=["registration"])


def execute_pair_registration(project_id: str, rgb: dict, thermal: dict, *, upload_dir=None, minimum_matches: int = 12):
    """Run alignment for one RGB/thermal pair, update thermal findings, and persist registration."""
    base_dir = upload_dir or get_upload_dir()
    try:
        result = align_images(
            base_dir / rgb["path"],
            base_dir / thermal["path"],
            minimum_matches=minimum_matches,
            reference_image_id=rgb["imageId"],
            moving_image_id=thermal["imageId"],
        )
    except Exception:
        logger.exception("Image registration failed for project %s", project_id)
        result = {"status": "UNREGISTERED", "reason": "Registration processing failed"}

    record = {
        "projectId": project_id,
        "referenceImageId": rgb["imageId"],
        "movingImageId": thermal["imageId"],
        "referenceModality": "rgb",
        "movingModality": "thermal",
        **result,
        "createdAt": utc_now(),
    }

    associated = 0
    if result.get("status") == "REGISTERED" and result.get("transform"):
        panels = panels_col.find_one({"projectId": project_id, "imageId": rgb["imageId"], "status": "COMPLETED"})
        thermal_run = detections_col.find_one(
            {"projectId": project_id, "imageId": thermal["imageId"], "imageType": "thermal", "status": "COMPLETED"},
            sort=[("analyzedAt", -1)],
        )
        if panels and thermal_run:
            reg_quality = result.get("quality")
            for detection in thermal_run.get("detections", []):
                transformed = transform_bbox(detection["bbox"], result["transform"])
                if transformed is None:
                    continue
                match = associate_defect(
                    {"bbox": transformed},
                    panels.get("panels", []),
                    registration_quality=reg_quality,
                    registration_status="REGISTERED",
                )
                risk = assess_finding(
                    detection["label"],
                    detection["confidence"],
                    match.get("spatial_match_confidence"),
                    evidence_quality="good" if (reg_quality or 0.0) >= 0.7 else "unknown",
                )
                query = {
                    "projectId": project_id,
                    "jobId": thermal_run["jobId"],
                    "modality": "thermal",
                    "evidence.imageId": thermal["imageId"],
                    "evidence.bbox": detection["bbox"],
                }
                update = {
                    "panelId": match.get("panel_id"),
                    "sitePanelId": match.get("site_panel_id"),
                    "matchStatus": match["match_status"],
                    "spatialMatchConfidence": match.get("spatial_match_confidence"),
                    "candidatePanelIds": match.get("candidate_panel_ids", []),
                    "inspectionPriority": risk["inspection_priority"],
                    "priorityRule": risk["priority_rule"],
                    "priorityExplanation": risk["priority_explanation"],
                    "reviewRequired": risk["review_required"] or match["match_status"] != "MATCHED",
                    "registrationId": f"{rgb['imageId']}:{thermal['imageId']}",
                }
                changed = findings_col.update_one(query, {"$set": update})
                associated += changed.modified_count

    record["associatedFindings"] = associated
    registrations_col.replace_one(
        {"projectId": project_id, "referenceImageId": rgb["imageId"], "movingImageId": thermal["imageId"]},
        record,
        upsert=True,
    )
    record.pop("_id", None)
    return record


def auto_register_project_pairs(
    project_id: str,
    *,
    upload_dir=None,
    minimum_matches: int = 12,
    max_time_diff_seconds: float = 10.0,
    max_gps_meters: float = 15.0,
):
    """Discover RGB/thermal pairs from metadata/filenames and attempt evidence-gated registration."""
    base_dir = upload_dir or get_upload_dir()
    images = list(images_col.find({"projectId": project_id}).sort("createdAt", 1))
    rgb_images = [img for img in images if img.get("imageType") == "rgb"]
    thermal_images = [img for img in images if img.get("imageType") == "thermal"]
    pairs = pair_rgb_thermal_images(
        rgb_images,
        thermal_images,
        upload_dir=base_dir,
        max_time_diff_seconds=max_time_diff_seconds,
        max_gps_meters=max_gps_meters,
    )
    rgb_by_id = {img["imageId"]: img for img in rgb_images}
    thm_by_id = {img["imageId"]: img for img in thermal_images}

    results = []
    for pair in pairs:
        rgb = rgb_by_id.get(pair["rgb_image_id"])
        thm = thm_by_id.get(pair["thermal_image_id"])
        if not rgb or not thm:
            continue
        reg = execute_pair_registration(project_id, rgb, thm, upload_dir=base_dir, minimum_matches=minimum_matches)
        reg["pairingSignals"] = pair["signals"]
        reg["pairingConfidence"] = pair["confidence"]
        results.append(reg)

    return {
        "projectId": project_id,
        "pairedCandidates": pairs,
        "results": results,
        "registeredCount": sum(1 for r in results if r.get("status") == "REGISTERED"),
        "unregisteredCount": sum(1 for r in results if r.get("status") != "REGISTERED"),
    }


@router.post("/api/projects/{project_id}/registration", dependencies=[Depends(require_project_access)])
async def register_images(project_id: str, reference_image_id: str, moving_image_id: str):
    if not projects_col.find_one({"_id": parse_project_oid(project_id)}):
        raise HTTPException(404, "Project not found")
    images = {
        row["imageId"]: row
        for row in images_col.find({"projectId": project_id, "imageId": {"$in": [reference_image_id, moving_image_id]}})
    }
    if len(images) != 2:
        raise HTTPException(404, "Both project images must exist")
    if {row["imageType"] for row in images.values()} != {"rgb", "thermal"}:
        raise HTTPException(422, "Registration requires one RGB image and one thermal image")
    rgb = next(row for row in images.values() if row["imageType"] == "rgb")
    thermal = next(row for row in images.values() if row["imageType"] == "thermal")
    return await run_in_threadpool(execute_pair_registration, project_id, rgb, thermal)


@router.post("/api/projects/{project_id}/registration/auto", dependencies=[Depends(require_project_access)])
async def auto_register_images(project_id: str, payload: AutoRegistrationRequest | None = None):
    if not projects_col.find_one({"_id": parse_project_oid(project_id)}):
        raise HTTPException(404, "Project not found")
    cfg = payload or AutoRegistrationRequest()
    return await run_in_threadpool(
        auto_register_project_pairs,
        project_id,
        minimum_matches=cfg.minimum_matches,
        max_time_diff_seconds=cfg.max_time_diff_seconds,
        max_gps_meters=cfg.max_gps_meters,
    )


@router.get("/api/projects/{project_id}/registrations", dependencies=[Depends(require_project_access)])
def get_registrations(project_id: str):
    if not projects_col.find_one({"_id": parse_project_oid(project_id)}):
        raise HTTPException(404, "Project not found")
    return serialize_docs(list(registrations_col.find({"projectId": project_id}).sort("createdAt", -1)))


@router.get("/api/projects/{project_id}/registration", dependencies=[Depends(require_project_access)])
def get_registration_overview(project_id: str):
    if not projects_col.find_one({"_id": parse_project_oid(project_id)}):
        raise HTTPException(404, "Project not found")
    records = serialize_docs(list(registrations_col.find({"projectId": project_id}).sort("createdAt", -1)))
    images = list(images_col.find({"projectId": project_id}).sort("createdAt", 1))
    rgb_images = [img for img in images if img.get("imageType") == "rgb"]
    thermal_images = [img for img in images if img.get("imageType") == "thermal"]
    suggested = pair_rgb_thermal_images(rgb_images, thermal_images, upload_dir=get_upload_dir())
    return {
        "projectId": project_id,
        "registrations": records,
        "suggestedPairs": suggested,
    }
