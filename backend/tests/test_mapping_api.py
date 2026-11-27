"""Integration tests for Track B mapping, auto-registration, and association FastAPI routers."""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from bson import ObjectId
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["AUTH_ENABLED"] = "false"

import main
from main import app
from database import (
    detections_col,
    findings_col,
    images_col,
    mappings_col,
    panels_col,
    projects_col,
    registrations_col,
)
from vision.mapping.panel_geometry import panel_record


def test_mapping_analyze_auto_registration_and_association_endpoints(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)

    base = np.zeros((320, 480), dtype=np.uint8)
    rng = np.random.default_rng(101)
    for _ in range(160):
        center = tuple(map(int, rng.integers(10, 300, size=2)))
        cv2.circle(base, center, int(rng.integers(2, 9)), int(rng.integers(90, 255)), -1)
    shifted = cv2.warpAffine(base, np.float32([[1, 0, 10], [0, 1, -6]]), (480, 320))

    project_id = str(projects_col.insert_one({"projectName": "Track B API test", "status": "In Progress"}).inserted_id)
    rgb_id, thm_id = f"rgb-{project_id}", f"thm-{project_id}"
    for img_id, modality, name, arr in (
        (rgb_id, "rgb", "DJI_0001_W.png", base),
        (thm_id, "thermal", "DJI_0001_T.png", shifted),
    ):
        rel = f"{modality}/{img_id}_{name}"
        full = tmp_path / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr).save(full)
        images_col.insert_one({
            "imageId": img_id,
            "projectId": project_id,
            "imageType": modality,
            "path": rel,
            "imageName": name,
            "metadata": {"width": 480, "height": 320},
        })

    panels = [
        panel_record((50, 40, 180, 140), 0.94, f"IMG{rgb_id}-R01C01"),
        panel_record((200, 40, 330, 140), 0.91, f"IMG{rgb_id}-R01C02"),
    ]
    panels_col.insert_one({
        "projectId": project_id,
        "imageId": rgb_id,
        "status": "COMPLETED",
        "imageSize": {"width": 480, "height": 320},
        "panels": panels,
        "analyzedAt": "now",
    })

    thm_bbox = {"x1": 90, "y1": 70, "x2": 120, "y2": 100}
    detections_col.insert_one({
        "projectId": project_id,
        "jobId": "job-trackb",
        "imageId": thm_id,
        "imageType": "thermal",
        "status": "COMPLETED",
        "detections": [{"bbox": thm_bbox, "label": "Hotspot", "confidence": 0.93}],
        "analyzedAt": "now",
    })
    detections_col.insert_one({
        "projectId": project_id,
        "jobId": "job-trackb",
        "imageId": rgb_id,
        "imageType": "rgb",
        "status": "COMPLETED",
        "detections": [],
        "analyzedAt": "now",
    })
    findings_col.insert_one({
        "findingId": f"finding-{project_id}",
        "projectId": project_id,
        "jobId": "job-trackb",
        "imageId": thm_id,
        "modality": "thermal",
        "defectType": "Hotspot",
        "modelConfidence": 0.93,
        "panelId": None,
        "matchStatus": "UNREGISTERED",
        "evidence": [{"imageId": thm_id, "bbox": thm_bbox}],
    })

    try:
        with TestClient(app) as client:
            overview = client.get(f"/api/projects/{project_id}/registration")
            assert overview.status_code == 200
            assert len(overview.json()["suggestedPairs"]) == 1

            auto_reg = client.post(f"/api/projects/{project_id}/registration/auto")
            assert auto_reg.status_code == 200
            assert auto_reg.json()["registeredCount"] == 1

            mapped = client.post(f"/api/projects/{project_id}/mapping/analyze", json={"job_id": "job-trackb"})
            assert mapped.status_code == 200
            mdata = mapped.json()
            assert mdata["status"] == "COMPLETED"
            assert mdata["panelAggregation"]["summary"]["total_panels"] == 2
            assert mdata["panelAggregation"]["summary"]["affected_panels"] == 1
            assert mdata["panelAggregation"]["summary"]["healthy_panels"] == 1
            assert mdata["quality"]["measured_accuracy_status"] == "UNMEASURED_NO_GROUND_TRUTH"

            quality_res = client.get(f"/api/projects/{project_id}/mapping/quality", params={"job_id": "job-trackb"})
            assert quality_res.status_code == 200
            assert quality_res.json()["stages"]["registration"]["registered_count"] == 1

            assoc_res = client.post(f"/api/projects/{project_id}/association/analyze", json={"job_id": "job-trackb"})
            assert assoc_res.status_code == 200
            summary_res = client.get(f"/api/projects/{project_id}/association/summary", params={"job_id": "job-trackb"})
            assert summary_res.status_code == 200
            assert summary_res.json()["panelAggregation"]["summary"]["health_rate"] == 50.0
    finally:
        projects_col.delete_one({"_id": ObjectId(project_id)})
        images_col.delete_many({"projectId": project_id})
        panels_col.delete_many({"projectId": project_id})
        detections_col.delete_many({"projectId": project_id})
        findings_col.delete_many({"projectId": project_id})
        registrations_col.delete_many({"projectId": project_id})
        mappings_col.delete_many({"projectId": project_id})
