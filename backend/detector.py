import os
import random
from pathlib import Path

# ── Model paths & definitions ──────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "best.pt")
CONF_MIN = 0.40   # minimum confidence threshold for YOLO inference

THERMAL_DEFECTS = [
    {"label": "Hotspot",                  "color": "#ef4444"},
    {"label": "Diode",                    "color": "#f59e0b"},
    {"label": "Anomaly",                  "color": "#8b5cf6"},
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

CLASS_COLORS = {
    "Hotspot": "#ef4444",
    "Diode": "#f59e0b",
    "Anomaly": "#8b5cf6",
    "Loose Electrical Connection": "#3b82f6",
    "Reverse Bias Cell": "#8b5cf6",
    "Bypass Diode Failure": "#f59e0b",
    "Cell Mismatch": "#ec4899",
    "Open Circuit": "#f97316",
    "Bird Dropping": "#f59e0b",
    "Leaves": "#10b981",
    "Dust Accumulation": "#a16207",
    "Mud": "#78350f",
    "Snow": "#bae6fd",
    "Cracked Glass": "#ef4444",
    "Broken Frame": "#dc2626",
    "Delamination": "#7c3aed",
    "Physical Damage": "#b91c1c",
    "Vegetation Shading": "#15803d",
}

SEVERITY_MAP = {
    "Hotspot": "High",
    "Diode": "High",
    "Anomaly": "Medium",
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

SEVERITY_ORDER = ("Low", "Medium", "High")


def modality(path: str) -> str:
    """Infer image modality from filename suffix (DJI convention: _T thermal, _V/_W/_Z rgb)."""
    n = Path(path).stem.upper()
    if n.endswith("_T"):
        return "thermal"
    if n.endswith(("_V", "_W", "_Z")):
        return "rgb"
    return "unknown"


def compute_severity(label: str, confidence: float) -> str:
    """Combine base class severity with detection confidence so low-confidence hits are downgraded."""
    base = SEVERITY_MAP.get(label, "Medium")
    if confidence < CONF_MIN:
        return "Low"
    if confidence < 0.60:
        idx = SEVERITY_ORDER.index(base) if base in SEVERITY_ORDER else 1
        return SEVERITY_ORDER[max(0, idx - 1)]
    return base


_yolo_model = None

def get_yolo_model(model_path: str = None):
    """
    Singleton loader for the YOLO defect detection model.
    """
    global _yolo_model
    if model_path is None:
        model_path = MODEL_PATH
    if _yolo_model is None and os.path.exists(model_path):
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO(model_path)
            print(f"[YOLO] Successfully loaded model from {model_path} with classes {_yolo_model.names}")
        except Exception as e:
            print(f"[YOLO load error]: {e}")
    return _yolo_model


def detect_defects(image_path: str, image_type: str = None, img_width: int = 640, img_height: int = 480, conf: float = CONF_MIN):
    """
    Performs defect detection:
    1. Routes by filename modality (and falls back to image_type if filename is unmarked);
       returns [] for non-thermal images since no RGB defect model is trained yet.
    2. If trained YOLO model exists (models/best.pt), runs real inference at conf >= CONF_MIN.
    3. Maps detected bounding boxes, confidence, labels, color, and confidence-aware severity.
    4. Falls back to simulated detection if model file is not present.
    """
    detected_modality = modality(image_path)
    effective_modality = detected_modality if detected_modality != "unknown" else (image_type or "unknown")
    if effective_modality != "thermal":
        return []

    model = get_yolo_model()
    if model is not None:
        try:
            results = model.predict(image_path, imgsz=640, conf=conf, verbose=False)
            detections = []
            for r in results:
                if not hasattr(r, "boxes") or r.boxes is None:
                    continue
                for b in r.boxes:
                    coords = b.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                    cls_id = int(b.cls[0].item())
                    score = float(b.conf[0].item())
                    label = model.names.get(cls_id, f"Class_{cls_id}")
                    bw = max(1, x2 - x1)
                    bh = max(1, y2 - y1)
                    color = CLASS_COLORS.get(label, "#ef4444")
                    severity = compute_severity(label, score)

                    detections.append({
                        "label": label,
                        "color": color,
                        "confidence": round(score, 2),
                        "severity": severity,
                        "x": max(0, x1),
                        "y": max(0, y1),
                        "w": bw,
                        "h": bh,
                        "cx": x1 + bw // 2,
                        "cy": y1 + bh // 2,
                    })
            return detections
        except Exception as e:
            print(f"[YOLO detection error]: {e}, falling back to simulation")

    # Simulation fallback if model weights are missing or failed
    rng = random.Random(hash(image_path) % 99991)
    defect_pool = THERMAL_DEFECTS if effective_modality == "thermal" else RGB_DEFECTS
    count = rng.choices([0, 1, 2, 3, 4], weights=[20, 35, 25, 15, 5])[0]
    detections = []

    for _ in range(count):
        defect = rng.choice(defect_pool)
        bw = int(img_width  * rng.uniform(0.08, 0.22))
        bh = int(img_height * rng.uniform(0.08, 0.20))
        bx = int(rng.uniform(0.05, 0.85) * img_width)
        by = int(rng.uniform(0.05, 0.80) * img_height)
        bx = min(bx, max(0, img_width  - bw))
        by = min(by, max(0, img_height - bh))
        sim_conf = round(rng.uniform(0.78, 0.97), 2)

        detections.append({
            "label":      defect["label"],
            "color":      defect["color"],
            "confidence": sim_conf,
            "severity":   compute_severity(defect["label"], sim_conf),
            "x": bx, "y": by, "w": bw, "h": bh,
            "cx": bx + bw // 2,
            "cy": by + bh // 2,
        })

    return detections


def detect_and_number_panels_yolo(image_path: str, model_path: str = None, conf: float = 0.25, save_output_path: str = None):
    """
    Implements panel detection and row-wise numbering matching Google Colab:
    1. Runs YOLOv8 inference if model weights exist.
    2. Calculates center coordinates: cx = (x1 + x2) / 2, cy = (y1 + y2) / 2.
    3. Groups panels into rows by vertical proximity.
    4. Sorts panels within each row left-to-right (x).
    5. Assigns sequential panel_id starting from 1.
    6. Draws red numbers using OpenCV cv2.putText.
    """
    if model_path is None:
        model_path = MODEL_PATH

    boxes = []

    # 1. Try real YOLO inference if model exists
    if os.path.exists(model_path):
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
            results = model.predict(image_path, imgsz=640, conf=conf, verbose=False)
            for r in results:
                if not hasattr(r, "boxes") or r.boxes is None:
                    continue
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
