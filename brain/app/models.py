"""Pydantic models. Mirror db/detection.schema.json and docs/CONTRACT.md."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


class Position(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    alt_m: Optional[float] = None


class Detection(BaseModel):
    detection_id: str = Field(min_length=8)
    node_id: str = Field(min_length=1)
    sensor_type: str = Field(min_length=1)  # registered string, not a closed enum
    observed_at: str                        # ISO-8601 UTC
    pps_precise: bool
    signature_class: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    bearing_deg: Optional[float] = Field(default=None, ge=0, le=360)
    bearing_uncertainty_deg: Optional[float] = Field(default=None, ge=0)
    signal_level: Optional[float] = None
    remote_id_payload: Optional[dict[str, Any]] = None
    raw_features: Optional[dict[str, Any]] = None
    node_position: Position
    time_source: Literal["gnss_pps", "ntp", "system"]
    schema_version: int = Field(ge=1)
    relayed_via: Optional[str] = None


class DetectionBatch(BaseModel):
    detections: list[Detection]


class SensorManifest(BaseModel):
    sensor_type: str = Field(min_length=1)
    signature_classes: list[str] = []
    provides_bearing: bool = False
    spec: dict[str, Any] = {}


class NodeManifest(BaseModel):
    node_id: str = Field(min_length=1)
    agent_version: str = "0.0.0"
    position: Position
    sensors: list[SensorManifest] = []
    schema_version: int = Field(ge=1)
