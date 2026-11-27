# Held-out model evaluation

Evaluation is offline and never writes production findings. Run one configured role at a time after supplying real weights and labeled images:

```bash
python backend/scripts/evaluate_models.py --model-role rgb_defect_detection \
  --images-dir data/test/images --labels-dir data/test/labels \
  --dataset-manifest data/test/dataset.json --split test \
  --require-site-holdout --output reports/rgb-test.json
```

Images and labels use YOLO text files with matching basenames. Detection rows are `class_id cx cy width height`, normalized to `[0, 1]`. Segmentation rows are `class_id x1 y1 x2 y2 ...`, with normalized polygon coordinates. Empty or missing label files represent images with no ground-truth instances.

The dataset manifest must declare `split` as `validation` or `test`; a CLI flag cannot substitute for a missing manifest split. To enforce site-disjoint evaluation, include `training_site_ids`, `evaluation_site_ids`, and `image_to_site` mappings, then pass `--require-site-holdout`. Overlapping train/evaluation site or flight IDs are rejected. Include `training_flight_ids`, `evaluation_flight_ids`, and `image_to_flight` to verify flight separation; reports warn when either grouping level is unavailable. Dataset version and class-name mappings should also be included.

Reports include precision, recall, F1, mAP@0.5, mAP@0.5:0.95, per-class AP, a background-aware confusion matrix, false-positive and false-negative examples, low-confidence candidates, latency summaries and segmentation IoU/Dice when applicable. When errors exist, real image overlays are written beside the report in a `<report>_errors` folder (green ground truth, red predictions, orange below-threshold candidates). The current latency runner measures model inference calls; it does not include image decoding or preprocessing. Memory is marked unavailable because portable GPU/CPU peak-memory instrumentation is not configured. Metrics are calculated only from the supplied labels and predictions; no metrics are available in this checkout because trained checkpoints and ground truth are absent.
