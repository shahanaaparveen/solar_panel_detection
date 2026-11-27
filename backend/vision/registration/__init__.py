"""Evidence-gated modality and cross-image registration."""
from .calibration import apply_camera_calibration, resolution_scale_matrix
from .feature_extraction import extract_features, preprocess_for_matching
from .feature_matching import match_descriptors
from .homography import estimate_homography
from .image_alignment import align_images
from .image_pairing import normalize_pair_stem, pair_rgb_thermal_images
from .metadata import extract_image_metadata, haversine_meters, parse_timestamp
from .validation import validate_homography_geometry, validate_registration

__all__ = [
    "align_images",
    "apply_camera_calibration",
    "estimate_homography",
    "extract_features",
    "extract_image_metadata",
    "haversine_meters",
    "match_descriptors",
    "normalize_pair_stem",
    "pair_rgb_thermal_images",
    "parse_timestamp",
    "preprocess_for_matching",
    "resolution_scale_matrix",
    "validate_homography_geometry",
    "validate_registration",
]
