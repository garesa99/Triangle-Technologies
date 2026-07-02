"""SENSOR-SPECIFIC module — isolated on purpose.

Friend-or-foe by Remote ID. A drone that is PHYSICALLY detected (acoustic/RF) but has NO
matching Remote ID broadcast nearby in time+space is *uncooperative* — the whole point of
the system. The generic association/scoring code never imports sensor names; it calls in here.
"""
from __future__ import annotations

from typing import Optional

from .geo import haversine_m
from .util import epoch_s

# A physical detection is considered "explained" by a cooperative broadcast if a remote_id
# detection sits within these bounds of it.
MATCH_TIME_S = 8.0
MATCH_RANGE_M = 1500.0


def is_remote_id(sensor_type: str) -> bool:
    return sensor_type == "remote_id"


def is_physical(sensor_type: str) -> bool:
    """A signature the drone cannot suppress (i.e. not a cooperative broadcast)."""
    return sensor_type in ("acoustic", "rf24", "rf58", "seismic", "magnetometer")


def remoteid_position(payload: Optional[dict]) -> Optional[tuple[float, float]]:
    if not payload:
        return None
    lat = payload.get("lat") or payload.get("latitude")
    lon = payload.get("lon") or payload.get("longitude")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def classify_cooperative(detections: list[dict]) -> dict:
    """Given the detections in one associated event (as dicts), decide cooperative vs
    uncooperative and return the evidence. `detections` rows carry sensor_type, observed_at,
    lat/lon, remote_id_payload."""
    rid = [d for d in detections if is_remote_id(d["sensor_type"])]
    phys = [d for d in detections if is_physical(d["sensor_type"])]

    cooperative = False
    matched_serial = None
    if rid and phys:
        for r in rid:
            rp = remoteid_position(r.get("remote_id_payload"))
            for p in phys:
                dt = abs(epoch_s(r["observed_at"]) - epoch_s(p["observed_at"]))
                if dt > MATCH_TIME_S:
                    continue
                if rp is not None:
                    d = haversine_m(rp[0], rp[1], p["lat"], p["lon"])
                    if d > MATCH_RANGE_M:
                        continue
                cooperative = True
                pl = r.get("remote_id_payload") or {}
                matched_serial = pl.get("uas_id") or pl.get("serial") or pl.get("id")
                break
            if cooperative:
                break
    elif rid and not phys:
        cooperative = True  # broadcasting, nothing physical -> friendly/cooperative
        pl = rid[0].get("remote_id_payload") or {}
        matched_serial = pl.get("uas_id") or pl.get("serial") or pl.get("id")

    return {
        "cooperative": cooperative,
        "matched_serial": matched_serial,
        "has_physical": bool(phys),
        "has_remote_id": bool(rid),
        # uncooperative when we have a physical hit and NO matching broadcast
        "uncooperative": bool(phys) and not cooperative,
    }
