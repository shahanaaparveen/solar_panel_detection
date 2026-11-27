"""RANSAC homography estimation and reprojection error measurement."""


def estimate_homography(kp1, kp2, matches, ransac_threshold=4.0):
    """Estimate projective transform mapping moving (kp2) to reference (kp1) coordinates."""
    import cv2
    import numpy as np

    if len(matches) < 4:
        return {"matrix": None, "inliers": 0, "inlier_ratio": 0.0, "mask": None, "errors": []}

    src = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, ransac_threshold)
    inliers = int(mask.sum()) if mask is not None else 0
    inlier_ratio = inliers / len(matches)
    if matrix is None or inliers == 0:
        return {
            "matrix": None,
            "inliers": inliers,
            "inlier_ratio": inlier_ratio,
            "mask": mask,
            "errors": [],
        }

    inlier_selector = mask.ravel() == 1
    projected = cv2.perspectiveTransform(src[inlier_selector], matrix)
    errors = np.linalg.norm(
        projected.reshape(-1, 2) - dst[inlier_selector].reshape(-1, 2),
        axis=1,
    )
    return {
        "matrix": matrix,
        "inliers": inliers,
        "inlier_ratio": float(inlier_ratio),
        "mask": mask,
        "errors": [float(e) for e in errors],
    }
