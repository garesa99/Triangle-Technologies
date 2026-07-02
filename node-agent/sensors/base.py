"""Sensor plugin interface — the extension point of the whole system.

A new sensor = ONE new file in node-agent/sensors/ implementing SensorDriver, plus a config
entry. No changes to the agent core or the brain. Drivers are discovered dynamically at
startup (see sensors/__init__.py).

Contract (docs/CONTRACT.md):
  manifest() -> SensorManifest   what this sensor is + its capabilities
  probe()    -> bool             is the hardware actually present/usable right now?
  detect()   -> Iterable[Detection]   yield real detections (or nothing = silence)
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

SCHEMA_VERSION = 1


@dataclass
class SensorManifest:
    sensor_type: str
    signature_classes: list[str]
    provides_bearing: bool = False
    spec: dict[str, Any] = field(default_factory=dict)


@dataclass
class Detection:
    """One normalized detection row. Matches db/detection.schema.json exactly."""
    node_id: str
    sensor_type: str
    signature_class: str
    confidence: float
    node_position: dict[str, Any]
    time_source: str = "system"          # gnss_pps | ntp | system
    pps_precise: bool = False
    observed_at: Optional[str] = None
    bearing_deg: Optional[float] = None
    bearing_uncertainty_deg: Optional[float] = None
    signal_level: Optional[float] = None
    remote_id_payload: Optional[dict] = None
    raw_features: Optional[dict] = None
    relayed_via: Optional[str] = None
    detection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.observed_at is None:
            self.observed_at = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


class SensorDriver:
    """Base class. Subclasses live in node-agent/sensors/ and set `sensor_type`."""

    sensor_type: str = "abstract"

    def __init__(self, node_ctx: "NodeContext", cfg: dict[str, Any]) -> None:
        self.node = node_ctx
        self.cfg = cfg
        self._cued_until: float = 0.0  # cross-cue: raised-sensitivity window (epoch s)

    def manifest(self) -> SensorManifest:
        raise NotImplementedError

    def probe(self) -> bool:
        """Return True only if the hardware is really present and readable. Honest probing
        is what lets the mesh run on any sensor subset and say what's missing."""
        raise NotImplementedError

    def detect(self) -> Iterable[Detection]:
        """Yield real detections. Yield nothing when there is nothing — silence is silence,
        never a fabricated row."""
        return ()

    # cross-cue hook — a neighbor's hint may transiently raise our sensitivity
    def apply_cue(self, cue: dict[str, Any], now: float, ttl_s: float) -> None:
        self._cued_until = max(self._cued_until, now + ttl_s)

    def is_cued(self, now: float) -> bool:
        return now < self._cued_until

    def new_detection(self, **kwargs: Any) -> Detection:
        """Helper that stamps node_id, position, and time source from the node context."""
        ts, precise = self.node.timestamp()
        return Detection(
            node_id=self.node.node_id,
            node_position=self.node.position,
            observed_at=ts,
            time_source=self.node.time_source,
            pps_precise=precise,
            **kwargs,
        )


class NodeContext:
    """What a driver needs from the node: identity, position, and the time source.

    time_source/timestamp() come from the GNSS monitor when PPS is locked, else NTP/system.
    This is how PRECISE (TDOA) localization stays honest end to end.
    """

    def __init__(self, node_id: str, position: dict[str, Any]) -> None:
        self.node_id = node_id
        self.position = position
        self.time_source = "system"
        self._pps_locked = False

    def set_time_source(self, source: str, pps_locked: bool) -> None:
        self.time_source = source
        self._pps_locked = pps_locked

    def timestamp(self) -> tuple[str, bool]:
        """Return (iso_utc, pps_precise). In a real PPS deployment the timestamp is
        disciplined by the GNSS PPS edge; here we report system time but flag precision
        honestly so the brain never grants a PRECISE fix it hasn't earned."""
        return datetime.now(timezone.utc).isoformat(), (self._pps_locked and self.time_source == "gnss_pps")
