"""Run the configured inference role against a labeled dataset."""
from time import perf_counter

from ..vision.inference.base_detector import infer
from ..vision.models.model_registry import registry


def run_predictions(model_role, samples, *, confidence=None):
    entry = registry.get(model_role)
    if model_role == "panel_detection" and not entry["target_class_ids"]:
        raise ValueError("Panel manifest must configure target_classes or target_class_ids")
    modality = "thermal" if model_role == "thermal_defect_detection" else "rgb"
    predictions = {}
    latencies = []
    for sample in samples:
        started = perf_counter()
        detections, model_ms, version = infer(model_role, sample["image_path"], modality, confidence=confidence)
        if model_role == "panel_detection":
            detections = [d for d in detections if d["class_id"] in entry["target_class_ids"]]
        predictions[sample["image_id"]] = detections
        latencies.append(model_ms if model_ms is not None else (perf_counter()-started)*1000)
    return predictions, latencies, registry.describe(model_role)
