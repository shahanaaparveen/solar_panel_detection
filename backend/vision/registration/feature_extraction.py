"""Multi-strategy keypoint and descriptor extraction for same-modal and cross-modal imagery."""


def preprocess_for_matching(gray_image, strategy="raw"):
    """Prepare grayscale image for keypoint detection using raw or structural gradient views."""
    import cv2
    import numpy as np

    if strategy == "raw":
        return gray_image
    if strategy == "clahe_edge":
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        norm = clahe.apply(gray_image)
        blurred = cv2.GaussianBlur(norm, (3, 3), 0)
        gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
        mag = cv2.magnitude(gx, gy)
        max_val = float(mag.max())
        if max_val <= 1e-6:
            return np.zeros_like(gray_image)
        return np.clip((mag / max_val) * 255.0, 0, 255).astype(np.uint8)
    raise ValueError(f"Unsupported preprocessing strategy: {strategy}")


def extract_features(gray_image, detector_name="SIFT", preprocess="raw"):
    """Extract keypoints and descriptors using SIFT, AKAZE, or ORB."""
    import cv2

    prepared = preprocess_for_matching(gray_image, strategy=preprocess)
    chosen = detector_name.upper()
    if chosen == "SIFT" and hasattr(cv2, "SIFT_create"):
        detector = cv2.SIFT_create()
        used_name = "SIFT"
    elif chosen in {"SIFT", "AKAZE"} and hasattr(cv2, "AKAZE_create"):
        detector = cv2.AKAZE_create()
        used_name = "AKAZE"
    else:
        detector = cv2.ORB_create(nfeatures=2500)
        used_name = "ORB"
    keypoints, descriptors = detector.detectAndCompute(prepared, None)
    return keypoints or [], descriptors, used_name
