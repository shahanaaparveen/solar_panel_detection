"""Descriptor matching with Lowe ratio test and optional mutual cross-check."""


def match_descriptors(des1, des2, ratio=0.72, cross_check=True):
    """Match descriptor arrays using BFMatcher, ratio filtering, and optional mutual check."""
    import cv2
    import numpy as np

    if des1 is None or des2 is None or len(des1) < 2 or len(des2) < 2:
        return []
    norm = cv2.NORM_L2 if des1.dtype == np.float32 else cv2.NORM_HAMMING
    matcher = cv2.BFMatcher(norm)
    raw_pairs = matcher.knnMatch(des1, des2, k=2)
    good_forward = [pair[0] for pair in raw_pairs if len(pair) == 2 and pair[0].distance < ratio * pair[1].distance]
    if not cross_check or not good_forward:
        return good_forward

    reverse_pairs = matcher.knnMatch(des2, des1, k=2)
    reverse_best = {}
    for pair in reverse_pairs:
        if len(pair) == 2 and pair[0].distance < ratio * pair[1].distance:
            reverse_best[pair[0].queryIdx] = pair[0].trainIdx
    mutual = [m for m in good_forward if reverse_best.get(m.trainIdx) == m.queryIdx]
    return mutual if len(mutual) >= len(good_forward) * 0.5 else good_forward
