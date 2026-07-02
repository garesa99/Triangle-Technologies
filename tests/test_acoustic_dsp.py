"""Acoustic DSP heuristic tests. Synthesizes signals to validate the ZERO-TRAINING detector
discriminates a propeller harmonic-comb from white noise, pure tones, and silence.

These are TEST FIXTURES (synthesized signals). They validate the detector's DSP; they NEVER
feed the live UI. On real hardware the same `analyze()` path runs on captured microphone audio.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "node-agent"))
from sensors.acoustic import acoustic_features, score_drone, gcc_phat  # noqa: E402

SR = 48000
DUR = 1.0
N = int(SR * DUR)
t = np.arange(N) / SR
rng = np.random.default_rng(42)


def synth_drone(f0=120.0, n_harm=6, broadband=0.15, snr=1.0):
    """Harmonic comb at f0 + overtones, plus broadband rotor noise. Mimics a multirotor."""
    sig = np.zeros(N)
    for h in range(1, n_harm + 1):
        sig += (1.0 / h) * np.sin(2 * math.pi * f0 * h * t)
    sig *= snr
    # broadband rotor noise, mid-band emphasized
    noise = rng.standard_normal(N)
    sig += broadband * noise
    return sig / (np.max(np.abs(sig)) + 1e-9)


def synth_white():
    x = rng.standard_normal(N)
    return x / (np.max(np.abs(x)) + 1e-9)


def synth_tone(f=1000.0):
    return np.sin(2 * math.pi * f * t)


def synth_silence():
    return 1e-4 * rng.standard_normal(N)


def test_drone_scores_higher_than_noise_and_tone():
    c_drone, sig = score_drone(acoustic_features(synth_drone(), SR))
    c_white, _ = score_drone(acoustic_features(synth_white(), SR))
    c_tone, _ = score_drone(acoustic_features(synth_tone(), SR))
    c_silence, _ = score_drone(acoustic_features(synth_silence(), SR))
    print(f"drone={c_drone:.3f} white={c_white:.3f} tone={c_tone:.3f} silence={c_silence:.3f}")
    assert c_drone > 0.45, f"drone should be detected, got {c_drone:.3f}"
    assert sig == "multirotor_acoustic"
    assert c_drone > c_white, "drone must beat white noise"
    assert c_drone > c_tone, "drone must beat a pure tone"
    assert c_drone > c_silence


def test_detects_across_fundamentals():
    for f0 in (70, 110, 160, 210):
        c, _ = score_drone(acoustic_features(synth_drone(f0=f0), SR))
        assert c > 0.4, f"f0={f0} gave {c:.3f}"


def test_gcc_phat_recovers_known_delay():
    # make two channels with a known integer-sample delay
    base = synth_drone(f0=130)
    delay = 12  # samples
    a = base
    b = np.roll(base, delay)
    tau = gcc_phat(a, b, SR, max_tau=0.01)
    est = tau * SR
    assert abs(est + delay) < 2 or abs(est - delay) < 2, f"expected +/-{delay}, got {est:.1f}"


def test_features_are_finite():
    f = acoustic_features(synth_drone(), SR)
    assert all(np.isfinite(v) for v in f.values())
    assert 0 <= f["spectral_flatness"] <= 1.01
