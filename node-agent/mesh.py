"""Mesh networking — nodes that talk to each other. The brain stays the single fusion
authority (no distributed consensus for MVP). This adds three things:

1. DISCOVERY: nodes announce themselves. Primary path is mDNS (`_triangle-node._tcp`) via
   zeroconf when available; because some WiFi APs block multicast, we ALSO run a UDP-broadcast
   beacon fallback that works anywhere on the LAN. Each node keeps a live neighbor table.
2. CROSS-CUE: a strong local detection multicasts a small hint to neighbors. Neighbors may
   raise sensitivity for ttl_s. Cues are HINTS — they NEVER enter the detection table.
3. RELAY: a tiny HTTP server exposing /relay + /health so a neighbor can hand us its buffered
   detections when its link to the brain is down; we forward them to the brain with relayed_via.

Transport is plain UDP (beacons/cues) + HTTP (relay). No MQTT broker — a broker is a single
point of failure in a field mesh.
"""
from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional

BEACON_PORT = 51900          # UDP broadcast: discovery beacons + cross-cues
BEACON_INTERVAL_S = 5.0
NEIGHBOR_TTL_S = 20.0


class NeighborTable:
    def __init__(self) -> None:
        self._n: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def update(self, node_id: str, ip: str, port: int, sensors: list, is_brain: bool = False) -> None:
        with self._lock:
            self._n[node_id] = {"node_id": node_id, "ip": ip, "relay_port": port,
                                "sensors": sensors, "is_brain": is_brain, "last_seen": time.time()}

    def alive(self) -> list[dict[str, Any]]:
        now = time.time()
        with self._lock:
            return [dict(v) for v in self._n.values() if now - v["last_seen"] < NEIGHBOR_TTL_S]

    def reachable_neighbors(self, self_id: str) -> list[dict[str, Any]]:
        return [n for n in self.alive() if n["node_id"] != self_id and not n["is_brain"]]


class Mesh:
    def __init__(self, node_id: str, relay_port: int, sensors: list, token: str,
                 on_cue: Optional[Callable[[dict], None]] = None) -> None:
        self.node_id = node_id
        self.relay_port = relay_port
        self.sensors = sensors
        self.token = token
        self.neighbors = NeighborTable()
        self._on_cue = on_cue
        self._stop = threading.Event()
        self._sock: Optional[socket.socket] = None
        self._threads: list[threading.Thread] = []

    # ---------------------------------------------------------------- discovery + cue
    def _open_socket(self) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            pass
        s.bind(("", BEACON_PORT))
        s.settimeout(1.0)
        return s

    def _beacon_loop(self) -> None:
        while not self._stop.is_set():
            msg = json.dumps({"kind": "beacon", "node_id": self.node_id,
                              "relay_port": self.relay_port, "sensors": self.sensors}).encode()
            try:
                self._sock.sendto(msg, ("<broadcast>", BEACON_PORT))
            except Exception:
                pass
            self._stop.wait(BEACON_INTERVAL_S)

    def _listen_loop(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except Exception:
                continue
            try:
                msg = json.loads(data.decode("utf-8", "ignore"))
            except Exception:
                continue
            kind = msg.get("kind")
            if kind == "beacon" and msg.get("node_id") != self.node_id:
                self.neighbors.update(msg["node_id"], addr[0], msg.get("relay_port", 0),
                                      msg.get("sensors", []), is_brain=msg.get("is_brain", False))
            elif kind == "cue" and msg.get("node_id") != self.node_id:
                if self._on_cue:
                    self._on_cue(msg)

    def send_cue(self, cue: dict[str, Any], ttl_s: float = 8.0) -> None:
        """Multicast a cross-cue hint to neighbors. NEVER a detection — a hint only."""
        payload = {"kind": "cue", "node_id": self.node_id, "ttl_s": ttl_s, **cue}
        try:
            self._sock.sendto(json.dumps(payload).encode(), ("<broadcast>", BEACON_PORT))
        except Exception:
            pass

    # ---------------------------------------------------------------- relay server
    def start_relay_server(self, brain_client) -> None:
        token = self.token
        mesh_self = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):  # quiet
                pass

            def _auth_ok(self) -> bool:
                return self.headers.get("Authorization") == f"Bearer {token}"

            def do_GET(self):
                if self.path == "/health":
                    self._json(200, {"ok": True, "node_id": mesh_self.node_id, "role": "relay"})
                else:
                    self._json(404, {"error": "not found"})

            def do_POST(self):
                if self.path != "/relay":
                    return self._json(404, {"error": "not found"})
                if not self._auth_ok():
                    return self._json(401, {"error": "unauthorized"})
                length = int(self.headers.get("Content-Length", 0))
                try:
                    body = json.loads(self.rfile.read(length))
                    dets = body.get("detections", [])
                except Exception:
                    return self._json(400, {"error": "bad json"})
                # forward to the brain; if brain is down too, we just report failure and the
                # origin node keeps the rows buffered (nothing lost).
                ok = brain_client.post_detections(dets)
                self._json(200 if ok else 503, {"relayed": ok, "count": len(dets)})

            def _json(self, code: int, obj: dict):
                data = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = ThreadingHTTPServer(("0.0.0.0", self.relay_port), Handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        self._threads.append(t)
        self._relay_server = server

    # ---------------------------------------------------------------- lifecycle
    def start(self) -> None:
        self._sock = self._open_socket()
        for target in (self._beacon_loop, self._listen_loop):
            t = threading.Thread(target=target, daemon=True)
            t.start()
            self._threads.append(t)
        self._try_zeroconf()

    def _try_zeroconf(self) -> None:
        """Best-effort mDNS advertisement; UDP beacons already cover discovery if this fails."""
        try:
            from zeroconf import ServiceInfo, Zeroconf
            zc = Zeroconf()
            ip = socket.inet_aton(_local_ip())
            info = ServiceInfo(
                "_triangle-node._tcp.local.",
                f"{self.node_id}._triangle-node._tcp.local.",
                addresses=[ip], port=self.relay_port,
                properties={"node_id": self.node_id},
            )
            zc.register_service(info)
            self._zc = zc
        except Exception:
            pass

    def stop(self) -> None:
        self._stop.set()
        if getattr(self, "_relay_server", None):
            try:
                self._relay_server.shutdown()
            except Exception:
                pass


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
