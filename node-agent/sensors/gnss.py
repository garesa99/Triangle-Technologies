"""GNSS monitor — u-blox module. Not a drone sensor: it provides (a) the node's own fixed
position, (b) a PPS pulse used to discipline detection timestamps (the gate for PRECISE/TDOA),
and (c) jamming/spoofing indicators. A jammed node near a detection is itself intelligence.

This driver's job in the agent is to update the shared NodeContext time source (system -> ntp
-> gnss_pps) and to emit node-HEALTH (not detections). It reads UBX via pyubx2 when present.
"""
from __future__ import annotations

from typing import Any, Optional

from .base import SensorDriver, SensorManifest


class GnssMonitor(SensorDriver):
    sensor_type = "gnss"

    def __init__(self, node_ctx, cfg):
        super().__init__(node_ctx, cfg)
        self.port = cfg.get("port", "/dev/ttyACM0")
        self.baud = int(cfg.get("baud", 38400))
        self.pps_gpio = cfg.get("pps_gpio")  # if PPS wired to a GPIO / kernel PPS device
        self._serial = None

    def manifest(self) -> SensorManifest:
        return SensorManifest(
            sensor_type=self.sensor_type,
            signature_classes=[],  # health source, not a detector
            provides_bearing=False,
            spec={"port": self.port, "provides": ["position", "pps_time", "jam_spoof"]},
        )

    def probe(self) -> bool:
        try:
            import serial
            s = serial.Serial(self.port, self.baud, timeout=0.2)
            s.close()
            return True
        except Exception:
            return False

    def read_health(self) -> dict[str, Any]:
        """Return a health dict AND update NodeContext time source. Falls back honestly:
        if no PPS lock, time_source becomes ntp/system and PRECISE fixes are refused downstream."""
        health = {
            "fix": None, "num_sv": None, "pps_lock": False,
            "jamming_state": None, "spoofing_state": None, "time_source": "system",
        }
        try:
            import serial
            from pyubx2 import UBXReader
            if self._serial is None:
                self._serial = serial.Serial(self.port, self.baud, timeout=0.5)
            ubr = UBXReader(self._serial)
            # read a few messages to catch NAV-PVT / NAV-STATUS / MON-RF
            for _ in range(8):
                _, parsed = ubr.read()
                if parsed is None:
                    continue
                ident = getattr(parsed, "identity", "")
                if ident == "NAV-PVT":
                    health["fix"] = getattr(parsed, "fixType", None)
                    health["num_sv"] = getattr(parsed, "numSV", None)
                    if health["fix"] and health["fix"] >= 3:
                        # 3D fix -> PPS is disciplining time; treat as gnss_pps
                        health["pps_lock"] = True
                        health["time_source"] = "gnss_pps"
                elif ident == "MON-RF":
                    health["jamming_state"] = getattr(parsed, "jammingState", None)
                elif ident in ("NAV-STATUS",):
                    health["spoofing_state"] = getattr(parsed, "spoofDetState", None)
        except Exception:
            # No GNSS hardware / no pyubx2: stay on system time honestly.
            pass

        self.node.set_time_source(health["time_source"], health["pps_lock"])
        return health

    def detect(self):  # GNSS emits health, not detections
        return ()
