"""Full-spine integration:
  (1) synthesized drone audio -> REAL acoustic detector -> brain ingest -> a track appears.
  (2) mesh store-and-forward: a node's /relay server forwards a buffered detection to a LIVE
      brain (real uvicorn), with relayed_via recorded — the 'link down -> data not lost' story.

Synthesized audio is a TEST FIXTURE and never feeds the live UI. On hardware the SAME
acoustic.analyze() path runs on real microphone captures.
"""
import math
import os
import socket
import sys
import threading
import time
import uuid

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "brain"))
sys.path.insert(0, os.path.join(ROOT, "node-agent"))

os.environ["TRIANGLE_TOKEN"] = "test-token"
H = {"Authorization": "Bearer test-token"}
SR = 48000


def _drone(n=SR, f0=120.0):
    t = np.arange(n) / SR
    rng = np.random.default_rng(1)
    sig = sum((1.0 / h) * np.sin(2 * math.pi * f0 * h * t) for h in range(1, 7))
    sig += 0.15 * rng.standard_normal(n)
    return sig / (np.max(np.abs(sig)) + 1e-9)


def test_acoustic_detection_becomes_a_track():
    os.environ["TRIANGLE_DB"] = ":memory:"
    from fastapi.testclient import TestClient
    import app.main as brain_main
    from sensors import NodeContext
    from sensors.acoustic import AcousticSensor

    client = TestClient(brain_main.app)
    client.__enter__()

    # register node
    pos = {"lat": 52.3702, "lon": 4.8952, "alt_m": 2}
    client.post("/register", json={"node_id": "node-alpha", "agent_version": "0.1.0",
                "position": pos, "sensors": [{"sensor_type": "acoustic",
                "signature_classes": ["multirotor_acoustic"], "provides_bearing": True, "spec": {}}],
                "schema_version": 1}, headers=H)

    # REAL detector path on a synthesized 2-channel capture (12-sample inter-mic delay -> bearing)
    ctx = NodeContext("node-alpha", pos)
    sensor = AcousticSensor(ctx, {"sample_rate": SR, "channels": 2, "mic_spacing_m": 0.15})
    mono = _drone()
    stereo = np.stack([mono, np.roll(mono, 12)], axis=1)
    det = sensor.analyze(stereo)
    assert det is not None, "real acoustic detector should fire on a synthesized drone"
    assert det.signature_class == "multirotor_acoustic"
    assert det.bearing_deg is not None, "2-mic array should produce a bearing"

    r = client.post("/detections", json={"detections": [det.to_json()]}, headers=H)
    assert r.status_code == 200, r.text
    tracks = client.get("/tracks", headers=H).json()
    assert tracks, "detection must produce a track"
    assert tracks[0]["localization"] == "BEARING_ONLY"  # single node + bearing = a ray
    assert "acoustic" in tracks[0]["sensor_types"]
    client.__exit__(None, None, None)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def test_mesh_relay_forwards_to_live_brain(tmp_path):
    """Bring up a REAL brain (uvicorn) + a node relay server; POST a detection to the relay and
    confirm it reaches the brain with relayed_via set."""
    import uvicorn
    os.environ["TRIANGLE_DB"] = str(tmp_path / "relay-brain.db")
    # fresh app instance bound to the file DB
    import importlib
    import app.config as cfg
    importlib.reload(cfg)
    import app.main as brain_main
    importlib.reload(brain_main)

    brain_port = _free_port()
    server = uvicorn.Server(uvicorn.Config(brain_main.app, host="127.0.0.1", port=brain_port,
                                           log_level="warning"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()

    import httpx
    base = f"http://127.0.0.1:{brain_port}"
    for _ in range(50):
        try:
            if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        raise AssertionError("brain did not come up")

    # register the origin node
    pos = {"lat": 52.37, "lon": 4.90, "alt_m": 2}
    httpx.post(f"{base}/register", headers=H, json={"node_id": "node-c", "agent_version": "0.1.0",
               "position": pos, "sensors": [], "schema_version": 1})

    # node-b runs a relay server pointing at the brain
    from client import BrainClient
    from mesh import Mesh
    relay_port = _free_port()
    bc = BrainClient(base, "test-token")
    mesh_b = Mesh("node-b", relay_port, [], "test-token")
    mesh_b.start_relay_server(bc)
    time.sleep(0.3)

    # node-c's link to the brain is "down": it relays via node-b
    det = {
        "detection_id": str(uuid.uuid4()), "node_id": "node-c", "sensor_type": "acoustic",
        "observed_at": "2026-07-02T12:00:00+00:00", "pps_precise": False,
        "signature_class": "multirotor_acoustic", "confidence": 0.7, "bearing_deg": 30.0,
        "bearing_uncertainty_deg": 5.0, "signal_level": -40.0, "remote_id_payload": None,
        "raw_features": {"t": "fixture"}, "node_position": pos, "time_source": "system",
        "schema_version": 1, "relayed_via": None,
    }
    origin = BrainClient(base, "test-token")
    ok = origin.relay_via(f"http://127.0.0.1:{relay_port}", [det], via_node_id="node-b")
    assert ok, "relay should succeed"

    tracks = httpx.get(f"{base}/tracks", headers=H).json()
    assert tracks, "relayed detection should have reached the brain and formed a track"
    assert "node-b" in (tracks[0].get("relay_path") or []), "relay path must record node-b"

    server.should_exit = True
    mesh_b.stop()
