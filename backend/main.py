from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from PIL import Image as PILImage
from dotenv import load_dotenv
import os, shutil, json

from database import projects_col, detections_col, reports_col
from detector import detect_defects

load_dotenv()

app = FastAPI(title="Solar Inspect API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def oid(doc):
    """Convert ObjectId to string for JSON serialization."""
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


def oids(docs):
    return [oid(d) for d in docs]


# ── PROJECTS ──────────────────────────────────────────────────────────────

@app.get("/api/projects")
def get_projects():
    return oids(list(projects_col.find().sort("createdAt", -1)))


@app.post("/api/projects")
def create_project(data: dict):
    data["status"]    = "In Progress"
    data["createdAt"] = datetime.utcnow().isoformat()
    data["thermalImages"] = []
    data["rgbImages"]     = []
    result = projects_col.insert_one(data)
    data["_id"] = str(result.inserted_id)
    return data


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    try:
        doc = projects_col.find_one({"_id": ObjectId(project_id)})
    except InvalidId:
        raise HTTPException(404, "Invalid project ID")
    if not doc:
        raise HTTPException(404, "Project not found")
    return oid(doc)


@app.put("/api/projects/{project_id}")
def update_project(project_id: str, data: dict):
    data.pop("_id", None)
    projects_col.update_one({"_id": ObjectId(project_id)}, {"$set": data})
    return get_project(project_id)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    projects_col.delete_one({"_id": ObjectId(project_id)})
    detections_col.delete_many({"projectId": project_id})
    reports_col.delete_many({"projectId": project_id})
    return {"ok": True}


# ── IMAGE UPLOAD + ANALYSIS ───────────────────────────────────────────────

@app.post("/api/projects/{project_id}/upload")
async def upload_images(
    project_id: str,
    image_type: str = Form(...),          # "thermal" or "rgb"
    files: list[UploadFile] = File(...),
):
    proj_dir = os.path.join(UPLOAD_DIR, image_type, project_id)
    os.makedirs(proj_dir, exist_ok=True)

    saved = []
    for f in files:
        dest = os.path.join(proj_dir, f.filename.replace("/", "_").replace("\\", "_"))
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(dest.replace("\\", "/"))

    # Store paths in project document
    field = "thermalImages" if image_type == "thermal" else "rgbImages"
    projects_col.update_one(
        {"_id": ObjectId(project_id)},
        {"$push": {field: {"$each": saved}}}
    )
    return {"uploaded": len(saved), "paths": saved}


@app.post("/api/projects/{project_id}/analyze")
def analyze_images(project_id: str):
    """
    Run defect detection on all uploaded images for this project.
    Stores results in detections collection.
    Replace detect_defects() with real YOLO model when ready.
    """
    proj = projects_col.find_one({"_id": ObjectId(project_id)})
    if not proj:
        raise HTTPException(404, "Project not found")

    # Clear old detections
    detections_col.delete_many({"projectId": project_id})

    all_detections = []

    for img_type in ["thermal", "rgb"]:
        field = "thermalImages" if img_type == "thermal" else "rgbImages"
        paths = proj.get(field, [])

        for path in paths:
            full_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
            if not os.path.exists(full_path):
                continue

            # Get image dimensions
            try:
                with PILImage.open(full_path) as img:
                    w, h = img.size
            except Exception:
                w, h = 640, 480

            boxes = detect_defects(full_path, img_type, w, h)

            doc = {
                "projectId":  project_id,
                "imageType":  img_type,
                "imagePath":  path,
                "imageName":  os.path.basename(path),
                "imageWidth": w,
                "imageHeight": h,
                "detections": boxes,
                "defectCount": len(boxes),
                "analyzedAt": datetime.utcnow().isoformat(),
            }
            detections_col.insert_one(doc)
            doc["_id"] = str(doc["_id"])
            all_detections.append(doc)

    # Update project status
    total_defects = sum(d["defectCount"] for d in all_detections)
    projects_col.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"status": "Analyzed", "totalDefects": total_defects}}
    )

    return {"analyzed": len(all_detections), "totalDefects": total_defects}


@app.get("/api/projects/{project_id}/detections")
def get_detections(project_id: str, image_type: str = None):
    query = {"projectId": project_id}
    if image_type:
        query["imageType"] = image_type
    docs = list(detections_col.find(query))
    return oids(docs)


# ── REPORTS ───────────────────────────────────────────────────────────────

@app.post("/api/projects/{project_id}/report")
def save_report(project_id: str, data: dict):
    data.pop("_id", None)
    data["projectId"]  = project_id
    data["createdAt"]  = datetime.utcnow().isoformat()
    reports_col.delete_many({"projectId": project_id})
    result = reports_col.insert_one(data)
    data["_id"] = str(result.inserted_id)
    projects_col.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"status": "Completed"}}
    )
    return data


@app.get("/api/projects/{project_id}/report")
def get_report(project_id: str):
    doc = reports_col.find_one({"projectId": project_id})
    if not doc:
        raise HTTPException(404, "No report found")
    return oid(doc)


@app.get("/api/reports")
def get_all_reports():
    docs = list(reports_col.find().sort("createdAt", -1))
    return oids(docs)


# ── HEALTH CHECK ──────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "db": "connected"}
