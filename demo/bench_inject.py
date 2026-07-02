"""BENCH TEST SIGNAL — honest live-pipeline demo for the operator picture.

This is the ONLY sanctioned way to show a populated picture without real sensors. It does NOT
hand-draw a fake track. It:
  1. synthesizes drone audio at a per-node level set by the target's distance (closer = louder),
  2. runs that audio through the REAL acoustic detector (node-agent/sensors/acoustic.py) — the
     exact code that runs on hardware — producing genuine detections (confidence from real DSP),
  3. tags each detection `raw_features.bench_test = true`, and
  4. posts them to the brain over the normal /detections path.

The brain fuses them like any other detection, so a real COARSE track + alert forms and MOVES
as the simulated target advances. Because every contributing detection is flagged, the brain
marks the track `bench_test` and the operator UI shows a persistent "BENCH TEST SIGNAL" banner —
so it is never mistaken for a live field detection.

Honest by construction: the audio is synthetic, the detection pipeline is real, the label says so.
No GNSS-PPS here, so localization stays COARSE (an uncertainty ellipse) — exactly what a
bearingless multi-node mesh yields. PRECISE/TDOA needs real PPS hardware (see FIELD_TEST.md).

Usage:
  python demo/bench_inject.py --brain http://localhost:8000 --token triangle-dev-token
  # Ctrl-C to stop. Tracks go stale on their own once injection stops.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time

import numpy as np
import httpx

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "node-agent"))
sys.path.insert(0, os.path.join(ROOT, "brain"))

from sensors import NodeContext                      # noqa: E402
from sensors.acoustic import AcousticSensor          # noqa: E402
from app.geo import haversine_m                      # noqa: E402

SR = 48000

# Three nodes (match db/seed/nodes.example.json) around a protected apron.
NODES = {
    "node-alpha": (52.3702, 4.8952),
    "node-bravo": (52.3728, 4.9010),
    "node-charlie": (52.3675, 4.9008),
}
# A simple approach path: the target crosses the area toward the apron centre.
PATH = [
    (52.3675, 4.9012), (52.3682, 4.9004), (52.3690, 4.8998),
    (52.3697, 4.8992), (52.3702, 4.8986), (52.3706, 4.8982),
    (52.3700, 4.8978), (52.3692, 4.8982), (52.3684, 4.8990),
]
rng = np.random.default_rng(20260702)


def synth_drone_at(amp: float, f0: float = 118.0) -> np.ndarray:
    """Harmonic comb + broadband rotor noise at amplitude `amp` (louder = closer)."""
    t = np.arange(SR) / SR
    sig = sum((amp / h) * np.sin(2 * math.pi * f0 * h * t) for h in range(1, 7))
    sig += 0.15 * rng.standard_normal(SR)  # fixed ambient noise floor
    peak = np.max(np.abs(sig)) + 1e-9
    return (sig / peak).astype(np.float64)


def amp_for_distance(dist_m: float) -> float:
    """Received level vs range — closer is louder. Beyond ~600 m it fades under the noise floor
    and the real detector simply returns nothing (honest silence)."""
    return 1.3 * math.exp(-dist_m / 300.0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brain", default="http://localhost:8000")
    ap.add_argument("--token", default="triangle-dev-token")
    ap.add_argument("--interval", type=float, default=1.5)
    ap.add_argument("--loops", type=int, default=0, help="0 = run until Ctrl-C")
    args = ap.parse_args()
    h = {"Authorization": f"Bearer {args.token}"}

    # sensors: one real AcousticSensor per node, bound to that node's identity + position
    sensors = {
        nid: AcousticSensor(NodeContext(nid, {"lat": lat, "lon": lon, "alt_m": 2}),
                            {"sample_rate": SR, "channels": 1})
        for nid, (lat, lon) in NODES.items()
    }

    # make sure the nodes are registered (idempotent)
    for nid, (lat, lon) in NODES.items():
        try:
            httpx.post(f"{args.brain}/register", headers=h, timeout=5, json={
                "node_id": nid, "agent_version": "bench", "schema_version": 1,
                "position": {"lat": lat, "lon": lon, "alt_m": 2},
                "sensors": [{"sensor_type": "acoustic", "signature_classes": ["multirotor_acoustic"],
                             "provides_bearing": False, "spec": {"channels": 1}}]})
        except Exception as e:
            print(f"! could not reach brain to register {nid}: {e}"); return

    print("=" * 68)
    print(" BENCH TEST SIGNAL — synthetic audio through the REAL detector pipeline")
    print(" Not a live field detection. The operator UI will label it as such.")
    print("=" * 68)

    step = 0
    try:
        while args.loops == 0 or step < args.loops * len(PATH):
            target = PATH[step % len(PATH)]
            batch = []
            hits = []
            for nid, sensor in sensors.items():
                dist = haversine_m(*NODES[nid], *target)
                audio = synth_drone_at(amp_for_distance(dist))
                det = sensor.analyze(audio)      # <-- REAL detector
                if det is None:
                    continue                     # too far / too quiet -> honest silence
                payload = det.to_json()
                payload["raw_features"] = {**(payload.get("raw_features") or {}),
                                           "bench_test": True,
                                           "bench_note": "synthetic audio via real detector"}
                batch.append(payload)
                hits.append(f"{nid.split('-')[1]}:{det.confidence:.2f}@{dist:.0f}m")
            if batch:
                r = httpx.post(f"{args.brain}/detections", headers=h, json={"detections": batch}, timeout=5)
                print(f"step {step:3d}  target=({target[0]:.4f},{target[1]:.4f})  "
                      f"detections=[{', '.join(hits)}]  -> {r.json().get('tracks_changed')} track(s), "
                      f"{r.json().get('alerts_changed')} alert(s)")
            else:
                print(f"step {step:3d}  target too far from all nodes — silence (honest)")
            step += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped. Bench track(s) will go stale and close on their own.")


if __name__ == "__main__":
    main()
