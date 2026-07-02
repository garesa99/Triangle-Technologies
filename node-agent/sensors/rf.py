"""RF control/video-link detector for 2.4 / 5.8 GHz — BAND-GATED by real hardware.

Drones use 2.4/5.8 GHz for control (RC) and analog/digital FPV video. A plain RTL-SDR tops
out ~1.7 GHz and CANNOT see these bands — so this driver PROBES the SDR and only enables a
band it can actually reach (HackRF, or RTL-SDR + an upconverter). We do energy/anomaly
detection above a rolling WiFi baseline. We are honest: WiFi/BT share 2.4 GHz, so output is a
probability, never a certainty.

One driver class, instantiated per band -> sensor_type rf24 or rf58. That keeps the plugin
model clean (capabilities differ only by center frequency).
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional

import numpy as np

from .base import Detection, SensorDriver, SensorManifest

BANDS = {
    "rf24": {"center_hz": 2_437_000_000, "label": "2.4 GHz"},
    "rf58": {"center_hz": 5_800_000_000, "label": "5.8 GHz"},
}


def band_power_db(iq: np.ndarray) -> float:
    """Mean power (dB) of a complex IQ block."""
    p = np.mean(np.abs(iq) ** 2) + 1e-12
    return 10.0 * math.log10(p)


def anomaly_confidence(power_db: float, baseline_db: float, spread_db: float) -> float:
    """Confidence that the current power is an above-baseline emission (drone link candidate).
    Uses a z-score over the rolling WiFi baseline, squashed to [0,1]."""
    z = (power_db - baseline_db) / (spread_db + 1e-6)
    return float(1.0 / (1.0 + math.exp(-(z - 3.0))))  # needs ~3 sigma before it climbs


class RFSensor(SensorDriver):
    def __init__(self, node_ctx, cfg):
        super().__init__(node_ctx, cfg)
        self.band = cfg.get("band", "rf24")
        assert self.band in BANDS, f"unknown rf band {self.band}"
        self.sensor_type = self.band
        self.center_hz = BANDS[self.band]["center_hz"]
        self.sample_rate = int(cfg.get("sample_rate", 2_000_000))
        self.n_samples = int(cfg.get("n_samples", 262144))
        self._baseline_db: Optional[float] = None
        self._spread_db = 3.0
        self._sdr = None
        self._band_ok = None  # cached probe result

    def manifest(self) -> SensorManifest:
        return SensorManifest(
            sensor_type=self.sensor_type,
            signature_classes=["fpv_video_link", "rc_control_link"],
            provides_bearing=False,
            spec={"center_hz": self.center_hz, "band": BANDS[self.band]["label"],
                  "sample_rate": self.sample_rate,
                  "note": "enabled only if the SDR can reach this band"},
        )

    def _detect_sdr_band_capable(self) -> bool:
        """Return True only if a present SDR can actually tune to this band."""
        try:
            import SoapySDR
            from SoapySDR import SOAPY_SDR_RX
            results = SoapySDR.Device.enumerate()
            for r in results:
                dev = SoapySDR.Device(dict(r))
                ranges = dev.getFrequencyRange(SOAPY_SDR_RX, 0)
                for rg in ranges:
                    if rg.minimum() <= self.center_hz <= rg.maximum():
                        return True
            return False
        except Exception:
            # SoapySDR absent -> cannot claim band capability
            return False

    def probe(self) -> bool:
        if self._band_ok is None:
            self._band_ok = self._detect_sdr_band_capable()
        return bool(self._band_ok)

    def _read_iq(self) -> Optional[np.ndarray]:
        try:
            import SoapySDR
            from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
            if self._sdr is None:
                results = SoapySDR.Device.enumerate()
                self._sdr = SoapySDR.Device(dict(results[0]))
                self._sdr.setSampleRate(SOAPY_SDR_RX, 0, self.sample_rate)
                self._sdr.setFrequency(SOAPY_SDR_RX, 0, self.center_hz)
                self._rx = self._sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
                self._sdr.activateStream(self._rx)
            buff = np.zeros(self.n_samples, np.complex64)
            self._sdr.readStream(self._rx, [buff], self.n_samples)
            return buff
        except Exception:
            return None

    def analyze(self, iq: np.ndarray) -> Optional[Detection]:
        """Pure path — testable by passing a synthesized IQ block."""
        power = band_power_db(iq)
        if self._baseline_db is None:
            self._baseline_db = power
            return None  # first block establishes the WiFi baseline
        conf = anomaly_confidence(power, self._baseline_db, self._spread_db)
        # slow-adapt the baseline so persistent WiFi doesn't keep firing
        self._baseline_db = 0.98 * self._baseline_db + 0.02 * power
        import time
        floor = 0.4 if self.is_cued(time.time()) else 0.55
        if conf < floor:
            return None
        return self.new_detection(
            sensor_type=self.sensor_type,
            signature_class="fpv_video_link",
            confidence=round(conf, 3), signal_level=round(power, 1),
            raw_features={"power_db": round(power, 2), "baseline_db": round(self._baseline_db, 2),
                          "band": BANDS[self.band]["label"], "note": "probabilistic; WiFi/BT share 2.4 GHz"},
        )

    def detect(self) -> Iterable[Detection]:
        iq = self._read_iq()
        if iq is None:
            return ()
        d = self.analyze(iq)
        return (d,) if d else ()
