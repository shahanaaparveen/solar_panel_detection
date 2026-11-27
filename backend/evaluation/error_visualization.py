"""Render actual ground-truth and inference boxes for evaluation errors."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


def write_error_visualizations(samples, predictions, errors, output_dir, class_names,
                               confidence_threshold=0.25):
    affected = {row["image_id"] for key in ("false_positives", "false_negatives", "low_confidence_predictions")
                for row in errors.get(key, [])}
    if not affected:
        return []
    sample_by_id = {sample["image_id"]: sample for sample in samples}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for image_id in sorted(affected):
        sample = sample_by_id.get(image_id)
        if not sample:
            continue
        with Image.open(sample["image_path"]) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        draw = ImageDraw.Draw(image)
        for truth in sample["ground_truth"]:
            box = truth["bbox"]
            draw.rectangle((box["x1"], box["y1"], box["x2"], box["y2"]), outline="#22c55e", width=3)
            draw.text((box["x1"] + 2, box["y1"] + 2),
                      f"GT {class_names.get(truth['class_id'], truth['class_id'])}", fill="#22c55e")
        for prediction in predictions.get(image_id, []):
            box = prediction["bbox"]
            color = "#f59e0b" if prediction["confidence"] < confidence_threshold else "#ef4444"
            draw.rectangle((box["x1"], box["y1"], box["x2"], box["y2"]), outline=color, width=3)
            label = class_names.get(prediction["class_id"], prediction["class_id"])
            draw.text((box["x1"] + 2, max(0, box["y1"] - 14)),
                      f"Pred {label} {prediction['confidence']:.2f}", fill=color)
        destination = output_dir / f"{Path(image_id).stem}.png"
        image.save(destination)
        paths.append(str(destination))
    return paths
