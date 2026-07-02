"""Train the OPTIONAL acoustic drone classifier on an open dataset.

The DSP heuristic (sensors/acoustic.py) is the zero-training default and always runs. This
script trains a small gradient-boosted classifier on the SAME features the heuristic computes,
so it plugs in with no new runtime deps beyond scikit-learn, and can only RAISE confidence.

Dataset (open, document which you used in FIELD_TEST/CAPABILITIES):
  - "DroneAudioDataset" (Al-Emadi et al.) — https://github.com/saraalemadi/DroneAudioDataset
  - or ESC-50 / UrbanSound8k negatives + any drone-audio positives you can license.

Expected layout:
  data/drone/*.wav      (positives)
  data/not_drone/*.wav  (negatives)

Usage:
  python train_acoustic.py --data ./data --out ../weights/acoustic_gbm.pkl
Prints REAL precision/recall on a held-out split — no inflated claims.
"""
from __future__ import annotations

import argparse
import glob
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sensors.acoustic import acoustic_features  # noqa: E402


def load_wav(path: str):
    import wave
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    if w.getnchannels() > 1:
        x = x[:: w.getnchannels()]
    x /= 32768.0
    return x, sr


def featurize(path: str):
    x, sr = load_wav(path)
    f = acoustic_features(x, sr)
    return [f["harmonic_comb"], f["spectral_flatness"], f["broadband_rotor"], f["fundamental_hz"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "weights", "acoustic_gbm.pkl"))
    args = ap.parse_args()

    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import precision_recall_fscore_support
    from sklearn.model_selection import train_test_split

    X, y = [], []
    for label, sub in ((1, "drone"), (0, "not_drone")):
        for wav in glob.glob(os.path.join(args.data, sub, "*.wav")):
            try:
                X.append(featurize(wav))
                y.append(label)
            except Exception as e:
                print(f"skip {wav}: {e}")
    if not X:
        raise SystemExit("no data found — see the expected layout in this file's docstring")

    X, y = np.array(X), np.array(y)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
    clf = GradientBoostingClassifier().fit(Xtr, ytr)
    pred = clf.predict(Xte)
    p, r, f1, _ = precision_recall_fscore_support(yte, pred, average="binary", zero_division=0)
    print(f"HELD-OUT  precision={p:.3f}  recall={r:.3f}  f1={f1:.3f}  n_test={len(yte)}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "wb") as fo:
        pickle.dump(clf, fo)
    print(f"saved -> {args.out}. Set sensors.acoustic.config.model_path to this file to enable.")


if __name__ == "__main__":
    main()
