"""Comprehensive unit tests for Track B mapping, registration, association, deduplication, and aggregation."""
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vision.association import (
    aggregate_panel_findings,
    associate_defect,
    box_iou,
    centroid_inside,
    deduplicate_findings_across_images,
    polygon_intersection_area,
    polygon_iou,
)
from vision.mapping import (
    clip_bbox,
    map_image_panels,
    map_panel_rows,
    panel_record,
    postprocess_panel_detections,
    reidentify_panels_across_images,
)
from vision.mapping.coordinate_transform import (
    estimate_array_frame,
    from_local_frame,
    to_local_frame,
    transform_bbox,
    transform_polygon,
)
from vision.registration import (
    align_images,
    pair_rgb_thermal_images,
    validate_homography_geometry,
)
from vision.risk import compute_mapping_quality


def test_bbox_clipping_and_validation():
    clipped, was_clipped = clip_bbox((-15, -5, 120, 80), image_width=100, image_height=70)
    assert was_clipped is True
    assert clipped == {"x1": 0.0, "y1": 0.0, "x2": 100.0, "y2": 70.0}
    assert box_iou(clipped, {"x1": 0, "y1": 0, "x2": 50, "y2": 70}) == 0.5


def test_polygon_intersection_and_concave_polygon_iou():
    rotated_panel = [[10.0, 0.0], [50.0, 20.0], [40.0, 40.0], [0.0, 20.0]]
    defect_box = {"x1": 15.0, "y1": 10.0, "x2": 35.0, "y2": 30.0}
    inter = polygon_intersection_area(defect_box, rotated_panel)
    assert inter > 150.0
    assert 0.0 < polygon_iou(defect_box, rotated_panel) < 1.0

    # L-shaped concave polygon overlapping a square defect inside the inner notch vs arm
    concave = [[0, 0], [60, 0], [60, 20], [20, 20], [20, 60], [0, 60]]
    arm_defect = {"x1": 5, "y1": 30, "x2": 15, "y2": 50}
    notch_defect = {"x1": 30, "y1": 30, "x2": 50, "y2": 50}
    assert polygon_intersection_area(arm_defect, concave) > 150.0
    assert polygon_intersection_area(notch_defect, concave) == 0.0
    assert centroid_inside((10, 40), concave) is True
    assert centroid_inside((40, 40), concave) is False


def test_postprocessing_suppresses_duplicates_and_rejects_invalid_detections():
    payload = {
        "image_id": "img-post",
        "image_width": 200,
        "image_height": 150,
        "detections": [
            {"class_id": 0, "class_name": "solar_panel", "confidence": 0.94, "bbox": {"x1": 10, "y1": 10, "x2": 60, "y2": 40}},
            # Near-duplicate detection of the same panel
            {"class_id": 0, "class_name": "solar_panel", "confidence": 0.72, "bbox": {"x1": 12, "y1": 11, "x2": 59, "y2": 39}},
            # Non-target class filtered when target_classes specified
            {"class_id": 1, "class_name": "roof", "confidence": 0.99, "bbox": {"x1": 0, "y1": 0, "x2": 200, "y2": 150}},
            # Low confidence filtered
            {"class_id": 0, "class_name": "solar_panel", "confidence": 0.1, "bbox": {"x1": 100, "y1": 10, "x2": 150, "y2": 40}},
            # Invalid negative-area / out-of-bounds box rejected
            {"class_id": 0, "class_name": "solar_panel", "confidence": 0.9, "bbox": {"x1": 210, "y1": 10, "x2": 240, "y2": 40}},
        ],
    }
    res = postprocess_panel_detections(payload, target_classes={"solar_panel"}, min_confidence=0.25)
    assert res["diagnostics"]["kept_count"] == 1
    assert res["diagnostics"]["suppressed_duplicates"] == 1
    assert res["diagnostics"]["filtered_non_target"] == 1
    assert res["diagnostics"]["filtered_low_confidence"] == 1
    assert res["diagnostics"]["rejected_count"] == 1


def test_coordinate_frame_roundtrip_and_projective_transforms():
    frame = estimate_array_frame([(10.0, 20.0), (50.0, 60.0)], math.radians(30.0))
    pt = {"x": 42.5, "y": 17.25}
    local = to_local_frame(pt, frame)
    restored = from_local_frame(local, frame)
    assert abs(restored["x"] - pt["x"]) < 1e-6
    assert abs(restored["y"] - pt["y"]) < 1e-6

    mat = [[1.0, 0.0, 15.0], [0.0, 1.0, -5.0], [0.0, 0.0, 1.0]]
    assert transform_bbox({"x1": 10, "y1": 20, "x2": 30, "y2": 40}, mat) == {
        "x1": 25.0, "y1": 15.0, "x2": 45.0, "y2": 35.0
    }
    assert transform_polygon([[0, 0], [10, 0], [10, 10]], mat) == [[15.0, -5.0], [25.0, -5.0], [25.0, 5.0]]


def test_multi_region_rotated_and_missing_panel_clustering():
    detections = []
    # Region 1: 2x3 array rotated +25 deg, with middle panel (row=0, col=1) missing
    theta1 = math.radians(25.0)
    for r in range(2):
        for c in range(3):
            if r == 0 and c == 1:
                continue
            along, across = c * 52.0, r * 36.0
            cx = 100 + along * math.cos(theta1) - across * math.sin(theta1)
            cy = 100 + along * math.sin(theta1) + across * math.cos(theta1)
            poly = [
                [cx - 18 * math.cos(theta1) + 9 * math.sin(theta1), cy - 18 * math.sin(theta1) - 9 * math.cos(theta1)],
                [cx + 18 * math.cos(theta1) + 9 * math.sin(theta1), cy + 18 * math.sin(theta1) - 9 * math.cos(theta1)],
                [cx + 18 * math.cos(theta1) - 9 * math.sin(theta1), cy + 18 * math.sin(theta1) + 9 * math.cos(theta1)],
                [cx - 18 * math.cos(theta1) - 9 * math.sin(theta1), cy - 18 * math.sin(theta1) + 9 * math.cos(theta1)],
            ]
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            detections.append({
                "class_id": 0, "class_name": "solar_panel", "confidence": 0.92,
                "bbox": {"x1": min(xs), "y1": min(ys), "x2": max(xs), "y2": max(ys)},
                "mask": poly,
            })

    # Region 2: separated horizontal 2x2 array far to the right
    for r in range(2):
        for c in range(2):
            cx, cy = 600 + c * 50, 320 + r * 35
            detections.append({
                "class_id": 0, "class_name": "solar_panel", "confidence": 0.90,
                "bbox": {"x1": cx - 18, "y1": cy - 9, "x2": cx + 18, "y2": cy + 9},
            })

    mapped = map_image_panels({"image_id": "site-img-1", "image_width": 900, "image_height": 600, "detections": detections}, image_scope="site-img-1")
    assert mapped["quality"]["clustering"]["region_count"] == 2
    assert len(mapped["panels"]) == 9

    region1_panels = [p for p in mapped["panels"] if p["region_id"] == 1]
    row1 = sorted([p for p in region1_panels if p["row_id"] == 1], key=lambda p: p["column_id"])
    assert len(row1) == 2
    assert row1[0]["column_label"] == "C-01"
    assert row1[1]["column_label"] == "C-03"  # Missing middle panel keeps C-03 alignment!
    assert mapped["regions"][0]["estimated_missing_slots"] >= 1


def test_homography_validation_rejects_degenerate_and_reflected_matrices():
    reflected = np.array([[-1.0, 0.0, 100.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    ok, _reason = validate_homography_geometry(reflected, (100, 100))
    assert ok is False

    tiny_scale = np.array([[0.01, 0.0, 0.0], [0.0, 0.01, 0.0], [0.0, 0.0, 1.0]])
    ok_scale, _ = validate_homography_geometry(tiny_scale, (100, 100))
    assert ok_scale is False

    valid = np.array([[1.0, 0.02, 12.0], [-0.02, 1.0, -8.0], [0.0, 0.0, 1.0]])
    ok_valid, _ = validate_homography_geometry(valid, (100, 100))
    assert ok_valid is True


def test_image_pairing_and_registration_rejection_for_unrelated_images(tmp_path):
    rgb_imgs = [{"imageId": "r1", "imageName": "DJI_0010_W.JPG", "metadata": {"capturedAt": "2026:10:01 10:00:00", "gps": {"latitude": 12.97, "longitude": 77.59}}}]
    thm_imgs = [
        {"imageId": "t1", "imageName": "DJI_0010_T.JPG", "metadata": {"capturedAt": "2026:10:01 10:00:01", "gps": {"latitude": 12.97001, "longitude": 77.59001}}},
        {"imageId": "t2", "imageName": "DJI_0099_T.JPG", "metadata": {"capturedAt": "2026:10:01 12:30:00", "gps": {"latitude": 13.50, "longitude": 78.10}}},
    ]
    pairs = pair_rgb_thermal_images(rgb_imgs, thm_imgs)
    assert len(pairs) == 1
    assert pairs[0]["rgb_image_id"] == "r1"
    assert pairs[0]["thermal_image_id"] == "t1"
    assert "filename_stem" in pairs[0]["signals"]

    # Unrelated synthetic patterns must NOT falsely register
    rng1 = np.random.default_rng(1)
    rng2 = np.random.default_rng(2)
    a = rng1.integers(0, 255, size=(256, 256), dtype=np.uint8)
    b = rng2.integers(0, 255, size=(256, 256), dtype=np.uint8)
    pa, pb = tmp_path / "a.png", tmp_path / "b.png"
    Image.fromarray(a).save(pa)
    Image.fromarray(b).save(pb)
    res = align_images(pa, pb, reference_image_id="r1", moving_image_id="t2")
    assert res["status"] == "UNREGISTERED"


def test_defect_association_handles_unregistered_unassigned_ambiguous_and_polygon_panels():
    poly_a = [[0, 0], [100, 0], [100, 80], [0, 80]]
    poly_b = [[95, 0], [195, 0], [195, 80], [95, 80]]
    panels = [
        panel_record((0, 0, 100, 80), 0.95, "IMG1-R01C01", geometry=poly_a),
        panel_record((95, 0, 195, 80), 0.95, "IMG1-R01C02", geometry=poly_b),
    ]
    matched = associate_defect({"bbox": {"x1": 20, "y1": 20, "x2": 45, "y2": 45}}, panels, registration_quality=0.8, registration_status="REGISTERED")
    assert matched["match_status"] == "MATCHED"
    assert matched["panel_id"] == "IMG1-R01C01"

    unreg = associate_defect({"bbox": {"x1": 20, "y1": 20, "x2": 45, "y2": 45}}, panels, registration_status="UNREGISTERED")
    assert unreg["match_status"] == "UNREGISTERED"
    assert unreg["panel_id"] is None

    unassigned = associate_defect({"bbox": {"x1": 250, "y1": 200, "x2": 280, "y2": 230}}, panels)
    assert unassigned["match_status"] == "UNASSIGNED"
    assert unassigned["panel_id"] is None

    straddling = associate_defect({"bbox": {"x1": 85, "y1": 20, "x2": 110, "y2": 45}}, panels)
    assert straddling["match_status"] == "REVIEW_REQUIRED"
    assert straddling["panel_id"] is None
    assert set(straddling["candidate_panel_ids"]) == {"IMG1-R01C01", "IMG1-R01C02"}


def test_cross_image_reid_dedup_and_panel_aggregation():
    panels_img1 = [
        panel_record((10, 10, 90, 60), 0.95, "IMG1-R01C01"),
        panel_record((110, 10, 190, 60), 0.93, "IMG1-R01C02"),
    ]
    panels_img2 = [
        panel_record((30, 10, 110, 60), 0.94, "IMG2-R01C01"),
    ]
    # Pure x+20 translation from img1 -> img2
    regs = [{
        "source_image_id": "img1",
        "target_image_id": "img2",
        "status": "REGISTERED",
        "transform": [[1.0, 0.0, 20.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "quality": 0.9,
        "mean_reprojection_error_px": 0.4,
    }]
    reid = reidentify_panels_across_images({"img1": panels_img1, "img2": panels_img2}, regs)
    assert reid["status"] == "VERIFIED_REGISTERED"
    assert panels_img1[0]["site_panel_id"] == panels_img2[0]["site_panel_id"]
    assert panels_img1[1]["site_panel_id"] is None
    site_id = panels_img1[0]["site_panel_id"]

    images_by_id = {
        "img1": {"imageId": "img1", "metadata": {"capturedAt": "2026:10:01 10:00:00"}},
        "img2": {"imageId": "img2", "metadata": {"capturedAt": "2026:10:01 10:00:05"}},
        "img3": {"imageId": "img3", "metadata": {"capturedAt": "2026:10:05 10:00:00"}},  # Different date!
    }
    findings = [
        {
            "findingId": "f1", "imageId": "img1", "panelId": "IMG1-R01C01", "sitePanelId": site_id,
            "defectType": "Hotspot", "modality": "thermal", "modelConfidence": 0.91,
            "spatialMatchConfidence": 0.9, "matchStatus": "MATCHED", "inspectionPriority": "High",
            "severity": None, "severityStatus": "UNVALIDATED", "reviewRequired": False,
            "evidence": [{"imageId": "img1", "bbox": {"x1": 30, "y1": 20, "x2": 50, "y2": 40}}],
        },
        # Duplicate observation of same physical hotspot in overlapping img2 (shifted +20 in x)
        {
            "findingId": "f2", "imageId": "img2", "panelId": "IMG2-R01C01", "sitePanelId": site_id,
            "defectType": "Hotspot", "modality": "thermal", "modelConfidence": 0.95,
            "spatialMatchConfidence": 0.92, "matchStatus": "MATCHED", "inspectionPriority": "High",
            "severity": None, "severityStatus": "UNVALIDATED", "reviewRequired": False,
            "evidence": [{"imageId": "img2", "bbox": {"x1": 50, "y1": 20, "x2": 70, "y2": 40}}],
        },
        # Different defect class on the same panel must NOT merge
        {
            "findingId": "f3", "imageId": "img1", "panelId": "IMG1-R01C01", "sitePanelId": site_id,
            "defectType": "Cracked Glass", "modality": "rgb", "modelConfidence": 0.88,
            "spatialMatchConfidence": 0.9, "matchStatus": "MATCHED", "inspectionPriority": "High",
            "severity": None, "severityStatus": "UNVALIDATED", "reviewRequired": False,
            "evidence": [{"imageId": "img1", "bbox": {"x1": 30, "y1": 20, "x2": 50, "y2": 40}}],
        },
        # Observation from a different inspection date must NOT merge with f1
        {
            "findingId": "f4", "imageId": "img3", "panelId": "IMG3-R01C01", "sitePanelId": site_id,
            "defectType": "Hotspot", "modality": "thermal", "modelConfidence": 0.86,
            "spatialMatchConfidence": 0.85, "matchStatus": "MATCHED", "inspectionPriority": "High",
            "severity": None, "severityStatus": "UNVALIDATED", "reviewRequired": False,
            "evidence": [{"imageId": "img3", "bbox": {"x1": 30, "y1": 20, "x2": 50, "y2": 40}}],
        },
    ]

    dedup = deduplicate_findings_across_images(
        findings,
        images_by_id=images_by_id,
        panels_by_image={"img1": panels_img1, "img2": panels_img2},
        pairwise_registrations=regs,
    )
    assert dedup["raw_observation_count"] == 4
    assert dedup["consolidated_count"] == 3
    assert dedup["duplicates_merged"] == 1
    hotspot_merged = next(f for f in dedup["consolidated_findings"] if f["defectType"] == "Hotspot" and f["observationCount"] == 2)
    assert set(hotspot_merged["sourceFindingIds"]) == {"f1", "f2"}

    agg = aggregate_panel_findings(
        {"img1": panels_img1, "img2": panels_img2},
        findings,
        consolidated_findings=dedup["consolidated_findings"][:2],
        image_analysis_statuses={"img1": "COMPLETED", "img2": "COMPLETED"},
    )
    assert agg["summary"]["total_panels"] == 2
    assert agg["summary"]["healthy_panels"] == 1
    assert agg["summary"]["affected_panels"] == 1
    assert agg["summary"]["health_rate"] == 50.0

    quality = compute_mapping_quality(
        panel_results=[{"panels": panels_img1}, {"panels": panels_img2}],
        registrations=regs,
        findings=findings,
        deduplication_report=dedup,
    )
    assert quality["measured_accuracy_status"] == "UNMEASURED_NO_GROUND_TRUTH"
    assert quality["stages"]["registration"]["registered_count"] == 1
    assert quality["stages"]["deduplication"]["duplicates_merged"] == 1
