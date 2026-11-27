"""End-to-end panel mapping pipeline orchestrating postprocessing, clustering, and numbering."""
from math import degrees
from .column_clustering import cluster_columns_in_region
from .numbering import assign_panel_identities, reidentify_panels_across_images
from .orientation import segment_array_regions
from .panel_postprocessing import postprocess_panel_detections
from .row_clustering import cluster_rows_in_region


def map_image_panels(
    payload_or_detections,
    *,
    image_width=None,
    image_height=None,
    image_id=None,
    image_scope=None,
    target_classes=None,
    target_class_ids=None,
    min_confidence=0.25,
    iou_threshold=0.55,
):
    """Run panel validation, duplicate suppression, multi-region clustering, and numbering."""
    post = postprocess_panel_detections(
        payload_or_detections,
        image_width=image_width,
        image_height=image_height,
        image_id=image_id,
        target_classes=target_classes,
        target_class_ids=target_class_ids,
        min_confidence=min_confidence,
        iou_threshold=iou_threshold,
    )
    panels = post["panels"]
    resolved_image_id = post["image_id"] or image_id
    if not panels:
        return {
            "status": "COMPLETED",
            "image_id": resolved_image_id,
            "image_size": post["image_size"],
            "panels": [],
            "regions": [],
            "quality": {
                "postprocessing": post["diagnostics"],
                "clustering": {
                    "region_count": 0,
                    "row_count": 0,
                    "column_count": 0,
                    "estimated_missing_slots": 0,
                    "assigned_ratio": 0.0,
                },
            },
        }

    regions = segment_array_regions(panels)
    mapped_panels = []
    region_summaries = []
    global_row_offset = 0
    total_missing_slots = 0

    for region_idx, region_panels in enumerate(regions, start=1):
        rows, row_info = cluster_rows_in_region(region_panels)
        col_info = cluster_columns_in_region(rows, theta=row_info["theta"])
        total_missing_slots += col_info["estimated_missing_slots"]
        for local_row_idx, row in enumerate(rows, start=1):
            row_id = global_row_offset + local_row_idx
            for col_idx, p in enumerate(row["items"], start=1):
                p["region_id"] = region_idx
                p["row_id"] = row_id
                p["grid_row_id"] = global_row_offset + row["grid_row_index"]
                p["column_id"] = col_idx
                p["region_orientation_degrees"] = round(degrees(row_info["theta"]), 3)
                mapped_panels.append(p)
        region_summaries.append({
            "region_id": region_idx,
            "panel_count": len(region_panels),
            "row_count": len(rows),
            "column_count": col_info["column_count"],
            "grid_column_count": col_info["grid_column_count"],
            "orientation_degrees": round(degrees(row_info["theta"]), 3),
            "row_pitch_px": row_info["row_pitch"],
            "column_pitch_px": col_info["column_pitch"],
            "row_spacing_cv": row_info["row_spacing_cv"],
            "column_spacing_cv": col_info["column_spacing_cv"],
            "estimated_missing_slots": col_info["estimated_missing_slots"],
        })
        global_row_offset += len(rows)

    assign_panel_identities(mapped_panels, image_id=resolved_image_id, image_scope=image_scope)

    assigned = sum(1 for p in mapped_panels if p.get("row_id") and p.get("column_id"))
    return {
        "status": "COMPLETED",
        "image_id": resolved_image_id,
        "image_size": post["image_size"],
        "panels": mapped_panels,
        "regions": region_summaries,
        "quality": {
            "postprocessing": post["diagnostics"],
            "clustering": {
                "region_count": len(region_summaries),
                "row_count": global_row_offset,
                "column_count": sum(r["column_count"] for r in region_summaries),
                "estimated_missing_slots": total_missing_slots,
                "assigned_ratio": round(assigned / len(mapped_panels), 4),
            },
        },
    }


def map_project_panels(image_results_by_id, registrations=None):
    """Aggregate mapped image panels and run verified cross-image re-identification."""
    panels_by_image = {img_id: res.get("panels", []) for img_id, res in image_results_by_id.items()}
    reid = reidentify_panels_across_images(panels_by_image, registrations)
    return {
        "images": image_results_by_id,
        "reidentification": reid,
    }
