"""Optional JSON model manifests; no class indices are assumed."""
import json
import hashlib
import re
from pathlib import Path


def load_manifest(model_path: Path):
    path = model_path.with_suffix(".json")
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid model manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Model manifest {path} must contain a JSON object")
    return data


def sha256_file(path: Path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


REQUIRED_MANIFEST_FIELDS = {
    "model_id", "role", "model_type", "architecture", "version", "checkpoint_path", "sha256", "class_ids", "class_names",
    "training_dataset_version", "training_image_dimensions", "preprocessing",
    "confidence_threshold", "nms_threshold", "evaluation_metrics",
    "training_timestamp", "deployment_timestamp",
}


def validate_manifest(manifest, model_path: Path, role: str, class_names=None):
    """Validate deployment metadata and checkpoint integrity without loading a model."""
    errors = []
    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    if missing:
        errors.append(f"Missing manifest fields: {', '.join(missing)}")
    if manifest.get("role") and manifest["role"] != role:
        errors.append(f"Manifest role {manifest['role']!r} does not match configured role {role!r}")
    if manifest.get("checkpoint_path") and Path(manifest["checkpoint_path"]).name != Path(model_path).name:
        errors.append("Manifest checkpoint_path does not match the configured weights filename")
    if manifest.get("sha256") and not re.fullmatch(r"[a-fA-F0-9]{64}", str(manifest["sha256"])):
        errors.append("Manifest sha256 must contain exactly 64 hexadecimal characters")
    for field in ("confidence_threshold", "nms_threshold"):
        value = manifest.get(field)
        if value is not None and (not isinstance(value, (int, float)) or not 0 <= value <= 1):
            errors.append(f"Manifest {field} must be a number in [0, 1]")
    dimensions = manifest.get("training_image_dimensions")
    if dimensions is not None and (not isinstance(dimensions, (list, tuple)) or len(dimensions) != 2
                                   or any(not isinstance(value, int) or value <= 0 for value in dimensions)):
        errors.append("Manifest training_image_dimensions must contain two positive integers")
    if "class_ids" in manifest and (not isinstance(manifest["class_ids"], list)
                                    or any(not isinstance(value, int) or value < 0 for value in manifest["class_ids"])
                                    or len(set(manifest["class_ids"])) != len(manifest["class_ids"])):
        errors.append("Manifest class_ids must be a list of unique nonnegative integers")
    if "class_names" in manifest and (not isinstance(manifest["class_names"], list)
                                      or any(not isinstance(value, str) or not value for value in manifest["class_names"])):
        errors.append("Manifest class_names must be a list of nonempty strings")
    if class_names is not None and isinstance(manifest.get("class_names"), list):
        declared = manifest["class_names"]
        if set(map(str, declared)) != set(class_names.values()):
            errors.append("Manifest class_names do not match model.names")
    if class_names is not None and isinstance(manifest.get("class_ids"), list):
        if set(map(int, manifest["class_ids"])) != set(class_names):
            errors.append("Manifest class_ids do not match model.names")
    expected = manifest.get("sha256")
    if expected:
        actual = sha256_file(model_path)
        if str(expected).lower() != actual:
            errors.append(f"Checkpoint SHA-256 mismatch: expected {expected}, got {actual}")
    return errors
