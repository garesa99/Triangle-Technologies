# Optional acoustic ML

The **DSP heuristic in `sensors/acoustic.py` is the default** and needs no training, no model,
and no extra dependencies. This directory is an *optional* upgrade path.

- `train_acoustic.py` trains a small gradient-boosted classifier on the **same features** the
  heuristic computes, using an **open** drone-audio dataset (e.g.
  [DroneAudioDataset](https://github.com/saraalemadi/DroneAudioDataset), or ESC-50/UrbanSound8k
  negatives with licensed drone positives).
- It prints **real** held-out precision/recall — record those numbers in `CAPABILITIES.md`.
  Do not ship inflated metrics.
- The trained model plugs in via `sensors.acoustic.config.model_path`. At runtime it can only
  **raise** confidence over the heuristic, never silently lower it.

Weights, if produced, live in `../weights/` (gitignored by default — commit only if small and
you have the right to distribute the training data's derived model).
