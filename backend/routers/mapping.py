"""FastAPI router for panel mapping, clustering, re-identification, and mapping quality."""
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from auth import require_project_access
from database import (
    detections_col,
    findings_col,
    images_col,
    mappings_col,
    panels_col,
    projects_col,
    registrations_col,
)
from vision.association.cross_image_dedup import deduplicate_findings_across_images
from vision.association.panel_aggregation import aggregate_panel_findings
from vision.mapping.mapping_service import map_image_panels, map_project_panels
from vision.registration.image_alignment import align_images
from vision.risk.mapping_quality import compute_mapping_quality
from .registration import auto_register_project_pairs
from .schemas import MappingAnalyzeRequest, get_upload_dir, parse_project_oid, serialize_doc, utc_now

router = APIRouter(tags=["mapping"])


def _run_rgb_overlap_registrations(project_id: str, rgb_images: list[dict], upload_dir):
    """Attempt pairwise same-modal registration between consecutive RGB frames."""
    same_modal = []
    for i in range(len(rgb_images) - 1):
        ref = rgb_images[i]
        mov = rgb_images[i + 1]
        res = align_images(
            upload_dir / ref["path"],
            upload_dir / mov["path"],
            reference_image_id=ref["imageId"],
            moving_image_id=mov["imageId"],
            modality_hint="same_modal",
        )
        same_modal.append({
            "projectId": project_id,
            "referenceImageId": ref["imageId"],
            "movingImageId": mov["imageId"],
            "referenceModality": "rgb",
            "movingModality": "rgb",
            **res,
        })
    return same_modal


def compute_project_mapping_snapshot(
    project_id: str,
    *,
    job_id: str | None = None,
    min_confidence: float = 0.25,
    iou_threshold: float = 0.55,
    min_overlap: float = 0.2,
    enable_cross_image_registration: bool = False,
    auto_pair_registration: bool = False,
    max_time_window_hours: float = 24.0,
    persist: bool = True,
):
    """Compute postprocessed panel mappings, cross-image re-ID, dedup, aggregation, and quality."""
    if not projects_col.find_one({"_id": parse_project_oid(project_id)}):
        raise HTTPException(404, "Project not found")

    upload_dir = get_upload_dir()
    if auto_pair_registration:
        auto_register_project_pairs(project_id, upload_dir=upload_dir)

    images = list(images_col.find({"projectId": project_id}).sort("createdAt", 1))
    images_by_id = {img["imageId"]: img for img in images}
    rgb_images = [img for img in images if img.get("imageType") == "rgb"]

    panel_docs = list(panels_col.find({"projectId": project_id}).sort("analyzedAt", -1))
    rgb_registrations = (
        _run_rgb_overlap_registrations(project_id, rgb_images, upload_dir)
        if enable_cross_image_registration and len(rgb_images) >= 2
        else []
    )

    mapped_by_image = {}
    mapping_diagnostics = []
    enriched_panel_docs = []

    for doc in panel_docs:
        img_id = doc.get("imageId")
        if doc.get("status") != "COMPLETED":
            enriched_panel_docs.append(serialize_doc(doc))
            continue
        img_meta = (images_by_id.get(img_id, {}) or {}).get("metadata") or doc.get("imageSize") or {}
        width = img_meta.get("width")
        height = img_meta.get("height")
        raw_panels = doc.get("panels", [])
        mapped = map_image_panels(
            raw_panels,
            image_width=width,
            image_height=height,
            image_id=img_id,
            image_scope=img_id,
            min_confidence=min_confidence,
            iou_threshold=iou_threshold,
        )
        # Preserve model provenance fields onto remapped panels.
        for p in mapped["panels"]:
            p["model_id"] = doc.get("model_id")
            p["model_version"] = doc.get("model_version")
            p["model_sha256"] = doc.get("model_sha256")
            p["model_run_id"] = doc.get("model_run_id")

        mapped_by_image[img_id] = mapped
        mapping_diagnostics.append(mapped["quality"])

        updated_doc = dict(doc)
        updated_doc["panels"] = mapped["panels"]
        updated_doc["regions"] = mapped["regions"]
        updated_doc["mappingQuality"] = mapped["quality"]
        enriched_panel_docs.append(serialize_doc(updated_doc))

    reid_report = map_project_panels(mapped_by_image, registrations=rgb_registrations)["reidentification"]
    panels_by_image = {img_id: res["panels"] for img_id, res in mapped_by_image.items()}

    if persist:
        for updated_doc in enriched_panel_docs:
            if updated_doc.get("status") == "COMPLETED":
                to_save = {k: v for k, v in updated_doc.items() if k != "_id"}
                panels_col.replace_one({"projectId": project_id, "imageId": to_save["imageId"]}, to_save, upsert=True)

    finding_query = {"projectId": project_id}
    det_query = {"projectId": project_id}
    if job_id:
        finding_query["jobId"] = job_id
        det_query["jobId"] = job_id

    raw_findings = [serialize_doc(f) for f in findings_col.find(finding_query).sort("createdAt", -1)]
    det_docs = list(detections_col.find(det_query).sort("analyzedAt", -1))
    image_analysis_statuses = {}
    for det in det_docs:
        img_id = det.get("imageId")
        if img_id and img_id not in image_analysis_statuses:
            image_analysis_statuses[img_id] = det.get("status")

    # Propagate any verified site_panel_id onto matched findings.
    site_id_by_local = {
        (img_id, p.get("panel_id")): p.get("site_panel_id")
        for img_id, plist in panels_by_image.items()
        for p in plist
        if p.get("site_panel_id")
    }
    for finding in raw_findings:
        key = (finding.get("imageId"), finding.get("panelId"))
        if key in site_id_by_local:
            finding["sitePanelId"] = site_id_by_local[key]

    registrations = [serialize_doc(r) for r in registrations_col.find({"projectId": project_id}).sort("createdAt", -1)]
    all_registrations = registrations + rgb_registrations

    dedup = deduplicate_findings_across_images(
        raw_findings,
        images_by_id=images_by_id,
        panels_by_image=panels_by_image,
        pairwise_registrations=all_registrations,
        max_time_window_hours=max_time_window_hours,
    )

    aggregation = aggregate_panel_findings(
        panels_by_image,
        raw_findings,
        consolidated_findings=dedup["consolidated_findings"],
        image_analysis_statuses=image_analysis_statuses,
    )

    quality = compute_mapping_quality(
        panel_results=enriched_panel_docs,
        mapping_diagnostics=mapping_diagnostics,
        registrations=all_registrations,
        findings=raw_findings,
        deduplication_report=dedup,
    )

    snapshot = {
        "projectId": project_id,
        "jobId": job_id,
        "status": "COMPLETED" if mapped_by_image else "NO_PANEL_DETECTIONS",
        "reidentification": reid_report,
        "regionsByImage": {img_id: res["regions"] for img_id, res in mapped_by_image.items()},
        "panelResults": enriched_panel_docs,
        "panelAggregation": aggregation,
        "deduplication": dedup,
        "registrations": all_registrations,
        "quality": quality,
        "updatedAt": utc_now(),
    }

    if persist:
        mappings_col.replace_one({"projectId": project_id}, dict(snapshot), upsert=True)

    return snapshot


@router.post("/api/projects/{project_id}/mapping/analyze", dependencies=[Depends(require_project_access)])
async def analyze_project_mapping(project_id: str, payload: MappingAnalyzeRequest | None = None):
    cfg = payload or MappingAnalyzeRequest()
    return await run_in_threadpool(
        compute_project_mapping_snapshot,
        project_id,
        job_id=cfg.job_id,
        min_confidence=cfg.min_confidence,
        iou_threshold=cfg.iou_threshold,
        min_overlap=cfg.min_overlap,
        enable_cross_image_registration=cfg.enable_cross_image_registration,
        auto_pair_registration=cfg.auto_pair_registration,
        max_time_window_hours=cfg.max_time_window_hours,
        persist=True,
    )


@router.get("/api/projects/{project_id}/mapping", dependencies=[Depends(require_project_access)])
def get_project_mapping(project_id: str, job_id: str | None = None):
    if not projects_col.find_one({"_id": parse_project_oid(project_id)}):
        raise HTTPException(404, "Project not found")
    saved = mappings_col.find_one({"projectId": project_id})
    if saved and (job_id is None or saved.get("jobId") == job_id):
        return serialize_doc(saved)
    return compute_project_mapping_snapshot(project_id, job_id=job_id, persist=False)


@router.get("/api/projects/{project_id}/mapping/quality", dependencies=[Depends(require_project_access)])
def get_mapping_quality(project_id: str, job_id: str | None = None):
    snapshot = get_project_mapping(project_id, job_id=job_id)
    return snapshot["quality"]
