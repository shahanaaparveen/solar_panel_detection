"""Parse YOLO normalized detection and segmentation label rows."""


def parse_yolo_label_line(line, width, height, *, source="label", line_number=1):
    values = line.split()
    if len(values) < 5:
        raise ValueError(f"{source}:{line_number}: expected class and at least four normalized box values")
    try:
        class_id = int(values[0])
        coords = [float(value) for value in values[1:]]
    except ValueError as exc:
        raise ValueError(f"{source}:{line_number}: invalid numeric label value") from exc
    if class_id < 0 or any(value < 0 or value > 1 for value in coords):
        raise ValueError(f"{source}:{line_number}: class must be nonnegative and coordinates normalized to [0,1]")
    if len(coords) > 4:
        if len(coords) % 2:
            raise ValueError(f"{source}:{line_number}: segmentation coordinates must be x/y pairs")
        polygon = [[coords[i] * width, coords[i+1] * height] for i in range(0, len(coords), 2)]
        if len(polygon) < 3:
            raise ValueError(f"{source}:{line_number}: segmentation polygon needs at least three points")
        return {"class_id": class_id,
                "bbox": {"x1": min(p[0] for p in polygon), "y1": min(p[1] for p in polygon),
                         "x2": max(p[0] for p in polygon), "y2": max(p[1] for p in polygon)},
                "polygon": polygon}
    cx, cy, box_width, box_height = coords[:4]
    if box_width <= 0 or box_height <= 0:
        raise ValueError(f"{source}:{line_number}: box width and height must be positive")
    x1 = max(0.0, (cx - box_width/2) * width)
    y1 = max(0.0, (cy - box_height/2) * height)
    x2 = min(float(width), (cx + box_width/2) * width)
    y2 = min(float(height), (cy + box_height/2) * height)
    return {"class_id": class_id, "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}, "polygon": None}
