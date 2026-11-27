"""Registry checks without loading heavyweight inference dependencies."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from vision.config import ModelConfig
from vision.models.model_registry import ModelRegistry, ModelUnavailable
from vision.models.model_manifest import REQUIRED_MANIFEST_FIELDS, sha256_file, validate_manifest


def test_missing_weights_are_reported_without_loading_ultralytics(tmp_path):
    config = ModelConfig("panel_detection", tmp_path / "missing.pt", "detect", "rgb")
    registry = ModelRegistry({"panel_detection": config})
    assert registry.readiness()["panel_detection"]["status"] == "MODEL_UNAVAILABLE"
    with pytest.raises(ModelUnavailable, match="weights unavailable"):
        registry.get("panel_detection")


def test_class_names_accept_lists_and_dictionaries():
    assert ModelRegistry._names(["module", "roof"]) == {0: "module", 1: "roof"}
    assert ModelRegistry._names({"0": "module", 1: "roof"}) == {0: "module", 1: "roof"}


def test_panel_target_classes_are_checked_against_model_names(tmp_path, monkeypatch):
    weights = tmp_path / "panels.pt"
    weights.write_bytes(b"test-placeholder")
    weights.with_suffix(".json").write_text('{"target_classes":["module"],"version":"test-v1"}', encoding="utf-8")

    class FakeYOLO:
        names = ["roof", "module"]

        def __init__(self, *_args, **_kwargs):
            pass

    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=FakeYOLO))
    config = ModelConfig("panel_detection", weights, "detect", "rgb")
    registry = ModelRegistry({"panel_detection": config})
    entry = registry.get("panel_detection")
    assert entry["target_class_ids"] == {1}
    assert registry.readiness()["panel_detection"]["version"] == "test-v1"


def test_manifest_validation_checks_required_metadata_thresholds_and_checksum(tmp_path):
    weights = tmp_path / "detector.pt"
    weights.write_bytes(b"checkpoint")
    manifest = {field: "metadata" for field in REQUIRED_MANIFEST_FIELDS}
    manifest.update({"role": "thermal_defect_detection", "checkpoint_path": "detector.pt",
        "sha256": sha256_file(weights), "class_ids": [0], "class_names": ["hotspot"],
        "training_image_dimensions": [4000, 3000], "confidence_threshold": 0.4,
        "nms_threshold": 0.5})
    assert validate_manifest(manifest, weights, "thermal_defect_detection", {0: "hotspot"}) == []
    manifest["sha256"] = "wrong"
    manifest["confidence_threshold"] = 1.5
    errors = validate_manifest(manifest, weights, "thermal_defect_detection", {0: "hotspot"})
    assert any("64 hexadecimal" in error for error in errors)
    assert any("confidence_threshold" in error for error in errors)
