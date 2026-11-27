"""Save evaluation results as JSON and a compact Markdown summary."""
import json
from pathlib import Path


def write_report(report, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    metrics = report.get("detection_metrics", {}).get("metrics") or {}
    lines = [f"# Model Evaluation: {report.get('model', {}).get('model_id', 'unknown')}", "",
             f"- Status: {report.get('status')}", f"- Model version: {report.get('model', {}).get('version')}",
             f"- Checkpoint SHA-256: {report.get('model', {}).get('sha256')}",
             f"- Dataset version: {report.get('dataset', {}).get('dataset_version')}",
             f"- Split: {report.get('dataset', {}).get('split')}",
             f"- Site split verified: {report.get('dataset', {}).get('site_split_verified')}",
             f"- Flight split verified: {report.get('dataset', {}).get('flight_split_verified')}",
             f"- Images evaluated: {report.get('image_count', 0)}", "",
             "## Detection metrics", "",
             f"- Precision: {metrics.get('precision')}", f"- Recall: {metrics.get('recall')}",
             f"- F1: {metrics.get('f1')}", f"- mAP@0.5: {metrics.get('map50')}",
             f"- mAP@0.5:0.95: {metrics.get('map50_95')}",
             f"- False positives: {metrics.get('false_positive_count')}",
             f"- False negatives: {metrics.get('false_negative_count')}", "",
             "## Warnings", ""]
    lines.extend(f"- {warning}" for warning in report.get("warnings", []))
    if not report.get("warnings"):
        lines.append("- None")
    output_path.with_suffix(".md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return output_path
