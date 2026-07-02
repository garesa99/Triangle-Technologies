"""Acoustic drone detector — the primary uncooperative-drone sensor.

A multirotor's propellers produce a *harmonic comb*: a blade-pass fundamental (tens to low
hundreds of Hz) plus strong overtones, riding on broadband rotor noise. That signature is
hard for the drone to suppress. We detect it two ways:

  (a) a zero-training DSP HEURISTIC (harmonic-comb strength + broadband rotor energy +
      spectral-flatness gating) — always available, the default; and
  (b) an OPTIONAL small ML model (CNN/GBM) trained on an open drone-audio dataset, loaded
      from node-agent/weights/ if present. See node-agent/ml/README.md and train_acoustic.py.

The DSP functions are PURE (operate on a numpy array) so they are testable with no microphone.
Audio capture (sounddevice/PyAudio) is isolated and only used when hardware is present.

If 2+ microphone channels are available with a known spacing, we estimate BEARING via GCC-PHAT
time-difference-of-arrival between channels; otherwise bearing is null (honest).
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional

import numpy as np

from .base import Detection, SensorDriver, SensorManifest

# multirotor blade-pass fundamentals live roughly here (2-blade props, few-thousand RPM)
F0_MIN_HZ = 40.0
F0_MAX_HZ = 260.0
N_HARMONICS = 6


# ----------------------------------------------------------------------- pure DSP
def power_spectrum(x: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    psd = (np.abs(X) ** 2) / (np.sum(w ** 2) + 1e-12)
    return freqs, psd


def spectral_flatness(psd: np.ndarray) -> float:
    """Wiener entropy in [0,1]. ~1 = white noise, ~0 = pure tone. Drones sit in between:
    tonal harmonics over broadband noise."""
    p = psd + 1e-12
    gm = np.exp(np.mean(np.log(p)))
    am = np.mean(p)
    return float(gm / am)


def harmonic_comb_strength(freqs: np.ndarray, psd: np.ndarray) -> tuple[float, float, int]:
    """Search f0 in [F0_MIN,F0_MAX]; return (best_ratio, best_f0, n_present).

    best_ratio  = harmonic-bin energy / total (comb prominence).
    n_present   = how many of the N harmonics actually carry energy (>10% of the strongest
                  harmonic peak). A real propeller comb populates MANY harmonics; a single pure
                  tone populates ONE — this count is what separates them."""
    band = (freqs >= F0_MIN_HZ) & (freqs <= F0_MAX_HZ * N_HARMONICS)
    if not band.any():
        return 0.0, 0.0, 0
    df = freqs[1] - freqs[0]
    total = float(psd.sum()) + 1e-12
    best_ratio, best_f0, best_present = 0.0, 0.0, 0
    f0_candidates = np.arange(F0_MIN_HZ, F0_MAX_HZ, max(df, 1.0))
    for f0 in f0_candidates:
        peaks = []
        for h in range(1, N_HARMONICS + 1):
            fc = f0 * h
            if fc >= freqs[-1]:
                break
            idx = int(round(fc / df))
            lo, hi = max(0, idx - 1), min(len(psd), idx + 2)
            peaks.append(float(psd[lo:hi].max()))
        if not peaks:
            continue
        harm_energy = sum(peaks)
        ratio = harm_energy / total
        thresh = 0.04 * max(peaks)  # ~ -14 dB below the strongest harmonic
        n_present = sum(1 for p in peaks if p > thresh)
        # prefer f0 that both concentrates energy AND lights up many harmonics
        score = ratio * n_present
        if score > best_ratio * max(1, best_present):
            best_ratio, best_f0, best_present = ratio, float(f0), n_present
    return best_ratio, best_f0, best_present


def broadband_rotor_energy(freqs: np.ndarray, psd: np.ndarray) -> float:
    """Fraction of energy in the mid band (200-4000 Hz) where rotor broadband noise sits."""
    band = (freqs >= 200) & (freqs <= 4000)
    return float(psd[band].sum() / (psd.sum() + 1e-12))


def acoustic_features(x: np.ndarray, sr: int) -> dict[str, float]:
    freqs, psd = power_spectrum(x, sr)
    comb, f0, n_present = harmonic_comb_strength(freqs, psd)
    return {
        "harmonic_comb": comb,
        "harmonics_present": float(n_present),
        "fundamental_hz": f0,
        "spectral_flatness": spectral_flatness(psd),
        "broadband_rotor": broadband_rotor_energy(freqs, psd),
        "rms": float(np.sqrt(np.mean(np.square(x - np.mean(x)))) + 1e-12),
    }


def score_drone(feat: dict[str, float]) -> tuple[float, str]:
    """Heuristic confidence in [0,1] + signature_class. Tuned to be conservative: it favours
    a clear harmonic comb with mid-band broadband energy and mid-range flatness. Returns
    ('multirotor_acoustic', c) or ('unknown', low)."""
    comb = feat["harmonic_comb"]
    flat = feat["spectral_flatness"]
    broad = feat["broadband_rotor"]
    n_present = feat.get("harmonics_present", 0.0)

    # comb term: saturating; a strong comb dominates
    comb_term = 1.0 - math.exp(-comb / 0.06)
    # harmonic-count gate: a lone tone (1 harmonic) -> 0; a comb of >=3 harmonics -> full pass
    count_gate = min(1.0, max(0.0, (n_present - 1.0) / 2.0))
    # flatness gate: penalise pure tones (flat~0) and pure white noise (flat~1)
    flat_gate = math.exp(-((flat - 0.35) ** 2) / (2 * 0.22 ** 2))
    # broadband presence gate
    broad_gate = min(1.0, broad / 0.25)

    conf = comb_term * count_gate * (0.5 + 0.5 * flat_gate) * (0.5 + 0.5 * broad_gate)
    conf = max(0.0, min(1.0, conf))
    sig = "multirotor_acoustic" if conf >= 0.45 else "unknown"
    return conf, sig


def gcc_phat(a: np.ndarray, b: np.ndarray, sr: int, max_tau: float) -> float:
    """Return estimated delay (s) of b relative to a via GCC-PHAT, clamped to +/-max_tau."""
    n = 1
    while n < len(a) + len(b):
        n <<= 1
    A = np.fft.rfft(a, n)
    B = np.fft.rfft(b, n)
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-12
    cc = np.fft.irfft(R, n)
    max_shift = int(sr * max_tau)
    cc = np.concatenate((cc[-max_shift:], cc[: max_shift + 1]))
    shift = np.argmax(np.abs(cc)) - max_shift
    return shift / float(sr)


def bearing_from_2mic(ch0: np.ndarray, ch1: np.ndarray, sr: int, spacing_m: float,
                      array_heading_deg: float = 0.0) -> Optional[float]:
    """Estimate bearing from a 2-mic array. Note: a single 2-mic baseline is ambiguous
    front/back; we return the [0,180) mapping rotated by the array heading. c = 343 m/s."""
    max_tau = spacing_m / 343.0
    tau = gcc_phat(ch0, ch1, sr, max_tau)
    val = max(-1.0, min(1.0, tau / max_tau)) if max_tau > 0 else 0.0
    angle = math.degrees(math.acos(val))  # 0..180 relative to baseline
    return (array_heading_deg + angle) % 360


# ----------------------------------------------------------------------- driver
class AcousticSensor(SensorDriver):
    sensor_type = "acoustic"

    def __init__(self, node_ctx, cfg):
        super().__init__(node_ctx, cfg)
        self.sr = int(cfg.get("sample_rate", 48000))
        self.frame = int(cfg.get("frame_samples", self.sr))  # 1 s window
        self.channels = int(cfg.get("channels", 1))
        self.mic_spacing_m = float(cfg.get("mic_spacing_m", 0.0))
        self.array_heading_deg = float(cfg.get("array_heading_deg", 0.0))
        self.device = cfg.get("device")
        self._stream = None
        self._ml = _try_load_ml(cfg.get("model_path"))

    def manifest(self) -> SensorManifest:
        return SensorManifest(
            sensor_type=self.sensor_type,
            signature_classes=["multirotor_acoustic"],
            provides_bearing=self.channels >= 2 and self.mic_spacing_m > 0,
            spec={"sample_rate": self.sr, "channels": self.channels,
                  "mic_spacing_m": self.mic_spacing_m, "ml": bool(self._ml)},
        )

    def probe(self) -> bool:
        try:
            import sounddevice as sd  # noqa
            devs = sd.query_devices()
            return any(d.get("max_input_channels", 0) > 0 for d in devs)
        except Exception:
            return False

    def _read_frame(self) -> Optional[np.ndarray]:
        try:
            import sounddevice as sd
            data = sd.rec(self.frame, samplerate=self.sr, channels=self.channels,
                          dtype="float32", device=self.device, blocking=True)
            return np.asarray(data)
        except Exception:
            return None

    def analyze(self, samples: np.ndarray) -> Optional[Detection]:
        """Pure analysis path — usable in tests by passing a captured/synthesized array.
        samples shape: (n,) mono or (n, channels)."""
        mono = samples if samples.ndim == 1 else samples[:, 0]
        feat = acoustic_features(mono, self.sr)
        conf, sig = score_drone(feat)
        if self._ml is not None:
            ml_conf = self._ml(mono, self.sr)
            feat["ml_confidence"] = ml_conf
            conf = max(conf, ml_conf)  # ML can raise, never silently lowers the heuristic
            if conf >= 0.45:
                sig = "multirotor_acoustic"
        # cross-cue: if a neighbor cued us, lower the reporting floor slightly
        import time
        floor = 0.35 if self.is_cued(time.time()) else 0.45
        if conf < floor:
            return None
        bearing = None
        if samples.ndim == 2 and samples.shape[1] >= 2 and self.mic_spacing_m > 0:
            bearing = bearing_from_2mic(samples[:, 0], samples[:, 1], self.sr,
                                        self.mic_spacing_m, self.array_heading_deg)
        return self.new_detection(
            sensor_type=self.sensor_type, signature_class=sig, confidence=round(conf, 3),
            bearing_deg=bearing, bearing_uncertainty_deg=(15.0 if bearing is not None else None),
            signal_level=round(20 * math.log10(feat["rms"]), 1), raw_features=feat,
        )

    def detect(self) -> Iterable[Detection]:
        frame = self._read_frame()
        if frame is None:
            return ()
        d = self.analyze(frame)
        return (d,) if d else ()


def _try_load_ml(model_path: Optional[str]):
    """Return a callable(samples, sr)->confidence, or None if no model is available.
    Kept optional so the heuristic is always the zero-dependency default."""
    if not model_path:
        return None
    try:
        import os
        if not os.path.exists(model_path):
            return None
        # Placeholder loader: real training/serialization lives in node-agent/ml/.
        # We import lazily so sklearn/torch are never hard requirements.
        import pickle
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        def infer(samples: np.ndarray, sr: int) -> float:
            feat = acoustic_features(samples, sr)
            X = np.array([[feat["harmonic_comb"], feat["spectral_flatness"],
                           feat["broadband_rotor"], feat["fundamental_hz"]]])
            try:
                return float(model.predict_proba(X)[0, 1])
            except Exception:
                return float(model.predict(X)[0])
        return infer
    except Exception:
        return None
