"""Validate images and preserve their original dimensions and EXIF orientation."""
from PIL import Image, ImageOps, UnidentifiedImageError


def load_image(path):
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).copy()
            image.load()
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise ValueError(f"Invalid or corrupted image: {exc}") from exc
    if image.width < 1 or image.height < 1:
        raise ValueError("Image has invalid dimensions")
    metadata = {"width": image.width, "height": image.height, "format": image.format,
                "mode": image.mode, "bands": list(image.getbands())}
    try:
        exif = image.getexif()
        for tag, key in ((271, "cameraMake"), (272, "cameraModel"), (306, "capturedAt")):
            if exif.get(tag):
                metadata[key] = str(exif.get(tag))
        gps = exif.get_ifd(34853)
        if gps:
            def degrees(value):
                parts = [float(x) for x in value]
                return parts[0] + parts[1] / 60 + parts[2] / 3600
            lat = degrees(gps[2]) if 2 in gps else None
            lon = degrees(gps[4]) if 4 in gps else None
            if lat is not None and gps.get(1) == "S": lat = -lat
            if lon is not None and gps.get(3) == "W": lon = -lon
            if lat is not None and lon is not None:
                metadata["gps"] = {"latitude": lat, "longitude": lon}
    except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
        # EXIF is optional and frequently incomplete on drone exports.
        pass
    return image, metadata
