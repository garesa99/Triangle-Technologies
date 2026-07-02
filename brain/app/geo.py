"""Geodesy helpers. Local-tangent-plane (ENU) math — good to a few km, which is well
beyond any acoustic/RF detection range, so a flat-earth local frame is honest here."""
from __future__ import annotations

import math
from typing import Optional

R_EARTH = 6_378_137.0  # WGS-84 equatorial radius (m)


def enu_from_ll(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    """Return (east_m, north_m) of (lat,lon) relative to a reference point."""
    dlat = math.radians(lat - ref_lat)
    dlon = math.radians(lon - ref_lon)
    north = dlat * R_EARTH
    east = dlon * R_EARTH * math.cos(math.radians(ref_lat))
    return east, north


def ll_from_enu(east: float, north: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    lat = ref_lat + math.degrees(north / R_EARTH)
    lon = ref_lon + math.degrees(east / (R_EARTH * math.cos(math.radians(ref_lat))))
    return lat, lon


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH * math.asin(math.sqrt(a))


def bearing_unit(bearing_deg: float) -> tuple[float, float]:
    """Bearing (deg from true north, clockwise) -> (east, north) unit vector."""
    r = math.radians(bearing_deg)
    return math.sin(r), math.cos(r)


def intersect_bearings(
    rays: list[tuple[float, float, float]], ref_lat: float, ref_lon: float
) -> Optional[tuple[float, float, float]]:
    """Least-squares intersection of bearing rays.

    rays: list of (node_lat, node_lon, bearing_deg).
    Returns (lat, lon, rms_residual_m) or None if geometry is degenerate (near-parallel).
    Each ray is the line through node point p with direction d; we minimise the sum of
    squared perpendicular distances: sum |(x - p) - ((x - p)·d) d|^2.
    """
    if len(rays) < 2:
        return None
    A = [[0.0, 0.0], [0.0, 0.0]]
    b = [0.0, 0.0]
    for lat, lon, brg in rays:
        px, py = enu_from_ll(lat, lon, ref_lat, ref_lon)
        dx, dy = bearing_unit(brg)
        # Projector onto the normal of the ray: I - d d^T
        nxx, nxy, nyy = 1 - dx * dx, -dx * dy, 1 - dy * dy
        A[0][0] += nxx
        A[0][1] += nxy
        A[1][0] += nxy
        A[1][1] += nyy
        b[0] += nxx * px + nxy * py
        b[1] += nxy * px + nyy * py
    det = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    if abs(det) < 1e-6:
        return None  # near-parallel rays -> no honest fix
    x = (A[1][1] * b[0] - A[0][1] * b[1]) / det
    y = (A[0][0] * b[1] - A[1][0] * b[0]) / det
    # RMS perpendicular residual
    sq = 0.0
    for lat, lon, brg in rays:
        px, py = enu_from_ll(lat, lon, ref_lat, ref_lon)
        dx, dy = bearing_unit(brg)
        ex, ey = x - px, y - py
        proj = ex * dx + ey * dy
        perp = math.hypot(ex - proj * dx, ey - proj * dy)
        sq += perp * perp
    rms = math.sqrt(sq / len(rays))
    lat_o, lon_o = ll_from_enu(x, y, ref_lat, ref_lon)
    return lat_o, lon_o, rms


def weighted_centroid(
    points: list[tuple[float, float, float]]
) -> tuple[float, float, float]:
    """points: (lat, lon, weight). Returns (lat, lon, spread_m) where spread is the
    weighted RMS distance of contributing nodes from the centroid (an honest ellipse size)."""
    wsum = sum(w for _, _, w in points) or 1.0
    lat = sum(la * w for la, _, w in points) / wsum
    lon = sum(lo * w for _, lo, w in points) / wsum
    var = sum(w * haversine_m(la, lo, lat, lon) ** 2 for la, lo, w in points) / wsum
    return lat, lon, math.sqrt(var)


def tdoa_multilaterate(
    anchors: list[tuple[float, float, float]], ref_lat: float, ref_lon: float,
    c: float = 343.0, iters: int = 30,
) -> Optional[tuple[float, float, float]]:
    """TDOA multilateration by Gauss-Newton in the local ENU plane.

    anchors: (lat, lon, toa_seconds) — absolute arrival time at each node, only valid when
    every contributing detection is GNSS-PPS disciplined (checked by the caller).
    Uses time DIFFERENCES relative to anchor 0 (unknown emit time cancels).
    Returns (lat, lon, residual_m) or None if it fails to converge / geometry degenerate.
    """
    if len(anchors) < 3:
        return None
    pts = [(enu_from_ll(la, lo, ref_lat, ref_lon), t) for la, lo, t in anchors]
    (x0, y0), t0 = pts[0]
    # initial guess: centroid of anchors
    x = sum(p[0][0] for p in pts) / len(pts)
    y = sum(p[0][1] for p in pts) / len(pts)
    for _ in range(iters):
        JtJ = [[0.0, 0.0], [0.0, 0.0]]
        Jtr = [0.0, 0.0]
        r0 = math.hypot(x - x0, y - y0)
        if r0 < 1e-6:
            r0 = 1e-6
        for (xi, yi), ti in pts[1:]:
            ri = math.hypot(x - xi, y - yi)
            if ri < 1e-6:
                ri = 1e-6
            pred = ri - r0                      # predicted range difference
            meas = c * (ti - t0)                # measured range difference
            res = pred - meas
            # gradient of (ri - r0) wrt (x,y)
            gx = (x - xi) / ri - (x - x0) / r0
            gy = (y - yi) / ri - (y - y0) / r0
            JtJ[0][0] += gx * gx
            JtJ[0][1] += gx * gy
            JtJ[1][0] += gx * gy
            JtJ[1][1] += gy * gy
            Jtr[0] += gx * res
            Jtr[1] += gy * res
        det = JtJ[0][0] * JtJ[1][1] - JtJ[0][1] * JtJ[1][0]
        if abs(det) < 1e-9:
            return None
        dx = -(JtJ[1][1] * Jtr[0] - JtJ[0][1] * Jtr[1]) / det
        dy = -(JtJ[0][0] * Jtr[1] - JtJ[1][0] * Jtr[0]) / det
        x += dx
        y += dy
        if math.hypot(dx, dy) < 0.5:
            break
    # residual
    r0 = math.hypot(x - x0, y - y0)
    sq = 0.0
    for (xi, yi), ti in pts[1:]:
        ri = math.hypot(x - xi, y - yi)
        res = (ri - r0) - c * (ti - t0)
        sq += res * res
    resid = math.sqrt(sq / max(1, len(pts) - 1))
    lat_o, lon_o = ll_from_enu(x, y, ref_lat, ref_lon)
    return lat_o, lon_o, resid
