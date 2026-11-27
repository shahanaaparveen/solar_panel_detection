"""Unit tests for geometry and inspection rules that do not require model weights."""
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vision.association.iou import box_iou
from vision.association.spatial_matching import associate_defect, centroid_inside
from vision.mapping.panel_geometry import panel_record
from vision.mapping.row_clustering import map_panel_rows
from vision.risk.severity_engine import assess_finding
from vision.preprocessing.thermal_metrics import thermal_pixel_metrics
from vision.registration.image_alignment import align_images


def test_iou_uses_intersection_over_union():
    assert box_iou((0, 0, 10, 10), (5, 5, 15, 15)) == 25 / 175
    assert box_iou((0, 0, 1, 1), (2, 2, 3, 3)) == 0


def test_rows_follow_rotated_array_geometry():
    panels = []
    # Two rows at 30 degrees, with three columns in each row.
    import math
    for row in range(2):
        for col in range(3):
            along, across = col * 55, row * 38
            cx = along * math.cos(math.pi/6) - across * math.sin(math.pi/6)
            cy = along * math.sin(math.pi/6) + across * math.cos(math.pi/6)
            panels.append(panel_record((cx-18, cy-9, cx+18, cy+9), 0.9))
    mapped = map_panel_rows(panels)
    assert len({p["row_id"] for p in mapped}) == 2
    assert sorted(p["column_id"] for p in mapped if p["row_id"] == 1) == [1, 2, 3]
    assert all(p["panel_id"].startswith("R") for p in mapped)


def test_defect_assignment_requires_spatial_overlap():
    panels = [panel_record((0, 0, 100, 100), 0.9, "P1")]
    match = associate_defect({"bbox": {"x1": 20, "y1": 20, "x2": 40, "y2": 40}}, panels)
    assert match["match_status"] == "MATCHED"
    assert match["panel_id"] == panels[0]["panel_id"]
    outside = associate_defect({"bbox": {"x1": 150, "y1": 150, "x2": 170, "y2": 170}}, panels)
    assert outside["match_status"] == "UNASSIGNED"


def test_polygon_centroid_containment():
    polygon = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert centroid_inside((5, 5), polygon)
    assert not centroid_inside((15, 5), polygon)


def test_irregular_incomplete_array_keeps_local_row_column_order():
    panels = [panel_record((x, y, x+30, y+18), 0.9)
              for y, xs in ((0, (0, 50, 150)), (45, (0, 100))) for x in xs]
    mapped = map_panel_rows(panels)
    assert len({panel["row_id"] for panel in mapped}) == 2
    assert sorted(panel["column_id"] for panel in mapped if panel["row_id"] == 1) == [1, 2, 3]
    assert sorted(panel["column_id"] for panel in mapped if panel["row_id"] == 2) == [1, 2]


def test_polygon_panel_association_and_ambiguity_are_reviewable():
    polygon = [(0, 0), (100, 0), (80, 80), (10, 100)]
    first = panel_record((0, 0, 100, 100), 0.9, "A", geometry=polygon)
    defect = {"bbox": {"x1": 20, "y1": 20, "x2": 30, "y2": 30}}
    assert associate_defect(defect, [first])["match_status"] == "MATCHED"
    second = panel_record((0, 0, 100, 100), 0.9, "B", geometry=polygon)
    ambiguous = associate_defect(defect, [first, second])
    assert ambiguous["match_status"] == "REVIEW_REQUIRED"
    assert ambiguous["panel_id"] is None
    assert ambiguous["candidate_panel_ids"] == ["A", "B"]


def test_multiple_synthetic_observations_can_share_one_local_panel():
    panel = panel_record((0, 0, 100, 100), 0.9, "IMGimage-1-R01C01")
    defects = [
        {"bbox": {"x1": 10, "y1": 10, "x2": 20, "y2": 20}},
        {"bbox": {"x1": 65, "y1": 65, "x2": 80, "y2": 80}},
    ]
    matches = [associate_defect(defect, [panel]) for defect in defects]
    assert [match["panel_id"] for match in matches] == [panel["panel_id"], panel["panel_id"]]


def test_synthetic_feature_registration_recovers_known_translation(tmp_path):
    import cv2
    import numpy as np
    rng = np.random.default_rng(19)
    reference = np.zeros((512, 512), dtype=np.uint8)
    for _ in range(180):
        center = tuple(map(int, rng.integers(10, 500, size=2)))
        radius = int(rng.integers(2, 12))
        color = int(rng.integers(90, 256))
        cv2.circle(reference, center, radius, color, -1)
    transform = np.float32([[1, 0, 12], [0, 1, -9]])
    moving = cv2.warpAffine(reference, transform, (512, 512))
    reference_path, moving_path = tmp_path / "reference.png", tmp_path / "moving.png"
    Image.fromarray(reference).save(reference_path)
    Image.fromarray(moving).save(moving_path)
    result = align_images(reference_path, moving_path)
    assert result["status"] == "REGISTERED"
    assert result["quality"] >= 0.5
    assert result["mean_reprojection_error_px"] < 2
    assert abs(result["transform"][0][2] + 12) < 2
    assert abs(result["transform"][1][2] - 9) < 2


def test_low_feature_images_remain_unregistered(tmp_path):
    reference, moving = tmp_path / "blank-a.png", tmp_path / "blank-b.png"
    Image.new("L", (128, 128), 0).save(reference)
    Image.new("L", (128, 128), 0).save(moving)
    result = align_images(reference, moving)
    assert result["status"] == "UNREGISTERED"


def test_confidence_does_not_downgrade_severity():
    low = assess_finding("Hotspot", 0.3)
    high = assess_finding("Hotspot", 0.95)
    assert low["severity"] is high["severity"] is None
    assert low["severity_status"] == high["severity_status"] == "UNVALIDATED"
    assert low["inspection_priority"] == high["inspection_priority"] == "High"
    assert low["review_required"]


def test_colorized_thermal_image_is_not_reported_as_radiometric(tmp_path):
    from PIL import Image
    path = tmp_path / "thermal.png"
    Image.new("RGB", (8, 8), (240, 40, 20)).save(path)
    assert thermal_pixel_metrics(path)["status"] == "NOT_RADIOMETRIC"


def test_high_bit_depth_thermal_values_are_not_claimed_as_degrees(tmp_path):
    from PIL import Image
    path = tmp_path / "radiometric.tiff"
    Image.new("I;16", (4, 4), 1234).save(path)
    metrics = thermal_pixel_metrics(path)
    assert metrics["status"] == "RAW_PIXEL_STATISTICS"
    assert metrics["units"] == "pixel_value"
    assert metrics["radiometric_temperature"] is False
