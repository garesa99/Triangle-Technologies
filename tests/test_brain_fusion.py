"""End-to-end fusion tests against the real brain (FastAPI TestClient, in-memory SQLite).

These are TEST FIXTURES. They exercise association, tiered localization, the PPS guard,
friend-or-foe, threat scoring, and idempotency. They NEVER run against, or feed, the live
operator UI — that is the non-negotiable rule.
"""
import math
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))
os.environ["TRIANGLE_DB"] = ":memory:"
os.environ["TRIANGLE_TOKEN"] = "test-token"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.geo import enu_from_ll  # noqa: E402

H = {"Authorization": "Bearer test-token"}
client = TestClient(app)
client.__enter__()  # fire lifespan startup (db.init) for the whole module

# three nodes forming a triangle around a target (Amsterdam-ish)
NODES = {
    "node-a": (52.3700, 4.8900),
    "node-b": (52.3720, 4.8960),
    "node-c": (52.3680, 4.8965),
}
TARGET = (52.3705, 4.8935)
C_SOUND = 343.0
T0 = datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc)


def bearing_to(node, target):
    e, n = enu_from_ll(target[0], target[1], node[0], node[1])
    return (math.degrees(math.atan2(e, n)) + 360) % 360


def toa(node, target, emit=T0):
    e, n = enu_from_ll(target[0], target[1], node[0], node[1])
    d = math.hypot(e, n)
    return emit + timedelta(seconds=d / C_SOUND)


def det(node_id, sensor, sig, conf, *, bearing=None, when=T0, pps=False,
        time_source="system", rid=None, relayed_via=None):
    lat, lon = NODES[node_id]
    return {
        "detection_id": str(uuid.uuid4()), "node_id": node_id, "sensor_type": sensor,
        "observed_at": when.isoformat(), "pps_precise": pps, "signature_class": sig,
        "confidence": conf, "bearing_deg": bearing,
        "bearing_uncertainty_deg": 5.0 if bearing is not None else None,
        "signal_level": -40.0, "remote_id_payload": rid, "raw_features": {"t": "fixture"},
        "node_position": {"lat": lat, "lon": lon, "alt_m": 2},
        "time_source": time_source, "schema_version": 1, "relayed_via": relayed_via,
    }


def post(dets):
    r = client.post("/detections", json={"detections": dets}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def register_all():
    for nid, (lat, lon) in NODES.items():
        m = {"node_id": nid, "agent_version": "0.1.0",
             "position": {"lat": lat, "lon": lon, "alt_m": 2},
             "sensors": [{"sensor_type": "acoustic", "signature_classes": ["multirotor_acoustic"],
                          "provides_bearing": True, "spec": {"channels": 2}}],
             "schema_version": 1}
        assert client.post("/register", json=m, headers=H).status_code == 200


def active_tracks():
    return client.get("/tracks", headers=H).json()


def test_auth_required():
    assert client.get("/nodes").status_code == 401
    assert client.get("/nodes", headers=H).status_code == 200


def test_registration_and_loadout():
    register_all()
    nodes = client.get("/nodes", headers=H).json()
    assert len(nodes) == 3
    assert nodes[0]["sensors"][0]["sensor_type"] == "acoustic"


def test_bearing_only_single_node():
    _reset()
    when = T0 + timedelta(seconds=100)
    post([det("node-a", "acoustic", "multirotor_acoustic", 0.6,
              bearing=bearing_to(NODES["node-a"], TARGET), when=when)])
    t = _track_in_window(when)
    assert t["localization"] == "BEARING_ONLY"
    assert t["lat"] is None  # a ray, never a fake point


def test_coarse_fix_bearing_intersection():
    _reset()
    when = T0 + timedelta(seconds=200)
    post([
        det("node-a", "acoustic", "multirotor_acoustic", 0.7, bearing=bearing_to(NODES["node-a"], TARGET), when=when),
        det("node-b", "acoustic", "multirotor_acoustic", 0.7, bearing=bearing_to(NODES["node-b"], TARGET), when=when),
    ])
    t = _track_in_window(when)
    assert t["localization"] == "COARSE_FIX"
    # intersection should land within ~150 m of the true target
    from app.geo import haversine_m
    assert haversine_m(t["lat"], t["lon"], *TARGET) < 150


def test_precise_requires_pps_else_downgrades():
    _reset()
    # 3 nodes, NON-pps timestamps -> must NOT be precise even with 3 nodes
    when = T0 + timedelta(seconds=300)
    post([det(n, "acoustic", "multirotor_acoustic", 0.8, when=when, pps=False, time_source="system")
          for n in NODES])
    t = _track_in_window(when)
    assert t["localization"] == "COARSE_FIX", "3 nodes on system clock must downgrade"


def test_precise_fix_with_pps_tdoa():
    _reset()
    emit = T0 + timedelta(seconds=400)
    dets = []
    for n in NODES:
        dets.append(det(n, "acoustic", "multirotor_acoustic", 0.8,
                        when=toa(NODES[n], TARGET, emit), pps=True, time_source="gnss_pps"))
    post(dets)
    t = active_tracks()[0]
    assert t["localization"] == "PRECISE_FIX"
    from app.geo import haversine_m
    assert haversine_m(t["lat"], t["lon"], *TARGET) < 80, "TDOA should be tight"


def test_uncooperative_bonus_and_alert():
    _reset()
    when = T0 + timedelta(seconds=500)
    r = post([det(n, "acoustic", "multirotor_acoustic", 0.85, when=when,
                  bearing=bearing_to(NODES[n], TARGET)) for n in NODES])
    assert r["alerts_changed"] >= 1  # uncooperative -> alert
    t = _track_in_window(when)
    assert t["cooperative"] is False
    assert t["threat_breakdown"]["factors"]["uncooperative_bonus"] > 1.0  # bonus applied


def test_cooperative_remote_id_suppresses_alert():
    _reset()
    when = T0 + timedelta(seconds=600)
    rid = {"uas_id": "MAVIC-123", "lat": TARGET[0], "lon": TARGET[1]}
    r = post([
        det("node-a", "acoustic", "multirotor_acoustic", 0.85, when=when),
        det("node-b", "remote_id", "mavic_remoteid", 0.99, when=when, rid=rid, time_source="gnss_pps"),
    ])
    t = _track_in_window(when)
    assert t["cooperative"] is True
    assert r["alerts_changed"] == 0  # friendly -> no alert


def test_idempotent_detection_id():
    _reset()
    d = det("node-a", "acoustic", "multirotor_acoustic", 0.6,
            bearing=10, when=T0 + timedelta(seconds=700))
    r1 = client.post("/detections", json={"detections": [d]}, headers=H).json()
    r2 = client.post("/detections", json={"detections": [d]}, headers=H).json()
    assert r1["inserted"] == 1 and r2["inserted"] == 0


def test_relay_path_recorded():
    _reset()
    when = T0 + timedelta(seconds=800)
    d = det("node-c", "acoustic", "multirotor_acoustic", 0.7, bearing=20, when=when, relayed_via="node-a")
    client.post("/relay", json={"detections": [d]}, headers=H)
    t = _track_in_window(when)
    assert "node-a" in t["relay_path"]


# --- helpers ---------------------------------------------------------------
def _reset():
    register_all()


def _track_in_window(when):
    ts = when.timestamp()
    cands = [t for t in active_tracks()
             if abs(datetime.fromisoformat(t["last_seen"]).timestamp() - ts) < 20]
    assert cands, "expected a track near the posted time"
    return cands[0]
