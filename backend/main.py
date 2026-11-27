"""FastAPI application for persistent, model-backed inspection workflows."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import logging
import os
from contextlib import asynccontextmanager
import hashlib

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image

from database import (projects_col, detections_col, reports_col, jobs_col,
                      panels_col, findings_col, images_col, registrations_col, model_runs_col,
                      client as mongo_client, index_errors, storage_mode, storage_error)
from vision.models.model_registry import registry
from vision.preprocessing.image_loader import load_image
from vision.inference.panel_detector import detect_panels
from vision.inference.inference_pipeline import analyze_image
from vision.models.model_registry import ModelUnavailable, ModelLoadError
from vision.association.spatial_matching import associate_defect
from vision.risk.severity_engine import assess_finding
from vision.registration.image_alignment import align_images
from vision.inference.job_processor import process_analysis as process_job
from auth import (authorized_project_ids, auth_status, get_current_user, is_admin,
                  project_filter, require_project_access)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("solar_inspect")


@asynccontextmanager
async def lifespan(_app):
    yield
    registry.unload()


app = FastAPI(title="Solar Inspect API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "20"))
ALLOWED_FORMATS = {"JPEG", "PNG", "TIFF", "BMP", "WEBP"}


class ProjectPayload(BaseModel):
    projectName: str | None = None
    companyName: str | None = None
    location: str | None = None
    inspectorName: str | None = None
    date: str | None = None
    notes: str | None = None


class ReportPayload(BaseModel):
    title: str | None = None
    notes: str | None = None
    jobId: str | None = None
    metadata: dict = Field(default_factory=dict)


def now():
    return datetime.now(timezone.utc).isoformat()


def project_oid(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(400, "Invalid project ID")


def serialize(doc):
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return doc


def serialize_many(docs):
    return [serialize(d) for d in docs]


def project_view(doc):
    if doc is None:
        return None
    result = dict(doc)
    result.pop("ownerSubject", None)
    project_id = str(result["_id"])
    stored_images = list(images_col.find({"projectId": project_id}).sort("createdAt", 1))
    for image_type, field in (("thermal", "thermalImages"), ("rgb", "rgbImages")):
        result[field] = [{key: value for key, value in image.items() if key != "_id"}
                         for image in stored_images if image.get("imageType") == image_type]
    return serialize(result)


def _transform_box(box, matrix):
    x1,y1,x2,y2 = (box[k] for k in ("x1", "y1", "x2", "y2"))
    mapped=[]
    for x,y in ((x1,y1),(x2,y1),(x2,y2),(x1,y2)):
        denominator = matrix[2][0]*x + matrix[2][1]*y + matrix[2][2]
        if abs(denominator) < 1e-9:
            return None
        mapped.append(((matrix[0][0]*x + matrix[0][1]*y + matrix[0][2])/denominator,
                       (matrix[1][0]*x + matrix[1][1]*y + matrix[1][2])/denominator))
    return {"x1": min(p[0] for p in mapped), "y1": min(p[1] for p in mapped),
            "x2": max(p[0] for p in mapped), "y2": max(p[1] for p in mapped)}


@app.get("/api/health")
def health():
    database_status = "IN_MEMORY_DEVELOPMENT" if storage_mode != "mongodb" else "CONNECTED"
    if storage_mode == "mongodb":
        try:
            mongo_client.admin.command("ping")
        except Exception:
            database_status = "DISCONNECTED"
            logger.exception("MongoDB health ping failed")
    models = registry.readiness()
    model_ready = all(value["status"] == "READY" for value in models.values())
    authentication = auth_status()
    return {"application": "ALIVE", "database": {"status": database_status,
            "persistent": database_status == "CONNECTED", "index_errors": sorted(index_errors)},
            "models": models,
            "authentication": authentication,
            "analysis_service": "READY" if model_ready and database_status == "CONNECTED" and not index_errors and authentication != "MISCONFIGURED" else "DEGRADED"}


@app.get("/api/models/readiness")
def model_readiness(_claims=Depends(get_current_user)):
    return registry.readiness()


@app.get("/api/projects")
def get_projects(claims=Depends(get_current_user)):
    return [project_view(doc) for doc in projects_col.find(project_filter(claims)).sort("createdAt", -1)]


@app.post("/api/projects")
def create_project(data: ProjectPayload, claims=Depends(get_current_user)):
    doc = data.model_dump(exclude_none=True)
    doc.update(status="In Progress", createdAt=now(), thermalImages=[], rgbImages=[], ownerSubject=claims["sub"])
    result = projects_col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return project_view(doc)


@app.get("/api/projects/{project_id}", dependencies=[Depends(require_project_access)])
def get_project(project_id: str):
    doc = projects_col.find_one({"_id": project_oid(project_id)})
    if not doc:
        raise HTTPException(404, "Project not found")
    return project_view(doc)


@app.put("/api/projects/{project_id}", dependencies=[Depends(require_project_access)])
def update_project(project_id: str, data: ProjectPayload):
    projects_col.update_one({"_id": project_oid(project_id)}, {"$set": data.model_dump(exclude_none=True)})
    return get_project(project_id)


@app.delete("/api/projects/{project_id}", dependencies=[Depends(require_project_access)])
def delete_project(project_id: str):
    oid = project_oid(project_id)
    result = projects_col.update_one({"_id": oid}, {"$set": {"status": "Archived", "deletedAt": now()}})
    if not result.matched_count:
        raise HTTPException(404, "Project not found")
    return {"ok": True, "archived": True}


@app.post("/api/projects/{project_id}/upload", dependencies=[Depends(require_project_access)])
async def upload_images(project_id: str, image_type: str = Form(...), files: list[UploadFile] = File(...)):
    oid = project_oid(project_id)
    project = projects_col.find_one({"_id": oid})
    if not project:
        raise HTTPException(404, "Project not found")
    if image_type not in {"thermal", "rgb"}:
        raise HTTPException(422, "image_type must be 'thermal' or 'rgb'")
    if not files:
        raise HTTPException(422, "At least one image is required")
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(413, f"At most {MAX_UPLOAD_FILES} images may be uploaded per request")
    saved=[]
    new_paths=[]
    reused=0
    for upload in files:
        content = await upload.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"File exceeds the {MAX_UPLOAD_BYTES} byte limit")
        try:
            from io import BytesIO
            with Image.open(BytesIO(content)) as im:
                if im.format not in ALLOWED_FORMATS:
                    raise ValueError("Unsupported image format")
                im.verify()
            # Decode once after verify and apply EXIF orientation for metadata validation.
            from vision.preprocessing.image_loader import load_image
            temp = UPLOAD_DIR / f".validate-{uuid4().hex}"
            temp.write_bytes(content)
            try:
                _, metadata = load_image(temp)
            finally:
                temp.unlink(missing_ok=True)
        except Exception:
            logger.info("Rejected invalid uploaded image")
            raise HTTPException(422, "Invalid image content or unsupported image format") from None
        content_sha256 = hashlib.sha256(content).hexdigest()
        existing = images_col.find_one({"projectId": project_id, "imageType": image_type, "sha256": content_sha256})
        if existing:
            saved.append({k:v for k,v in existing.items() if k != "_id"})
            reused += 1
            await upload.close()
            continue
        filename = f"{uuid4().hex}{Path(upload.filename or 'image').suffix.lower()}"
        relative = Path(image_type) / project_id / filename
        destination = (UPLOAD_DIR / relative).resolve()
        if UPLOAD_DIR not in destination.parents:
            raise HTTPException(400, "Invalid upload path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        image_id = uuid4().hex
        record = {"imageId": image_id, "projectId": project_id, "imageType": image_type,
                  "path": str(relative).replace("\\", "/"), "imageName": Path(upload.filename or filename).name,
                  "sha256": content_sha256, "metadata": metadata, "createdAt": now()}
        try:
            images_col.insert_one(record)
        except DuplicateKeyError:
            destination.unlink(missing_ok=True)
            existing = images_col.find_one({"projectId": project_id, "imageType": image_type, "sha256": content_sha256})
            if not existing:
                raise HTTPException(409, "Duplicate image upload raced with another request")
            saved.append({k:v for k,v in existing.items() if k != "_id"})
            reused += 1
            await upload.close()
            continue
        saved.append({k:v for k,v in record.items() if k != "_id"})
        new_paths.append(record["path"])
        await upload.close()
    if new_paths:
        projects_col.update_one({"_id": oid}, {"$push": {"thermalImages" if image_type == "thermal" else "rgbImages": {"$each": new_paths}}})
    return {"uploaded": len(saved) - reused, "reused": reused, "images": saved, "paths": [x["path"] for x in saved]}


@app.get("/api/projects/{project_id}/images/{image_id}/content", dependencies=[Depends(require_project_access)])
def get_image_content(project_id: str, image_id: str):
    image = images_col.find_one({"projectId": project_id, "imageId": image_id})
    if not image:
        raise HTTPException(404, "Image not found")
    image_path = (UPLOAD_DIR / image["path"]).resolve()
    if UPLOAD_DIR not in image_path.parents or not image_path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(image_path, filename=Path(image["imageName"]).name)


def process_analysis(project_id, job_id, image_ids):
    process_job(job_id, image_ids, jobs=jobs_col, images=images_col,
        detections=detections_col, panels=panels_col, findings=findings_col,
        model_runs=model_runs_col, projects=projects_col, upload_dir=UPLOAD_DIR,
        project_object_id=project_oid)


@app.post("/api/projects/{project_id}/analyze", status_code=202, dependencies=[Depends(require_project_access)])
def analyze_images(project_id: str, background_tasks: BackgroundTasks,
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if not projects_col.find_one({"_id": project_oid(project_id)}):
        raise HTTPException(404, "Project not found")
    image_records = list(images_col.find({"projectId": project_id}).sort("createdAt", 1))
    if not image_records:
        raise HTTPException(422, "Upload images before starting analysis")
    if idempotency_key and len(idempotency_key) > 128:
        raise HTTPException(422, "Idempotency-Key must be at most 128 characters")
    if idempotency_key:
        existing = jobs_col.find_one({"projectId": project_id, "requestId": idempotency_key})
        if existing:
            return serialize(existing)
    job_id = uuid4().hex
    image_ids = [image["imageId"] for image in image_records]
    job = {"jobId": job_id, "projectId": project_id, "status": "PENDING", "stage": "queued",
        "totalImages": len(image_records), "completedImages": 0, "successfulImages": 0,
        "partialImages": 0, "failedImages": 0, "percentage": 0,
        "images": [{"imageId": image["imageId"], "imageType": image["imageType"],
                    "imageName": image["imageName"], "status": "PENDING"} for image in image_records],
        "createdAt": now(), "updatedAt": now()}
    if idempotency_key:
        job["requestId"] = idempotency_key
    try:
        jobs_col.insert_one(job)
    except DuplicateKeyError:
        existing = jobs_col.find_one({"projectId": project_id, "requestId": idempotency_key})
        if existing:
            return serialize(existing)
        raise HTTPException(409, "Analysis request could not be created safely")
    background_tasks.add_task(process_analysis, project_id, job_id, image_ids)
    return serialize(job)


@app.get("/api/projects/{project_id}/analysis/{job_id}", dependencies=[Depends(require_project_access)])
def get_analysis_job(project_id: str, job_id: str):
    doc = jobs_col.find_one({"projectId": project_id, "jobId": job_id})
    if not doc:
        raise HTTPException(404, "Analysis job not found")
    return serialize(doc)


@app.post("/api/projects/{project_id}/analysis/{job_id}/retry", status_code=202, dependencies=[Depends(require_project_access)])
def retry_analysis(project_id: str, job_id: str, background_tasks: BackgroundTasks):
    job = jobs_col.find_one({"projectId": project_id, "jobId": job_id})
    if not job:
        raise HTTPException(404, "Analysis job not found")
    if job["status"] in {"PENDING", "PROCESSING"}:
        return serialize(job)
    if job["status"] not in {"PARTIALLY_COMPLETED", "FAILED"}:
        raise HTTPException(409, "Only incomplete analysis jobs can be retried")
    retry_ids = [image["imageId"] for image in job.get("images", []) if image.get("status") != "COMPLETED"]
    if not retry_ids:
        raise HTTPException(409, "No incomplete images are available to retry")
    claimed = jobs_col.update_one({"jobId": job_id, "status": job["status"]}, {"$set": {
        "status": "PENDING", "stage": "retry_queued", "updatedAt": now(), "failureDetails": None}})
    if not claimed.modified_count:
        return serialize(jobs_col.find_one({"jobId": job_id}))
    background_tasks.add_task(process_analysis, project_id, job_id, retry_ids)
    return serialize(jobs_col.find_one({"jobId": job_id}))


@app.get("/api/projects/{project_id}/detections", dependencies=[Depends(require_project_access)])
def get_detections(project_id: str, image_type: str | None = None, job_id: str | None = None):
    query = {"projectId": project_id}
    if image_type:
        if image_type not in {"thermal", "rgb"}:
            raise HTTPException(422, "Unsupported image_type")
        query["imageType"] = image_type
    if job_id:
        query["jobId"] = job_id
    return serialize_many(list(detections_col.find(query).sort("analyzedAt", 1)))


@app.post("/api/projects/{project_id}/images/{image_id}/panels", dependencies=[Depends(require_project_access)])
def map_panels(project_id: str, image_id: str):
    image = images_col.find_one({"projectId": project_id, "imageId": image_id, "imageType": "rgb"})
    if not image:
        raise HTTPException(404, "RGB image not found")
    path = UPLOAD_DIR / image["path"]
    try:
        result = detect_panels(path, image_id=image_id)
    except ModelLoadError as exc:
        return {"status": "MODEL_ERROR", "panels": [], "message": str(exc)}
    except ModelUnavailable as exc:
        return {"status": "MODEL_UNAVAILABLE", "panels": [], "message": str(exc)}
    result.update(projectId=project_id, imageId=image_id, imageSize=image.get("metadata", {}), analyzedAt=now())
    panels_col.replace_one({"projectId": project_id, "imageId": image_id}, result.copy(), upsert=True)
    return result


@app.get("/api/projects/{project_id}/panels", dependencies=[Depends(require_project_access)])
def get_panels(project_id: str, image_id: str | None = None):
    query = {"projectId": project_id}
    if image_id:
        query["imageId"] = image_id
    return serialize_many(list(panels_col.find(query).sort("analyzedAt", -1)))


@app.get("/api/projects/{project_id}/findings", dependencies=[Depends(require_project_access)])
def get_findings(project_id: str, job_id: str | None = None):
    query = {"projectId": project_id}
    if job_id:
        query["jobId"] = job_id
    return serialize_many(list(findings_col.find(query).sort("createdAt", -1)))


@app.post("/api/projects/{project_id}/registration", dependencies=[Depends(require_project_access)])
def register_images(project_id: str, reference_image_id: str, moving_image_id: str):
    images = {row["imageId"]: row for row in images_col.find({"projectId": project_id, "imageId": {"$in": [reference_image_id, moving_image_id]}})}
    if len(images) != 2:
        raise HTTPException(404, "Both project images must exist")
    if {row["imageType"] for row in images.values()} != {"rgb", "thermal"}:
        raise HTTPException(422, "Registration requires one RGB image and one thermal image")
    rgb = next(row for row in images.values() if row["imageType"] == "rgb")
    thermal = next(row for row in images.values() if row["imageType"] == "thermal")
    try:
        result = align_images(UPLOAD_DIR / rgb["path"], UPLOAD_DIR / thermal["path"])
    except Exception:
        logger.exception("Image registration failed for project %s", project_id)
        result = {"status": "UNREGISTERED", "reason": "Registration processing failed"}
    record = {"projectId": project_id, "referenceImageId": rgb["imageId"], "movingImageId": thermal["imageId"],
              "referenceModality": "rgb", "movingModality": "thermal", **result, "createdAt": now()}
    associated = 0
    if result.get("status") == "REGISTERED":
        panels = panels_col.find_one({"projectId": project_id, "imageId": rgb["imageId"], "status": "COMPLETED"})
        thermal_run = detections_col.find_one({"projectId": project_id, "imageId": thermal["imageId"], "imageType": "thermal", "status": "COMPLETED"}, sort=[("analyzedAt", -1)])
        if panels and thermal_run:
            for detection in thermal_run.get("detections", []):
                transformed = _transform_box(detection["bbox"], result["transform"])
                if transformed is None:
                    continue
                match = associate_defect({"bbox": transformed}, panels.get("panels", []))
                risk = assess_finding(detection["label"], detection["confidence"], match.get("spatial_match_confidence"))
                query = {"projectId": project_id, "jobId": thermal_run["jobId"], "modality": "thermal",
                         "evidence.imageId": thermal["imageId"], "evidence.bbox": detection["bbox"]}
                update = {"panelId": match.get("panel_id"), "matchStatus": match["match_status"],
                          "spatialMatchConfidence": match.get("spatial_match_confidence"),
                          "candidatePanelIds": match.get("candidate_panel_ids", []),
                          "inspectionPriority": risk["inspection_priority"],
                          "priorityRule": risk["priority_rule"],
                          "priorityExplanation": risk["priority_explanation"],
                          "reviewRequired": risk["review_required"] or match["match_status"] != "MATCHED",
                          "registrationId": f"{rgb['imageId']}:{thermal['imageId']}"}
                changed = findings_col.update_one(query, {"$set": update})
                associated += changed.modified_count
    record["associatedFindings"] = associated
    registrations_col.replace_one({"projectId": project_id, "referenceImageId": rgb["imageId"], "movingImageId": thermal["imageId"]}, record, upsert=True)
    record.pop("_id", None)
    return record


@app.get("/api/projects/{project_id}/registrations", dependencies=[Depends(require_project_access)])
def get_registrations(project_id: str):
    return serialize_many(list(registrations_col.find({"projectId": project_id}).sort("createdAt", -1)))


@app.post("/api/projects/{project_id}/report", dependencies=[Depends(require_project_access)])
def save_report(project_id: str, data: ReportPayload):
    if not projects_col.find_one({"_id": project_oid(project_id)}):
        raise HTTPException(404, "Project not found")
    if not data.jobId:
        raise HTTPException(422, "jobId is required to create a traceable report")
    job = jobs_col.find_one({"projectId": project_id, "jobId": data.jobId})
    if not job:
        raise HTTPException(404, "Analysis job not found")
    findings = [{**row, "_id": str(row["_id"])} for row in findings_col.find({"projectId": project_id, "jobId": data.jobId})]
    model_runs = [{**row, "_id": str(row["_id"])} for row in model_runs_col.find({"projectId": project_id, "jobId": data.jobId})]
    image_results = [{**row, "_id": str(row["_id"])} for row in detections_col.find({"projectId": project_id, "jobId": data.jobId})]
    image_refs = [{key: value for key, value in row.items() if key != "_id"}
                  for row in images_col.find({"projectId": project_id, "imageId": {"$in": [x["imageId"] for x in job.get("images", [])]}})]
    expected_image_ids = {row.get("imageId") for row in job.get("images", [])}
    completed_image_ids = {row.get("imageId") for row in job.get("images", [])
                           if row.get("status") == "COMPLETED"}
    complete_job = (job.get("status") == "COMPLETED" and bool(expected_image_ids)
                    and completed_image_ids == expected_image_ids
                    and job.get("completedImages", len(completed_image_ids)) == len(expected_image_ids))
    report_status = "COMPLETED" if complete_job else "DRAFT_INCOMPLETE"
    doc = {"projectId": project_id, "jobId": data.jobId, "jobStatus": job.get("status"),
           "status": report_status, "title": data.title, "notes": data.notes,
           "metadata": data.metadata, "findingIds": [x.get("findingId") for x in findings],
           "findingCount": len(findings), "findings": findings, "modelRuns": model_runs,
           "imageResults": image_results, "images": image_refs, "createdAt": now()}
    result = reports_col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    if report_status == "COMPLETED":
        projects_col.update_one({"_id": project_oid(project_id)}, {"$set": {"status": "Completed"}})
    return doc


@app.get("/api/projects/{project_id}/report", dependencies=[Depends(require_project_access)])
def get_report(project_id: str):
    doc = reports_col.find_one({"projectId": project_id}, sort=[("createdAt", -1)])
    if not doc:
        raise HTTPException(404, "No report found")
    return serialize(doc)


@app.get("/api/reports")
def get_all_reports(claims=Depends(get_current_user)):
    if is_admin(claims):
        query = {}
    else:
        permitted = authorized_project_ids(claims)
        owned = [str(row["_id"]) for row in projects_col.find({"ownerSubject": claims["sub"]}, {"_id": 1})]
        query = {"projectId": {"$in": sorted(permitted | set(owned))}}
    return serialize_many(list(reports_col.find(query).sort("createdAt", -1)))
