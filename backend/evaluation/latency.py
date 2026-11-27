"""Latency and throughput summaries for completed inference calls."""
from math import ceil


def summarize_latency(milliseconds):
    values = sorted(float(value) for value in milliseconds)
    if not values:
        return {"count": 0, "mean_ms": None, "median_ms": None, "p95_ms": None, "images_per_second": None}
    p95 = values[max(0, ceil(0.95 * len(values)) - 1)]
    mean = sum(values) / len(values)
    total_seconds = sum(values) / 1000
    return {"count": len(values), "mean_ms": mean,
            "median_ms": values[len(values)//2] if len(values) % 2 else (values[len(values)//2-1]+values[len(values)//2])/2,
            "p95_ms": p95, "images_per_second": len(values)/total_seconds if total_seconds else None}
