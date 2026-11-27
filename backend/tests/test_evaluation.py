"""Metrics and dataset split checks for the held-out evaluation tools."""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from backend.evaluation.dataset_loader import load_yolo_dataset
from backend.evaluation.detection_metrics import compute_detection_metrics
from backend.evaluation.error_visualization import write_error_visualizations
from backend.evaluation.ground_truth import parse_yolo_label_line
from backend.evaluation.latency import summarize_latency
from backend.evaluation.segmentation_metrics import mask_iou_dice


def test_detection_metrics_capture_perfect_prediction_and_false_negative():
    samples = [{"image_id": "one.png", "ground_truth": [
        {"class_id": 0, "bbox": {"x1": 0, "y1": 0, "x2": 10, "y2": 10}},
        {"class_id": 1, "bbox": {"x1": 20, "y1": 20, "x2": 30, "y2": 30}},
    ]}]
    predictions = {"one.png": [{"class_id": 0, "confidence": 0.9,
                                 "bbox": {"x1": 0, "y1": 0, "x2": 10, "y2": 10}},
                                {"class_id": 1, "confidence": 0.1,
                                 "bbox": {"x1": 20, "y1": 20, "x2": 30, "y2": 30}}]}
    result = compute_detection_metrics(samples, predictions, {0: "panel", 1: "hotspot"})
    assert result["metrics"]["precision"] == 1
    assert result["metrics"]["recall"] == 0.5
    assert result["metrics"]["false_negative_count"] == 1
    assert len(result["errors"]["low_confidence_predictions"]) == 1
    assert result["per_class"][0]["ap50"] == 1
    assert result["per_class"][1]["ap50"] == 1


def test_dataset_loader_requires_held_out_split_and_rejects_site_leakage(tmp_path):
    images, labels = tmp_path / "images", tmp_path / "labels"
    images.mkdir()
    labels.mkdir()
    Image.new("RGB", (20, 10)).save(images / "capture.png")
    with pytest.raises(ValueError, match="split='validation' or split='test'"):
        load_yolo_dataset(images, labels)
    with pytest.raises(ValueError, match="split='validation' or split='test'"):
        load_yolo_dataset(images, labels, split="test")
    manifest = tmp_path / "dataset.json"
    manifest.write_text(json.dumps({"split": "test", "training_site_ids": ["site-a"],
                                    "evaluation_site_ids": ["site-a"]}), encoding="utf-8")
    with pytest.raises(ValueError, match="Dataset leakage"):
        load_yolo_dataset(images, labels, manifest_path=manifest)
    manifest.write_text(json.dumps({"split": "test", "training_site_ids": ["site-a"],
        "evaluation_site_ids": ["site-b"], "training_flight_ids": ["flight-a"],
        "evaluation_flight_ids": ["flight-b"], "image_to_site": {"capture.png": "site-b"},
        "image_to_flight": {"capture.png": "flight-b"}}), encoding="utf-8")
    samples, info = load_yolo_dataset(images, labels, manifest_path=manifest, require_site_holdout=True)
    assert len(samples) == 1
    assert info["site_split_verified"] is True
    assert info["flight_split_verified"] is True
    manifest.write_text(json.dumps({"split": "test", "training_site_ids": ["site-a"],
        "evaluation_site_ids": ["site-b"], "training_flight_ids": ["flight-b"],
        "evaluation_flight_ids": ["flight-b"], "image_to_site": {"capture.png": "site-b"},
        "image_to_flight": {"capture.png": "flight-b"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Dataset leakage: flight IDs"):
        load_yolo_dataset(images, labels, manifest_path=manifest)


def test_yolo_segmentation_polygon_and_latency_summary():
    annotation = parse_yolo_label_line("2 0.1 0.2 0.5 0.2 0.5 0.6 0.1 0.6", 100, 50)
    assert annotation["class_id"] == 2
    assert annotation["bbox"] == {"x1": 10, "y1": 10, "x2": 50, "y2": 30}
    assert summarize_latency([10, 20, 30])["median_ms"] == 20
    assert summarize_latency([10, 20, 30])["p95_ms"] == 30
    mask = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    assert mask_iou_dice(mask, mask) == {"iou": 1.0, "dice": 1.0}


def test_error_visualization_uses_real_image_and_reported_boxes(tmp_path):
    image_path = tmp_path / "evidence.png"
    Image.new("RGB", (40, 30), "white").save(image_path)
    samples = [{"image_id": "evidence.png", "image_path": image_path,
                "ground_truth": [{"class_id": 0, "bbox": {"x1": 2, "y1": 2, "x2": 12, "y2": 12}}]}]
    predictions = {"evidence.png": [{"class_id": 0, "confidence": 0.1,
                                     "bbox": {"x1": 3, "y1": 3, "x2": 13, "y2": 13}}]}
    paths = write_error_visualizations(samples, predictions,
        {"low_confidence_predictions": [{"image_id": "evidence.png"}]}, tmp_path / "errors",
        {0: "hotspot"}, confidence_threshold=0.25)
    assert len(paths) == 1
    assert Path(paths[0]).is_file()
