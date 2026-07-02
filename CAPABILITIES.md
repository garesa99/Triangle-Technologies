# CAPABILITIES — what each layer really does, and what it cannot

Honesty is the credibility. This is the document a serious evaluator reads first. Every claim
here is bounded by physics and by what the code actually implements.

## What the system IS
A mesh of low-cost passive nodes, built from commercially available components, that detects **uncooperative** drones (no Remote ID broadcast) by
signatures they cannot suppress — propeller **sound** and control/video **RF** — fuses those
detections across nodes, and localizes to an **honestly-labeled** tier (ray / ellipse / fix).

## Detection layers

### Acoustic (primary) — LIVE
- Detects the multirotor propeller **harmonic comb** + broadband rotor noise via a zero-training
  DSP heuristic (`node-agent/sensors/acoustic.py`). Optional GBM model on an open dataset.
- **Synthetic sanity-check** (`tests/eval_acoustic_synthetic.py`, printed, reproducible):
  precision **1.000**, recall **0.875**, F1 **0.933** on labeled synthetic signals.
  *This is a detector-discrimination number on synthetic data — NOT a field range/accuracy claim.*
- Bearing: only with a **2+ mic array** of known spacing (GCC-PHAT TDOA); a single 2-mic baseline
  is front/back ambiguous. Single mic → no bearing (honest null).
- **Cannot**: hear a gliding/idling fixed-wing, detect through strong wind or high ambient noise,
  or reach far — acoustic range for a small quad is realistically tens to low-hundreds of metres
  and degrades fast with wind and background noise. Validate real range with `FIELD_TEST.md`.

### RF 2.4 / 5.8 GHz — LIVE ONLY IF BAND-CAPABLE HARDWARE PRESENT
- Energy/anomaly detection of control (RC) and FPV video links above a rolling WiFi baseline.
- **Band-gated**: enabled only if the SDR can actually tune the band. Plain RTL-SDR (~≤1.7 GHz)
  → disabled by design. HackRF / RTL-SDR+upconverter → enabled.
- **Cannot** be certain: WiFi, Bluetooth, and other 2.4 GHz traffic share the band. Output is a
  probability with the baseline shown, never a binary "drone". Digital/frequency-hopping links
  and fully autonomous drones flying a pre-programmed mission with the RF link off are hard/impossible here.

### Remote ID — LIVE (cooperative, friend-or-foe)
- Reads the legally-mandated ASTM F3411 / EU broadcast via an ESP32 OpenDroneID receiver. High
  confidence, carries serial/operator/position. A physical detection with **no** matching Remote
  ID is what flags a target **uncooperative**.
- **Cannot** see a drone that (illegally) does not broadcast — which is exactly why the acoustic
  and RF layers exist. Remote ID is the friend filter, not the detector.

### GNSS — LIVE (health, not a drone sensor)
- Provides node position, the **PPS time discipline** that gates PRECISE fixes, and jam/spoof
  indicators. A jammed node near a detection is itself intelligence.

### PIR / seismic / magnetometer — STUBS
- Plugin path proven (manifest + probe + TODO detect). Not detectors yet; they exist to show a
  new sensor is one file with no brain change.

## Localization — tiered and enforced in code
- **BEARING_ONLY**: one node, one bearing → a ray. No position is drawn.
- **COARSE_FIX**: 2+ concurrent detections → bearing intersection or signal-weighted centroid →
  an **uncertainty ellipse**, never a bare point.
- **PRECISE_FIX**: 3+ nodes with **GNSS-PPS** timestamps → TDOA multilateration. The code
  **refuses** precise on NTP/system clocks and downgrades to COARSE (tested:
  `tests/test_brain_fusion.py::test_precise_requires_pps_else_downgrades`). On synthetic geometry,
  TDOA lands within ~80 m and bearing intersection within ~150 m in the test fixtures.

## Threat score — decomposable, never a bare number
`signature_confidence × corroboration × uncooperative_bonus × geofence_proximity × approach_vector`,
every factor stored and shown. Unknown factors default to neutral (1.0) so absence of a geofence
never silently inflates or deflates a score.

## Known limitations (say them out loud)
- Detection is **probabilistic and range-limited**. Wind, ambient noise, and RF congestion reduce it.
- A silent, gliding, or RF-dark autonomous drone is the hard case for a passive system — this is a
  known gap, not a solved problem.
- The mesh needs multicast **or** broadcast on the LAN for zero-config discovery; locked-down APs
  may require a wired switch / dedicated AP.
- Field range/accuracy numbers are **not** claimed here — run `FIELD_TEST.md` with a real drone.
