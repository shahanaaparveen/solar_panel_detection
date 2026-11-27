"""Per-class precision, recall, F1 and AP summaries."""


def compute_per_class_metrics(class_ids, class_names, truth_by_class, pred_by_class,
                              thresholds, confidence_threshold, average_precision):
    metrics = {}
    for class_id in class_ids:
        scores = pred_by_class[class_id]
        truths = truth_by_class[class_id]
        aps = [average_precision(scores, truths, threshold)[0] for threshold in thresholds]
        aps = [value for value in aps if value is not None]
        ap50 = average_precision(scores, truths, 0.5)[0]
        thresholded = [row for row in scores if row["confidence"] >= confidence_threshold]
        _, true_positives, false_positives = average_precision(thresholded, truths, 0.5)
        ground_truth_count = sum(map(len, truths.values()))
        false_negatives = ground_truth_count - true_positives
        precision = true_positives/(true_positives+false_positives) if true_positives+false_positives else 0.0
        recall = true_positives/(true_positives+false_negatives) if true_positives+false_negatives else 0.0
        metrics[class_id] = {"class_name": class_names.get(class_id, f"class_{class_id}"),
            "ground_truth_count": ground_truth_count, "prediction_count": len(scores),
            "precision": precision, "recall": recall,
            "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0,
            "ap50": ap50, "ap50_95": sum(aps)/len(aps) if aps else None}
    return metrics
