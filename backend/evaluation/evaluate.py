"""Run a reproducible evaluation against a labeled validation or test split."""
from .dataset_loader import load_yolo_dataset
from .detection_metrics import compute_detection_metrics
from .error_visualization import write_error_visualizations
from .evaluation_report import write_report
from .latency import summarize_latency
from .prediction_runner import run_predictions
from .segmentation_metrics import evaluate_segmentation
from ..vision.models.model_registry import registry


def evaluate_model(model_role, images_dir, labels_dir, *, manifest_path=None, split=None,
                   require_site_holdout=False, confidence=None, output_path=None):
    samples, dataset_info = load_yolo_dataset(images_dir, labels_dir,
        manifest_path=manifest_path, split=split, require_site_holdout=require_site_holdout)
    entry = registry.get(model_role)
    evaluation_threshold = confidence if confidence is not None else entry["config"].confidence
    # Collect low-confidence candidates so reports can surface them separately.
    predictions, latencies, model_info = run_predictions(model_role, samples,
        confidence=min(0.001, evaluation_threshold))
    class_names = entry["names"]
    if model_role == "panel_detection":
        targets = entry["target_class_ids"]
        samples = [{**sample, "ground_truth": [row for row in sample["ground_truth"] if row["class_id"] in targets]}
                   for sample in samples]
        class_names = {class_id: name for class_id, name in class_names.items() if class_id in targets}
    if dataset_info.get("class_names"):
        declared = dataset_info["class_names"]
        if isinstance(declared, list):
            declared = {i: name for i, name in enumerate(declared)}
        else:
            declared = {int(key): value for key, value in declared.items()}
        expected = {class_id: class_names[class_id] for class_id in class_names if class_id in declared}
        if expected != {class_id: name for class_id, name in declared.items() if class_id in class_names}:
            raise ValueError("Dataset class_names do not match the configured model class IDs")
    detection_metrics = compute_detection_metrics(samples, predictions, class_names,
        confidence_threshold=evaluation_threshold)
    scored_predictions = {image_id: [prediction for prediction in rows
                                     if prediction["confidence"] >= evaluation_threshold]
                         for image_id, rows in predictions.items()}
    segmentation = evaluate_segmentation(samples, scored_predictions)
    warnings = list(dataset_info["warnings"])
    if not model_info.get("sha256"):
        warnings.append("Checkpoint checksum is unavailable; results are not fully reproducible.")
    report = {"status": detection_metrics["status"], "model": model_info,
        "dataset": dataset_info, "image_count": len(samples),
        "inference_latency": summarize_latency(latencies),
        "memory_usage_bytes": None,
        "detection_metrics": detection_metrics,
        "segmentation_metrics": segmentation,
        "warnings": warnings,
        "error_analysis": detection_metrics.get("errors", {})}
    if output_path:
        report_path = Path(output_path)
        report["error_visualizations"] = write_error_visualizations(samples, predictions,
            report["error_analysis"], report_path.parent / f"{report_path.stem}_errors",
            class_names, confidence_threshold=evaluation_threshold)
        write_report(report, output_path)
    return report
