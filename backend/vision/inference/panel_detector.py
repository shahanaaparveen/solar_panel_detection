"""Panel localization service. No geometric grid fallback is used."""
from pathlib import Path
from hashlib import sha1
from uuid import uuid4
from ..models.model_registry import registry
from ..mapping.panel_geometry import panel_record
from ..mapping.row_clustering import map_panel_rows
from .base_detector import infer


def detect_panels(image_path, image_id=None, **kwargs):
    detections, elapsed_ms, version = infer("panel_detection", image_path, "rgb", **kwargs)
    model_entry = registry.get("panel_detection")
    target_ids = model_entry["target_class_ids"]
    if not target_ids:
        return {"status": "MODEL_CONFIGURATION_ERROR", "panels": [], "model_id": "panel_detection",
                "model_version": version, "inference_ms": elapsed_ms,
                "message": "Configure target_classes or target_class_ids in the panel model manifest."}
    panels = [panel_record((d["bbox"]["x1"], d["bbox"]["y1"], d["bbox"]["x2"], d["bbox"]["y2"]), d["confidence"], geometry=d.get("mask")) for d in detections if d["class_id"] in target_ids]
    image_scope = str(image_id or sha1(Path(image_path).name.encode("utf-8")).hexdigest()[:10])
    mapped = map_panel_rows(panels)
    model_info = registry.describe("panel_detection")
    model_run_id = uuid4().hex
    for panel in mapped:
        # Namespace the mapper's local row/column label after it assigns that label.
        panel["panel_id"] = f"IMG{image_scope}-{panel['panel_id']}"
        panel["identity_scope"] = "image_local"
        panel["image_id"] = image_id
        panel["model_id"] = model_info.get("model_id", "panel_detection")
        panel["model_version"] = version
        panel["model_sha256"] = model_info.get("sha256")
        panel["model_run_id"] = model_run_id
    return {"status": "COMPLETED", "panels": mapped, "image_id": image_id,
            "model_run_id": model_run_id, "model_id": model_info.get("model_id", "panel_detection"),
            "model_version": version, "model_sha256": model_info.get("sha256"), "inference_ms": elapsed_ms,
            "image_dimensions": detections[0].get("image_size") if detections else None}
