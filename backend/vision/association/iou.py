"""Bounding box intersection over union."""


def box_iou(a, b):
    ax1, ay1, ax2, ay2 = coords(a)
    bx1, by1, bx2, by2 = coords(b)
    iw, ih = max(0.0, min(ax2,bx2)-max(ax1,bx1)), max(0.0, min(ay2,by2)-max(ay1,by1))
    intersection = iw * ih
    area_a = max(0.0, ax2-ax1) * max(0.0, ay2-ay1)
    area_b = max(0.0, bx2-bx1) * max(0.0, by2-by1)
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def coords(box):
    if "bbox" in box:
        box = box["bbox"]
    if isinstance(box, (list, tuple)):
        return tuple(map(float, box))
    if {"x1", "y1", "x2", "y2"}.issubset(box):
        return tuple(float(box[k]) for k in ("x1", "y1", "x2", "y2"))
    return (float(box["x"]), float(box["y"]), float(box["x"]+box["w"]), float(box["y"]+box["h"]))
