from __future__ import annotations

import math
from typing import Any


def validate_transformation(metrics: dict[str, Any], *, max_allowed_shift_pixels: float = 10.0, min_valid_overlap_fraction: float = 0.1) -> dict[str, Any]:
    dx = metrics.get("dx")
    dy = metrics.get("dy")
    if dx is None or dy is None:
        return {"accepted": False, "reason": "missing_dx_or_dy", "status": "rejected"}
    if not math.isfinite(float(dx)) or not math.isfinite(float(dy)):
        return {"accepted": False, "reason": "non_finite_shift", "status": "rejected"}
    valid_overlap_fraction = float(metrics.get("valid_overlap_fraction", 0.0))
    valid_overlap_count = int(metrics.get("valid_overlap_count", 0))
    ncc = float(metrics.get("ncc", 0.0))
    if valid_overlap_count <= 0 or valid_overlap_fraction < min_valid_overlap_fraction:
        return {"accepted": False, "reason": "insufficient_overlap", "status": "rejected"}
    if abs(float(dx)) > max_allowed_shift_pixels or abs(float(dy)) > max_allowed_shift_pixels:
        return {"accepted": False, "reason": "shift_exceeds_max_allowed", "status": "rejected"}
    if not math.isfinite(ncc):
        return {"accepted": False, "reason": "non_finite_similarity", "status": "rejected"}
    if ncc < 0.0:
        return {"accepted": False, "reason": "insufficient_similarity", "status": "rejected"}
    return {"accepted": True, "reason": "accepted", "status": "accepted", "ncc": ncc}
