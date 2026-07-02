"""Triangle node-agent — runs on each Pi.

Boots the enabled sensor plugins, probes which hardware is actually present, registers the
real loadout with the brain, then loops: read detections, cross-cue neighbors on strong hits,
buffer everything, and deliver to the brain (or via a neighbor relay if the brain is
unreachable). Runs with ANY sensor subset and reports what is missing — it never fabricates.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any

import httpx

sys.path.insert(0, os.path.dirname(__file__))

from buffer import Buffer
from client import BrainClient
from config import env_override, load_config
from mesh import Mesh
from sensors import NodeContext, build_driver

CUE_MIN_CONFIDENCE = 0.5
HEALTH_INTERVAL_S = 10.0
REGISTER_INTERVAL_S = 20.0


class Agent:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.node_id = cfg["node_id"]
        self.position = cfg["position"]  # {lat, lon, alt_m}
        self.token = cfg.get("token", "triangle-dev-token")
        self.ctx = NodeContext(self.node_id, self.position)
        self.client = BrainClient(cfg.get("brain_url"), self.token)
        self.buffer = Buffer(cfg.get("buffer_path", f"/tmp/triangle-{self.node_id}.outbox.db"))
        self.drivers: list = []
        self.gnss = None
        self._last_health = 0.0
        self._last_register = 0.0

        self._build_sensors()
        active_types = [d.sensor_type for d in self.drivers]
        self.mesh = Mesh(self.node_id, int(cfg.get("relay_port", 51901)),
                         active_types, self.token, on_cue=self._on_cue)

    # ------------------------------------------------------------- sensor bring-up
    def _build_sensors(self) -> None:
        for s in self.cfg.get("sensors", []):
            stype = s["type"]
            try:
                driver = build_driver(stype, self.ctx, s.get("config", {}))
            except KeyError as e:
                print(f"[{self.node_id}] skip unknown sensor '{stype}': {e}")
                continue
            present = driver.probe()
            print(f"[{self.node_id}] sensor {stype:12s} probe={'PRESENT' if present else 'absent '}")
            if stype == "gnss":
                self.gnss = driver  # health source; keep even if absent to report system time
                if present:
                    self.drivers_gnss_present = True
                continue
            if present:
                self.drivers.append(driver)
        if not self.drivers:
            print(f"[{self.node_id}] WARNING: no detection sensors present — node will report silence + health only")

    def manifest(self) -> dict[str, Any]:
        sensors = [d.manifest().__dict__ for d in self.drivers]
        if self.gnss:
            sensors.append(self.gnss.manifest().__dict__)
        return {
            "node_id": self.node_id, "agent_version": "0.1.0",
            "position": self.position, "sensors": sensors, "schema_version": 1,
        }

    # ------------------------------------------------------------- cross-cue
    def _on_cue(self, cue: dict[str, Any]) -> None:
        """A neighbor's hint: transiently raise sensitivity on matching sensors."""
        now = time.time()
        ttl = float(cue.get("ttl_s", 8.0))
        for d in self.drivers:
            # cue any sensor of the cued type, or all physical sensors for a generic drone cue
            if cue.get("sensor_type") in (None, d.sensor_type) or True:
                d.apply_cue(cue, now, ttl)
        print(f"[{self.node_id}] cue from {cue.get('node_id')} ({cue.get('signature_class')}) "
              f"-> sensitivity raised {ttl:.0f}s")

    # ------------------------------------------------------------- delivery
    def _deliver(self) -> None:
        pending = self.buffer.pending()
        if not pending:
            return
        if self.client.brain_reachable():
            if self.client.post_detections(pending):
                self.buffer.ack([d["detection_id"] for d in pending])
                return
        # brain unreachable -> try to relay via a neighbor (store-and-forward)
        for n in self.mesh.neighbors.reachable_neighbors(self.node_id):
            url = f"http://{n['ip']}:{n['relay_port']}"
            if self.client.relay_via(url, pending, via_node_id=n["node_id"]):
                self.buffer.ack([d["detection_id"] for d in pending])
                print(f"[{self.node_id}] relayed {len(pending)} detections via {n['node_id']}")
                return
        # nobody reachable — keep buffered, nothing lost
        print(f"[{self.node_id}] brain + neighbors unreachable; {self.buffer.count()} buffered")

    # ------------------------------------------------------------- health
    def _push_health(self) -> None:
        health = self.gnss.read_health() if self.gnss else {"time_source": self.ctx.time_source}
        health["neighbors"] = [n["node_id"] for n in self.mesh.neighbors.reachable_neighbors(self.node_id)]
        health["active_sensors"] = [d.sensor_type for d in self.drivers]
        health["buffered"] = self.buffer.count()
        if self.client.brain_url:
            try:
                httpx.post(f"{self.client.brain_url}/nodes/{self.node_id}/health", json=health,
                           headers={"Authorization": f"Bearer {self.token}"}, timeout=3.0)
            except Exception:
                pass

    # ------------------------------------------------------------- main loop
    def run(self) -> None:
        self.mesh.start()
        self.mesh.start_relay_server(self.client)
        if not self.client.register(self.manifest()):
            print(f"[{self.node_id}] brain registration deferred (not reachable yet)")
        print(f"[{self.node_id}] running. {len(self.drivers)} active sensor(s). Ctrl-C to stop.")
        try:
            while True:
                now = time.time()
                if now - self._last_register > REGISTER_INTERVAL_S:
                    self.client.register(self.manifest())
                    self._last_register = now
                if now - self._last_health > HEALTH_INTERVAL_S:
                    self._push_health()
                    self._last_health = now

                for d in self.drivers:
                    for det in d.detect():
                        if det is None:
                            continue
                        payload = det.to_json()
                        self.buffer.add(payload)
                        if det.confidence >= CUE_MIN_CONFIDENCE:
                            self.mesh.send_cue({
                                "sensor_type": det.sensor_type,
                                "signature_class": det.signature_class,
                                "confidence": det.confidence,
                                "bearing_deg": det.bearing_deg,
                                "observed_at": det.observed_at,
                            })
                        print(f"[{self.node_id}] DET {det.sensor_type} {det.signature_class} "
                              f"conf={det.confidence:.2f} bearing={det.bearing_deg}")
                self._deliver()
                time.sleep(float(self.cfg.get("loop_interval_s", 0.5)))
        except KeyboardInterrupt:
            print(f"\n[{self.node_id}] stopping")
        finally:
            self.mesh.stop()


def main() -> None:
    ap = argparse.ArgumentParser(description="Triangle Mesh node-agent")
    ap.add_argument("-c", "--config", default=os.environ.get("TRIANGLE_CONFIG", "config.yaml"))
    args = ap.parse_args()
    cfg = env_override(load_config(args.config))
    Agent(cfg).run()


if __name__ == "__main__":
    main()
