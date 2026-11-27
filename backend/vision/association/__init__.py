"""Spatial association, polygon matching, cross-image deduplication, and panel aggregation."""
from .association_validation import compute_association_score, is_ambiguous_match, validate_defect_geometry
from .centroid_matching import centroid_inside, defect_centroid, normalized_centroid_distance
from .cross_image_dedup import deduplicate_findings_across_images
from .defect_assignment import associate_defect
from .iou import box_area, box_iou, coords, intersection_area
from .panel_aggregation import aggregate_panel_findings
from .polygon_matching import bbox_to_polygon, defect_panel_polygon_metrics, polygon_intersection_area, polygon_iou

__all__ = [
    "aggregate_panel_findings",
    "associate_defect",
    "bbox_to_polygon",
    "box_area",
    "box_iou",
    "centroid_inside",
    "compute_association_score",
    "coords",
    "deduplicate_findings_across_images",
    "defect_centroid",
    "defect_panel_polygon_metrics",
    "intersection_area",
    "is_ambiguous_match",
    "normalized_centroid_distance",
    "polygon_intersection_area",
    "polygon_iou",
    "validate_defect_geometry",
]
