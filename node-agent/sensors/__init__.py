"""Dynamic sensor registry. Drivers register a factory keyed by sensor_type; the agent builds
whichever ones the node config enables, probes them, and runs the ones whose hardware is present.

Adding a sensor = drop a module in this package and register its class here (or auto-discover).
"""
from __future__ import annotations

from typing import Any, Callable

from .base import Detection, NodeContext, SensorDriver, SensorManifest
from .acoustic import AcousticSensor
from .remote_id import RemoteIdSensor
from .rf import RFSensor
from .gnss import GnssMonitor
from .stubs import MagnetometerSensor, PirSensor, SeismicSensor

# factory registry: sensor_type key -> driver class
REGISTRY: dict[str, Callable[..., SensorDriver]] = {
    "acoustic": AcousticSensor,
    "remote_id": RemoteIdSensor,
    "rf24": RFSensor,
    "rf58": RFSensor,
    "gnss": GnssMonitor,
    "pir": PirSensor,
    "seismic": SeismicSensor,
    "magnetometer": MagnetometerSensor,
}


def build_driver(sensor_type: str, node_ctx: NodeContext, cfg: dict[str, Any]) -> SensorDriver:
    key = sensor_type
    if key not in REGISTRY:
        raise KeyError(f"unknown sensor_type '{sensor_type}'. Registered: {sorted(REGISTRY)}")
    # rf24/rf58 share RFSensor; pass the band through config
    if key in ("rf24", "rf58"):
        cfg = {**cfg, "band": key}
    return REGISTRY[key](node_ctx, cfg)


__all__ = ["REGISTRY", "build_driver", "Detection", "NodeContext", "SensorDriver", "SensorManifest"]
