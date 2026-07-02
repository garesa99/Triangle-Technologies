"""Remote ID reader — cooperative friend-or-foe input.

An ESP32 running OpenDroneID receiver firmware listens for the legally-mandated Remote ID
broadcast (ASTM F3411 / EU) and forwards parsed messages to the Pi over serial/USB. A drone
that broadcasts Remote ID is *cooperative*; its ABSENCE next to a physical detection is what
makes a target uncooperative. High confidence when present.

The ESP32 firmware emits newline-delimited JSON like:
  {"type":"remoteid","uas_id":"1596...","lat":52.37,"lon":4.90,"alt":80,
   "operator_id":"OP-123","speed":6.2,"heading":210,"rssi":-63}
We also accept raw ASTM basic-ID/location fields and normalize them.
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from .base import Detection, SensorDriver, SensorManifest

DEFAULT_BAUD = 115200


def parse_line(line: str) -> Optional[dict[str, Any]]:
    """Parse one line from the ESP32 stream into a normalized remote_id payload, or None."""
    line = line.strip()
    if not line:
        return None
    try:
        msg = json.loads(line)
    except Exception:
        return None
    if not isinstance(msg, dict):
        return None
    lat = msg.get("lat", msg.get("latitude"))
    lon = msg.get("lon", msg.get("longitude"))
    uas = msg.get("uas_id") or msg.get("serial") or msg.get("id") or msg.get("basic_id")
    if uas is None and lat is None:
        return None
    return {
        "uas_id": uas,
        "lat": lat, "lon": lon, "alt": msg.get("alt", msg.get("altitude")),
        "operator_id": msg.get("operator_id"),
        "speed": msg.get("speed"), "heading": msg.get("heading"),
        "rssi": msg.get("rssi"),
    }


class RemoteIdSensor(SensorDriver):
    sensor_type = "remote_id"

    def __init__(self, node_ctx, cfg):
        super().__init__(node_ctx, cfg)
        self.port = cfg.get("port", "/dev/ttyUSB0")
        self.baud = int(cfg.get("baud", DEFAULT_BAUD))
        self._serial = None

    def manifest(self) -> SensorManifest:
        return SensorManifest(
            sensor_type=self.sensor_type,
            signature_classes=["mavic_remoteid", "generic_remoteid"],
            provides_bearing=False,
            spec={"port": self.port, "baud": self.baud, "standard": "ASTM F3411 / EU"},
        )

    def probe(self) -> bool:
        try:
            import serial  # pyserial
            s = serial.Serial(self.port, self.baud, timeout=0.2)
            s.close()
            return True
        except Exception:
            return False

    def _open(self):
        import serial
        if self._serial is None:
            self._serial = serial.Serial(self.port, self.baud, timeout=0.5)
        return self._serial

    def detection_from_payload(self, payload: dict[str, Any]) -> Detection:
        sig = "mavic_remoteid" if str(payload.get("uas_id", "")).lower().startswith("1596") else "generic_remoteid"
        rssi = payload.get("rssi")
        return self.new_detection(
            sensor_type=self.sensor_type, signature_class=sig, confidence=0.98,
            signal_level=(float(rssi) if rssi is not None else None),
            remote_id_payload=payload, raw_features={"source": "opendroneid"},
        )

    def detect(self) -> Iterable[Detection]:
        try:
            ser = self._open()
            line = ser.readline().decode("utf-8", "ignore")
        except Exception:
            return ()
        payload = parse_line(line)
        if not payload:
            return ()
        return (self.detection_from_payload(payload),)
