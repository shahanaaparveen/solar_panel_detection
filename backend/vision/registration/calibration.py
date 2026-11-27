"""Optional camera intrinsics, resolution scaling, and calibrated extrinsic transforms."""


def resolution_scale_matrix(src_shape, dst_shape):
    """Build affine scale matrix mapping src (h, w) coordinates to dst (h, w)."""
    src_h, src_w = src_shape[:2]
    dst_h, dst_w = dst_shape[:2]
    if src_w <= 0 or src_h <= 0 or dst_w <= 0 or dst_h <= 0:
        raise ValueError("Image dimensions must be positive")
    sx = float(dst_w) / float(src_w)
    sy = float(dst_h) / float(src_h)
    return [[sx, 0.0, 0.0], [0.0, sy, 0.0], [0.0, 0.0, 1.0]]


def apply_camera_calibration(gray_image, camera_matrix=None, dist_coeffs=None):
    """Undistort image only when explicit camera intrinsics and distortion coefficients exist."""
    if camera_matrix is None or dist_coeffs is None:
        return gray_image, False
    import cv2
    import numpy as np

    k = np.asarray(camera_matrix, dtype=np.float64)
    d = np.asarray(dist_coeffs, dtype=np.float64)
    return cv2.undistort(gray_image, k, d), True
