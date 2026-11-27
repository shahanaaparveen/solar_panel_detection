"""Evidence-gated RGB/thermal and same-modal image registration."""
from PIL import Image, ImageOps
from .calibration import apply_camera_calibration, resolution_scale_matrix
from .feature_extraction import extract_features
from .feature_matching import match_descriptors
from .homography import estimate_homography
from .metadata import extract_image_metadata
from .validation import validate_registration


def _compose_with_prescale(matrix, moving_shape, ref_shape):
    """Compose moving->scaled_moving->ref homography back to original moving pixel coordinates."""
    import numpy as np

    scale = np.asarray(resolution_scale_matrix(moving_shape, ref_shape), dtype=np.float64)
    return matrix @ scale


def align_images(
    reference_path,
    moving_path,
    minimum_matches=12,
    reference_image_id=None,
    moving_image_id=None,
    calibration=None,
    modality_hint="cross_modal",
):
    """Register moving_path into reference_path pixel coordinates when feature/calibration checks pass."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {
            "status": "UNREGISTERED",
            "reason": "OpenCV is unavailable",
            "source_image_id": moving_image_id,
            "target_image_id": reference_image_id,
        }

    try:
        with Image.open(reference_path) as source:
            reference = np.asarray(ImageOps.exif_transpose(source).convert("L"))
        with Image.open(moving_path) as source:
            moving = np.asarray(ImageOps.exif_transpose(source).convert("L"))
    except (OSError, ValueError):
        return {
            "status": "UNREGISTERED",
            "reason": "An image could not be decoded",
            "source_image_id": moving_image_id,
            "target_image_id": reference_image_id,
        }

    if calibration and calibration.get("extrinsic_homography"):
        return {
            "status": "REGISTERED",
            "source_image_id": moving_image_id,
            "target_image_id": reference_image_id,
            "transform": calibration["extrinsic_homography"],
            "matches": None,
            "inliers": None,
            "inlier_ratio": 1.0,
            "quality": 1.0,
            "mean_reprojection_error_px": 0.0,
            "method": "Calibrated Extrinsic Parameters",
        }

    ref_cal, _ = apply_camera_calibration(
        reference,
        (calibration or {}).get("reference_camera_matrix"),
        (calibration or {}).get("reference_dist_coeffs"),
    )
    mov_cal, _ = apply_camera_calibration(
        moving,
        (calibration or {}).get("moving_camera_matrix"),
        (calibration or {}).get("moving_dist_coeffs"),
    )

    strategies = [("SIFT", "raw", False)]
    if modality_hint == "cross_modal":
        strategies.append(("SIFT", "clahe_edge", mov_cal.shape != ref_cal.shape))
        strategies.append(("AKAZE", "clahe_edge", mov_cal.shape != ref_cal.shape))

    best_failure = None
    for det_name, prep_mode, prescale in strategies:
        mov_input = (
            cv2.resize(mov_cal, (ref_cal.shape[1], ref_cal.shape[0]), interpolation=cv2.INTER_AREA)
            if prescale
            else mov_cal
        )
        kp1, des1, used_det = extract_features(ref_cal, detector_name=det_name, preprocess=prep_mode)
        kp2, des2, _ = extract_features(mov_input, detector_name=det_name, preprocess=prep_mode)
        if des1 is None or des2 is None:
            best_failure = best_failure or {
                "status": "UNREGISTERED",
                "reason": "Insufficient visual features",
            }
            continue

        good = match_descriptors(des1, des2, ratio=0.72, cross_check=(prep_mode != "raw"))
        if len(good) < minimum_matches:
            best_failure = best_failure or {
                "status": "UNREGISTERED",
                "reason": "Insufficient feature correspondences",
                "matches": len(good),
            }
            continue

        est = estimate_homography(kp1, kp2, good, ransac_threshold=4.0)
        if est["matrix"] is not None and prescale:
            est["matrix"] = _compose_with_prescale(est["matrix"], mov_cal.shape, ref_cal.shape)

        verdict = validate_registration(
            est,
            len(good),
            mov_cal.shape,
            minimum_matches=minimum_matches,
            min_inlier_ratio=0.5,
        )
        if verdict["valid"]:
            method_label = (
                "SIFT/AKAZE + RANSAC"
                if prep_mode == "raw"
                else f"{used_det} ({prep_mode}) + RANSAC"
            )
            return {
                "status": "REGISTERED",
                "source_image_id": moving_image_id,
                "target_image_id": reference_image_id,
                "transform": est["matrix"].tolist(),
                "matches": verdict["matches"],
                "inliers": verdict["inliers"],
                "inlier_ratio": verdict["quality"],
                "quality": verdict["quality"],
                "mean_reprojection_error_px": verdict["mean_reprojection_error_px"],
                "rmse_reprojection_error_px": verdict["rmse_reprojection_error_px"],
                "max_reprojection_error_px": verdict["max_reprojection_error_px"],
                "method": method_label,
                "metadata": {
                    "reference": extract_image_metadata(reference_path),
                    "moving": extract_image_metadata(moving_path),
                },
            }
        best_failure = {
            "status": "UNREGISTERED",
            "reason": verdict["reason"],
            "matches": verdict["matches"],
            "inliers": verdict["inliers"],
            "inlier_ratio": verdict["quality"],
            "quality": verdict["quality"],
        }

    result = best_failure or {"status": "UNREGISTERED", "reason": "Registration failed"}
    result.setdefault("source_image_id", moving_image_id)
    result.setdefault("target_image_id", reference_image_id)
    return result
