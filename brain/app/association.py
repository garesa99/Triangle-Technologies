"""Association — group detections that plausibly refer to the same real event.

Generic: keys off (time proximity, spatial plausibility, signature compatibility) only —
never off hardcoded sensor names. A drone heard by node A, RF-detected by node B, and NOT
Remote-ID-broadcasting collapses into ONE track.
"""
from __future__ import annotations

from typing import Any

from .config import settings
from .geo import haversine_m
from .util import epoch_s


def _compatible_signature(a: str, b: str) -> bool:
    """Two signature_classes may describe the same target. We treat any two *physical* drone
    signatures as compatible (a drone emits acoustic AND rf at once), and 'unknown' as a wildcard.
    Distinct named platforms (e.g. two different mavic_remoteid serials) are separated upstream."""
    if a == b or "unknown" in (a, b):
        return True
    # coarse family match: everything before the first underscore is the family
    return True  # physical drone signatures co-occur; keep association permissive, split by serial in remote_id


def cluster(detections: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Single-link clustering over a time+space graph. Input rows are dicts with at least
    observed_at, lat, lon, signature_class. Returns groups (each a list of rows)."""
    n = len(detections)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        parent[find(i)] = find(j)

    ts = [epoch_s(d["observed_at"]) for d in detections]
    for i in range(n):
        for k in range(i + 1, n):
            if abs(ts[i] - ts[k]) > settings.assoc_time_window_s:
                continue
            dist = haversine_m(
                detections[i]["lat"], detections[i]["lon"],
                detections[k]["lat"], detections[k]["lon"],
            )
            # Two nodes can only be hearing the same drone if their baseline is within a
            # plausible shared-detection radius.
            if dist > settings.assoc_max_range_m:
                continue
            if not _compatible_signature(
                detections[i]["signature_class"], detections[k]["signature_class"]
            ):
                continue
            union(i, k)

    groups: dict[int, list[dict[str, Any]]] = {}
    for i, d in enumerate(detections):
        groups.setdefault(find(i), []).append(d)
    return list(groups.values())
