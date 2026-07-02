"""Brain configuration. Everything runs offline/local by default — no cloud, no internet."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _f(name: str, default: float) -> float:
    v = os.environ.get(name)
    return float(v) if v not in (None, "") else default


@dataclass
class Settings:
    # Auth — same token as node->brain and node->node. Override in the field.
    token: str = os.environ.get("TRIANGLE_TOKEN", "triangle-dev-token")
    # DB — SQLite file for zero-setup local mode. Set TRIANGLE_DB to a path.
    db_path: str = os.environ.get("TRIANGLE_DB", os.path.join(os.path.dirname(__file__), "..", "triangle.db"))

    # Association
    assoc_time_window_s: float = _f("ASSOC_WINDOW_S", 4.0)      # detections within this window may fuse
    assoc_max_range_m: float = _f("ASSOC_MAX_RANGE_M", 3000.0)  # plausible shared-event radius

    # Localization
    coarse_min_nodes: int = int(_f("COARSE_MIN_NODES", 2))
    precise_min_nodes: int = int(_f("PRECISE_MIN_NODES", 3))

    # Threat / alerts
    alert_threshold: float = _f("ALERT_THRESHOLD", 0.55)
    cue_min_confidence: float = _f("CUE_MIN_CONFIDENCE", 0.4)

    # Geofences the operator hasn't drawn yet — protected zones can be seeded here.
    protected_zones: list[dict] = field(default_factory=list)

    node_stale_after_s: float = _f("NODE_STALE_S", 30.0)


settings = Settings()
