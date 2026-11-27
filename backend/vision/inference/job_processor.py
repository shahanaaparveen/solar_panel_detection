"""Image-isolated, idempotent processing for the API's simple background queue."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import logging

from ..association.spatial_matching import associate_defect
from ..models.model_registry import registry, ModelUnavailable, ModelLoadError
from ..preprocessing.image_loader import load_image
from ..preprocessing.thermal_metrics import thermal_pixel_metrics
from ..risk.severity_engine import assess_finding
from .inference_pipeline import analyze_image
from .panel_detector import detect_panels

logger = logging.getLogger("solar_inspect.jobs")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _legacy_detection(detection, image_id, image_type, model_run_id, inference_ms):
    box = detection["bbox"]
    x1, y1, x2, y2 = (box[k] for k in ("x1", "y1", "x2", "y2"))
    decision = assess_finding(detection["class_name"], detection["confidence"])
    return {**detection, "image_id": image_id, "modality": image_type,
            "model_run_id": model_run_id, "inference_ms": inference_ms,
            "label": detection["class_name"], "x": x1, "y": y1,
            "w": x2-x1, "h": y2-y1, "cx": (x1+x2)/2, "cy": (y1+y2)/2,
            "severity": None, "inspection_priority": decision["inspection_priority"],
            "review_required": decision["review_required"]}


def _record_model_run(collection, job_id, image, role, result, fallback_status=None):
    model_info = result.get("model_metadata") or registry.describe(role)
    run_id = result.get("model_run_id") or uuid4().hex
    record = {"modelRunId": run_id, "jobId": job_id, "projectId": image["projectId"],
              "imageId": image["imageId"], "modality": image["imageType"],
              "modelRole": role, "modelId": result.get("model_id") or model_info.get("model_id"),
              "modelVersion": result.get("model_version") or model_info.get("version"),
              "checkpointSha256": result.get("model_sha256") or model_info.get("sha256"),
              "status": result.get("status", fallback_status or "UNKNOWN"),
              "inferenceMs": result.get("inference_ms"),
              "modelMetadata": model_info, "createdAt": _now()}
    collection.replace_one({"modelRunId": run_id}, record, upsert=True)
    return run_id


def _set_image_state(jobs, job_id, image_id, values):
    updates = {f"images.$.{key}": value for key, value in values.items()}
    updates["updatedAt"] = _now()
    jobs.update_one({"jobId": job_id, "images.imageId": image_id}, {"$set": updates})


def process_analysis(job_id, image_ids, *, jobs, images, detections, panels, findings, model_runs,
                     projects, upload_dir, project_object_id):
    """Process selected images independently; each image result is replaced idempotently."""
    claim = jobs.update_one({"jobId": job_id, "status": "PENDING"},
                            {"$set": {"status": "PROCESSING", "stage": "starting", "startedAt": _now(), "updatedAt": _now()}})
    if not claim.matched_count:
        return
    job = jobs.find_one({"jobId": job_id})
    project_id = job["projectId"]
    selected = set(image_ids)
    image_records = [row for row in images.find({"projectId": project_id, "imageId": {"$in": list(selected)}})
                     if row["imageId"] in selected]
    completed = sum(1 for image in job.get("images", [])
                    if image.get("status") == "COMPLETED" and image.get("imageId") not in selected)
    partial = 0
    failed = 0
    total = len(job.get("images", []))
    try:
        for image in image_records:
            image_id = image["imageId"]
            _set_image_state(jobs, job_id, image_id, {"status": "PROCESSING", "stage": "validating", "error": None})
            try:
                full_path = Path(upload_dir) / image["path"]
                _, metadata = load_image(full_path)
                modality = image["imageType"]
                inference = analyze_image(full_path, modality)
                defect_role = f"{modality}_defect_detection"
                defect_run_id = _record_model_run(model_runs, job_id, image, defect_role, inference)
                raw_detections = inference.get("detections", [])
                image_detections = [_legacy_detection(d, image_id, modality, defect_run_id, inference.get("inference_ms"))
                                    for d in raw_detections]
                thermal_metrics = thermal_pixel_metrics(full_path) if modality == "thermal" else None

                panel_result = None
                panel_run_id = None
                if modality == "rgb":
                    try:
                        panel_result = detect_panels(full_path, image_id=image_id)
                    except ModelLoadError as exc:
                        panel_result = {"status": "MODEL_ERROR", "panels": [], "message": str(exc)}
                    except ModelUnavailable as exc:
                        panel_result = {"status": "MODEL_UNAVAILABLE", "panels": [], "message": str(exc)}
                    panel_role = "panel_detection"
                    panel_info = registry.describe(panel_role)
                    panel_run_id = uuid4().hex
                    panel_result.setdefault("model_id", panel_info.get("model_id"))
                    panel_result.setdefault("model_version", panel_info.get("version"))
                    panel_result.setdefault("model_sha256", panel_info.get("sha256"))
                    panel_result.setdefault("model_metadata", panel_info)
                    panel_result.setdefault("model_run_id", panel_run_id)
                    panel_result.update(projectId=project_id, imageId=image_id,
                                        imageSize={"width": metadata["width"], "height": metadata["height"]},
                                        analyzedAt=_now())
                    panel_run_id = _record_model_run(model_runs, job_id, image, panel_role, panel_result)
                    for panel in panel_result.get("panels", []):
                        panel["model_id"] = panel_result.get("model_id")
                        panel["model_version"] = panel_result.get("model_version")
                        panel["model_sha256"] = panel_result.get("model_sha256")
                        panel["model_run_id"] = panel_run_id
                        panel["image_id"] = image_id
                    panels.replace_one({"projectId": project_id, "imageId": image_id}, panel_result, upsert=True)

                new_findings = []
                for detection in image_detections:
                    if modality == "rgb" and panel_result and panel_result.get("status") == "COMPLETED":
                        match = associate_defect(detection, panel_result.get("panels", []))
                    else:
                        match = {"panel_id": None, "match_status": "UNREGISTERED",
                                 "spatial_match_confidence": 0.0, "candidate_panel_ids": []}
                    risk = assess_finding(detection["label"], detection["confidence"],
                                          match.get("spatial_match_confidence"))
                    new_findings.append({"findingId": uuid4().hex, "projectId": project_id,
                        "jobId": job_id, "imageId": image_id, "modelRunId": defect_run_id,
                        "panelId": match.get("panel_id"), "defectType": detection["label"],
                        "modality": modality, "modelConfidence": detection["confidence"],
                        "spatialMatchConfidence": match.get("spatial_match_confidence"),
                        "matchStatus": match["match_status"], "candidatePanelIds": match.get("candidate_panel_ids", []),
                        "findingStatus": "SUSPECTED", "severity": None,
                        "severityStatus": risk["severity_status"],
                        "inspectionPriority": risk["inspection_priority"],
                        "priorityRule": risk["priority_rule"],
                        "priorityExplanation": risk["priority_explanation"],
                        "reviewRequired": risk["review_required"] or match["match_status"] != "MATCHED",
                        "recommendation": risk["recommendation"],
                        "evidence": [{"imageId": image_id, "imagePath": image["path"],
                                      "modelRunId": defect_run_id, "bbox": detection["bbox"]}], "createdAt": _now()})

                image_complete = inference.get("status") == "COMPLETED" and (
                    modality != "rgb" or panel_result.get("status") == "COMPLETED")
                image_status = "COMPLETED" if image_complete else "PARTIALLY_COMPLETED"
                # Replace only this image's prior findings after this attempt has a terminal result.
                findings.delete_many({"projectId": project_id, "jobId": job_id, "imageId": image_id})
                for finding in new_findings:
                    findings.replace_one({"projectId": project_id, "findingId": finding["findingId"]}, finding, upsert=True)
                result_doc = {"projectId": project_id, "jobId": job_id, "imageId": image_id,
                    "imageType": modality, "imagePath": image["path"], "imageName": image["imageName"],
                    "imageWidth": metadata["width"], "imageHeight": metadata["height"],
                    "detections": image_detections, "defectCount": len(image_detections),
                    "status": inference.get("status"), "imageStatus": image_status,
                    "message": inference.get("message"), "modelId": inference.get("model_id"),
                    "modelVersion": inference.get("model_version"), "modelRunId": defect_run_id,
                    "modelSha256": inference.get("model_sha256"), "inferenceMs": inference.get("inference_ms"),
                    "panelStatus": panel_result.get("status") if panel_result else "NOT_APPLICABLE",
                    "panelRunId": panel_run_id,
                    "panelCount": len(panel_result.get("panels", [])) if panel_result else 0,
                    "thermalMetrics": thermal_metrics, "preprocessingMetadata": metadata,
                    "analyzedAt": _now()}
                detections.replace_one({"jobId": job_id, "imageId": image_id}, result_doc, upsert=True)
                _set_image_state(jobs, job_id, image_id, {"status": image_status, "stage": "complete",
                    "defectModelStatus": inference.get("status"),
                    "panelModelStatus": result_doc["panelStatus"], "error": None})
                if image_complete:
                    completed += 1
                else:
                    partial += 1
            except Exception as exc:
                logger.exception("Image %s failed in analysis job %s", image_id, job_id)
                findings.delete_many({"projectId": project_id, "jobId": job_id, "imageId": image_id})
                detections.replace_one({"jobId": job_id, "imageId": image_id}, {
                    "projectId": project_id, "jobId": job_id, "imageId": image_id,
                    "imageType": image.get("imageType"), "imagePath": image.get("path"),
                    "imageName": image.get("imageName"), "detections": [], "defectCount": 0,
                    "status": "IMAGE_ERROR", "imageStatus": "FAILED",
                    "message": "Image processing failed; see backend logs.",
                    "failureCode": type(exc).__name__, "analyzedAt": _now()}, upsert=True)
                _set_image_state(jobs, job_id, image_id, {"status": "FAILED", "stage": "failed",
                    "error": {"code": type(exc).__name__, "message": "Image processing failed; see backend logs."}})
                failed += 1
            terminal = completed + partial + failed
            jobs.update_one({"jobId": job_id}, {"$set": {
                "completedImages": terminal, "successfulImages": completed,
                "partialImages": partial, "failedImages": failed,
                "percentage": int(terminal * 100 / max(total, 1)), "stage": "processing_images",
                "updatedAt": _now()}})

        if completed == total:
            status, stage = "COMPLETED", "completed"
        elif completed + partial > 0:
            status, stage = "PARTIALLY_COMPLETED", "partially_completed"
        else:
            status, stage = "FAILED", "failed"
        jobs.update_one({"jobId": job_id}, {"$set": {"status": status, "stage": stage,
            "completedAt": _now(), "updatedAt": _now(), "percentage": 100,
            "failureDetails": None if status != "FAILED" else "No images could be processed."}})
        projects.update_one({"_id": project_object_id(project_id)}, {"$set": {
            "status": "Analyzed" if status == "COMPLETED" else "Analysis Incomplete",
            "totalDefects": sum(row.get("defectCount", 0) for row in detections.find({"jobId": job_id}))}})
    except Exception:
        logger.exception("Analysis job finalization failed: %s", job_id)
        jobs.update_one({"jobId": job_id}, {"$set": {"status": "FAILED", "stage": "failed",
            "failureDetails": "Job finalization failed; see backend logs.", "completedAt": _now()}})
