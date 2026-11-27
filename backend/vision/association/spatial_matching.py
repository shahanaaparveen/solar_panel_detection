"""Compatibility facade for evidence-based defect-to-panel spatial matching."""
from .centroid_matching import centroid_inside
from .defect_assignment import associate_defect

__all__ = ["associate_defect", "centroid_inside"]
