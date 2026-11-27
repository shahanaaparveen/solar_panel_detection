"""Synthetic integration checks between inference records and mapping adapters."""
from threading import RLock
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vision.config import ModelConfig
from vision.inference import base_detector, panel_detector
from vision.association.spatial_matching import associate_defect


class _Scalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class _Array:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def tolist(self):
        return self.value


class _Box:
    def __init__(self, bbox):
        self.xyxy = [_Array(bbox)]
        self.cls = [_Scalar(0)]
        self.conf = [_Scalar(0.93)]


class _Result:
    def __init__(self, image, boxes):
        self.orig_shape = image.shape[:2]
        self.boxes = boxes
        self.masks = None


def test_synthetic_tiled_inference_restores_original_coordinates(tmp_path, monkeypatch):
    image = np.zeros((1024, 2048, 3), dtype=np.uint8)
    image[100:140, 900:940] = (255, 20, 10)
    path = tmp_path / "tile-contract.png"
    Image.fromarray(image).save(path)

    class SyntheticDetector:
        def predict(self, *, source, **_kwargs):
            rgb = np.asarray(source)
            ys, xs = np.where((rgb[:, :, 0] > 200) & (rgb[:, :, 1] < 80))
            boxes = [_Box([int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)])] if len(xs) else []
            return [_Result(rgb, boxes)]

    config = ModelConfig("thermal_defect_detection", path, "detect", "thermal",
                         image_size=1024, confidence=0.2, iou=0.5, device="auto")
    entry = {"config": config, "model": SyntheticDetector(), "names": {0: "hotspot"},
             "manifest": {"model_id": "synthetic-thermal", "version": "test-v1"}, "sha256": "c" * 64,
             "inference_lock": RLock()}
    monkeypatch.setattr(base_detector.registry, "get", lambda _role: entry)
    detections, _duration, version = base_detector.infer("thermal_defect_detection", path, "thermal")

    assert version == "test-v1"
    assert len(detections) == 1  # overlapping tile hits were deduplicated
    detection = detections[0]
    assert detection["bbox"] == {"x1": 900.0, "y1": 100.0, "x2": 940.0, "y2": 140.0}
    assert detection["normalized_bbox"]["x1"] == 900 / 2048
    assert detection["coordinate_convention"] == "xyxy_pixels_exif_oriented"
    assert detection["image_size"] == {"width": 2048, "height": 1024}


def test_synthetic_panel_adapter_namespaces_local_rows_and_exports_run_metadata(monkeypatch, tmp_path):
    config = ModelConfig("panel_detection", tmp_path / "panels.pt", "detect", "rgb")
    entry = {"target_class_ids": {0}}
    model_info = {"model_id": "synthetic-panel", "sha256": "a" * 64}
    monkeypatch.setattr(panel_detector, "infer", lambda *_args, **_kwargs: ([
        {"class_id": 0, "confidence": 0.9, "bbox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
         "image_size": {"width": 100, "height": 80}},
    ], 3.2, "panel-v1"))
    monkeypatch.setattr(panel_detector.registry, "get", lambda _role: entry)
    monkeypatch.setattr(panel_detector.registry, "describe", lambda _role: model_info)
    first = panel_detector.detect_panels("synthetic.png", image_id="image-a")
    second = panel_detector.detect_panels("synthetic.png", image_id="image-b")
    assert first["panels"][0]["panel_id"].endswith("R01C01")
    assert first["panels"][0]["panel_id"] != second["panels"][0]["panel_id"]
    assert first["panels"][0]["image_id"] == "image-a"
    assert first["panels"][0]["model_sha256"] == "a" * 64
    assert first["panels"][0]["model_run_id"] == first["model_run_id"]


def test_synthetic_contract_detection_is_consumed_by_spatial_association():
    detection = {"image_id": "img-1", "model_run_id": "run-1", "model_id": "thermal-model",
        "model_version": "v1", "model_sha256": "b" * 64, "modality": "thermal",
        "class_id": 2, "class_name": "hotspot", "confidence": 0.92,
        "image_size": {"width": 100, "height": 100},
        "bbox": {"x1": 25, "y1": 25, "x2": 45, "y2": 45},
        "normalized_bbox": {"x1": 0.25, "y1": 0.25, "x2": 0.45, "y2": 0.45},
        "inference_ms": 5.1, "mask": None}
    panel = {"panel_id": "IMGimg-1-R01C01", "bbox": {"x1": 0, "y1": 0, "x2": 60, "y2": 60}}
    matched = associate_defect(detection, [panel])
    assert matched["panel_id"] == panel["panel_id"]
    assert matched["match_status"] == "MATCHED"
