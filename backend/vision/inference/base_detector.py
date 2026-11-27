"""Shared model inference conversion."""
from time import perf_counter
from PIL import Image, ImageOps
import numpy as np
from ..models.model_registry import registry
from ..schemas.detection import Detection
from ..association.iou import box_iou


def _tile_bounds(width, height, size=1024, overlap=0.2):
    stride = max(1, int(size * (1-overlap)))
    xs = list(range(0, max(1, width-size+1), stride))
    ys = list(range(0, max(1, height-size+1), stride))
    if not xs or xs[-1] + size < width: xs.append(max(0, width-size))
    if not ys or ys[-1] + size < height: ys.append(max(0, height-size))
    return [(x,y,min(width,x+size),min(height,y+size)) for y in ys for x in xs]


def _suppress_duplicates(detections, threshold=0.6):
    kept=[]
    for item in sorted(detections, key=lambda d:d["confidence"], reverse=True):
        if any(item["class_id"] == old["class_id"] and box_iou(item["bbox"], old["bbox"]) >= threshold for old in kept):
            continue
        kept.append(item)
    return kept


def infer(role, image_path, modality, image_size=None, confidence=None):
    entry = registry.get(role)
    config = entry["config"]
    started = perf_counter()
    kwargs = {"source": str(image_path), "imgsz": image_size or config.image_size,
              "conf": confidence if confidence is not None else config.confidence,
              "iou": config.iou, "verbose": False}
    if config.device != "auto":
        kwargs["device"] = config.device
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    tile_bounds = _tile_bounds(*image.size) if max(image.size) > config.image_size * 1.5 else None
    sources = [(np.asarray(image.crop((x,y,x2,y2))), x, y) for x,y,x2,y2 in tile_bounds] if tile_bounds else [(np.asarray(image), 0, 0)]
    output = []
    for source, offset_x, offset_y in sources:
        with entry["inference_lock"]:
            results = entry["model"].predict(**{**kwargs, "source": source})
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            h, w = result.orig_shape
            masks = getattr(result, "masks", None)
            for index, box in enumerate(boxes):
                xyxy = box.xyxy[0].cpu().tolist()
                class_id = int(box.cls[0].item())
                if class_id not in entry["names"]:
                    continue
                x1 = max(0.0, min(float(image.width), float(xyxy[0]) + offset_x))
                y1 = max(0.0, min(float(image.height), float(xyxy[1]) + offset_y))
                x2 = max(0.0, min(float(image.width), float(xyxy[2]) + offset_x))
                y2 = max(0.0, min(float(image.height), float(xyxy[3]) + offset_y))
                if x2 <= x1 or y2 <= y1:
                    continue
                confidence_score = float(box.conf[0].item())
                if not 0 <= confidence_score <= 1:
                    continue
                polygon = None
                if masks is not None and index < len(masks.xy):
                    polygon = [[max(0.0, min(float(image.width), float(x)+offset_x)), max(0.0, min(float(image.height), float(y)+offset_y))] for x, y in masks.xy[index].tolist()]
                bbox = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                normalized = {"x1": x1/image.width, "y1": y1/image.height, "x2": x2/image.width, "y2": y2/image.height}
                output.append(Detection(class_id, entry["names"][class_id], confidence_score,
                    bbox, modality, entry["manifest"].get("model_id", role),
                    {"width": image.width, "height": image.height}, polygon, normalized,
                    model_version=entry["manifest"].get("version", config.version),
                    model_sha256=entry["sha256"]).to_dict())
    return _suppress_duplicates(output, threshold=config.iou), (perf_counter()-started)*1000, entry["manifest"].get("version", config.version)
