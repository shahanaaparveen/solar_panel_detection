"""Conservative feature-based RGB/thermal registration."""
from PIL import Image, ImageOps


def align_images(reference_path, moving_path, minimum_matches=12):
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"status": "UNREGISTERED", "reason": "OpenCV is unavailable"}
    try:
        with Image.open(reference_path) as source:
            reference = np.asarray(ImageOps.exif_transpose(source).convert("L"))
        with Image.open(moving_path) as source:
            moving = np.asarray(ImageOps.exif_transpose(source).convert("L"))
    except (OSError, ValueError):
        return {"status": "UNREGISTERED", "reason": "An image could not be decoded"}
    detector = cv2.SIFT_create() if hasattr(cv2, "SIFT_create") else cv2.AKAZE_create()
    kp1, des1 = detector.detectAndCompute(reference, None)
    kp2, des2 = detector.detectAndCompute(moving, None)
    if des1 is None or des2 is None:
        return {"status": "UNREGISTERED", "reason": "Insufficient visual features"}
    norm = cv2.NORM_L2 if des1.dtype == np.float32 else cv2.NORM_HAMMING
    pairs = cv2.BFMatcher(norm).knnMatch(des1, des2, k=2)
    good = [a for a,b in pairs if a.distance < 0.72*b.distance]
    if len(good) < minimum_matches:
        return {"status": "UNREGISTERED", "reason": "Insufficient feature correspondences", "matches": len(good)}
    src = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)
    dst = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    inliers = int(mask.sum()) if mask is not None else 0
    quality = inliers / len(good)
    if matrix is None or inliers < minimum_matches or quality < 0.5:
        return {"status": "UNREGISTERED", "reason": "Homography did not pass inlier checks", "matches": len(good), "inliers": inliers, "quality": quality}
    projected = cv2.perspectiveTransform(src[mask.ravel() == 1], matrix)
    errors = np.linalg.norm(projected.reshape(-1, 2) - dst[mask.ravel() == 1].reshape(-1, 2), axis=1)
    return {"status": "REGISTERED", "transform": matrix.tolist(), "matches": len(good), "inliers": inliers,
            "quality": quality, "mean_reprojection_error_px": float(errors.mean()), "method": "SIFT/AKAZE + RANSAC"}
