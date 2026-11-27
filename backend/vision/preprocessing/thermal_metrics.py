"""Extract raw pixel statistics only from high-bit-depth single-channel imagery."""
from PIL import Image, ImageOps
from math import isfinite


def thermal_pixel_metrics(path):
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source)
            mode = image.mode
            if mode not in {"I;16", "I;16L", "I;16B", "I", "F"}:
                return {"status": "NOT_RADIOMETRIC", "reason": "Image does not expose high-bit-depth single-channel samples"}
            values = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
            stride = max(1, len(values) // 1_000_000)
            sample = [float(values[i]) for i in range(0, len(values), stride) if isfinite(float(values[i]))]
            if not sample:
                return {"status": "UNAVAILABLE", "reason": "No finite thermal pixel samples"}
            minimum, maximum = min(sample), max(sample)
            return {"status": "RAW_PIXEL_STATISTICS", "units": "pixel_value",
                    "minimum": minimum, "maximum": maximum,
                    "mean": sum(sample) / len(sample), "delta": maximum - minimum,
                    "sample_count": len(sample), "radiometric_temperature": False}
    except (OSError, ValueError, TypeError) as exc:
        return {"status": "UNAVAILABLE", "reason": str(exc)}
