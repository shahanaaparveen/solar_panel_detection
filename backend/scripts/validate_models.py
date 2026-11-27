"""Validate model manifests/checkpoint hashes and optionally smoke-test inference."""
import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.vision.config import MODEL_CONFIGS
from backend.vision.inference.base_detector import infer
from backend.vision.models.model_manifest import load_manifest, validate_manifest
from backend.vision.models.model_registry import registry


def _images(values):
    result = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError("Use --image ROLE=PATH")
        role, path = value.split("=", 1)
        result[role] = Path(path)
    return result


def validate(images_by_role=None):
    images_by_role = images_by_role or {}
    report = {"models": {}, "valid": True}
    for role, config in MODEL_CONFIGS.items():
        row = {"role": role, "checkpoint": config.path.name, "errors": [], "warnings": []}
        if not config.path.is_file():
            row["errors"].append(f"Configured checkpoint is missing: {config.path}")
            row["status"] = "MODEL_UNAVAILABLE"
            report["valid"] = False
            report["models"][role] = row
            continue
        try:
            manifest = load_manifest(config.path)
            if not manifest:
                row["errors"].append(f"Required manifest is missing: {config.path.with_suffix('.json').name}")
            row["errors"].extend(validate_manifest(manifest, config.path, role))
            entry = registry.get(role)
            row["errors"].extend(validate_manifest(manifest, config.path, role, entry["names"]))
            row["model"] = registry.describe(role)
            if role in images_by_role:
                image_path = images_by_role[role]
                if not image_path.is_file():
                    row["errors"].append(f"Smoke-test image does not exist: {image_path}")
                else:
                    modality = "thermal" if config.modality == "thermal" else "rgb"
                    detections, elapsed_ms, version = infer(role, image_path, modality)
                    row["smoke_test"] = {"status": "PASSED", "detection_count": len(detections),
                                          "inference_ms": elapsed_ms, "version": version}
            else:
                row["warnings"].append("No --image ROLE=PATH supplied; inference smoke test was not run.")
            row["status"] = "VALID" if not row["errors"] else "INVALID"
        except Exception as exc:
            row["errors"].append(f"{type(exc).__name__}: {exc}")
        if row["errors"]:
            row["status"] = "MODEL_ERROR" if any("Unable to load model" in error for error in row["errors"]) else "INVALID"
            report["valid"] = False
        elif "status" not in row:
            row["status"] = "VALID"
        report["models"][role] = row
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", action="append", default=[], metavar="ROLE=PATH",
                        help="Optional real image for a role-specific inference smoke test; repeat per role")
    parser.add_argument("--output", type=Path, help="Optional JSON report output path")
    args = parser.parse_args()
    report = validate(_images(args.image))
    rendered = json.dumps(report, indent=2, default=str)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
