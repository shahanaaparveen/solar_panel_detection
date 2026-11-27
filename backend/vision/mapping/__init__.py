"""Panel geometry, postprocessing, clustering, and deterministic numbering."""
from .geometry import clip_bbox, normalize_polygon, panel_dimensions, panel_record, polygon_area, polygon_centroid
from .panel_postprocessing import assess_panel_quality, postprocess_panel_detections, suppress_duplicate_panels
from .orientation import estimate_region_orientation, segment_array_regions
from .row_clustering import cluster_rows_in_region, map_panel_rows
from .column_clustering import cluster_columns_in_region
from .numbering import assign_panel_identities, reidentify_panels_across_images
from .mapping_service import map_image_panels, map_project_panels

__all__ = [
    "assess_panel_quality",
    "assign_panel_identities",
    "clip_bbox",
    "cluster_columns_in_region",
    "cluster_rows_in_region",
    "estimate_region_orientation",
    "map_image_panels",
    "map_panel_rows",
    "map_project_panels",
    "normalize_polygon",
    "panel_dimensions",
    "panel_record",
    "polygon_area",
    "polygon_centroid",
    "postprocess_panel_detections",
    "reidentify_panels_across_images",
    "segment_array_regions",
    "suppress_duplicate_panels",
]
