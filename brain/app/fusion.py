"""Fusion engine — the brain's core loop.

On each detection batch: pull the recent detection window, associate into events, localize
each (tiered + PPS-guarded), run friend-or-foe, score threat, upsert tracks, and raise/refresh
alerts. Returns the set of changed tracks + alerts for the websocket to push.

Sensor-agnostic: everything here operates on the generic schema. The only sensor-specific
call is into remote_id (isolated, friend-or-foe).
"""
from __future__ import annotations

import hashlib
from typing import Any

from . import db, localization, remote_id, scoring
from .config import settings
from .geo import haversine_m
from .util import epoch_s, now_iso

# recent window we reconsider on each batch (a bit wider than the assoc window)
FUSION_WINDOW_S = 15.0
# temporal track continuity: a fresh cluster reuses a recent nearby track's id
TRACK_MATCH_TIME_S = 10.0
TRACK_MATCH_DIST_M = 600.0
# a track with no fresh detections is closed (state != active) so the picture stays current
STALE_TTL_S = 20.0


def _row_to_dict(r) -> dict[str, Any]:
    d = dict(r)
    d["remote_id_payload"] = db.loads(d.get("remote_id_payload"))
    d["raw_features"] = db.loads(d.get("raw_features"))
    d["pps_precise"] = bool(d["pps_precise"])
    return d


def _stable_track_id(dets: list[dict]) -> str:
    """Deterministic id from the earliest detection so re-runs converge on the same track."""
    d0 = min(dets, key=lambda d: epoch_s(d["observed_at"]))
    seed = f"{d0['detection_id']}"
    return "trk-" + hashlib.sha1(seed.encode()).hexdigest()[:12]


def _geofences() -> list[dict]:
    out = []
    for r in db.query("SELECT * FROM geofences"):
        out.append({"name": r["name"], "kind": r["kind"], "polygon": db.loads(r["polygon_json"])})
    for z in settings.protected_zones:
        out.append(z)
    return out


def process_recent() -> dict[str, list]:
    """Re-fuse the recent window. Returns {'tracks': [...], 'alerts': [...]} that changed.

    The window is anchored to the most recent detection's observed_at (not wall-clock now),
    so fusion is correct under node/brain clock skew and deterministic for tests."""
    latest = db.query_one("SELECT MAX(observed_at) AS m FROM detections")
    if not latest or not latest["m"]:
        return {"tracks": [], "alerts": []}
    cutoff = epoch_s(latest["m"]) - FUSION_WINDOW_S
    rows = db.query("SELECT * FROM detections WHERE observed_at >= ? ORDER BY observed_at",
                    (_iso_at(cutoff),))
    dets = [_row_to_dict(r) for r in rows]
    if not dets:
        return {"tracks": [], "alerts": []}

    from .association import cluster
    groups = cluster(dets)
    gf = _geofences()
    latest_epoch = epoch_s(latest["m"])
    changed_tracks: list[dict] = []
    changed_alerts: list[dict] = []

    for group in groups:
        foe = remote_id.classify_cooperative(group)
        loc = localization.localize(group)
        # continuity: attach to a recent nearby active track if one exists, else a new id
        track_id = _assign_track_id(group, loc, latest_epoch)

        # history for heading: prior located points of this track + this fix
        hist = [
            (epoch_s(r["observed_at"]), r["lat"], r["lon"])
            for r in db.query(
                "SELECT observed_at, lat, lon FROM detections WHERE track_id=? ORDER BY observed_at", (track_id,))
        ]
        if loc["lat"] is not None:
            hist.append((epoch_s(group[-1]["observed_at"]), loc["lat"], loc["lon"]))
        hdg = localization.heading(hist)

        node_ids = sorted({d["node_id"] for d in group})
        sensor_types = sorted({d["sensor_type"] for d in group})
        relay_path = sorted({d["relayed_via"] for d in group if d.get("relayed_via")})
        # provenance: a track is bench-flagged if ANY contributing detection was a labeled
        # bench-injected test signal — the UI surfaces this so it is never read as live.
        bench = 1 if any((d.get("raw_features") or {}).get("bench_test") for d in group) else 0
        conf = max(d["confidence"] for d in group)
        sig = max(group, key=lambda d: d["confidence"])["signature_class"]

        threat = scoring.score_track(
            signature_confidence=conf,
            n_nodes=len(node_ids),
            n_sensor_types=len(sensor_types),
            uncooperative=foe["uncooperative"],
            lat=loc["lat"], lon=loc["lon"], heading_deg=hdg, geofences=gf,
        )

        first_seen = min(d["observed_at"] for d in group)
        last_seen = max(d["observed_at"] for d in group)

        db.execute(
            """INSERT INTO tracks
               (track_id, first_seen, last_seen, localization, lat, lon, uncertainty_m,
                heading_deg, signature_class, confidence, cooperative, threat_score,
                threat_breakdown, node_ids, sensor_types, relay_path, bench_test, state)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'active')
               ON CONFLICT(track_id) DO UPDATE SET
                 last_seen=excluded.last_seen, localization=excluded.localization,
                 lat=excluded.lat, lon=excluded.lon, uncertainty_m=excluded.uncertainty_m,
                 heading_deg=excluded.heading_deg, signature_class=excluded.signature_class,
                 confidence=excluded.confidence, cooperative=excluded.cooperative,
                 threat_score=excluded.threat_score, threat_breakdown=excluded.threat_breakdown,
                 node_ids=excluded.node_ids, sensor_types=excluded.sensor_types,
                 relay_path=excluded.relay_path, bench_test=excluded.bench_test, state='active'""",
            (track_id, first_seen, last_seen, loc["localization"], loc["lat"], loc["lon"],
             loc["uncertainty_m"], hdg, sig, conf, int(foe["cooperative"]), threat["score"],
             db.j(threat), db.j(node_ids), db.j(sensor_types), db.j(relay_path), bench),
        )
        for d in group:
            db.execute("UPDATE detections SET track_id=? WHERE detection_id=?",
                       (track_id, d["detection_id"]))

        track_obj = _load_track(track_id, loc, foe)
        changed_tracks.append(track_obj)

        # --- alert lifecycle ---
        if threat["score"] >= settings.alert_threshold and not foe["cooperative"]:
            a = _upsert_alert(track_id, threat, loc, foe, node_ids, sensor_types, relay_path)
            if a:
                changed_alerts.append(a)

    # close tracks that have gone quiet so the operator picture reflects only current activity
    db.execute("UPDATE tracks SET state='stale' WHERE state='active' AND last_seen < ?",
               (_iso_at(latest_epoch - STALE_TTL_S),))

    return {"tracks": changed_tracks, "alerts": changed_alerts}


def _assign_track_id(group: list[dict], loc: dict, latest_epoch: float) -> str:
    """Temporal continuity: reuse a recent active track's id when this cluster plausibly
    continues it (nearest fix within a gate, or a shared contributing node for bearing-only),
    else mint a new stable id. Keeps a moving target as ONE track instead of many."""
    cutoff = _iso_at(latest_epoch - TRACK_MATCH_TIME_S)
    rows = db.query(
        "SELECT track_id, lat, lon, node_ids FROM tracks WHERE state='active' AND last_seen >= ?",
        (cutoff,),
    )
    if loc.get("lat") is not None:
        best, best_d = None, TRACK_MATCH_DIST_M
        for r in rows:
            if r["lat"] is None:
                continue
            d = haversine_m(loc["lat"], loc["lon"], r["lat"], r["lon"])
            if d < best_d:
                best, best_d = r["track_id"], d
        if best:
            return best
    else:
        gnodes = {d["node_id"] for d in group}
        for r in rows:
            if gnodes & set(db.loads(r["node_ids"]) or []):
                return r["track_id"]
    return _stable_track_id(group)


def _upsert_alert(track_id, threat, loc, foe, node_ids, sensor_types, relay_path):
    existing = db.query_one("SELECT * FROM alerts WHERE track_id=? AND state!='closed'", (track_id,))
    evidence = {
        "nodes": node_ids,
        "sensors": sensor_types,
        "localization": loc["localization"],
        "cooperative": foe["cooperative"],
        "uncooperative": foe["uncooperative"],
        "relay_path": relay_path,
        "threat": threat,
        "note": loc.get("note"),
    }
    if existing:
        db.execute("UPDATE alerts SET threat_score=?, evidence=?, updated_at=? WHERE alert_id=?",
                   (threat["score"], db.j(evidence), now_iso(), existing["alert_id"]))
        alert_id = existing["alert_id"]
        state = existing["state"]
    else:
        alert_id = "alt-" + hashlib.sha1(track_id.encode()).hexdigest()[:12]
        db.execute(
            "INSERT OR IGNORE INTO alerts (alert_id, track_id, created_at, state, threat_score, evidence, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (alert_id, track_id, now_iso(), "new", threat["score"], db.j(evidence), now_iso()),
        )
        state = "new"
    return {"alert_id": alert_id, "track_id": track_id, "state": state,
            "threat_score": threat["score"], "evidence": evidence}


def _load_track(track_id: str, loc: dict, foe: dict) -> dict:
    r = db.query_one("SELECT * FROM tracks WHERE track_id=?", (track_id,))
    t = dict(r)
    t["node_ids"] = db.loads(t["node_ids"])
    t["sensor_types"] = db.loads(t["sensor_types"])
    t["relay_path"] = db.loads(t["relay_path"])
    t["threat_breakdown"] = db.loads(t["threat_breakdown"])
    t["cooperative"] = bool(t["cooperative"])
    t["bench_test"] = bool(t.get("bench_test"))
    t["rays"] = loc.get("rays", [])
    t["localization_note"] = loc.get("note")
    t["friend_or_foe"] = foe
    return t


def _iso_at(epoch: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
