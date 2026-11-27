"""EXIF, GPS, camera, and drone XMP metadata extraction for image registration and pairing."""
from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt
import re
from PIL import Image, ImageOps

_XMP_FLOAT_TAGS = {
    "AbsoluteAltitude": "altitude_m",
    "RelativeAltitude": "relative_altitude_m",
    "GimbalYawDegree": "gimbal_yaw_deg",
    "GimbalPitchDegree": "gimbal_pitch_deg",
    "GimbalRollDegree": "gimbal_roll_deg",
    "FlightYawDegree": "flight_yaw_deg",
}


def _rational_to_float(val):
    try:
        return float(val)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _extract_xmp_telemetry(raw_bytes):
    telemetry = {}
    start = raw_bytes.find(b"<x:xmpmeta")
    end = raw_bytes.find(b"</x:xmpmeta>")
    if start == -1 or end == -1 or end <= start:
        return telemetry
    xmp_text = raw_bytes[start : end + 12].decode("utf-8", errors="ignore")
    for tag, out_key in _XMP_FLOAT_TAGS.items():
        match = re.search(rf'(?:drone-dji:{tag}|tiff:{tag}|{tag})=["\']?([+-]?\d+(?:\.\d+)?)', xmp_text)
        if not match:
            match = re.search(rf'<[^>]*{tag}[^>]*>\s*([+-]?\d+(?:\.\d+)?)\s*<', xmp_text)
        if match:
            try:
                telemetry[out_key] = float(match.group(1))
            except ValueError:
                pass
    if "thermal" in xmp_text.lower() or "flir" in xmp_text.lower() or "rjpeg" in xmp_text.lower():
        telemetry["thermal_xmp_present"] = True
    return telemetry


def parse_timestamp(value):
    """Parse EXIF or ISO-8601 timestamp string into a UTC-aware datetime, or None."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def haversine_meters(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters between two WGS84 latitude/longitude coordinates."""
    earth_r = 6_371_000.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2.0) ** 2 + cos(p1) * cos(p2) * sin(dl / 2.0) ** 2
    return 2.0 * earth_r * atan2(sqrt(a), sqrt(max(0.0, 1.0 - a)))


def extract_image_metadata(path):
    """Extract camera, timestamp, GPS, and drone XMP telemetry without fabricating missing values."""
    meta = {}
    try:
        with open(path, "rb") as fh:
            head = fh.read(256 * 1024)
        meta.update(_extract_xmp_telemetry(head))
    except OSError:
        pass

    try:
        with Image.open(path) as source:
            img = ImageOps.exif_transpose(source)
            meta["width"] = img.width
            meta["height"] = img.height
            meta["format"] = img.format
            meta["mode"] = img.mode
            exif = img.getexif()
            for tag, key in ((271, "cameraMake"), (272, "cameraModel"), (306, "capturedAt")):
                if exif.get(tag):
                    meta[key] = str(exif.get(tag))
            sub_ifd = exif.get_ifd(34665) if hasattr(exif, "get_ifd") else {}
            if sub_ifd:
                if sub_ifd.get(36867) and "capturedAt" not in meta:
                    meta["capturedAt"] = str(sub_ifd.get(36867))
                if sub_ifd.get(37386):
                    fl = _rational_to_float(sub_ifd.get(37386))
                    if fl is not None:
                        meta["focalLengthMm"] = fl
                if sub_ifd.get(41989):
                    fl35 = _rational_to_float(sub_ifd.get(41989))
                    if fl35 is not None:
                        meta["focalLength35mm"] = fl35
            gps = exif.get_ifd(34853) if hasattr(exif, "get_ifd") else None
            if gps:
                def _deg(vals):
                    parts = [float(x) for x in vals]
                    return parts[0] + parts[1] / 60.0 + parts[2] / 3600.0
                lat = _deg(gps[2]) if 2 in gps else None
                lon = _deg(gps[4]) if 4 in gps else None
                if lat is not None and gps.get(1) == "S":
                    lat = -lat
                if lon is not None and gps.get(3) == "W":
                    lon = -lon
                if lat is not None and lon is not None:
                    gps_obj = {"latitude": lat, "longitude": lon}
                    if 6 in gps:
                        alt = _rational_to_float(gps[6])
                        if alt is not None:
                            gps_obj["altitude"] = -alt if gps.get(5) == 1 else alt
                    meta["gps"] = gps_obj
    except Exception:
        pass
    return meta
