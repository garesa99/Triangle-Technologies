"""Brain client + relay. Posts registration and detections to the brain; if the brain is
unreachable, hands the batch to a reachable neighbor's /relay endpoint (store-and-forward).
Bearer-token auth, same token brain and mesh. No custom binary protocol — plain HTTP/JSON.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx


class BrainClient:
    def __init__(self, brain_url: str, token: str, timeout: float = 5.0) -> None:
        self.brain_url = brain_url.rstrip("/") if brain_url else None
        self.token = token
        self.timeout = timeout
        self._h = {"Authorization": f"Bearer {token}"}

    def set_brain_url(self, url: str) -> None:
        self.brain_url = url.rstrip("/") if url else None

    def register(self, manifest: dict[str, Any]) -> bool:
        if not self.brain_url:
            return False
        try:
            r = httpx.post(f"{self.brain_url}/register", json=manifest, headers=self._h,
                           timeout=self.timeout)
            return r.status_code == 200
        except Exception:
            return False

    def post_detections(self, detections: list[dict[str, Any]]) -> bool:
        """Direct to brain. Returns True on success (rows accepted / idempotently ignored)."""
        if not self.brain_url or not detections:
            return False
        try:
            r = httpx.post(f"{self.brain_url}/detections", json={"detections": detections},
                           headers=self._h, timeout=self.timeout)
            return r.status_code == 200
        except Exception:
            return False

    def relay_via(self, neighbor_url: str, detections: list[dict[str, Any]], via_node_id: str) -> bool:
        """Ask a neighbor to relay our detections to the brain. We stamp relayed_via so the
        brain knows the path; idempotency by detection_id makes duplicates harmless."""
        stamped = [{**d, "relayed_via": via_node_id} for d in detections]
        try:
            r = httpx.post(f"{neighbor_url.rstrip('/')}/relay", json={"detections": stamped},
                           headers=self._h, timeout=self.timeout)
            return r.status_code == 200
        except Exception:
            return False

    def brain_reachable(self) -> bool:
        if not self.brain_url:
            return False
        try:
            return httpx.get(f"{self.brain_url}/health", timeout=2.0).status_code == 200
        except Exception:
            return False
