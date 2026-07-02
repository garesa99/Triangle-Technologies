"""Triangle Mesh brain — FastAPI fusion server. Runs fully offline/local."""
from __future__ import annotations

import json
import os
from typing import Any

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import db, fusion
from .auth import require_token, require_token_ws
from .config import settings
from .models import DetectionBatch, NodeManifest, SCHEMA_VERSION
from .util import now_iso
from .ws import hub


@asynccontextmanager
async def lifespan(app: FastAPI):
    path = settings.db_path if settings.db_path == ":memory:" else os.path.abspath(settings.db_path)
    db.init(path)
    yield


app = FastAPI(title="Triangle Mesh Brain", version="0.1.0", lifespan=lifespan)

# The operator UI is served from a different origin in dev; it only ever uses the bearer token.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# --------------------------------------------------------------------------- registration
@app.post("/register", dependencies=[Depends(require_token)])
def register(manifest: NodeManifest) -> dict[str, Any]:
    if manifest.schema_version != SCHEMA_VERSION:
        raise HTTPException(422, f"schema_version mismatch: node={manifest.schema_version} brain={SCHEMA_VERSION}")
    existing = db.query_one("SELECT registered_at FROM nodes WHERE node_id=?", (manifest.node_id,))
    reg_at = existing["registered_at"] if existing else now_iso()
    db.execute(
        """INSERT INTO nodes (node_id, agent_version, lat, lon, alt_m, sensors_json, registered_at, last_seen)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(node_id) DO UPDATE SET
             agent_version=excluded.agent_version, lat=excluded.lat, lon=excluded.lon,
             alt_m=excluded.alt_m, sensors_json=excluded.sensors_json, last_seen=excluded.last_seen""",
        (manifest.node_id, manifest.agent_version, manifest.position.lat, manifest.position.lon,
         manifest.position.alt_m, json.dumps([s.model_dump() for s in manifest.sensors]), reg_at, now_iso()),
    )
    return {"ok": True, "node_id": manifest.node_id, "schema_version": SCHEMA_VERSION}


# --------------------------------------------------------------------------- ingest
async def _ingest(batch: DetectionBatch) -> dict[str, Any]:
    inserted = 0
    seen_nodes: set[str] = set()
    for d in batch.detections:
        if d.schema_version != SCHEMA_VERSION:
            raise HTTPException(422, f"detection schema_version {d.schema_version} != brain {SCHEMA_VERSION}")
        cur = db.execute(
            """INSERT OR IGNORE INTO detections
               (detection_id, node_id, sensor_type, observed_at, pps_precise, signature_class,
                confidence, bearing_deg, bearing_uncertainty_deg, signal_level, remote_id_payload,
                raw_features, lat, lon, alt_m, time_source, schema_version, relayed_via, received_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d.detection_id, d.node_id, d.sensor_type, d.observed_at, int(d.pps_precise),
             d.signature_class, d.confidence, d.bearing_deg, d.bearing_uncertainty_deg,
             d.signal_level, db.j(d.remote_id_payload), db.j(d.raw_features),
             d.node_position.lat, d.node_position.lon, d.node_position.alt_m,
             d.time_source, d.schema_version, d.relayed_via, now_iso()),
        )
        inserted += cur.rowcount
        seen_nodes.add(d.node_id)
    for nid in seen_nodes:
        db.execute("UPDATE nodes SET last_seen=? WHERE node_id=?", (now_iso(), nid))

    result = fusion.process_recent()
    if result["tracks"]:
        await hub.broadcast("tracks", result["tracks"])
    if result["alerts"]:
        await hub.broadcast("alerts", result["alerts"])
    if seen_nodes:
        await hub.broadcast("nodes", _nodes_payload())
    return {"ok": True, "inserted": inserted, "received": len(batch.detections),
            "tracks_changed": len(result["tracks"]), "alerts_changed": len(result["alerts"])}


@app.post("/detections", dependencies=[Depends(require_token)])
async def detections(batch: DetectionBatch) -> dict[str, Any]:
    return await _ingest(batch)


@app.post("/relay", dependencies=[Depends(require_token)])
async def relay(batch: DetectionBatch) -> dict[str, Any]:
    """Store-and-forward entry point — same as /detections; rows already carry relayed_via."""
    return await _ingest(batch)


# --------------------------------------------------------------------------- reads
def _nodes_payload() -> list[dict[str, Any]]:
    out = []
    for r in db.query("SELECT * FROM nodes"):
        stale = _is_stale(r["last_seen"])
        out.append({
            "node_id": r["node_id"], "agent_version": r["agent_version"],
            "position": {"lat": r["lat"], "lon": r["lon"], "alt_m": r["alt_m"]},
            "sensors": db.loads(r["sensors_json"]) or [],
            "last_seen": r["last_seen"], "online": not stale,
            "health": db.loads(r["last_health"]),
        })
    return out


def _is_stale(last_seen: str | None) -> bool:
    if not last_seen:
        return True
    from .util import epoch_s
    return (epoch_s(now_iso()) - epoch_s(last_seen)) > settings.node_stale_after_s


@app.get("/nodes", dependencies=[Depends(require_token)])
def nodes() -> list[dict[str, Any]]:
    return _nodes_payload()


@app.post("/nodes/{node_id}/health", dependencies=[Depends(require_token)])
async def node_health(node_id: str, health: dict[str, Any]) -> dict[str, Any]:
    """Node heartbeat carrying GNSS/PPS lock, neighbors seen, jam/spoof state. Updates
    last_seen (online) and last_health (rendered in the UI node strip)."""
    if not db.query_one("SELECT node_id FROM nodes WHERE node_id=?", (node_id,)):
        raise HTTPException(404, "unknown node — register first")
    db.execute("UPDATE nodes SET last_seen=?, last_health=? WHERE node_id=?",
               (now_iso(), db.j(health), node_id))
    await hub.broadcast("nodes", _nodes_payload())
    return {"ok": True}


@app.get("/tracks", dependencies=[Depends(require_token)])
def tracks() -> list[dict[str, Any]]:
    out = []
    for r in db.query("SELECT * FROM tracks WHERE state='active' ORDER BY last_seen DESC"):
        t = dict(r)
        for k in ("node_ids", "sensor_types", "relay_path", "threat_breakdown"):
            t[k] = db.loads(t[k])
        t["cooperative"] = bool(t["cooperative"])
        out.append(t)
    return out


@app.get("/detections/{detection_id}", dependencies=[Depends(require_token)])
def detection(detection_id: str) -> dict[str, Any]:
    r = db.query_one("SELECT * FROM detections WHERE detection_id=?", (detection_id,))
    if not r:
        raise HTTPException(404, "not found")
    d = dict(r)
    d["remote_id_payload"] = db.loads(d["remote_id_payload"])
    d["raw_features"] = db.loads(d["raw_features"])
    d["pps_precise"] = bool(d["pps_precise"])
    return d


# --------------------------------------------------------------------------- alerts
@app.get("/alerts", dependencies=[Depends(require_token)])
def alerts() -> list[dict[str, Any]]:
    out = []
    for r in db.query("SELECT * FROM alerts ORDER BY created_at DESC"):
        a = dict(r)
        a["evidence"] = db.loads(a["evidence"])
        out.append(a)
    return out


@app.post("/alerts/{alert_id}/ack", dependencies=[Depends(require_token)])
async def ack(alert_id: str) -> dict[str, Any]:
    return await _set_alert_state(alert_id, "acknowledged")


@app.post("/alerts/{alert_id}/close", dependencies=[Depends(require_token)])
async def close(alert_id: str) -> dict[str, Any]:
    return await _set_alert_state(alert_id, "closed")


async def _set_alert_state(alert_id: str, state: str) -> dict[str, Any]:
    r = db.query_one("SELECT * FROM alerts WHERE alert_id=?", (alert_id,))
    if not r:
        raise HTTPException(404, "alert not found")
    db.execute("UPDATE alerts SET state=?, updated_at=? WHERE alert_id=?", (state, now_iso(), alert_id))
    await hub.broadcast("alerts", [{"alert_id": alert_id, "track_id": r["track_id"], "state": state,
                                    "threat_score": r["threat_score"], "evidence": db.loads(r["evidence"])}])
    return {"ok": True, "alert_id": alert_id, "state": state}


# --------------------------------------------------------------------------- geofences
@app.get("/geofences", dependencies=[Depends(require_token)])
def geofences() -> list[dict[str, Any]]:
    return [{"id": r["id"], "name": r["name"], "kind": r["kind"],
             "polygon": db.loads(r["polygon_json"])} for r in db.query("SELECT * FROM geofences")]


@app.post("/geofences", dependencies=[Depends(require_token)])
def create_geofence(body: dict[str, Any]) -> dict[str, Any]:
    import hashlib
    gid = body.get("id") or "gf-" + hashlib.sha1(json.dumps(body.get("polygon")).encode()).hexdigest()[:10]
    db.execute("INSERT OR REPLACE INTO geofences (id, name, kind, polygon_json, created_at) VALUES (?,?,?,?,?)",
               (gid, body.get("name", "zone"), body.get("kind", "protected"), db.j(body["polygon"]), now_iso()))
    return {"ok": True, "id": gid}


@app.delete("/geofences/{gid}", dependencies=[Depends(require_token)])
def delete_geofence(gid: str) -> dict[str, Any]:
    db.execute("DELETE FROM geofences WHERE id=?", (gid,))
    return {"ok": True}


# --------------------------------------------------------------------------- health + ws
@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "schema_version": SCHEMA_VERSION, "service": "triangle-brain"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    token = ws.query_params.get("token", "")
    if not require_token_ws(token):
        await ws.close(code=4401)
        return
    await hub.connect(ws)
    # initial snapshot so a fresh client is immediately consistent
    await ws.send_text(json.dumps({"type": "snapshot", "data": {
        "nodes": _nodes_payload(), "tracks": tracks(), "alerts": alerts(),
        "geofences": geofences(),
    }}))
    try:
        while True:
            await ws.receive_text()  # UI is read-only over WS; ignore inbound
    except WebSocketDisconnect:
        await hub.disconnect(ws)
