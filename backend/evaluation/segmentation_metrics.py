"""Mask IoU and Dice metrics for matched polygon annotations, when available."""
import numpy as np


def polygon_mask(points, width, height):
    import cv2
    mask = np.zeros((height, width), dtype=np.uint8)
    if points and len(points) >= 3:
        polygon = np.asarray(points, dtype=np.float32).reshape((-1, 1, 2)).round().astype(np.int32)
        cv2.fillPoly(mask, [polygon], 1)
    return mask


def mask_iou_dice(truth, prediction):
    if truth.shape != prediction.shape:
        raise ValueError("Truth and prediction masks must have identical dimensions")
    truth = truth.astype(bool)
    prediction = prediction.astype(bool)
    intersection = int(np.logical_and(truth, prediction).sum())
    union = int(np.logical_or(truth, prediction).sum())
    denominator = int(truth.sum() + prediction.sum())
    return {"iou": intersection/union if union else 1.0,
            "dice": 2*intersection/denominator if denominator else 1.0}


def evaluate_segmentation(samples, predictions):
    per_class = {}
    matched_objects = 0
    unmatched_truths = 0
    unmatched_predictions = 0
    for sample in samples:
        image_id = sample["image_id"]
        width, height = sample["width"], sample["height"]
        classes = {annotation["class_id"] for annotation in sample["ground_truth"] if annotation.get("polygon")}
        classes.update(prediction["class_id"] for prediction in predictions.get(image_id, []) if prediction.get("mask"))
        for class_id in classes:
            truths = [polygon_mask(annotation["polygon"], width, height) for annotation in sample["ground_truth"]
                      if annotation["class_id"] == class_id and annotation.get("polygon")]
            preds = [polygon_mask(prediction["mask"], width, height) for prediction in predictions.get(image_id, [])
                     if prediction["class_id"] == class_id and prediction.get("mask")]
            used = set()
            stats = per_class.setdefault(class_id, {"ious": [], "dices": []})
            for truth in truths:
                best_index, best_iou = None, -1.0
                for index, pred in enumerate(preds):
                    if index in used:
                        continue
                    value = mask_iou_dice(truth, pred)["iou"]
                    if value > best_iou:
                        best_index, best_iou = index, value
                if best_index is None or best_iou < 0.5:
                    stats["ious"].append(0.0)
                    stats["dices"].append(0.0)
                    unmatched_truths += 1
                else:
                    used.add(best_index)
                    metrics = mask_iou_dice(truth, preds[best_index])
                    stats["ious"].append(metrics["iou"])
                    stats["dices"].append(metrics["dice"])
                    matched_objects += 1
            unmatched_predictions += len(preds) - len(used)
    if not per_class:
        return {"status": "NOT_EVALUATED", "reason": "No polygon ground truth or predicted masks were available", "per_class": {}}
    formatted = {class_id: {"iou": sum(v["ious"])/len(v["ious"]) if v["ious"] else None,
                            "dice": sum(v["dices"])/len(v["dices"]) if v["dices"] else None,
                            "ground_truth_instances": len(v["ious"])} for class_id, v in per_class.items()}
    return {"status": "EVALUATED", "per_class": formatted, "matched_instances": matched_objects,
            "unmatched_ground_truth_instances": unmatched_truths,
            "unmatched_prediction_instances": unmatched_predictions}
