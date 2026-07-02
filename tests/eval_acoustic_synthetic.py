"""SYNTHETIC sanity-check of the acoustic DSP heuristic. Prints REAL precision/recall on a
labeled SYNTHETIC set (harmonic-comb 'drones' vs noise/tone/traffic-like negatives).

IMPORTANT: these numbers characterize the DETECTOR ON SYNTHETIC SIGNALS. They are NOT a claim
about real-world range or field accuracy — for that you must run train_acoustic.py on an open
dataset and the procedure in FIELD_TEST.md. This harness exists so the detector's discrimination
is measured and printed, never asserted.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "node-agent"))
from sensors.acoustic import acoustic_features, score_drone  # noqa: E402

SR = 48000
N = SR
THRESH = 0.45


def t():
    return np.arange(N) / SR


def drone(rng, f0):
    x = sum((1.0 / h) * np.sin(2 * math.pi * f0 * h * t()) for h in range(1, 7))
    x += 0.15 * rng.standard_normal(N)
    return x / (np.max(np.abs(x)) + 1e-9)


def white(rng):
    x = rng.standard_normal(N)
    return x / (np.max(np.abs(x)) + 1e-9)


def tone(f):
    return np.sin(2 * math.pi * f * t())


def traffic(rng):
    # low-frequency rumble + broadband, NO clean harmonic comb
    x = 0.6 * np.sin(2 * math.pi * 40 * t()) + rng.standard_normal(N)
    x = np.cumsum(x)  # pink-ish
    return x / (np.max(np.abs(x)) + 1e-9)


def run():
    rng = np.random.default_rng(7)
    y_true, y_pred = [], []
    # positives
    for f0 in (60, 80, 100, 120, 140, 170, 200, 230):
        for _ in range(6):
            c, _ = score_drone(acoustic_features(drone(rng, f0 + rng.uniform(-8, 8)), SR))
            y_true.append(1); y_pred.append(1 if c >= THRESH else 0)
    # negatives
    for _ in range(24):
        c, _ = score_drone(acoustic_features(white(rng), SR)); y_true.append(0); y_pred.append(1 if c >= THRESH else 0)
    for f in (400, 800, 1500, 3000):
        for _ in range(4):
            c, _ = score_drone(acoustic_features(tone(f), SR)); y_true.append(0); y_pred.append(1 if c >= THRESH else 0)
    for _ in range(16):
        c, _ = score_drone(acoustic_features(traffic(rng), SR)); y_true.append(0); y_pred.append(1 if c >= THRESH else 0)

    tp = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 0)
    tn = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 0)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    print("=== Acoustic DSP heuristic — SYNTHETIC sanity-check (NOT a field claim) ===")
    print(f"positives={tp+fn}  negatives={tn+fp}  threshold={THRESH}")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"precision={prec:.3f}  recall={rec:.3f}  f1={f1:.3f}")
    return prec, rec, f1


def test_synthetic_eval_reasonable():
    prec, rec, f1 = run()
    # sanity floors only — the point is that the numbers are printed and honest
    assert prec >= 0.8, f"synthetic precision too low: {prec}"
    assert rec >= 0.8, f"synthetic recall too low: {rec}"


if __name__ == "__main__":
    run()
