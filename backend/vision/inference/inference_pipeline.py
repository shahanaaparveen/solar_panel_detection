"""Route inference to a model dedicated to its modality."""
from uuid import uuid4
from ..models.model_registry import ModelLoadError, ModelUnavailable, registry
from .thermal_detector import detect_thermal
from .rgb_detector import detect_rgb


def analyze_image(image_path, modality, **kwargs):
    if modality not in {"thermal", "rgb"}:
        return {"status": "UNSUPPORTED_MODALITY", "detections": [], "model_id": None}
    detector = detect_thermal if modality == "thermal" else detect_rgb
    role = f"{modality}_defect_detection"
    try:
        detections, elapsed_ms, version = detector(image_path, **kwargs)
    except ModelLoadError as exc:
        return {"status": "MODEL_ERROR", "message": str(exc), "detections": [], "model_id": f"{modality}_defect_detection"}
    except ModelUnavailable as exc:
        return {"status": "MODEL_UNAVAILABLE", "message": str(exc), "detections": [], "model_id": f"{modality}_defect_detection"}
    model_run_id = uuid4().hex
    model_info = registry.describe(role)
    for detection in detections:
        detection["model_version"] = version
        detection["model_sha256"] = model_info["sha256"]
        detection["model_run_id"] = model_run_id
        detection["inference_ms"] = elapsed_ms
    return {"status": "COMPLETED", "detections": detections, "model_id": model_info["model_id"],
            "model_role": role, "model_run_id": model_run_id, "model_version": version,
            "model_sha256": model_info["sha256"], "model_metadata": model_info, "inference_ms": elapsed_ms}
