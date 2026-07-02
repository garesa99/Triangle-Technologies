"""Stub sensor plugins — PIR / seismic / magnetometer. Ground-target extension.

These prove the plugin path end to end: they declare a manifest + capabilities (so the brain
stores them and the UI renders them), probe honestly (return False until wired), and have a
detect() with a clearly-marked TODO. Adding a real ground sensor = fill in detect(), nothing
in the agent core or the brain changes.
"""
from __future__ import annotations

from typing import Iterable

from .base import Detection, SensorDriver, SensorManifest


class PirSensor(SensorDriver):
    sensor_type = "pir"

    def manifest(self) -> SensorManifest:
        return SensorManifest(self.sensor_type, ["ground_motion"], provides_bearing=False,
                              spec={"gpio": self.cfg.get("gpio"), "status": "stub"})

    def probe(self) -> bool:
        # TODO: check the configured GPIO / device is readable.
        return False

    def detect(self) -> Iterable[Detection]:
        # TODO: on rising edge, emit new_detection(signature_class="ground_motion", ...)
        return ()


class SeismicSensor(SensorDriver):
    sensor_type = "seismic"

    def manifest(self) -> SensorManifest:
        return SensorManifest(self.sensor_type, ["ground_vehicle", "footfall"], provides_bearing=False,
                              spec={"adc": self.cfg.get("adc"), "status": "stub"})

    def probe(self) -> bool:
        # TODO: probe the geophone ADC (e.g. ADS1115) over I2C.
        return False

    def detect(self) -> Iterable[Detection]:
        # TODO: band-pass the geophone stream; emit on energy threshold.
        return ()


class MagnetometerSensor(SensorDriver):
    sensor_type = "magnetometer"

    def manifest(self) -> SensorManifest:
        return SensorManifest(self.sensor_type, ["ferrous_object"], provides_bearing=False,
                              spec={"i2c_addr": self.cfg.get("i2c_addr"), "status": "stub"})

    def probe(self) -> bool:
        # TODO: probe the magnetometer (e.g. QMC5883L) over I2C.
        return False

    def detect(self) -> Iterable[Detection]:
        # TODO: detect field anomalies vs a rolling baseline.
        return ()
