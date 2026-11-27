# Model artifacts

The registry has independent `panel_detection`, `thermal_defect_detection`, and `rgb_defect_detection` roles. Set the role-specific `*_MODEL_PATH` variables or use the default paths under `backend/models/`. Confidence, IoU, image-size, device, and version settings use the corresponding role prefixes (for example `THERMAL_CONFIDENCE=0.3`). `MODEL_DEVICE=auto` lets Ultralytics select CPU or CUDA.

Each deployed checkpoint should have a JSON manifest beside it, with the same basename. A complete manifest follows this schema (fill in values from the actual training and deployment records):

```json
{
  "model_id": "panel-localizer",
  "role": "panel_detection",
  "model_type": "instance_segmentation",
  "architecture": "ultralytics-segmentation",
  "version": "1.0.0",
  "checkpoint_path": "panel_detection.pt",
  "sha256": "<64-character-checkpoint-sha256>",
  "training_dataset_version": "<dataset-version>",
  "training_image_dimensions": [4000, 3000],
  "class_ids": [0],
  "class_names": ["panel"],
  "target_classes": ["panel"],
  "preprocessing": {"color_space": "RGB", "exif_orientation": "transpose", "tile_overlap": 0.2},
  "confidence_threshold": 0.25,
  "nms_threshold": 0.5,
  "evaluation_metrics": {},
  "training_timestamp": "<ISO-8601-training-time>",
  "deployment_timestamp": "<ISO-8601-deployment-time>"
}
```

Keep checkpoint SHA-256 synchronized with the artifact. `python backend/scripts/validate_models.py` checks the manifest, checkpoint, class mapping and optional per-role smoke-test inference; a missing checkpoint or manifest is reported per role. For a multi-class panel model, `target_classes` or `target_class_ids` is required. The registry validates these values against `model.names`; no class index is presumed. Manifest validation is also available without loading a model through `validate_models.py` only when the checkpoint can load; otherwise the load failure is reported explicitly.

Do not commit model weights or raw image data. Distribute verified artifacts with Git LFS or an artifact store, and record their provenance, class mapping, validation metrics, and version before configuring them.

The shared inference contract uses EXIF-oriented original-image pixel coordinates (`xyxy`: left, top, right, bottom), with the origin at the top-left. Detection records also carry normalized coordinates, modality, image dimensions, model ID, class ID/name, confidence, optional mask polygon, image ID, model-run ID and inference time. The API adapts these records into persisted image results and model-run references. See the schema in `schemas/detection.py`.

## Model-delivery checklist

- [ ] Deliver three role-specific artifacts: `panel_detection`, `thermal_defect_detection`, and `rgb_defect_detection`; do not reuse a defect checkpoint as a panel model.
- [ ] Supply the complete adjacent manifest and compute its SHA-256 from the delivered checkpoint.
- [ ] Confirm framework/task compatibility, input dimensions, class IDs/names, target panel classes, thresholds, device, and modality-specific preprocessing with the training owner.
- [ ] Run `python backend/scripts/validate_models.py` with one real `--image ROLE=PATH` for each role; require each role to report `VALID` and smoke test `PASSED`.
- [ ] Run held-out validation with site and flight grouping metadata; record JSON/Markdown reports and review error overlays before deployment.
- [ ] Confirm production MongoDB, `AUTH_ENABLED=true`, trusted OIDC issuer/audience/JWKS configuration, CORS origins, reverse-proxy rate limits, and upload limits.
- [ ] Verify persisted model-run IDs, checksums, original-image coordinates, project-scoped images, findings and report snapshots in a deployment smoke test.

No checkpoint, validation image, annotation, measured accuracy, or training metadata is included in this repository. The checklist remains incomplete until those real artifacts are supplied and tested.
