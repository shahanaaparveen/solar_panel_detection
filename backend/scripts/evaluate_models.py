"""Evaluate one configured detector on a manifest-declared validation/test split."""
import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.evaluation.evaluate import evaluate_model
from backend.vision.config import MODEL_CONFIGS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-role", choices=sorted(MODEL_CONFIGS), required=True)
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--labels-dir", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--split", choices=["validation", "test"], required=True)
    parser.add_argument("--require-site-holdout", action="store_true")
    parser.add_argument("--confidence", type=float)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate_model(args.model_role, args.images_dir, args.labels_dir,
        manifest_path=args.dataset_manifest, split=args.split,
        require_site_holdout=args.require_site_holdout, confidence=args.confidence,
        output_path=args.output)
    print(f"Evaluation status: {report['status']}; report: {args.output} and {args.output.with_suffix('.md')}")
    return 0 if report["status"] == "EVALUATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
