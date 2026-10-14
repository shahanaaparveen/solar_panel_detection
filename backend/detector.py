import random

# ── Defect definitions ─────────────────────────────────────────────────────
THERMAL_DEFECTS = [
    {"label": "Hotspot",                  "color": "#ef4444"},
    {"label": "Loose Electrical Connection","color": "#3b82f6"},
    {"label": "Reverse Bias Cell",        "color": "#8b5cf6"},
    {"label": "Bypass Diode Failure",     "color": "#f59e0b"},
    {"label": "Cell Mismatch",            "color": "#ec4899"},
    {"label": "Open Circuit",             "color": "#f97316"},
]

RGB_DEFECTS = [
    {"label": "Bird Dropping",            "color": "#f59e0b"},
    {"label": "Leaves",                   "color": "#10b981"},
    {"label": "Dust Accumulation",        "color": "#a16207"},
    {"label": "Mud",                      "color": "#78350f"},
    {"label": "Snow",                     "color": "#bae6fd"},
    {"label": "Cracked Glass",            "color": "#ef4444"},
    {"label": "Broken Frame",             "color": "#dc2626"},
    {"label": "Delamination",             "color": "#7c3aed"},
    {"label": "Physical Damage",          "color": "#b91c1c"},
    {"label": "Vegetation Shading",       "color": "#15803d"},
]

SEVERITY_MAP = {
    "Hotspot": "High",
    "Loose Electrical Connection": "High",
    "Reverse Bias Cell": "High",
    "Bypass Diode Failure": "High",
    "Cell Mismatch": "Medium",
    "Open Circuit": "High",
    "Bird Dropping": "Low",
    "Leaves": "Low",
    "Dust Accumulation": "Low",
    "Mud": "Medium",
    "Snow": "Medium",
    "Cracked Glass": "High",
    "Broken Frame": "High",
    "Delamination": "High",
    "Physical Damage": "High",
    "Vegetation Shading": "Low",
}


def detect_defects(image_path: str, image_type: str, img_width: int, img_height: int):
    """
    Simulates YOLO detection.
    Returns list of bounding boxes with defect labels.
    Replace this function body with real YOLOv8 inference when model is ready.

    Each detection:
    {
        "label": str,
        "confidence": float,
        "severity": str,
        "color": str,
        "x": int,   # top-left x (pixels)
        "y": int,   # top-left y (pixels)
        "w": int,   # width
        "h": int,   # height
        "cx": int,  # center x
        "cy": int,  # center y
    }
    """
    rng = random.Random(hash(image_path) % 99991)

    defect_pool = THERMAL_DEFECTS if image_type == "thermal" else RGB_DEFECTS

    # Simulate 0–4 defects per image
    count = rng.choices([0, 1, 2, 3, 4], weights=[20, 35, 25, 15, 5])[0]
    detections = []

    for _ in range(count):
        defect = rng.choice(defect_pool)
        # Random bounding box
        bw = int(img_width  * rng.uniform(0.08, 0.22))
        bh = int(img_height * rng.uniform(0.08, 0.20))
        bx = int(rng.uniform(0.05, 0.85) * img_width)
        by = int(rng.uniform(0.05, 0.80) * img_height)
        bx = min(bx, img_width  - bw)
        by = min(by, img_height - bh)

        detections.append({
            "label":      defect["label"],
            "color":      defect["color"],
            "confidence": round(rng.uniform(0.78, 0.97), 2),
            "severity":   SEVERITY_MAP.get(defect["label"], "Medium"),
            "x": bx, "y": by, "w": bw, "h": bh,
            "cx": bx + bw // 2,
            "cy": by + bh // 2,
        })

    return detections


def detect_and_number_panels_yolo(image_path: str, model_path: str = "models/best.pt", conf: float = 0.25, save_output_path: str = None):
    """
    Implements panel detection and row-wise numbering matching Google Colab:
    1. Runs YOLOv8 inference if model weights exist.
    2. Calculates center coordinates: cx = (x1 + x2) / 2, cy = (y1 + y2) / 2.
    3. Groups panels into rows by vertical proximity.
    4. Sorts panels within each row left-to-right (x).
    5. Assigns sequential panel_id starting from 1.
    6. Draws red numbers using OpenCV cv2.putText.
    """
    import os
    boxes = []

    # 1. Try real YOLO inference if model exists
    if os.path.exists(model_path):
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
            results = model.predict(image_path, imgsz=640, conf=conf)
            for r in results:
                for b in r.boxes.xyxy.cpu().numpy():
                    x1, y1, x2, y2 = b[:4]
                    boxes.append({
                        "x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2),
                        "w": int(x2 - x1), "h": int(y2 - y1),
                        "cx": int((x1 + x2) / 2),
                        "cy": int((y1 + y2) / 2),
                    })
        except Exception as e:
            print(f"[YOLO detection fallback] Error running model: {e}")

    # Fallback to adaptive grid if no model or no detections
    if not boxes:
        try:
            from PIL import Image as PILImg
            with PILImg.open(image_path) as im:
                w, h = im.size
        except Exception:
            w, h = 1920, 1080

        cols, rows = 16, 8
        mx, my = int(w * 0.05), int(h * 0.05)
        cw = (w - 2 * mx) // cols
        ch = (h - 2 * my) // rows
        for r in range(rows):
            for c in range(cols):
                bx = mx + c * cw
                by = my + r * ch
                boxes.append({
                    "x1": bx, "y1": by, "x2": bx + cw - 4, "y2": by + ch - 4,
                    "w": cw - 4, "h": ch - 4,
                    "cx": bx + cw // 2, "cy": by + ch // 2
                })

    # 2. Group into rows by Y coordinate
    avg_h = sum(b["h"] for b in boxes) / max(1, len(boxes))
    row_thresh = avg_h * 0.6
    sorted_by_y = sorted(boxes, key=lambda b: b["cy"])

    row_groups = []
    for box in sorted_by_y:
        matched = False
        for row in row_groups:
            if abs(row[0]["cy"] - box["cy"]) < row_thresh:
                row.append(box)
                matched = True
                break
        if not matched:
            row_groups.append([box])

    # 3. Sort each row left -> right by X
    for row in row_groups:
        row.sort(key=lambda b: b["cx"])

    # 4. Assign sequential panel IDs (1, 2, 3...)
    numbered_panels = []
    pid = 1
    for row in row_groups:
        for box in row:
            box["panel_id"] = pid
            numbered_panels.append(box)
            pid += 1

    # 5. Draw OpenCV red numbers if image and save_output_path provided
    if save_output_path:
        try:
            import cv2
            img = cv2.imread(image_path)
            if img is not None:
                for panel in numbered_panels:
                    cv2.putText(
                        img,
                        str(panel["panel_id"]),
                        (panel["cx"] - 10, panel["cy"] + 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),  # Red in BGR
                        2
                    )
                os.makedirs(os.path.dirname(os.path.abspath(save_output_path)), exist_ok=True)
                cv2.imwrite(save_output_path, img)
        except Exception as e:
            print(f"[OpenCV drawing error]: {e}")

    return numbered_panels
