"""Geometric and statistical validation of estimated RGB/thermal homographies."""
from math import sqrt


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def validate_homography_geometry(matrix, moving_shape, min_scale=0.1, max_scale=12.0, max_condition=4.5):
    """Reject singular, reflected, wildly skewed, or self-intersecting homographies."""
    import cv2
    import numpy as np

    if matrix is None:
        return False, "No homography matrix produced"
    mat = np.asarray(matrix, dtype=np.float64)
    if mat.shape != (3, 3) or not np.all(np.isfinite(mat)) or abs(mat[2, 2]) < 1e-9:
        return False, "Homography matrix is degenerate"

    linear = mat[:2, :2] / mat[2, 2]
    det = float(np.linalg.det(linear))
    if det <= 0:
        return False, "Homography contains an invalid reflection or collapse"

    _, svals, _ = np.linalg.svd(linear)
    s_max, s_min = float(svals[0]), float(svals[1])
    if s_min < min_scale or s_max > max_scale:
        return False, f"Homography scale out of bounds ({s_min:.3f}..{s_max:.3f})"
    if s_min <= 1e-9 or (s_max / s_min) > max_condition:
        return False, "Homography shear/anisotropy exceeds valid bounds"

    h, w = moving_shape[:2]
    corners = np.float32([[[0, 0]], [[w, 0]], [[w, h]], [[0, h]]])
    warped = cv2.perspectiveTransform(corners, mat).reshape(4, 2)
    if not np.all(np.isfinite(warped)):
        return False, "Warped image corners are non-finite"
    signs = [
        _cross(warped[i], warped[(i + 1) % 4], warped[(i + 2) % 4])
        for i in range(4)
    ]
    if not (all(s > 0 for s in signs) or all(s < 0 for s in signs)):
        return False, "Warped image quadrilateral is non-convex"
    return True, "OK"


def validate_registration(
    estimation,
    matches_count,
    moving_shape,
    *,
    minimum_matches=12,
    min_inlier_ratio=0.5,
    max_mean_error_px=6.0,
):
    """Validate RANSAC inliers, reprojection error, and projective geometry sanity."""
    inliers = estimation["inliers"]
    quality = estimation["inlier_ratio"]
    matrix = estimation["matrix"]
    if matrix is None or inliers < minimum_matches or quality < min_inlier_ratio:
        return {
            "valid": False,
            "reason": "Homography did not pass inlier checks",
            "matches": matches_count,
            "inliers": inliers,
            "quality": quality,
        }

    geom_ok, geom_reason = validate_homography_geometry(matrix, moving_shape)
    if not geom_ok:
        return {
            "valid": False,
            "reason": geom_reason,
            "matches": matches_count,
            "inliers": inliers,
            "quality": quality,
        }

    errors = estimation["errors"]
    mean_err = sum(errors) / len(errors) if errors else float("inf")
    rmse_err = sqrt(sum(e * e for e in errors) / len(errors)) if errors else float("inf")
    max_err = max(errors) if errors else float("inf")
    if mean_err > max_mean_error_px:
        return {
            "valid": False,
            "reason": f"Mean reprojection error {mean_err:.2f}px exceeds {max_mean_error_px:.1f}px",
            "matches": matches_count,
            "inliers": inliers,
            "quality": quality,
            "mean_reprojection_error_px": mean_err,
        }

    return {
        "valid": True,
        "matches": matches_count,
        "inliers": inliers,
        "quality": quality,
        "mean_reprojection_error_px": mean_err,
        "rmse_reprojection_error_px": rmse_err,
        "max_reprojection_error_px": max_err,
    }
