"""COCO-style IoU-threshold detection metrics and image-level error details."""
from ..vision.association.iou import box_iou
from .per_class_metrics import compute_per_class_metrics


def _average_precision(scores, truths, iou_threshold):
    ordered = sorted(scores, key=lambda item: item["confidence"], reverse=True)
    matched = {image_id: set() for image_id in truths}
    tp, fp = [], []
    for prediction in ordered:
        candidates = truths.get(prediction["image_id"], [])
        best_index, best_iou = None, 0.0
        for index, truth in enumerate(candidates):
            if index in matched[prediction["image_id"]]:
                continue
            overlap = box_iou(prediction["bbox"], truth["bbox"])
            if overlap > best_iou:
                best_index, best_iou = index, overlap
        if best_index is not None and best_iou >= iou_threshold:
            matched[prediction["image_id"]].add(best_index)
            tp.append(1)
            fp.append(0)
        else:
            tp.append(0)
            fp.append(1)
    total_gt = sum(map(len, truths.values()))
    if not total_gt:
        return None, 0, len(ordered)
    cumulative_tp, cumulative_fp = [], []
    t, f = 0, 0
    for true_positive, false_positive in zip(tp, fp):
        t += true_positive
        f += false_positive
        cumulative_tp.append(t)
        cumulative_fp.append(f)
    recalls = [value/total_gt for value in cumulative_tp]
    precisions = [t/(t+f) if t+f else 0.0 for t,f in zip(cumulative_tp,cumulative_fp)]
    area = 0.0
    for step in range(101):
        recall_level = step/100
        area += max((p for p,r in zip(precisions,recalls) if r >= recall_level), default=0.0)
    return area/101, sum(tp), sum(fp)


def compute_detection_metrics(samples, predictions, class_names, *, confidence_threshold=0.25,
                              iou_thresholds=None):
    thresholds = list(iou_thresholds or [0.5 + 0.05*i for i in range(10)])
    class_ids = sorted(set(class_names) | {a["class_id"] for s in samples for a in s["ground_truth"]})
    if not class_ids:
        return {"status": "NO_GROUND_TRUTH_CLASSES", "metrics": None, "per_class": {}, "errors": {"false_positives": [], "false_negatives": []}}
    truth_by_class = {class_id: {} for class_id in class_ids}
    pred_by_class = {class_id: [] for class_id in class_ids}
    image_truth = {}
    image_predictions = {}
    for sample in samples:
        image_id = sample["image_id"]
        image_truth[image_id] = sample["ground_truth"]
        image_predictions[image_id] = [p for p in predictions.get(image_id, []) if p["confidence"] >= confidence_threshold]
        for class_id in class_ids:
            truth_by_class[class_id][image_id] = [a for a in sample["ground_truth"] if a["class_id"] == class_id]
        for pred in predictions.get(image_id, []):
            if pred["class_id"] in pred_by_class:
                pred_by_class[pred["class_id"]].append({"image_id": image_id, **pred})

    per_class = compute_per_class_metrics(class_ids, class_names, truth_by_class, pred_by_class,
        thresholds, confidence_threshold, _average_precision)

    labels = class_ids + [-1]
    matrix = {str(true): {str(pred): 0 for pred in labels} for true in labels}
    false_positives, false_negatives = [], []
    low_confidence_predictions = []
    total_tp=0
    for image_id, gt_boxes in image_truth.items():
        remaining = set(range(len(gt_boxes)))
        low_confidence_predictions.extend({"image_id": image_id, **prediction, "reason": "below_evaluation_threshold"}
            for prediction in predictions.get(image_id, []) if prediction["confidence"] < confidence_threshold)
        for prediction in sorted(image_predictions[image_id], key=lambda p:p["confidence"], reverse=True):
            best_idx, best_overlap = None, 0.0
            for index in remaining:
                overlap = box_iou(prediction["bbox"], gt_boxes[index]["bbox"])
                if overlap > best_overlap:
                    best_idx, best_overlap = index, overlap
            if best_idx is not None and best_overlap >= 0.5:
                truth = gt_boxes[best_idx]
                matrix[str(truth["class_id"])][str(prediction["class_id"])] += 1
                remaining.remove(best_idx)
                if truth["class_id"] == prediction["class_id"]:
                    total_tp += 1
                else:
                    false_positives.append({"image_id": image_id, **prediction, "reason": "class_mismatch"})
                    false_negatives.append({"image_id": image_id, **truth, "reason": "class_mismatch"})
            else:
                matrix[str(-1)][str(prediction["class_id"])] += 1
                false_positives.append({"image_id": image_id, **prediction, "reason": "no_iou_match"})
        for index in remaining:
            truth=gt_boxes[index]
            matrix[str(truth["class_id"])][str(-1)] += 1
            false_negatives.append({"image_id": image_id, **truth, "reason": "missed"})

    total_gt = sum(len(x) for x in image_truth.values())
    total_pred = sum(len(x) for x in image_predictions.values())
    total_fp = len(false_positives)
    total_fn = len(false_negatives)
    precision = total_tp/(total_tp+total_fp) if total_tp+total_fp else 0.0
    recall = total_tp/(total_tp+total_fn) if total_tp+total_fn else 0.0
    aps50 = [item["ap50"] for item in per_class.values() if item["ap50"] is not None]
    aps_all = [item["ap50_95"] for item in per_class.values() if item["ap50_95"] is not None]
    return {"status": "EVALUATED", "metrics": {"precision": precision, "recall": recall,
        "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0,
        "map50": sum(aps50)/len(aps50) if aps50 else None,
        "map50_95": sum(aps_all)/len(aps_all) if aps_all else None,
        "false_positive_count": total_fp, "false_negative_count": total_fn,
        "ground_truth_count": total_gt, "prediction_count": total_pred,
        "confusion_matrix": {"class_ids": labels, "background_class_id": -1, "counts": matrix}},
        "per_class": per_class,
        "errors": {"false_positives": false_positives, "false_negatives": false_negatives,
                   "low_confidence_predictions": low_confidence_predictions}}
