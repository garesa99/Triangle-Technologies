"""Decomposable threat score. NEVER a bare number — every factor is stored and shown.

Model: signature_confidence is the BASE in [0,1]. The other factors are MULTIPLIERS that
default to 1.0 (neutral) when the information is unknown, so absence of a geofence or heading
never silently deflates the score. The product is clamped to [0,1].

  score = clamp( signature_confidence
                 × corroboration_bonus   (>=1, more independent nodes/sensors)
                 × uncooperative_bonus   (1.0 cooperative, >1 when physical & no Remote ID)
                 × geofence_proximity    (1.0 far/unknown, >1 near a protected zone)
                 × approach_vector )     (1.0 unknown, >1 heading toward the zone)
"""
from __future__ import annotations

import math
from typing import Any, Optional

CORROB_MAX = 1.6
UNCOOP_BONUS = 1.6
GEOFENCE_MAX = 1.5
APPROACH_MAX = 1.3


def _point_to_polygon_m(lat: float, lon: float, poly: list[list[float]]) -> float:
    """Approx distance (m) from point to polygon boundary; 0 if inside. poly: [[lat,lon],...]."""
    def seg_dist(px, py, ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        yi, xi = poly[i]
        yj, xj = poly[j]
        if ((xi > lon) != (xj > lon)) and (lat < (yj - yi) * (lon - xi) / (xj - xi) + yi):
            inside = not inside
        j = i
    if inside:
        return 0.0
    best = min(
        seg_dist(lat, lon, poly[i][0], poly[i][1],
                 poly[(i + 1) % len(poly)][0], poly[(i + 1) % len(poly)][1])
        for i in range(len(poly))
    ) * 111_000  # deg -> m rough (local)
    return best


def score_track(
    *,
    signature_confidence: float,
    n_nodes: int,
    n_sensor_types: int,
    uncooperative: bool,
    lat: Optional[float],
    lon: Optional[float],
    heading_deg: Optional[float],
    geofences: list[dict],
) -> dict[str, Any]:
    corroboration_bonus = min(CORROB_MAX, 1.0 + 0.15 * (n_nodes - 1) + 0.1 * (n_sensor_types - 1))
    uncooperative_bonus = UNCOOP_BONUS if uncooperative else 1.0

    geofence_proximity = 1.0
    approach_vector = 1.0
    nearest = None
    if lat is not None and lon is not None and geofences:
        dists = []
        for g in geofences:
            poly = g.get("polygon") or g.get("polygon_json") or []
            if poly:
                dists.append((_point_to_polygon_m(lat, lon, poly), g))
        if dists:
            d, g = min(dists, key=lambda x: x[0])
            poly = g.get("polygon") or []
            nearest = {"name": g.get("name"), "distance_m": round(d, 1)}
            # closer -> higher, saturating at 2 km; inside -> full bonus
            geofence_proximity = 1.0 + (GEOFENCE_MAX - 1.0) * max(0.0, 1.0 - d / 2000.0)
            if heading_deg is not None and poly:
                cy = sum(p[0] for p in poly) / len(poly)
                cx = sum(p[1] for p in poly) / len(poly)
                brg_to_zone = (math.degrees(math.atan2(cx - lon, cy - lat)) + 360) % 360
                diff = abs((brg_to_zone - heading_deg + 180) % 360 - 180)
                approach_vector = 1.0 + (APPROACH_MAX - 1.0) * max(0.0, 1.0 - diff / 180.0)

    factors = {
        "signature_confidence": round(signature_confidence, 3),
        "corroboration_bonus": round(corroboration_bonus, 3),
        "uncooperative_bonus": round(uncooperative_bonus, 3),
        "geofence_proximity": round(geofence_proximity, 3),
        "approach_vector": round(approach_vector, 3),
    }
    raw = 1.0
    for v in factors.values():
        raw *= v
    return {
        "score": round(min(1.0, raw), 4),
        "factors": factors,
        "nearest_geofence": nearest,
    }
