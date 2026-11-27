"""API behavior tests using the configured development MongoDB fallback."""
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["AUTH_ENABLED"] = "false"

from fastapi.testclient import TestClient
from PIL import Image
import numpy as np
import cv2
from bson import ObjectId
from main import app
from main import _transform_box
from database import (storage_mode, images_col, detections_col, findings_col, jobs_col,
                      panels_col, registrations_col, projects_col)
import main
from vision.mapping.panel_geometry import panel_record
from vision.inference import job_processor


def _png(color=(120, 140, 160)):
    image = Image.new("RGB", (64, 48), color)
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output


def test_health_reports_actual_storage_mode_and_model_readiness():
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["database"]["status"] in {"CONNECTED", "DISCONNECTED", "IN_MEMORY_DEVELOPMENT"}
        assert response.json()["database"]["persistent"] is (storage_mode == "mongodb")
        assert set(response.json()["models"]) == {"panel_detection", "thermal_defect_detection", "rgb_defect_detection"}
        assert response.json()["authentication"] == "DISABLED_DEVELOPMENT"


def test_health_reports_database_failure(monkeypatch):
    class BrokenAdmin:
        @staticmethod
        def command(_name):
            raise OSError("test database outage")
    class BrokenMongo:
        admin = BrokenAdmin()
    monkeypatch.setattr(main, "storage_mode", "mongodb")
    monkeypatch.setattr(main, "mongo_client", BrokenMongo())
    assert client_health_status() == "DISCONNECTED"


def client_health_status():
    with TestClient(app) as client:
        return client.get("/api/health").json()["database"]["status"]


def test_invalid_object_id_is_rejected_as_client_error():
    with TestClient(app) as client:
        assert client.get("/api/projects/not-an-object-id").status_code == 400


def test_homography_restores_transformed_bounding_box():
    transformed = _transform_box({"x1": 10, "y1": 20, "x2": 30, "y2": 40}, [[1, 0, 5], [0, 1, -3], [0, 0, 1]])
    assert transformed == {"x1": 15.0, "y1": 17.0, "x2": 35.0, "y2": 37.0}


def test_upload_and_analysis_job_never_fabricate_missing_model_predictions():
    with TestClient(app) as client:
        created = client.post("/api/projects", json={"projectName": "Test inspection"})
        assert created.status_code == 200
        project_id = created.json()["_id"]
        uploaded = client.post(f"/api/projects/{project_id}/upload", data={"image_type": "thermal"}, files={"files": ("thermal.png", _png(), "image/png")})
        assert uploaded.status_code == 200
        assert uploaded.json()["uploaded"] == 1
        rgb_uploaded = client.post(f"/api/projects/{project_id}/upload", data={"image_type": "rgb"}, files={"files": ("visible.png", _png(), "image/png")})
        assert rgb_uploaded.status_code == 200
        duplicate = client.post(f"/api/projects/{project_id}/upload", data={"image_type": "thermal"}, files={"files": ("same-image.png", _png(), "image/png")})
        assert duplicate.json()["uploaded"] == 0
        assert duplicate.json()["reused"] == 1
        assert duplicate.json()["images"][0]["imageId"] == uploaded.json()["images"][0]["imageId"]
        accepted = client.post(f"/api/projects/{project_id}/analyze", headers={"Idempotency-Key": "integration-run-1"})
        assert accepted.status_code == 202
        job_id = accepted.json()["jobId"]
        job = client.get(f"/api/projects/{project_id}/analysis/{job_id}").json()
        assert job["status"] == "PARTIALLY_COMPLETED"
        assert job["partialImages"] == 2
        repeated = client.post(f"/api/projects/{project_id}/analyze", headers={"Idempotency-Key": "integration-run-1"})
        assert repeated.json()["jobId"] == job_id
        detections = client.get(f"/api/projects/{project_id}/detections", params={"job_id": job_id}).json()
        assert len(detections) == 2
        assert all(d["status"] == "MODEL_UNAVAILABLE" and d["detections"] == [] for d in detections)
        panel_results = client.get(f"/api/projects/{project_id}/panels").json()
        assert len(panel_results) == 1
        assert panel_results[0]["status"] == "MODEL_UNAVAILABLE"
        assert panel_results[0]["panels"] == []
        before_retry = findings_col.count_documents({"jobId": job_id})
        retried = client.post(f"/api/projects/{project_id}/analysis/{job_id}/retry")
        assert retried.status_code == 202
        after_retry = client.get(f"/api/projects/{project_id}/detections", params={"job_id": job_id}).json()
        assert len(after_retry) == 2
        assert findings_col.count_documents({"jobId": job_id}) == before_retry


def test_one_image_error_does_not_stop_other_images():
    with TestClient(app) as client:
        project_id = client.post("/api/projects", json={"projectName": "Partial job"}).json()["_id"]
        uploaded = client.post(f"/api/projects/{project_id}/upload", data={"image_type": "thermal"}, files={"files": ("ok.png", _png(), "image/png")})
        valid_id = uploaded.json()["images"][0]["imageId"]
        images_col.insert_one({"imageId": "missing-image", "projectId": project_id, "imageType": "thermal",
            "path": "thermal/missing/missing.png", "imageName": "missing.png", "createdAt": "9999"})
        job_id = client.post(f"/api/projects/{project_id}/analyze").json()["jobId"]
        job = client.get(f"/api/projects/{project_id}/analysis/{job_id}").json()
        assert job["status"] == "PARTIALLY_COMPLETED"
        assert job["failedImages"] == 1
        assert job["partialImages"] == 1
        assert {image["imageId"] for image in job["images"]} == {valid_id, "missing-image"}
        assert detections_col.count_documents({"jobId": job_id}) == 2


def test_incomplete_job_saves_an_explicit_draft_report_snapshot():
    with TestClient(app) as client:
        project_id = client.post("/api/projects", json={"projectName": "Draft report"}).json()["_id"]
        client.post(f"/api/projects/{project_id}/upload", data={"image_type": "thermal"}, files={"files": ("thermal.png", _png(), "image/png")})
        job_id = client.post(f"/api/projects/{project_id}/analyze").json()["jobId"]
        report = client.post(f"/api/projects/{project_id}/report", json={"title": "Draft", "jobId": job_id})
        assert report.status_code == 200
        data = report.json()
        assert data["status"] == "DRAFT_INCOMPLETE"
        assert data["jobStatus"] == "PARTIALLY_COMPLETED"
        assert data["images"]
        assert data["imageResults"]
        assert data["modelRuns"]
        assert client.get(f"/api/projects/{project_id}").json()["status"] == "Analysis Incomplete"
        jobs_col.update_one({"jobId": job_id}, {"$set": {"status": "COMPLETED"}})
        complete_report = client.post(f"/api/projects/{project_id}/report", json={"title": "Complete", "jobId": job_id})
        assert complete_report.json()["status"] == "DRAFT_INCOMPLETE"
        jobs_col.update_one({"jobId": job_id}, {"$set": {
            "images.0.status": "COMPLETED", "completedImages": 1,
        }})
        complete_report = client.post(f"/api/projects/{project_id}/report", json={"title": "Complete", "jobId": job_id})
        assert complete_report.json()["status"] == "COMPLETED"


def test_synthetic_registered_pair_updates_persisted_thermal_finding(monkeypatch, tmp_path):
    image = np.zeros((480, 640), dtype=np.uint8)
    rng = np.random.default_rng(73)
    for _ in range(180):
        center = tuple(map(int, rng.integers(10, 620, size=2)))
        cv2.circle(image, center, int(rng.integers(2, 10)), int(rng.integers(80, 255)), -1)
    moving = cv2.warpAffine(image, np.float32([[1, 0, 12], [0, 1, -8]]), (640, 480))
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    project_id = str(projects_col.insert_one({"projectName": "Synthetic registration", "status": "In Progress"}).inserted_id)
    rgb_id, thermal_id = "synthetic-rgb-" + project_id, "synthetic-thermal-" + project_id
    for image_id, modality, array in ((rgb_id, "rgb", image), (thermal_id, "thermal", moving)):
        relative = f"{modality}/{image_id}.png"
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(array).save(path)
        images_col.insert_one({"imageId": image_id, "projectId": project_id, "imageType": modality,
            "path": relative, "imageName": path.name, "metadata": {"width": 640, "height": 480}})
    panel = panel_record((100, 100, 420, 380), 0.95, "IMGsynthetic-R01C01")
    panels_col.insert_one({"projectId": project_id, "imageId": rgb_id, "status": "COMPLETED",
                           "panels": [panel], "analyzedAt": "now"})
    bbox = {"x1": 240, "y1": 180, "x2": 280, "y2": 220}
    detections_col.insert_one({"projectId": project_id, "jobId": "synthetic-job", "imageId": thermal_id,
        "imageType": "thermal", "status": "COMPLETED", "detections": [{"bbox": bbox,
        "label": "Hotspot", "confidence": 0.94}], "analyzedAt": "now"})
    findings_col.insert_one({"findingId": "synthetic-finding-" + project_id, "projectId": project_id,
        "jobId": "synthetic-job", "imageId": thermal_id, "modality": "thermal", "panelId": None,
        "matchStatus": "UNREGISTERED", "evidence": [{"imageId": thermal_id, "bbox": bbox}]})
    try:
        with TestClient(app) as client:
            response = client.post(f"/api/projects/{project_id}/registration",
                params={"reference_image_id": rgb_id, "moving_image_id": thermal_id})
            assert response.status_code == 200
            registration = response.json()
            assert registration["status"] == "REGISTERED"
            assert registration["mean_reprojection_error_px"] < 2
            finding = findings_col.find_one({"findingId": "synthetic-finding-" + project_id})
            assert finding["panelId"] == panel["panel_id"]
            assert finding["matchStatus"] == "MATCHED"
            assert finding["registrationId"] == f"{rgb_id}:{thermal_id}"
            assert registrations_col.find_one({"projectId": project_id})["associatedFindings"] == 1
    finally:
        projects_col.delete_one({"_id": ObjectId(project_id)})
        images_col.delete_many({"projectId": project_id})
        panels_col.delete_many({"projectId": project_id})
        detections_col.delete_many({"projectId": project_id})
        findings_col.delete_many({"projectId": project_id})
        registrations_col.delete_many({"projectId": project_id})


def test_multiple_rgb_and_thermal_images_keep_independent_model_states():
    with TestClient(app) as client:
        project_id = client.post("/api/projects", json={"projectName": "Four image inspection"}).json()["_id"]
        for image_type, color, name in (
            ("rgb", (20, 120, 180), "rgb-a.png"), ("rgb", (80, 140, 200), "rgb-b.png"),
            ("thermal", (200, 40, 20), "thermal-a.png"), ("thermal", (220, 80, 10), "thermal-b.png"),
        ):
            assert client.post(f"/api/projects/{project_id}/upload", data={"image_type": image_type},
                files={"files": (name, _png(color), "image/png")}).status_code == 200
        job = client.post(f"/api/projects/{project_id}/analyze").json()
        job = client.get(f"/api/projects/{project_id}/analysis/{job['jobId']}").json()
        assert job["status"] == "PARTIALLY_COMPLETED"
        assert job["totalImages"] == 4
        assert {row["imageType"] for row in job["images"]} == {"rgb", "thermal"}
        assert len(client.get(f"/api/projects/{project_id}/detections", params={"job_id": job["jobId"]}).json()) == 4


def test_synthetic_upload_to_inference_mapping_findings_and_report(monkeypatch, tmp_path):
    """Synthetic model outputs exercise the real queue and persistence path; they are not model results."""
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)

    def synthetic_defect_inference(_path, modality):
        model_id = f"synthetic-{modality}-model"
        run_id = f"synthetic-{modality}-run"
        return {"status": "COMPLETED", "model_id": model_id, "model_version": "fixture-v1",
            "model_sha256": "d" * 64, "model_run_id": run_id,
            "model_metadata": {"model_id": model_id, "version": "fixture-v1", "sha256": "d" * 64},
            "inference_ms": 1.25, "detections": [{"class_id": 0, "class_name": "Hotspot",
            "confidence": 0.93, "modality": modality, "model_id": model_id, "model_version": "fixture-v1",
            "model_sha256": "d" * 64, "model_run_id": run_id, "inference_ms": 1.25,
            "image_size": {"width": 64, "height": 48},
            "bbox": {"x1": 20, "y1": 12, "x2": 30, "y2": 24},
            "normalized_bbox": {"x1": 20/64, "y1": 12/48, "x2": 30/64, "y2": 24/48},
            "coordinate_convention": "xyxy_pixels_exif_oriented"}]}

    def synthetic_panel_inference(_path, image_id=None):
        panel_run = f"synthetic-panel-run-{image_id}"
        return {"status": "COMPLETED", "image_id": image_id, "image_dimensions": {"width": 64, "height": 48},
            "model_id": "synthetic-panel-model", "model_version": "fixture-v1",
            "model_sha256": "e" * 64, "model_run_id": panel_run,
            "model_metadata": {"model_id": "synthetic-panel-model", "version": "fixture-v1", "sha256": "e" * 64},
            "inference_ms": 1.5, "panels": [panel_record((5, 5, 55, 43), 0.97, "IMGfixture-R01C01")]}

    monkeypatch.setattr(job_processor, "analyze_image", synthetic_defect_inference)
    monkeypatch.setattr(job_processor, "detect_panels", synthetic_panel_inference)
    with TestClient(app) as client:
        project_id = client.post("/api/projects", json={"projectName": "Synthetic pipeline"}).json()["_id"]
        for modality, color in (("rgb", (50, 120, 180)), ("thermal", (180, 40, 20))):
            uploaded = client.post(f"/api/projects/{project_id}/upload", data={"image_type": modality},
                files={"files": (f"{modality}.png", _png(color), "image/png")})
            assert uploaded.status_code == 200
        accepted = client.post(f"/api/projects/{project_id}/analyze")
        job_id = accepted.json()["jobId"]
        job = client.get(f"/api/projects/{project_id}/analysis/{job_id}").json()
        assert job["status"] == "COMPLETED"
        detections = client.get(f"/api/projects/{project_id}/detections", params={"job_id": job_id}).json()
        assert len(detections) == 2
        assert all(row["detections"][0]["model_sha256"] == "d" * 64 for row in detections)
        panel_rows = client.get(f"/api/projects/{project_id}/panels").json()
        assert len(panel_rows) == 1
        assert panel_rows[0]["panels"][0]["panel_id"].startswith("IMG")
        findings = client.get(f"/api/projects/{project_id}/findings", params={"job_id": job_id}).json()
        rgb_finding = next(row for row in findings if row["modality"] == "rgb")
        thermal_finding = next(row for row in findings if row["modality"] == "thermal")
        assert rgb_finding["matchStatus"] == "MATCHED"
        assert thermal_finding["matchStatus"] == "UNREGISTERED"
        report = client.post(f"/api/projects/{project_id}/report", json={"jobId": job_id, "title": "Synthetic"}).json()
        assert report["status"] == "COMPLETED"
        assert report["findingCount"] == 2
        assert len(report["modelRuns"]) == 3
