"""Load a YOLO-format held-out split and its optional site-split manifest."""
import json
from pathlib import Path

from ..vision.preprocessing.image_loader import load_image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def load_yolo_dataset(images_dir, labels_dir, *, manifest_path=None, split=None, require_site_holdout=False):
    images_dir, labels_dir = Path(images_dir), Path(labels_dir)
    if not images_dir.is_dir() or not labels_dir.is_dir():
        raise ValueError("Both images_dir and labels_dir must exist")
    manifest = {}
    if manifest_path:
        try:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid dataset manifest: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ValueError("Dataset manifest must contain a JSON object")
    declared_split = manifest.get("split", "unknown")
    if split and manifest.get("split") and manifest["split"] != split:
        raise ValueError(f"Requested split {split!r} does not match manifest split {manifest['split']!r}")
    if declared_split not in {"validation", "test"}:
        raise ValueError("Evaluation requires a dataset manifest declaring split='validation' or split='test'")
    def id_set(field):
        value = manifest.get(field, [])
        if not isinstance(value, list):
            raise ValueError(f"Dataset manifest {field} must be a list")
        return set(map(str, value))
    training_sites = id_set("training_site_ids")
    evaluation_sites = id_set("evaluation_site_ids")
    training_flights = id_set("training_flight_ids")
    evaluation_flights = id_set("evaluation_flight_ids")
    if training_sites & evaluation_sites:
        overlap = sorted(training_sites & evaluation_sites)
        raise ValueError(f"Dataset leakage: site IDs appear in training and evaluation: {overlap}")
    if training_flights & evaluation_flights:
        overlap = sorted(training_flights & evaluation_flights)
        raise ValueError(f"Dataset leakage: flight IDs appear in training and evaluation: {overlap}")
    images = sorted(path for path in images_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise ValueError("No supported images found in images_dir")
    site_map = manifest.get("image_to_site", {})
    flight_map = manifest.get("image_to_flight", {})
    if not isinstance(site_map, dict) or not isinstance(flight_map, dict):
        raise ValueError("Dataset manifest image_to_site and image_to_flight must be objects")
    image_names = {path.name for path in images}
    site_verified = bool(training_sites and evaluation_sites and image_names <= set(site_map)
                         and all(str(site_map[name]) in evaluation_sites for name in image_names))
    if require_site_holdout and not site_verified:
        raise ValueError("Site-disjoint training/evaluation IDs and site mappings for every evaluation image are required")
    flight_verified = bool(training_flights and evaluation_flights and image_names <= set(flight_map)
                           and all(str(flight_map[name]) in evaluation_flights for name in image_names))
    samples = []
    for image_path in images:
        image, metadata = load_image(image_path)
        label_path = labels_dir / f"{image_path.stem}.txt"
        annotations = []
        if label_path.exists():
            from .ground_truth import parse_yolo_label_line
            for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
                if line.strip():
                    annotations.append(parse_yolo_label_line(line, image.width, image.height,
                                                             source=str(label_path), line_number=line_number))
        site_id = site_map.get(image_path.name)
        flight_id = flight_map.get(image_path.name)
        if site_id is not None and str(site_id) in training_sites:
            raise ValueError(f"Dataset leakage: evaluation image {image_path.name!r} belongs to training site {site_id!r}")
        if flight_id is not None and str(flight_id) in training_flights:
            raise ValueError(f"Dataset leakage: evaluation image {image_path.name!r} belongs to training flight {flight_id!r}")
        if evaluation_sites and site_id is not None and str(site_id) not in evaluation_sites:
            raise ValueError(f"Evaluation image {image_path.name!r} has site ID outside evaluation_site_ids")
        if evaluation_flights and flight_id is not None and str(flight_id) not in evaluation_flights:
            raise ValueError(f"Evaluation image {image_path.name!r} has flight ID outside evaluation_flight_ids")
        samples.append({"image_id": image_path.name, "image_path": image_path,
                        "width": image.width, "height": image.height,
                        "ground_truth": annotations, "site_id": site_id, "flight_id": flight_id})
    return samples, {"dataset_version": manifest.get("dataset_version", "unversioned"),
                     "split": declared_split, "site_split_verified": site_verified,
                     "flight_split_verified": flight_verified,
                     "site_ids": sorted(evaluation_sites),
                     "flight_ids": sorted(evaluation_flights),
                     "class_names": manifest.get("class_names"),
                     "warnings": ([] if site_verified else ["Site-level train/evaluation separation was not verified."])
                         + ([] if flight_verified else ["Flight-level train/evaluation separation was not verified."])}
