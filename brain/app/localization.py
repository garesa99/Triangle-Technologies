"""Tiered, honest localization. The code REFUSES a precise fix without GNSS-PPS.

BEARING_ONLY : 1 node, 1 bearing -> a ray (no fix).
COARSE_FIX   : 2+ concurrent detections -> bearing intersection, else signal-weighted centroid.
               Always reports an uncertainty radius (ellipse), never a bare point.
PRECISE_FIX  : 3+ nodes, ALL pps_precise + time_source==gnss_pps -> TDOA multilateration.
"""
from __future__ import annotations

from typing import Any, Optional

from . import geo
from .config import settings
from .util import epoch_s

BEARING_ONLY = "BEARING_ONLY"
COARSE_FIX = "COARSE_FIX"
PRECISE_FIX = "PRECISE_FIX"


def _distinct_nodes(dets: list[dict]) -> list[str]:
    seen: list[str] = []
    for d in dets:
        if d["node_id"] not in seen:
            seen.append(d["node_id"])
    return seen


def _pps_ok(dets: list[dict]) -> bool:
    """PRECISE requires EVERY contributing row to be GNSS-PPS disciplined."""
    return all(bool(d.get("pps_precise")) and d.get("time_source") == "gnss_pps" for d in dets)


def localize(dets: list[dict]) -> dict[str, Any]:
    """Return {localization, lat, lon, uncertainty_m, rays, note}. lat/lon may be None
    for BEARING_ONLY. `rays` carries bearing rays for the UI to draw."""
    nodes = _distinct_nodes(dets)
    rays = [
        {"node_id": d["node_id"], "lat": d["lat"], "lon": d["lon"],
         "bearing_deg": d["bearing_deg"],
         "bearing_uncertainty_deg": d.get("bearing_uncertainty_deg")}
        for d in dets if d.get("bearing_deg") is not None
    ]
    ref_lat = sum(d["lat"] for d in dets) / len(dets)
    ref_lon = sum(d["lon"] for d in dets) / len(dets)

    # --- PRECISE (TDOA) — only with PPS on 3+ nodes -------------------------------------
    if len(nodes) >= settings.precise_min_nodes and _pps_ok(dets):
        # one arrival time per node (earliest observed for that node)
        per_node: dict[str, dict] = {}
        for d in dets:
            if d["node_id"] not in per_node or epoch_s(d["observed_at"]) < epoch_s(per_node[d["node_id"]]["observed_at"]):
                per_node[d["node_id"]] = d
        anchors = [(v["lat"], v["lon"], epoch_s(v["observed_at"])) for v in per_node.values()]
        res = geo.tdoa_multilaterate(anchors, ref_lat, ref_lon)
        if res is not None:
            lat, lon, resid = res
            return {
                "localization": PRECISE_FIX, "lat": lat, "lon": lon,
                "uncertainty_m": max(15.0, resid), "rays": rays,
                "note": f"TDOA over {len(anchors)} PPS-disciplined nodes",
            }
        # fall through to COARSE if TDOA geometry was degenerate

    # --- COARSE — 2+ nodes ---------------------------------------------------------------
    if len(nodes) >= settings.coarse_min_nodes:
        bearing_nodes = {r["node_id"] for r in rays}
        if len(bearing_nodes) >= 2:
            fix = geo.intersect_bearings(
                [(r["lat"], r["lon"], r["bearing_deg"]) for r in rays], ref_lat, ref_lon
            )
            if fix is not None:
                lat, lon, rms = fix
                return {
                    "localization": COARSE_FIX, "lat": lat, "lon": lon,
                    "uncertainty_m": max(50.0, rms), "rays": rays,
                    "note": "bearing intersection (no PPS -> not precise)",
                }
        # no usable bearings -> signal-weighted centroid of contributing nodes
        pts = [(d["lat"], d["lon"], max(0.05, d["confidence"])) for d in dets]
        lat, lon, spread = geo.weighted_centroid(pts)
        return {
            "localization": COARSE_FIX, "lat": lat, "lon": lon,
            "uncertainty_m": max(150.0, spread), "rays": rays,
            "note": "signal-weighted centroid (no bearings)",
        }

    # --- BEARING_ONLY — single node -----------------------------------------------------
    if rays:
        return {
            "localization": BEARING_ONLY, "lat": None, "lon": None,
            "uncertainty_m": None, "rays": rays, "note": "single node bearing — a ray, not a fix",
        }
    # single node, no bearing: we only know "something near this node"
    d0 = dets[0]
    return {
        "localization": BEARING_ONLY, "lat": None, "lon": None, "uncertainty_m": None,
        "rays": [], "note": f"single-node detection at {d0['node_id']} — direction unknown",
    }


def heading(track_history: list[tuple[float, float, float]]) -> Optional[float]:
    """Estimate heading (deg true north) from the last two located fixes:
    history items are (epoch_s, lat, lon)."""
    fixes = [h for h in track_history if h[1] is not None and h[2] is not None]
    if len(fixes) < 2:
        return None
    (_, la1, lo1), (_, la2, lo2) = fixes[-2], fixes[-1]
    import math
    e, n = geo.enu_from_ll(la2, lo2, la1, lo1)
    if abs(e) < 1e-6 and abs(n) < 1e-6:
        return None
    return (math.degrees(math.atan2(e, n)) + 360) % 360
