"""Thread-safe, role-specific lazy model cache."""
from threading import RLock
from time import perf_counter
from .model_manifest import load_manifest, sha256_file
from ..config import MODEL_CONFIGS


class ModelUnavailable(RuntimeError):
    pass


class ModelLoadError(ModelUnavailable):
    pass


class ModelRegistry:
    def __init__(self, configs=None):
        self.configs = configs or MODEL_CONFIGS
        self._models = {}
        self._errors = {}
        self._lock = RLock()

    @staticmethod
    def _names(raw):
        if isinstance(raw, dict):
            return {int(k): str(v) for k, v in raw.items()}
        if isinstance(raw, (list, tuple)):
            return {i: str(v) for i, v in enumerate(raw)}
        return {}

    def get(self, role):
        if role not in self.configs:
            raise ModelUnavailable(f"Unknown model role: {role}")
        with self._lock:
            config = self.configs[role]
            if role in self._models:
                return self._models[role]
            if role in self._errors:
                raise ModelLoadError(f"Unable to load model role '{role}': {self._errors[role]}")
            if not config.path.is_file():
                raise ModelUnavailable(f"Model weights unavailable for role '{role}'")
            try:
                manifest = load_manifest(config.path)
                if manifest.get("modality") and manifest["modality"] != config.modality:
                    raise ValueError(f"Manifest modality {manifest['modality']!r} does not match role modality {config.modality!r}")
                from ultralytics import YOLO
                model = YOLO(str(config.path), task=manifest.get("task", config.task))
                names = self._names(getattr(model, "names", None))
                if not names:
                    raise ValueError("Model metadata does not provide class names")
                declared = manifest.get("class_names")
                if declared and names and set(map(str, declared)) != set(names.values()):
                    raise ValueError("Manifest class_names do not match model.names")
                declared_ids = manifest.get("class_ids")
                if declared_ids is not None and set(map(int, declared_ids)) != set(names):
                    raise ValueError("Manifest class_ids do not match model.names")
                target_ids = set(map(int, manifest.get("target_class_ids", [])))
                target_names = set(map(str, manifest.get("target_classes", [])))
                if target_names:
                    target_ids.update(class_id for class_id, name in names.items() if name in target_names)
                    if target_names - set(names.values()):
                        raise ValueError("Manifest target_classes do not match model.names")
                if role == "panel_detection" and not target_ids and len(names) == 1:
                    target_ids = set(names)
                if any(class_id not in names for class_id in target_ids):
                    raise ValueError("Manifest target_class_ids do not match model.names")
                checkpoint_sha256 = sha256_file(config.path)
                expected_sha256 = manifest.get("sha256")
                if expected_sha256 and expected_sha256.lower() != checkpoint_sha256:
                    raise ValueError(f"Checkpoint SHA-256 mismatch: expected {expected_sha256}, got {checkpoint_sha256}")
                entry = {"model": model, "names": names, "manifest": manifest, "config": config,
                         "target_class_ids": target_ids, "sha256": checkpoint_sha256,
                         "inference_lock": RLock()}
                self._models[role] = entry
                return entry
            except Exception as exc:
                detail = str(exc).replace(str(config.path), "<configured checkpoint>")
                self._errors[role] = detail
                raise ModelLoadError(f"Unable to load model role '{role}': {detail}") from exc

    def readiness(self):
        result = {}
        for role, config in self.configs.items():
            state = "READY" if role in self._models else ("AVAILABLE" if config.path.is_file() else "MODEL_UNAVAILABLE")
            if role in self._errors:
                state = "MODEL_ERROR"
            loaded_manifest = self._models.get(role, {}).get("manifest", {})
            result[role] = {"status": state, "configured": config.path.is_file(), "version": loaded_manifest.get("version", config.version),
                            "sha256": self._models.get(role, {}).get("sha256"),
                            "classes": {str(k): v for k, v in self._models.get(role, {}).get("names", {}).items()},
                            "error": self._errors.get(role)}
        return result

    def describe(self, role):
        """Return traceable deployment metadata when a model is loaded."""
        entry = self._models.get(role)
        config = self.configs[role]
        if not entry:
            return {"model_id": role, "role": role, "status": self.readiness()[role]["status"]}
        manifest = entry["manifest"]
        return {"model_id": manifest.get("model_id", role), "role": role,
                "architecture": manifest.get("architecture"), "version": manifest.get("version", config.version),
                "sha256": entry["sha256"],
                "class_names": {str(k): v for k, v in entry["names"].items()}, "image_size": config.image_size,
                "confidence_threshold": config.confidence, "nms_threshold": config.iou,
                "device": config.device, "preprocessing": manifest.get("preprocessing", {}),
                "training_dataset_version": manifest.get("training_dataset_version"),
                "evaluation_metrics": manifest.get("evaluation_metrics")}

    def unload(self):
        with self._lock:
            self._models.clear()


registry = ModelRegistry()
